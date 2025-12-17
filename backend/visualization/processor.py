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
        """Generate professional cartographic visualization with two-panel layout"""
        
        try:
            # Set up professional styling
            plt.style.use('default')
            fig = plt.figure(figsize=(16, 10), dpi=300, facecolor='white')
            
            # Create two-panel layout: Map (70%) + Info Sidebar (30%)
            from matplotlib.gridspec import GridSpec
            gs = GridSpec(1, 2, figure=fig, width_ratios=[7, 3], wspace=0.02)
            
            # Map panel (left)
            proj = ccrs.PlateCarree()
            ax_map = fig.add_subplot(gs[0], projection=proj)
            
            # Information sidebar (right)
            ax_info = fig.add_subplot(gs[1])
            ax_info.axis('off')
            
            # Set map extent
            ax_map.set_extent(extent, crs=ccrs.PlateCarree())
            
            # Add base features to map
            self.add_base_features(ax_map)
            
            # Create color scheme
            cmap, norm = self.create_color_scheme(analysis_type)
            
            # Plot the data on map
            im = ax_map.imshow(data, 
                          extent=extent,
                          transform=ccrs.PlateCarree(),
                          cmap=cmap,
                          norm=norm,
                          alpha=0.8,
                          interpolation='nearest')
            
            # Add map title (only element on map besides the data)
            self.add_map_title(ax_map, region_name, start_date, end_date)
            
            # Add cartographic elements to map
            self.add_north_arrow(ax_map, extent)
            self.add_scale_bar(ax_map, extent)
            
            # Add all information to sidebar
            self.add_information_sidebar(ax_info, region_name, start_date, end_date, 
                                        statistics, analysis_type, cmap, norm)
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, 
                       format='png',
                       dpi=300,
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
            # Drought to wet color scheme
            colors = [
                '#8B0000',  # Extreme Drought (dark red)
                '#B22222',  # Severe Drought 
                '#DC143C',  # Severe Drought (crimson)
                '#FF6347',  # Moderate Drought (tomato)
                '#FF8C00',  # Moderate Drought (dark orange)
                '#FFD700',  # Light Drought (gold)
                '#FFFF00',  # Light Drought (yellow)
                '#F0F8FF',  # Near Normal (alice blue)
                '#FFFFFF',  # Normal (white)
                '#E0FFFF',  # Above Normal (light cyan)
                '#B0E0E6',  # Above Normal (powder blue)
                '#87CEEB',  # Much Above Normal (sky blue)
                '#4682B4',  # Much Above Normal (steel blue)
                '#1E90FF',  # Exceptional (dodger blue)
                '#0000CD',  # Exceptional (medium blue)
                '#000080'   # Exceptional (navy)
            ]
            boundaries = [-0.08, -0.05, -0.03, -0.02, -0.01, 0.00, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15]
            
        elif analysis_type == 'percentage':
            # Percentage change color scheme
            colors = ['#8B0000', '#FF6347', '#FFD700', '#FFFFFF', '#87CEEB', '#4682B4', '#000080']
            boundaries = [-50, -25, -10, 0, 10, 25, 50]
            
        else:  # absolute
            # Absolute moisture color scheme
            colors = ['#8B4513', '#CD853F', '#F4A460', '#F5DEB3', '#E0FFFF', '#B0E0E6', '#4682B4']
            boundaries = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
        
        cmap = ListedColormap(colors)
        norm = BoundaryNorm(boundaries, cmap.N)
        
        return cmap, norm
    
    def add_base_features(self, ax):
        """Add base cartographic features"""
        
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5, color='gray')
        ax.add_feature(cfeature.BORDERS, linewidth=0.8, color='black')
        ax.add_feature(cfeature.RIVERS, linewidth=0.3, color='blue', alpha=0.6)
        ax.add_feature(cfeature.LAKES, linewidth=0.3, color='blue', alpha=0.3)
        
        # Add grid lines
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                         linewidth=0.3, color='gray', alpha=0.7, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
    
    def add_map_title(self, ax_map, region_name: str, start_date: str, end_date: str):
        """Add clean title above map"""
        
        # Format date range
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_dt.year == end_dt.year:
            if start_dt.month == end_dt.month:
                date_str = f"{start_dt.strftime('%b %d')}-{end_dt.strftime('%d, %Y')}"
            else:
                date_str = f"{start_dt.strftime('%b %d')} to {end_dt.strftime('%b %d, %Y')}"
        else:
            date_str = f"{start_dt.strftime('%b %d, %Y')} to {end_dt.strftime('%b %d, %Y')}"
        
        # Main title - only element above map
        title = f"{region_name} (Complete Country) Soil Moisture Anomaly – {date_str}"
        ax_map.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    def add_information_sidebar(self, ax_info, region_name: str, start_date: str, 
                               end_date: str, statistics: Dict, analysis_type: str,
                               cmap, norm):
        """Add organized information sidebar with all metadata"""
        
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)
        
        # Section 1: Data Source Header (top)
        ax_info.text(0.5, 0.98, 'DATA SOURCE', ha='center', va='top', 
                    fontsize=11, weight='bold', style='italic')
        ax_info.text(0.5, 0.94, 'ERA5-Land Satellite\nObservations\n(0-7cm soil layer)', 
                    ha='center', va='top', fontsize=9, style='italic')
        
        # Section 2: Regional Statistics Box
        from matplotlib.patches import FancyBboxPatch
        stats_box = FancyBboxPatch((0.05, 0.78), 0.9, 0.13, 
                                   boxstyle="round,pad=0.01", 
                                   edgecolor='black', facecolor='#f0f0f0', 
                                   linewidth=1.5)
        ax_info.add_patch(stats_box)
        
        ax_info.text(0.5, 0.88, 'REGIONAL STATISTICS', ha='center', va='top',
                    fontsize=10, weight='bold')
        
        percentage = statistics.get('percentage_change', 0)
        mean_anomaly = statistics.get('mean_anomaly', 0)
        
        ax_info.text(0.5, 0.845, f"Mean: {mean_anomaly:.3f} m³/m³", 
                    ha='center', va='top', fontsize=10, weight='bold')
        ax_info.text(0.5, 0.81, f"Change: {percentage:+.1f}% from normal", 
                    ha='center', va='top', fontsize=9,
                    color='red' if percentage < 0 else 'blue')
        
        # Section 3: Legend (largest section)
        ax_info.text(0.5, 0.74, 'LEGEND', ha='center', va='top',
                    fontsize=11, weight='bold')
        
        # Legend title
        titles = {
            'anomaly': 'Soil Moisture Difference\nfrom Normal (m³/m³)',
            'percentage': 'Percentage Change\nfrom Normal (%)',
            'absolute': 'Absolute Soil Moisture (m³/m³)'
        }
        
        ax_info.text(0.5, 0.70, titles.get(analysis_type, 'Soil Moisture Analysis'),
                    ha='center', va='top', fontsize=8, style='italic')
        
        # Legend categories
        if analysis_type == 'anomaly':
            legend_items = [
                ('Exceptional Above Normal', '#000080'),
                ('Much Above Normal', '#4682B4'),
                ('Above Normal', '#87CEEB'),
                ('Normal Conditions', '#FFFFFF'),
                ('Below Normal', '#FFD700'),
                ('Much Below Normal', '#FF6347'),
                ('Extreme Drought', '#8B0000')
            ]
        else:
            legend_items = [
                ('High', '#000080'),
                ('Above Average', '#4682B4'),
                ('Average', '#FFFFFF'),
                ('Below Average', '#FFD700'),
                ('Low', '#8B0000')
            ]
        
        y_positions = np.linspace(0.64, 0.28, len(legend_items))
        
        for (label, color), y_pos in zip(legend_items, y_positions):
            # Color patch
            rect = plt.Rectangle((0.08, y_pos-0.015), 0.12, 0.025,
                               facecolor=color, edgecolor='black', linewidth=0.8)
            ax_info.add_patch(rect)
            
            # Label
            ax_info.text(0.25, y_pos, label, va='center', ha='left', fontsize=9)
        
        # Section 4: Processing Information
        ax_info.text(0.5, 0.22, 'PROCESSING', ha='center', va='top',
                    fontsize=10, weight='bold')
        ax_info.text(0.5, 0.18, 'Google Earth Engine', ha='center', va='top', fontsize=8)
        ax_info.text(0.5, 0.15, 'Yieldera Platform', ha='center', va='top', fontsize=8)
        
        # Section 5: Attribution (bottom)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        ax_info.text(0.5, 0.08, 'GENERATED', ha='center', va='top',
                    fontsize=9, weight='bold')
        ax_info.text(0.5, 0.05, timestamp, ha='center', va='top', 
                    fontsize=7, style='italic')
        ax_info.text(0.5, 0.02, 'Analysis by Yieldera Platform', ha='center', va='top',
                    fontsize=7, style='italic')
    
    def add_north_arrow(self, ax, extent: List[float]):
        """Add north arrow"""
        
        x_range = extent[1] - extent[0]
        y_range = extent[3] - extent[2]
        
        arrow_x = extent[1] - x_range * 0.08
        arrow_y = extent[3] - y_range * 0.08
        
        ax.annotate('N', xy=(arrow_x, arrow_y), xytext=(arrow_x, arrow_y - y_range * 0.05),
                   ha='center', va='center', fontsize=12, fontweight='bold',
                   arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    
    def add_scale_bar(self, ax, extent: List[float]):
        """Add scale bar"""
        try:
            from matplotlib_scalebar.scalebar import ScaleBar
            scalebar = ScaleBar(111320, location='lower right', box_alpha=0.8, color='black')
            ax.add_artist(scalebar)
        except ImportError:
            # If matplotlib-scalebar not available, skip scale bar
            pass
    

    
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
