/**
 * YIELDERA DASHBOARD CONFIGURATION
 * All configuration constants and settings
 */

const CONFIG = {
  // API Configuration
  GEE_API_TOKEN: 'e5ab51a6982394b7ed747afdac005a1c851d128fb060898b7b7134789b25f518',
  GEE_API_URL: '/api/gee_ndvi',
  REPORT_API_URL: '/api/advanced-report',

  // Map Configuration
  MAP: {
    DEFAULT_CENTER: [0, 0],
    DEFAULT_ZOOM: 2,
    ZIMBABWE_CENTER: [-17.8, 31.05],
    ZIMBABWE_ZOOM: 6,
    MAX_ZOOM: 20,
    MAX_NATIVE_ZOOM: 18,
    TILE_SIZE: 256
  },

  // Index Configuration
  INDEX: {
    DEFAULT_TYPE: 'RGB',
    TYPES: ['RGB', 'NDVI', 'EVI', 'SAVI', 'NDMI', 'NDWI'],
    MAX_RETRIES: 3,
    REQUEST_TIMEOUT: 20000
  },

  // Date Configuration
  DATE: {
    DEFAULT_RANGE_DAYS: 14
  },

  // UI Configuration
  UI: {
    NOTIFICATION_DURATION: 5000,
    FIELD_BATCH_SIZE: 5,
    BATCH_PROCESS_DELAY: 10
  }
};

// Index configurations (will be populated from backend)
const INDEX_CONFIGS = {};

// Export configuration
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CONFIG, INDEX_CONFIGS };
}
