"""
Pre-cache script for Cartopy Natural Earth datasets.
Run this during build to avoid runtime downloads.
"""
import os
import cartopy
import cartopy.io.shapereader as shpreader
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def pre_cache():
    # Define local cache directory
    # Use standard environment variable if set (consistency with Render config)
    env_cache_dir = os.getenv("CARTOPY_USER_DATADIR")
    if env_cache_dir:
        cache_dir = os.path.abspath(env_cache_dir)
    else:
        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "cartopy_cache"))
    
    os.makedirs(cache_dir, exist_ok=True)
    
    # Configure cartopy to use this directory
    cartopy.config['data_dir'] = cache_dir
    
    logger.info(f"Using Cartopy data directory: {cache_dir}")
    
    # List of datasets to pre-cache (10m Resolution for professional quality)
    datasets = [
        ('physical', 'coastline', '10m'),
        ('cultural', 'admin_0_boundary_lines_land', '10m'),
        ('physical', 'rivers_lake_centerlines', '10m'),
        ('physical', 'lakes', '10m'),
    ]
    
    downloader = shpreader.NEShpDownloader()
    
    success_count = 0
    for category, name, resolution in datasets:
        logger.info(f"Pre-caching {category}/{name} at {resolution}...")
        try:
            # This triggers the download and verification
            shpreader.natural_earth(resolution=resolution, category=category, name=name)
            logger.info(f"✅ Successfully cached {name}")
            success_count += 1
        except Exception as e:
            logger.error(f"❌ Failed to cache {name}: {e}")
            
    logger.info(f"Pre-caching routine finished. {success_count}/{len(datasets)} datasets secured.")

if __name__ == "__main__":
    pre_cache()
