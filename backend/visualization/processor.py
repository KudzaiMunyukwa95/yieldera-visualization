"""
Main visualization processor
Handles GEE analysis and cartographic generation
"""

import ee
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from datetime import datetime, timedelta
import os
import logging
import tempfile
import requests
import json
from typing import Dict, List, Optional, Tuple, Callable

from ..config import settings

class VisualizationProcessor:
    """Main processor for GEE analysis and cartographic generation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        self.initialize_gee()
    
    def initialize_gee(self):
        """Initialize Google Earth Engine"""
        try:
            if settings.gee_config:
                # Use proven initialization pattern from gee_ndvi_generator.py
                # key_data MUST be a JSON string, not a dict object
                credentials = ee.ServiceAccountCredentials(
                    email=settings.gee_config.get("client_email"),
                    key_data=json.dumps(settings.gee_config)
                )
                ee.Initialize(credentials)
                self.is_initialized = True
                self.logger.info("✅ Google Earth Engine initialized successfully")
            else:
                self.logger.warning("⚠️ No GEE credentials provided")
                self.is_initialized = False
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Google Earth Engine: {e}")
            self.is_initialized = False
    
    def process_job(self, job_id: str, job_data: Dict, progress_callback: Callable = None) -> Dict:
        """Main entry point for processing visualization jobs"""
        
        try:
            if not self.is_initialized:
                raise Exception("Google Earth Engine not initialized")
            
            # Extract parameters
            region_name = job_data['region_name']
            geometry = job_data['geometry']
            start_date = job_data['start_date']
            end_date = job_data['end_date']
            analysis_type = job_data['analysis_type']
            
            self.logger.info(f"🚀 Starting visualization job {job_id} for {region_name}")
            
            # Update progress
            if progress_callback:
                progress_callback(10, "Converting geometry and loading data...")
            
            # Convert GeoJSON geometry to EE geometry
            ee_geometry = ee.Geometry(geometry)
            
            # Run GEE analysis
            gee_result = self.run_gee_analysis(
                ee_geometry, start_date, end_date, analysis_type, progress_callback
            )
            
            if not gee_result['success']:
                raise Exception(gee_result['error'])
            
            # Update progress
            if progress_callback:
                progress_callback(70, "Generating professional cartography...")
            
            # Generate cartographic visualization
            map_result = self.generate_cartography(
                gee_result['data'], 
                gee_result['extent'],
                region_name,
                start_date,
                end_date,
                gee_result['statistics'],
                analysis_type
            )
            
            # Save files
            output_paths = self.save_outputs(job_id, map_result, gee_result)
            
            # Update progress
            if progress_callback:
                progress_callback(100, "Processing completed successfully")
            
            return {
                'success': True,
                'statistics': gee_result['statistics'],
                'map_image_path': output_paths['map_image'],
                'export_paths': output_paths,
                'extent': gee_result['extent']
            }
            
        except Exception as e:
            self.logger.error(f"❌ Job {job_id} failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def run_gee_analysis(self, geometry: ee.Geometry, start_date: str, end_date: str, 
                        analysis_type: str, progress_callback: Callable = None) -> Dict:
        """Execute GEE analysis for soil moisture anomaly"""
        
        try:
            if progress_callback:
                progress_callback(15, "Loading ERA5-Land satellite data...")
            
            # Load ERA5-Land data
            era5_land = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
                         .select(['volumetric_soil_water_layer_1']) \
                         .filterBounds(geometry)
            
            self.logger.info(f"ERA5-Land collection size: {era5_land.size().getInfo()}")
            
            if progress_callback:
                progress_callback(25, "Processing current period data...")
            
            # Current period analysis
            current_period = era5_land \
                .filterDate(start_date, end_date) \
                .mean() \
                .clip(geometry)
            
            if progress_callback:
                progress_callback(35, "Calculating historical baseline...")
            
            # Historical baseline calculation
            baseline = self.calculate_baseline(era5_land, start_date, end_date, geometry)
            
            if progress_callback:
                progress_callback(45, "Computing anomalies...")
            
            # Calculate anomalies
            if analysis_type == 'anomaly':
                result_image = current_period.subtract(baseline)
            elif analysis_type == 'percentage':
                result_image = current_period.subtract(baseline).divide(baseline).multiply(100)
            elif analysis_type == 'absolute':
                result_image = current_period
            else:
                result_image = current_period.subtract(baseline)  # Default to anomaly
            
            if progress_callback:
                progress_callback(55, "Calculating statistics...")
            
            # Calculate comprehensive statistics
            statistics = self.calculate_statistics(current_period, baseline, result_image, geometry)
            
            if progress_callback:
                progress_callback(65, "Preparing visualization data...")
            
            # Get data for visualization
            extent = self.get_geometry_bounds(geometry)
            data_array = self.export_image_data(result_image, geometry)
            
            return {
                'success': True,
                'data': data_array,
                'extent': extent,
                'statistics': statistics,
                'current_image': current_period,
                'baseline_image': baseline,
                'result_image': result_image
            }
            
        except Exception as e:
            self.logger.error(f"GEE analysis failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def calculate_baseline(self, collection: ee.ImageCollection, start_date: str, 
                          end_date: str, geometry: ee.Geometry) -> ee.Image:
        """Calculate historical baseline for same calendar period"""
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Historical years (2015-2024)
        baseline_years = list(range(2015, 2025))
        
        # Filter for same calendar period in baseline years
        baseline = collection \
            .filter(ee.Filter.calendarRange(2015, 2024, 'year')) \
            .filter(ee.Filter.calendarRange(start_dt.month, end_dt.month, 'month'))
        
        # If spanning multiple months, add day filtering
        if start_dt.month == end_dt.month:
            baseline = baseline.filter(ee.Filter.calendarRange(start_dt.day, end_dt.day, 'day_of_month'))
        
        return baseline.mean().clip(geometry)
    
    def calculate_statistics(self, current: ee.Image, baseline: ee.Image, 
                           anomaly: ee.Image, geometry: ee.Geometry) -> Dict:
        """Calculate comprehensive statistics"""
        
        # Anomaly statistics
        anomaly_stats = anomaly.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.minMax().combine(
                    reducer2=ee.Reducer.stdDev(),
                    sharedInputs=True
                ),
                sharedInputs=True
            ),
            geometry=geometry,
            scale=10000,
            maxPixels=1e9
        ).getInfo()
        
        # Current period statistics
        current_stats = current.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10000,
            maxPixels=1e9
        ).getInfo()
        
        # Baseline statistics
        baseline_stats = baseline.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10000,
            maxPixels=1e9
        ).getInfo()
        
        # Calculate percentage change
        current_mean = current_stats.get('volumetric_soil_water_layer_1', 0)
        baseline_mean = baseline_stats.get('volumetric_soil_water_layer_1', 0)
        percentage_change = ((current_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0
        
        return {
            'mean_anomaly': anomaly_stats.get('volumetric_soil_water_layer_1_mean', 0),
            'min_anomaly': anomaly_stats.get('volumetric_soil_water_layer_1_min', 0),
            'max_anomaly': anomaly_stats.get('volumetric_soil_water_layer_1_max', 0),
            'std_anomaly': anomaly_stats.get('volumetric_soil_water_layer_1_stdDev', 0),
            'current_mean': current_mean,
            'baseline_mean': baseline_mean,
            'percentage_change': percentage_change
        }
    
    def get_geometry_bounds(self, geometry: ee.Geometry) -> List[float]:
        """Get bounding box from EE geometry"""
        
        bounds = geometry.bounds().getInfo()['coordinates'][0]
        
        # Extract min/max coordinates
        lons = [coord[0] for coord in bounds]
        lats = [coord[1] for coord in bounds]
        
        return [min(lons), max(lons), min(lats), max(lats)]
    
    def export_image_data(self, image: ee.Image, geometry: ee.Geometry) -> np.ndarray:
        """Export EE image to NumPy array"""
        
        # Get download URL
        url = image.getDownloadURL({
            'region': geometry,
            'scale': 10000,
            'format': 'GEO_TIFF'
        })
        
        # Download and convert to numpy
        response = requests.get(url)
        
        with tempfile.NamedTemporaryFile(suffix='.tif') as tmp_file:
            tmp_file.write(response.content)
            tmp_file.flush()
            
            # Read with rasterio
            import rasterio
            with rasterio.open(tmp_file.name) as src:
                data = src.read(1)
                
        return data
    
    def generate_cartography(self, data: np.ndarray, extent: List[float], 
                           region_name: str, start_date: str, end_date: str,
                           statistics: Dict, analysis_type: str) -> Dict:
        """Generate professional cartographic visualization"""
        
        try:
            # Set up professional stylings
            plt.style.use('default')
            # Optimization: Use smaller canvas and lower DPI to prevent OOM on free tier
            # Previous: (16, 12) @ 400 DPI = ~30MP image (Too big for 512MB RAM)
            # New: (10, 8) @ 150 DPI = ~1.2MP image (Safe)
            fig = plt.figure(figsize=(10, 8), dpi=150, facecolor='white')
            
            # Create map projection
            proj = ccrs.PlateCarree()
            ax = fig.add_subplot(111, projection=proj)
            
            # Adjust margins for professional look
            plt.subplots_adjust(left=0.05, right=0.95, top=0.90, bottom=0.10)
            
            # Set map extent
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            
            # Add base features
            self.add_base_features(ax)
            
            # Create color scheme
            cmap, norm = self.create_color_scheme(analysis_type)
            
            # Plot the data with interpolation for smoother look
            im = ax.imshow(data, 
                          extent=extent,
                          transform=ccrs.PlateCarree(),
                          cmap=cmap,
                          norm=norm,
                          alpha=0.9,
                          interpolation='bilinear') # Upgrade: smoother interpolation
            
            # Add cartographic elements
            self.add_title_block(fig, region_name, start_date, end_date, analysis_type)
            self.add_legend(fig, cmap, norm, analysis_type)
            self.add_statistics_box(fig, statistics, analysis_type) # Upgrade: New stats box
            # self.add_inset_map(fig, extent) # Disabled for performance optimization on free tier
            
            self.add_north_arrow(ax, extent)
            self.add_scale_bar(ax, extent)
            self.add_attribution(fig)
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, 
                       format='png',
                       dpi=150, # Optimization: Safe DPI
                       bbox_inches='tight',
                       facecolor='white',
                       edgecolor='none')
            buffer.seek(0)
            
            # Convert to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            plt.close(fig)
            
            return {
                'success': True,
                'image_buffer': buffer,
                'image_base64': image_base64
            }
            
        except Exception as e:
            self.logger.error(f"Cartography generation failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_color_scheme(self, analysis_type: str) -> Tuple:
        """Create professional color scheme for different analysis types"""
        
        if analysis_type == 'anomaly':
            # Upgrade: Enhanced drought color palette (High Contrast)
            colors = [
                '#800000',  # Extreme Drought (darker red)
                '#B22222',  # Severe Drought (fire brick)
                '#DC143C',  # Moderate Drought (crimson)
                '#FF4500',  # Light Drought (orange red)
                '#FFA500',  # Below Normal (orange)
                '#FFD700',  # Near Normal (gold)
                '#FFFFFF',  # Normal (white)
                '#E0F6FF',  # Above Normal (very light blue)
                '#87CEEB',  # Much Above Normal (sky blue)
                '#4169E1',  # Exceptional (royal blue)
                '#000080'   # Extreme Wet (navy)
            ]
            # Updated boundaries for clearer separation
            boundaries = [-0.08, -0.05, -0.03, -0.02, -0.01, 0.00, 0.01, 0.02, 0.03, 0.05, 0.08]
            
        elif analysis_type == 'percentage':
            colors = ['#8B0000', '#FF4500', '#FFD700', '#FFFFFF', '#87CEEB', '#4169E1', '#000080']
            boundaries = [-50, -25, -10, 0, 10, 25, 50]
            
        else:  # absolute
            colors = ['#8B4513', '#CD853F', '#F4A460', '#F5DEB3', '#E0FFFF', '#B0E0E6', '#4682B4']
            boundaries = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
        
        cmap = ListedColormap(colors)
        # Ensure boundaries match color count + 1
        if len(boundaries) < len(colors) + 1:
            # Extend boundaries if needed (simple linear extension for now)
            while len(boundaries) < len(colors) + 1:
                boundaries.append(boundaries[-1] + 0.05)
                
        norm = BoundaryNorm(boundaries, cmap.N)
        return cmap, norm
    
    def add_title_block(self, fig, region_name: str, start_date: str, end_date: str, analysis_type: str):
        """Add professional title block with improved hierarchy"""
        
        # Format date range
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        date_str = f"{start_dt.strftime('%d %b')} - {end_dt.strftime('%d %b %Y')}"
        
        # Main title - Larger and bolder
        title = f"{region_name} Soil Moisture Analysis"
        fig.suptitle(title, fontsize=24, fontweight='900', y=0.97, ha='center', color='#1a1a1a')
        
        # Subtitle with date and type
        subtitle = f"{analysis_type.title().replace('_', ' ')} Assessment | Period: {date_str}"
        fig.text(0.5, 0.94, subtitle, ha='center', fontsize=16, color='#404040')
        
        # Technical subtitle
        fig.text(0.5, 0.92, "Data Source: ERA5-Land Satellite Observations (0-7cm Soil depth)",
                ha='center', fontsize=12, style='italic', color='#666666')

    def add_statistics_box(self, fig, statistics: Dict, analysis_type: str):
        """Add professional statistics summary box"""
        
        stats_ax = fig.add_axes([0.65, 0.05, 0.30, 0.15]) # Bottom right
        stats_ax.axis('off')
        
        # Create background box
        rect = mpatches.FancyBboxPatch((0, 0), 1, 1,
                                     boxstyle="round,pad=0.05",
                                     ec="#333333", fc="white", 
                                     alpha=0.9, transform=stats_ax.transAxes,
                                     linewidth=1.5, zorder=1)
        stats_ax.add_patch(rect)
        
        # Title
        stats_ax.text(0.5, 0.85, "REGIONAL ANALYSIS SUMMARY", 
                     ha='center', va='center', fontsize=12, fontweight='bold',
                     color='white', bbox=dict(facecolor='#333333', edgecolor='none', pad=4.0))
        
        # Metrics
        mean_val = statistics.get('mean_anomaly', 0)
        percentage = statistics.get('percentage_change', 0)
        
        # Determine risk level
        if percentage < -20:
            risk_level = "CRITICAL DROUGHT"
            risk_color = "#8B0000"
        elif percentage < -10:
            risk_level = "HIGH RISK"
            risk_color = "#FF4500"
        elif percentage < 0:
            risk_level = "MODERATE WATCH"
            risk_color = "#FFA500"
        elif percentage < 10:
            risk_level = "NORMAL CONDITIONS"
            risk_color = "#2E8B57"
        else:
            risk_level = "FAVORABLE MOISTURE"
            risk_color = "#006400"
            
        # Display metrics
        stats_ax.text(0.1, 0.65, f"Mean Anomaly:", fontsize=11, fontweight='bold')
        stats_ax.text(0.9, 0.65, f"{mean_val:+.3f} m³/m³", fontsize=11, ha='right')
        
        stats_ax.text(0.1, 0.45, f"Departure:", fontsize=11, fontweight='bold')
        stats_ax.text(0.9, 0.45, f"{percentage:+.1f}%", fontsize=11, ha='right', 
                     color='red' if percentage < 0 else 'green')
        
        stats_ax.text(0.1, 0.20, f"Risk Status:", fontsize=11, fontweight='bold')
        stats_ax.text(0.9, 0.20, risk_level, fontsize=11, ha='right', 
                     fontweight='bold', color=risk_color)

    def add_legend(self, fig, cmap, norm, analysis_type: str):
        """Add professional legend with thresholds"""
        
        # Adjust legend position to not overlap with map or stats
        legend_ax = fig.add_axes([0.03, 0.05, 0.25, 0.35]) 
        legend_ax.axis('off')
        
        # Legend Title
        title = "Soil Moisture\nAnomaly (m³/m³)" if analysis_type == 'anomaly' else "Analysis Scale"
        legend_ax.text(0.0, 1.0, title, va='top', ha='left', fontsize=14, fontweight='bold')
        
        # Define categories with quantitative thresholds labels
        if analysis_type == 'anomaly':
            items = [
                ('> +0.08', 'Extreme Wet', '#000080'),
                ('+0.05 to +0.08', 'Exceptional', '#4169E1'),
                ('+0.03 to +0.05', 'Much Above', '#87CEEB'),
                ('+0.02 to +0.03', 'Above Normal', '#E0F6FF'),
                ('-0.01 to +0.01', 'Normal Range', '#FFFFFF'),
                ('-0.02 to -0.01', 'Below Normal', '#FFD700'),
                ('-0.03 to -0.02', 'Moderate Drought', '#FF4500'),
                ('-0.05 to -0.03', 'Severe Drought', '#B22222'),
                ('< -0.08', 'Extreme Drought', '#800000'),
            ]
        else:
            items = [('High', 'High', '#000080'), ('Low', 'Low', '#8B0000')] # Fallback
            
        # Draw legend items
        y_start = 0.85
        spacing = 0.09
        
        for i, (threshold, label, color) in enumerate(items):
            y_pos = y_start - (i * spacing)
            
            # Color box
            rect = plt.Rectangle((0.0, y_pos), 0.15, 0.06, 
                               fc=color, ec='black', lw=0.5)
            legend_ax.add_patch(rect)
            
            # Label
            legend_ax.text(0.20, y_pos + 0.03, label, 
                          va='center', fontsize=10, fontweight='bold')
            
            # Threshold
            legend_ax.text(0.20, y_pos - 0.02, threshold, 
                          va='top', fontsize=9, color='#444444')

    def add_inset_map(self, fig, extent):
        """Add inset map showing location in Africa"""
        try:
            # Create inset axes at top right
            inset_ax = fig.add_axes([0.75, 0.70, 0.2, 0.2], projection=ccrs.PlateCarree())
            
            # Add Africa context
            inset_ax.set_extent([-20, 55, -40, 40], crs=ccrs.PlateCarree())
            inset_ax.add_feature(cfeature.LAND, facecolor='#E0E0E0')
            inset_ax.add_feature(cfeature.OCEAN, facecolor='#F0F8FF')
            inset_ax.add_feature(cfeature.BORDERS, linewidth=0.5, color='white')
            
            # Highlight current extent (Zimbabwe region)
            # Create a box for the current extent
            lons = [extent[0], extent[1], extent[1], extent[0], extent[0]]
            lats = [extent[2], extent[2], extent[3], extent[3], extent[2]]
            
            inset_ax.plot(lons, lats, color='red', linewidth=2, transform=ccrs.PlateCarree())
            
            # Add simple border
            for spine in inset_ax.spines.values():
                spine.set_edgecolor('black')
                spine.set_linewidth(1)
                
        except Exception as e:
            self.logger.warning(f"Could not add inset map: {e}")

    def add_base_features(self, ax):
        """Add base map features with optimized resolution"""
        # Use 110m resolution (coarse) for fastest processing on free tier
        land_110m = cfeature.NaturalEarthFeature('physical', 'land', '110m',
                                              edgecolor='none', facecolor='#F5F5F5')
        ocean_110m = cfeature.NaturalEarthFeature('physical', 'ocean', '110m',
                                               edgecolor='none', facecolor='#E0F6FF')
        borders_110m = cfeature.NaturalEarthFeature('cultural', 'admin_0_countries', '110m',
                                                 edgecolor='#444444', facecolor='none', linewidth=0.5)
        
        ax.add_feature(land_110m)
        ax.add_feature(ocean_110m)
        ax.add_feature(borders_110m)
        # Coastline 110m is often essentially the same as borders for land/ocean
        
        # Add gridlines
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', 
                         alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        gl.xlabel_style = {'size': 10, 'color': 'gray'}
        gl.ylabel_style = {'size': 10, 'color': 'gray'}

    def add_north_arrow(self, ax, extent):
        """Add north arrow to map"""
        x, y, arrow_length = 0.95, 0.95, 0.1
        ax.annotate('N', xy=(x, y), xytext=(x, y-arrow_length),
                   arrowprops=dict(facecolor='black', width=5, headwidth=15),
                   ha='center', va='center', fontsize=12,
                   xycoords=ax.transAxes)

    def add_scale_bar(self, ax, extent):
        """Add scale bar to map"""
        try:
            from matplotlib_scalebar.scalebar import ScaleBar
            # Approx 1 degree lat = 111km. This is a rough approx for scale bar.
            scalebar = ScaleBar(111319, location='lower right', pad=0.5) 
            ax.add_artist(scalebar)
        except ImportError:
            pass # Skip if library missing

    def add_attribution(self, fig):
        """Add professional attribution line"""
        text = f"Generated by Yieldera Intelligence Platform | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        fig.text(0.98, 0.02, text, ha='right', fontsize=9, color='#666666', style='italic')
    
    def save_outputs(self, job_id: str, map_result: Dict, gee_result: Dict) -> Dict:
        """Save visualization outputs to storage"""
        
        output_paths = {}
        
        # Ensure storage directory exists
        os.makedirs(settings.VISUALIZATION_STORAGE_PATH, exist_ok=True)
        
        # Save PNG image
        if map_result['success'] and 'image_buffer' in map_result:
            png_path = os.path.join(settings.VISUALIZATION_STORAGE_PATH, f"{job_id}_map.png")
            
            with open(png_path, 'wb') as f:
                f.write(map_result['image_buffer'].getvalue())
            
            output_paths['map_image'] = png_path
            
            self.logger.info(f"✅ Saved map image: {png_path}")
        
        # Save statistics JSON
        stats_path = os.path.join(settings.VISUALIZATION_STORAGE_PATH, f"{job_id}_statistics.json")
        with open(stats_path, 'w') as f:
            json.dump(gee_result['statistics'], f, indent=2)
        
        output_paths['statistics'] = stats_path
        
        # Save metadata
        metadata = {
            'job_id': job_id,
            'generated_at': datetime.utcnow().isoformat(),
            'extent': gee_result['extent'],
            'statistics': gee_result['statistics']
        }
        
        metadata_path = os.path.join(settings.VISUALIZATION_STORAGE_PATH, f"{job_id}_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        output_paths['metadata'] = metadata_path
        
        return output_paths
