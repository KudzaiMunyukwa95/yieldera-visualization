"""
Main visualization processor
Handles GEE analysis and cartographic generation
"""

import os
import logging
from ..config import settings

# CRITICAL: Configure cartopy cache directory before ANY OTHER cartopy/matplotlib imports
# This ensures that global constants in cartopy.feature use the correct path
cartopy_data_dir = getattr(settings, 'CARTOPY_USER_DATADIR', None)
if cartopy_data_dir:
    import cartopy
    # Set both the config object and the environment variable for sub-processes
    cartopy.config['data_dir'] = cartopy_data_dir
    os.environ['CARTOPY_USER_DATADIR'] = cartopy_data_dir
    os.makedirs(cartopy_data_dir, exist_ok=True)
    logging.info(f"📍 Global Cartopy path locked to: {cartopy_data_dir}")

import ee
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import tempfile
from datetime import datetime, timedelta
import requests
import json
from typing import Dict, List, Optional, Tuple, Callable

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
            region_type = job_data.get('region_type', 'custom')
            
            self.logger.info(f"🚀 Starting visualization job {job_id} for {region_name} ({region_type})")
            
            # Update progress
            if progress_callback:
                progress_callback(10, "Converting geometry and loading data...")
            
            # If it's a country, try to use official LSIB boundaries for strict masking
            ee_geometry = ee.Geometry(geometry)
            if region_type == 'country':
                try:
                    # Search specifically for the country in official administrative boundaries
                    # Filter by country name to get the precise polygon
                    clean_name = region_name.replace("(Complete Country)", "").strip()
                    lsib = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
                    country_feature = lsib.filter(ee.Filter.eq('country_na', clean_name)).first()
                    
                    if country_feature.geometry():
                         ee_geometry = country_feature.geometry()
                         self.logger.info(f"📍 Using precise administrative boundaries for {clean_name}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not fetch precise boundaries for {region_name}: {e}. Falling back to provided geometry.")

            # Run GEE analysis
            gee_result = self.run_gee_analysis(
                ee_geometry, start_date, end_date, analysis_type, 
                job_data.get('baseline_type', 'same-period'),
                job_data.get('baseline_config'),
                progress_callback,
                region_type  # Pass region_type for dynamic scaling
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
                analysis_type,
                region_type  # Pass region type for inset map logic
            )
            
            # Save files
            output_paths = self.save_outputs(job_id, map_result, gee_result)
            
            # Generate AI Commentary (Executive Summary)
            if progress_callback:
                progress_callback(85, "Generating AI Executive Summary...")
            
            from .intelligence import ai_intel
            ai_commentary = ai_intel.generate_commentary(
                statistics=gee_result['statistics'],
                region_name=region_name,
                analysis_type=analysis_type
            )
            
            # Update progress
            if progress_callback:
                progress_callback(100, "Processing completed successfully")
            
            return {
                'success': True,
                'statistics': gee_result['statistics'],
                'ai_commentary': ai_commentary,
                'map_image_path': output_paths['map_image'],
                'export_paths': output_paths,
                'extent': gee_result['extent']
            }
        
        except Exception as e:
            self.logger.error(f"❌ Job {job_id} failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def run_gee_analysis(self, geometry: ee.Geometry, start_date: str, end_date: str, 
                        analysis_type: str, baseline_type: str = 'same-period',
                        baseline_config: Dict = None, progress_callback: Callable = None,
                        region_type: str = 'country') -> Dict:
        """Execute GEE analysis for soil moisture anomaly with dynamic baselines"""
        
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
            baseline = self.calculate_baseline(era5_land, start_date, end_date, geometry, baseline_type, baseline_config)
            
            if progress_callback:
                progress_callback(40, "Loading MODIS Vegetation Health (NDVI)...")
            
            # Load MODIS NDVI (MOD13Q1.061)
            # MODIS NDVI is a 16-day composite, scale factor 0.0001
            modis_coll = ee.ImageCollection("MODIS/061/MOD13Q1").filterBounds(geometry)
            
            modis_v61 = modis_coll \
                          .filterDate(start_date, end_date) \
                          .select('NDVI') \
                          .mean() \
                          .multiply(0.0001) \
                          .clip(geometry)
            
            # Historical NDVI baseline
            baseline_ndvi = self.calculate_ndvi_baseline(modis_coll, start_date, end_date, geometry, baseline_type, baseline_config)

            if progress_callback:
                progress_callback(42, "Loading CHIRPS Precipitation data...")

            # Load CHIRPS Rainfall data
            chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
                       .select('precipitation') \
                       .filterBounds(geometry)
            
            # Total rainfall for current period
            current_rainfall = chirps.filterDate(start_date, end_date).sum().clip(geometry)
            
            # Historical rainfall for context (synchronized baseline)
            baseline_rainfall = self.calculate_rainfall_baseline(chirps, start_date, end_date, geometry, baseline_type, baseline_config)
            
            if progress_callback:
                progress_callback(45, "Computing anomalies & multi-peril correlation...")
            
            # Calculate Soil Moisture anomalies
            if analysis_type == 'percentage':
                result_image = current_period.subtract(baseline).divide(baseline).multiply(100)
            elif analysis_type == 'absolute':
                result_image = current_period
            else:
                result_image = current_period.subtract(baseline)  # Default to anomaly
            
            if progress_callback:
                progress_callback(55, "Calculating statistics & Zonal Area...")
            
            # Calculate comprehensive statistics and ZONAL AREA
            statistics = self.calculate_advanced_statistics(
                current_period, baseline, result_image, modis_v61, baseline_ndvi, current_rainfall, baseline_rainfall, geometry
            )
            
            # Capture period context for the report
            statistics['analysis_period'] = {'start': start_date, 'end': end_date}
            
            if progress_callback:
                progress_callback(65, "Preparing visualization data...")
            
            # Get data for visualization
            extent = self.get_geometry_bounds(geometry)
            data_array = self.export_image_data(result_image, extent)
            
            return {
                'success': True,
                'data': data_array,
                'extent': extent,
                'statistics': statistics,
                'current_image': current_period,
                'baseline_image': baseline,
                'result_image': result_image,
                'ndvi_image': modis_v61
            }
            
        except Exception as e:
            self.logger.error(f"❌ GEE analysis failed: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def calculate_baseline(self, collection: ee.ImageCollection, start_date: str, 
                          end_date: str, geometry: ee.Geometry, 
                          baseline_type: str = 'same-period', baseline_config: Dict = None) -> ee.Image:
        """Calculate historical baseline based on user selection"""
        
        if baseline_type == 'custom' and baseline_config:
            # Custom fixed period baseline
            return collection.filterDate(baseline_config['start'], baseline_config['end']).mean().clip(geometry)
            
        # Same-period logic (default)
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        baseline = collection \
            .filter(ee.Filter.calendarRange(2015, 2024, 'year')) \
            .filter(ee.Filter.calendarRange(start_dt.month, end_dt.month, 'month'))
        
        return baseline.mean().clip(geometry)

    def calculate_rainfall_baseline(self, collection: ee.ImageCollection, start_date: str, 
                                   end_date: str, geometry: ee.Geometry,
                                   baseline_type: str = 'same-period', baseline_config: Dict = None) -> ee.Image:
        """Calculate historical rainfall baseline synchronized with baseline selection"""
        if baseline_type == 'custom' and baseline_config:
            return collection.filterDate(baseline_config['start'], baseline_config['end']).sum().clip(geometry)

        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Use 10-year baseline for Rainfall
        baseline = collection \
            .filter(ee.Filter.calendarRange(2015, 2024, 'year')) \
            .filter(ee.Filter.calendarRange(start_dt.month, end_dt.month, 'month'))
        
        return baseline.sum().divide(10).clip(geometry)
    
    def calculate_ndvi_baseline(self, collection: ee.ImageCollection, start_date: str, 
                               end_date: str, geometry: ee.Geometry,
                               baseline_type: str = 'same-period', baseline_config: Dict = None) -> ee.Image:
        """Calculate historical NDVI baseline synchronized with baseline selection"""
        if baseline_type == 'custom' and baseline_config:
            return collection.filterDate(baseline_config['start'], baseline_config['end']).mean().clip(geometry)

        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Use 10-year baseline for NDVI
        baseline = collection \
            .filter(ee.Filter.calendarRange(2015, 2024, 'year')) \
            .filter(ee.Filter.calendarRange(start_dt.month, end_dt.month, 'month')) \
            .select('NDVI')
            
        return baseline.mean().multiply(0.0001).clip(geometry)
    
    def calculate_advanced_statistics(self, current: ee.Image, baseline: ee.Image, 
                                   anomaly: ee.Image, ndvi: ee.Image, baseline_ndvi_img: ee.Image,
                                   rainfall: ee.Image, baseline_rain: ee.Image, 
                                   geometry: ee.Geometry) -> Dict:
        """Calculate advanced statistics including Zonal Impact, Vegetation, and Precipitation"""
        
        # 1. Base Soil Moisture Stats
        anomaly_stats = anomaly.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.minMax(),
                sharedInputs=True
            ),
            geometry=geometry,
            scale=15000, # Matched with buffer scale for OOM stability
            maxPixels=1e9
        ).getInfo()
        
        current_mean = current.reduceRegion(ee.Reducer.mean(), geometry, 15000).getInfo().get('volumetric_soil_water_layer_1', 0)
        baseline_mean = baseline.reduceRegion(ee.Reducer.mean(), geometry, 15000).getInfo().get('volumetric_soil_water_layer_1', 0)
        
        # 2. NDVI Statistics (Vegetation Health)
        ndvi_current = ndvi.reduceRegion(ee.Reducer.mean(), geometry, 5000).getInfo().get('NDVI', 0)
        baseline_ndvi = baseline_ndvi_img.reduceRegion(ee.Reducer.mean(), geometry, 5000).getInfo().get('NDVI', 0)
        
        # 3. Rainfall Statistics (CHIRPS)
        rain_total = rainfall.reduceRegion(ee.Reducer.mean(), geometry, 5000).getInfo().get('precipitation', 0)
        baseline_rain_total = baseline_rain.reduceRegion(ee.Reducer.mean(), geometry, 5000).getInfo().get('precipitation', 0)
        
        # 4. Enhanced Zonal Impact Assessment - COMPARATIVE
        zonal_impact = self.calculate_enhanced_zonal_impact(
            anomaly, current, baseline, ndvi, rainfall, baseline_rain, geometry
        )
        
        # 5. Total Area calculation (for percentages)
        total_area_ha = sum(z['area_ha'] for z in zonal_impact.values())
        for zone in zonal_impact.values():
            zone['percentage'] = (zone['area_ha'] / total_area_ha * 100) if total_area_ha > 0 else 0
        
        # 6. Multi-Peril Collision Correlation
        # Identify "High Risk" zones: where Soil Moisture Anomaly < -0.03 AND NDVI < 0.4
        risk_zones = anomaly.lt(-0.03).And(ndvi.lt(0.4))
        risk_area = risk_zones.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=5000,
            maxPixels=1e9
        ).getInfo().get('volumetric_soil_water_layer_1', 0) / 10000 
        
        return {
            'mean_anomaly': anomaly_stats.get('volumetric_soil_water_layer_1_mean', 0),
            'min_anomaly': anomaly_stats.get('volumetric_soil_water_layer_1_min', 0),
            'max_anomaly': anomaly_stats.get('volumetric_soil_water_layer_1_max', 0),
            'current_mean': current_mean,
            'baseline_mean': baseline_mean,
            'total_area_ha': total_area_ha,
            'percentage_change': ((current_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0,
            'mean_ndvi': ndvi_current,
            'baseline_ndvi': baseline_ndvi,
            'ndvi_change': ((ndvi_current - baseline_ndvi) / baseline_ndvi * 100) if baseline_ndvi > 0 else 0,
            'mean_rainfall': rain_total,
            'baseline_rainfall': baseline_rain_total,
            'rainfall_change': ((rain_total - baseline_rain_total) / baseline_rain_total * 100) if baseline_rain_total > 0 else 0,
            'zonal_impact': zonal_impact, 
            'multi_peril_risk_hectares': risk_area
        }
    
    def calculate_enhanced_zonal_impact(self, anomaly: ee.Image, current_moisture: ee.Image, 
                                      baseline_moisture: ee.Image, ndvi: ee.Image, 
                                      current_rain: ee.Image, baseline_rain: ee.Image, 
                                      geometry: ee.Geometry) -> Dict[str, Dict]:
        """Calculates COMPARATIVE hectares, moisture, and rainfall for each drought intensity zone"""
        
        # 1. Categories based on anomaly thresholds
        zones = ee.Image(0).where(anomaly.lt(-0.05), 1) \
                          .where(anomaly.lt(-0.03).And(anomaly.gte(-0.05)), 2) \
                          .where(anomaly.lt(-0.01).And(anomaly.gte(-0.03)), 3) \
                          .where(anomaly.lt(0.01).And(anomaly.gte(-0.01)), 4) \
                          .where(anomaly.gt(0.01), 5)
        
        # 2. Strict Band Stacking for Comparative Stats
        # Band 0: area, Band 1: cur_moist, Band 2: bas_moist, Band 3: cur_rain, Band 4: bas_rain, Band 5: ndvi, Band 6: zone
        stack = ee.Image.cat([
            ee.Image.pixelArea(),
            current_moisture.select([0]),
            baseline_moisture.select([0]),
            current_rain.select([0]),
            baseline_rain.select([0]),
            ndvi.select([0]),
            zones.select([0])
        ]).clip(geometry)
        
        # 3. Build Safe Grouped Reducer
        reducer = ee.Reducer.sum().setOutputs(['sum']) \
                   .combine(ee.Reducer.mean().setOutputs(['cur_moist']), '', False) \
                   .combine(ee.Reducer.mean().setOutputs(['bas_moist']), '', False) \
                   .combine(ee.Reducer.mean().setOutputs(['cur_rain']), '', False) \
                   .combine(ee.Reducer.mean().setOutputs(['bas_rain']), '', False) \
                   .combine(ee.Reducer.mean().setOutputs(['ndvi']), '', False) \
                   .group(groupField=6, groupName='zone')
        
        # 4. Map Zone IDs to labels
        zone_map = {
            1: 'extreme_drought',
            2: 'severe_drought',
            3: 'moderate_drought',
            4: 'normal',
            5: 'wet_conditions'
        }
        
        impact_data = {label: {
            'area_ha': 0.0, 
            'current_moisture': 0.0, 'baseline_moisture': 0.0,
            'current_rain': 0.0, 'baseline_rain': 0.0,
            'mean_ndvi': 0.0
        } for label in zone_map.values()}
        
        try:
            # 5. Execute
            raw_stats = stack.reduceRegion(
                reducer=reducer,
                geometry=geometry,
                scale=5000,
                maxPixels=1e9
            ).get('groups')
            
            if raw_stats:
                groups = raw_stats.getInfo()
                for group in groups:
                    z_id = group.get('zone')
                    if z_id in zone_map:
                        label = zone_map[z_id]
                        impact_data[label]['area_ha'] = group.get('sum', 0) / 10000.0
                        impact_data[label]['current_moisture'] = group.get('cur_moist', 0)
                        impact_data[label]['baseline_moisture'] = group.get('bas_moist', 0)
                        impact_data[label]['current_rain'] = group.get('cur_rain', 0)
                        impact_data[label]['baseline_rain'] = group.get('bas_rain', 0)
                        impact_data[label]['mean_ndvi'] = group.get('ndvi', 0)
        
        except Exception as e:
            self.logger.error(f"❌ Enhanced Zonal Reduction Failed: {e}")
            
        return impact_data
    
    def calculate_zonal_impact(self, anomaly: ee.Image, geometry: ee.Geometry) -> Dict[str, float]:
        """Calculates hectares for each drought intensity zone"""
        
        # Define thresholds matching our color scheme
        # Boundaries: [-0.08, -0.05, -0.03, -0.01, 0.01, 0.03, 0.05, 0.08]
        zones = ee.Image(0).where(anomaly.lt(-0.05), 1) \
                          .where(anomaly.lt(-0.03).And(anomaly.gte(-0.05)), 2) \
                          .where(anomaly.lt(-0.01).And(anomaly.gte(-0.03)), 3) \
                          .where(anomaly.lt(0.01).And(anomaly.gte(-0.01)), 4) \
                          .where(anomaly.gt(0.01), 5)
        
        # Area calculation for each zone
        # Multiply by pixelArea() and sum
        area_image = ee.Image.pixelArea().addBands(zones)
        areas = area_image.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName='zone'),
            geometry=geometry,
            scale=10000,
            maxPixels=1e9
        ).get('groups')
        
        # Convert to dictionary with hectares
        impact_dict = {
            'extreme_drought': 0.0,
            'severe_drought': 0.0,
            'moderate_drought': 0.0,
            'normal': 0.0,
            'wet_conditions': 0.0
        }
        
        zone_map = {
            1: 'extreme_drought',
            2: 'severe_drought',
            3: 'moderate_drought',
            4: 'normal',
            5: 'wet_conditions'
        }
        
        if areas:
            for group in areas.getInfo():
                zone_id = group.get('zone')
                area_m2 = group.get('sum')
                if zone_id in zone_map:
                    impact_dict[zone_map[zone_id]] = area_m2 / 10000.0 # m2 to hectares
        
        return impact_dict
    
    def get_geometry_bounds(self, geometry: ee.Geometry) -> List[float]:
        """Get tight bounding box from EE geometry with padding for zoom-fit.
        Includes a mainland heuristic to ignore far-flung islands (e.g. for South Africa).
        """
        
        # Mainland Heuristic: Filter by largest area to ignore sub-antarctic islands (e.g. SA Prince Edward Islands)
        target_geom = geometry
        try:
            if geometry.type().getInfo() == 'MultiPolygon':
                geoms = geometry.geometries()
                if geoms.length().getInfo() > 1:
                    geoms_list = geoms.getInfo()
                    # We pick the geometry with the most coordinates as the Mainland
                    mainland = max(geoms_list, key=lambda g: len(str(g)))
                    target_geom = ee.Geometry(mainland)
        except Exception as e:
            self.logger.warning(f"Mainland heuristic failed: {e}. Using full geometry.")
            target_geom = geometry

        bounds = target_geom.bounds().getInfo()['coordinates'][0]
        
        lons = [coord[0] for coord in bounds]
        lats = [coord[1] for coord in bounds]
        
        # Calculate dynamic extent with 5% geographic padding for "Zoom-Fit" effect
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        
        lon_pad = (max_lon - min_lon) * 0.05
        lat_pad = (max_lat - min_lat) * 0.05
        
        return [min_lon - lon_pad, max_lon + lon_pad, min_lat - lat_pad, max_lat + lat_pad]
    
    def export_image_data(self, image: ee.Image, extent: List[float]) -> np.ndarray:
        """Export EE image to NumPy array using exact bounding box extent"""
        
        # Convert extent [min_lon, max_lon, min_lat, max_lat] to ee.Geometry.Rectangle
        # coords: [min_lon, min_lat, max_lon, max_lat]
        export_region = ee.Geometry.Rectangle([extent[0], extent[2], extent[1], extent[3]])

        # Get download URL - REDUCED RESOLUTION for 512MB RAM stability
        url = image.getDownloadURL({
            'region': export_region,
            'scale': 15000, 
            'format': 'GEO_TIFF'
        })
        
        response = requests.get(url)
        with tempfile.NamedTemporaryFile(suffix='.tif') as tmp_file:
            tmp_file.write(response.content)
            tmp_file.flush()
            
            import rasterio
            with rasterio.open(tmp_file.name) as src:
                # Use masked=True to handle transparency for non-land areas
                data = src.read(1, masked=True)
                
        return data
    
    def generate_cartography(self, data: np.ndarray, extent: List[float], 
                           region_name: str, start_date: str, end_date: str,
                           statistics: Dict, analysis_type: str, 
                           region_type: str = 'country') -> Dict:
        """Generate professional cartographic visualization with zoom-fit and clean canvas"""
        
        try:
            plt.style.use('default')
            fig = plt.figure(figsize=(14, 8.5), dpi=150, facecolor='white')
            
            from matplotlib.gridspec import GridSpec
            gs = GridSpec(1, 2, figure=fig, width_ratios=[7, 3], wspace=0.02)
            
            proj = ccrs.PlateCarree()
            ax_map = fig.add_subplot(gs[0], projection=proj)
            
            # Set Ocean/Background color to clean up dead space
            ax_map.set_facecolor('#e0f2fe') # Light blue/ocean color
            
            ax_info = fig.add_subplot(gs[1])
            ax_info.axis('off')
            
            # Use the calculated tight extent for Zoom-Fit
            ax_map.set_extent(extent, crs=ccrs.PlateCarree())
            
            self.add_base_features(ax_map)
            
            # Ocean feature with specific color
            ax_map.add_feature(cfeature.OCEAN, facecolor='#f1f5f9', zorder=-1)
            
            cmap, norm = self.create_color_scheme(analysis_type)
            
            # Plot data
            im = ax_map.imshow(data, 
                          extent=extent,
                          transform=ccrs.PlateCarree(),
                          cmap=cmap,
                          norm=norm,
                          alpha=0.9,
                          zorder=1,
                          interpolation='bilinear')
            
            # Add map title (only element on map besides the data)
            self.add_map_title(ax_map, region_name, start_date, end_date)
            
            # Add cartographic elements to map
            self.add_north_arrow(ax_map, extent)
            self.add_scale_bar(ax_map, extent)
            
            # Add all information to sidebar
            self.add_information_sidebar(ax_info, region_name, start_date, end_date, 
                                        statistics, analysis_type, cmap, norm)
            
            # Add inset map for provinces/districts to show Zimbabwe context
            if region_type in ['province', 'district']:
                self.add_context_inset_map(fig, ax_map, region_name, region_type)
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, 
                       format='png',
                       dpi=150, # Reduced from 300 to stabilize 512MB RAM
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
        """Create professional color scheme with enhanced contrast"""
        
        if analysis_type == 'anomaly':
            # Enhanced drought to wet color scheme with better contrast
            colors = [
                '#8B0000',  # Extreme Drought (dark red)
                '#DC143C',  # Severe Drought (crimson)
                '#FF6347',  # Moderate Drought (tomato)
                '#FFD700',  # Below Normal (gold)
                '#FFFFFF',  # Normal (white)
                '#87CEEB',  # Above Normal (sky blue)
                '#4169E1',  # Much Above Normal (royal blue)
                '#000080'   # Exceptional (navy)
            ]
            boundaries = [-0.08, -0.05, -0.03, -0.01, 0.01, 0.03, 0.05, 0.08]
            
        elif analysis_type == 'percentage':
            # Percentage change color scheme
            colors = ['#8B0000', '#FF6347', '#FFD700', '#FFFFFF', '#87CEEB', '#4169E1', '#000080']
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
        
        # Main title - fix duplication issue
        # Remove (Complete Country) if present to avoid duplication/clutter
        clean_region_name = region_name.replace("(Complete Country)", "").strip()
        title = f"{clean_region_name} Soil Moisture Anomaly – {date_str}"
        ax_map.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    def add_context_inset_map(self, fig, ax_map, region_name: str, region_type: str):
        """Add context by masking outside the region (clipping) and showing neighbors"""
        
        try:
            import os
            # Set config to restore/create .shx if missing
            os.environ['SHAPE_RESTORE_SHX'] = 'YES'
            
            import cartopy.io.shapereader as shpreader
            from shapely.geometry import box, Polygon, MultiPolygon
            
            # Paths to local shapefiles
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prov_shp_path = os.path.join(base_dir, 'data', 'nationalProv_ZWE_1.shp')
            dist_shp_path = os.path.join(base_dir, 'data', 'zim_district.shp')
            
            if not os.path.exists(prov_shp_path):
                return

            # Check for sidecar files
            prov_dbf_path = prov_shp_path.replace('.shp', '.dbf')
            has_attributes = os.path.exists(prov_dbf_path)
            
            # Read shapefiles
            prov_reader = shpreader.Reader(prov_shp_path)
            dist_reader = shpreader.Reader(dist_shp_path) if os.path.exists(dist_shp_path) else None
            
            # Clean region name
            clean_name = region_name.lower()
            for suffix in [' province', ' district', ' rural', ' urban', ' metropolitan']:
                clean_name = clean_name.replace(suffix, '')
            clean_name = clean_name.strip()
            
            # 1. FIND THE TARGET REGION GEOMETRY
            best_match_geometry = None
            best_match_score = 0
            selected_reader = dist_reader if region_type == 'district' and dist_reader else prov_reader
            
            if has_attributes:
                for record in selected_reader.records():
                    attrs = record.attributes
                    admin_name = str(attrs.get('NAME_1', attrs.get('NAME_2', attrs.get('name', '')))).lower()
                    clean_admin = admin_name.replace(' province', '').replace(' district', '').strip()
                    
                    match_score = 0
                    if clean_name == clean_admin:
                        match_score = 100
                    elif clean_admin in clean_name and len(clean_admin) > 3:
                         match_score = 80 + len(clean_admin)
                    elif clean_name in clean_admin and len(clean_name) > 3:
                         match_score = 80 + len(clean_name)
                    
                    if match_score > best_match_score:
                        best_match_score = match_score
                        best_match_geometry = record.geometry
            
            # 2. APPLY INVERSE MASK (Clipping Effect)
            # If we found the geometry, we mask everything OUTSIDE it
            if best_match_geometry and best_match_score >= 80:
                # Get map extent polygon
                extent = ax_map.get_extent()
                # Create a big box covering the map
                bbox = box(extent[0], extent[2], extent[1], extent[3])
                
                # Attempt to subtract the region geometry from the bbox
                # This creates a "hole" in the shape of our province
                try:
                    # Convert best_match to shapely geometry if needed
                    # Note: record.geometry is usually already a shapely object
                    
                    # Create the mask polygon (Box minus Region)
                    mask_geom = bbox.difference(best_match_geometry)
                    
                    # Add the mask layer (matches background color to "hide" outside data)
                    ax_map.add_geometries(
                        [mask_geom],
                        ccrs.PlateCarree(),
                        facecolor='#f1f5f9',      # Slate-50 background color
                        edgecolor='none',
                        zorder=5                  # Above data (z=1), below border (z=10)
                    )
                    
                    # Add a nice border around the region
                    ax_map.add_geometries(
                        [best_match_geometry],
                        ccrs.PlateCarree(),
                        facecolor='none',
                        edgecolor='#1e293b',      # Dark Slate border
                        linewidth=1.5,
                        zorder=10
                    )
                    self.logger.info(f"✂️ Applied clipping mask for {region_name}")
                    
                except Exception as clip_err:
                    self.logger.warning(f"Clipping failed: {clip_err}")
            
            # 3. DRAW NEIGHBOR CONTEXT
            # Draw all province boundaries faint gray on top of the mask
            # This restores context that might have been masked out
            zim_provinces = list(prov_reader.geometries())
            ax_map.add_geometries(
                zim_provinces,
                ccrs.PlateCarree(),
                facecolor='none',
                edgecolor='#94a3b8',      # Slate-400
                linewidth=0.5,
                alpha=0.6,
                zorder=6                  # On top of mask (z=5)
            )

            # 4. ADD NATIONAL INSET (Corner Context)
            from mpl_toolkits.axes_grid1.inset_locator import inset_axes
            
            ax_inset = inset_axes(ax_map, 
                                  width="20%", 
                                  height="25%",
                                  loc='lower left',
                                  axes_class=cartopy.mpl.geoaxes.GeoAxes,
                                  axes_kwargs={'projection': ccrs.PlateCarree()},
                                  borderpad=1)
            
            ax_inset.set_extent([25, 33.5, -22.5, -15.5], crs=ccrs.PlateCarree())
            ax_inset.add_geometries(zim_provinces, ccrs.PlateCarree(), facecolor='white', edgecolor='#64748b', linewidth=0.3)
            
            if best_match_geometry:
                ax_inset.add_geometries([best_match_geometry], ccrs.PlateCarree(), facecolor='#B6BF00', edgecolor='none')
            
            ax_inset.spines['geo'].set_linewidth(0.5)
            ax_inset.tick_params(left=False, right=False, bottom=False, top=False, labelleft=False, labelbottom=False)
            
        except Exception as e:
            self.logger.warning(f"Could not add shapefile context: {str(e)}")
    
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
        
        # Section 2: Regional Statistics (removed risk assessment)
        percentage = statistics.get('percentage_change', 0)
        mean_anomaly = statistics.get('mean_anomaly', 0)
        
        # Determine color based on percentage
        if percentage > 15:
            stat_color = '#2E7D32'  # Green
        elif percentage > 0:
            stat_color = '#1976D2'  # Blue
        elif percentage > -15:
            stat_color = '#F57C00'  # Orange
        else:
            stat_color = '#C62828'  # Red
        
        from matplotlib.patches import FancyBboxPatch
        
        # Statistics box (moved down further to fix collision with Data Source)
        # Top was 0.88. Moving down to top 0.84 to give clear gap.
        stats_box = FancyBboxPatch((0.05, 0.75), 0.9, 0.09, 
                                   boxstyle="round,pad=0.01", 
                                   edgecolor='black', facecolor='#f0f0f0', 
                                   linewidth=1.5)
        ax_info.add_patch(stats_box)
        
        ax_info.text(0.5, 0.825, 'REGIONAL STATISTICS', ha='center', va='top',
                    fontsize=10, weight='bold')
        
        ax_info.text(0.5, 0.79, f"Mean: {mean_anomaly:.3f} m³/m³", 
                    ha='center', va='top', fontsize=10, weight='bold')
        ax_info.text(0.5, 0.76, f"Change: {percentage:+.1f}% from normal", 
                    ha='center', va='top', fontsize=9,
                    color=stat_color, weight='bold')
        
        # Section 3: Legend with thresholds (moved down)
        ax_info.text(0.05, 0.71, 'LEGEND', ha='left', va='top',
                    fontsize=11, weight='bold')
        
        # Legend title
        titles = {
            'anomaly': 'Soil Moisture Difference from Normal (m³/m³)',
            'percentage': 'Percentage Change from Normal (%)',
            'absolute': 'Absolute Soil Moisture (m³/m³)'
        }
        
        ax_info.text(0.05, 0.67, titles.get(analysis_type, 'Soil Moisture Analysis'),
                    ha='left', va='top', fontsize=7, style='italic')
        
        # Legend categories with thresholds
        if analysis_type == 'anomaly':
            legend_items = [
                ('Exceptional Above Normal', '#000080', '(+0.05 to +0.08)'),
                ('Much Above Normal', '#4169E1', '(+0.03 to +0.05)'),
                ('Above Normal', '#87CEEB', '(+0.01 to +0.03)'),
                ('Normal Conditions', '#FFFFFF', '(-0.01 to +0.01)'),
                ('Below Normal', '#FFD700', '(-0.03 to -0.01)'),
                ('Severe Drought', '#FF6347', '(-0.05 to -0.03)'),
                ('Extreme Drought', '#8B0000', '(< -0.05)')
            ]
        else:
            legend_items = [
                ('High', '#000080', ''),
                ('Above Average', '#4169E1', ''),
                ('Average', '#FFFFFF', ''),
                ('Below Average', '#FFD700', ''),
                ('Low', '#8B0000', '')
            ]
        
        # Legend positioning adjusted down
        y_positions = np.linspace(0.62, 0.19, len(legend_items))
        
        for (label, color, threshold), y_pos in zip(legend_items, y_positions):
            # Color patch
            rect = plt.Rectangle((0.05, y_pos-0.010), 0.10, 0.018,
                               facecolor=color, edgecolor='black', linewidth=0.8)
            ax_info.add_patch(rect)
            
            # Label with threshold (tighter spacing)
            if threshold:
                ax_info.text(0.18, y_pos, label, va='center', ha='left', fontsize=8, weight='bold')
                ax_info.text(0.18, y_pos-0.012, threshold, va='top', ha='left', 
                           fontsize=6, style='italic', color='gray')
            else:
                ax_info.text(0.18, y_pos, label, va='center', ha='left', fontsize=9)
        
        # Attribution (bottom) - moved down to avoid collision
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        ax_info.text(0.5, 0.14, 'GENERATED', ha='center', va='top',
                    fontsize=9, weight='bold')
        ax_info.text(0.5, 0.11, timestamp, ha='center', va='top', 
                    fontsize=7, style='italic')
        ax_info.text(0.5, 0.08, 'Analysis by Yieldera Platform', ha='center', va='top',
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
