/**
 * MAP MANAGER
 * Handles all map-related functionality
 */

const MapManager = {
  map: null,
  baseLayer: null,
  currentIndexLayer: null,
  currentMapMode: 'satellite',
  layerTransitionInProgress: false,

  init() {
    Utils.updateLoadingProgress(10, 'Initializing map...');
    
    this.map = L.map('map', {
      zoomControl: true,
      zoomSnap: 0.25,
      zoomDelta: 0.5,
      attributionControl: true,
      preferCanvas: true
    }).setView(CONFIG.MAP.DEFAULT_CENTER, CONFIG.MAP.DEFAULT_ZOOM);
    
    this.baseLayer = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&key=AIzaSyA6CWnH5Ra7i9Aj2MnZaD_lzuhLxZyVMuk', {
      attribution: 'Imagery © Google Maps | Rendered by Yieldera GeoEngine',
      maxZoom: CONFIG.MAP.MAX_ZOOM,
      subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      keepBuffer: 2,
      maxNativeZoom: CONFIG.MAP.MAX_NATIVE_ZOOM,
      tileSize: CONFIG.MAP.TILE_SIZE,
      zoomOffset: 0
    }).addTo(this.map);
    
    this.initUserLocation();
    this.initMapControls();
    Utils.updateLoadingProgress(30, 'Map initialized...');
    
    return this.map;
  },

  initUserLocation() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const userLat = position.coords.latitude;
          const userLng = position.coords.longitude;
          this.map.setView([userLat, userLng], 10);
          Utils.updateLoadingProgress(20, 'Located user...');
        },
        (error) => {
          console.warn("Geolocation error:", error);
          Utils.updateLoadingProgress(20, 'Using default location...');
          this.map.setView(CONFIG.MAP.ZIMBABWE_CENTER, CONFIG.MAP.ZIMBABWE_ZOOM);
        }
      );
    }
  },

  initMapControls() {
    document.getElementById('satelliteBtn').addEventListener('click', () => {
      if (this.layerTransitionInProgress) return;
      this.setMapMode('satellite');
      document.getElementById('satelliteBtn').classList.add('active');
      document.getElementById('indexBtn').classList.remove('active');
      document.getElementById('indexSelector').classList.add('hidden');
    });
    
    document.getElementById('indexBtn').addEventListener('click', () => {
      if (this.layerTransitionInProgress) return;
      this.setMapMode('index');
      document.getElementById('indexBtn').classList.add('active');
      document.getElementById('satelliteBtn').classList.remove('active');
      const indexSelector = document.getElementById('indexSelector');
      indexSelector.classList.remove('hidden');
      indexSelector.style.display = 'flex';
    });

    this.initIndexSelector();
  },

  initIndexSelector() {
    const selectorBtn = document.getElementById('indexSelectorBtn');
    const dropdown = document.getElementById('indexDropdown');
    const selectedIndexName = document.getElementById('selectedIndexName');
    
    selectorBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown.classList.toggle('hidden');
    });
    
    document.addEventListener('click', (e) => {
      if (!selectorBtn.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.add('hidden');
      }
    });
    
    dropdown.addEventListener('click', (e) => {
      const option = e.target.closest('.index-option');
      if (!option) return;
      
      const indexType = option.dataset.index;
      if (indexType === window.DashboardState.currentIndexType) return;
      
      IndexManager.setCurrentIndex(indexType);
      selectedIndexName.textContent = indexType;
      
      dropdown.querySelectorAll('.index-option').forEach(opt => {
        opt.classList.remove('active');
      });
      option.classList.add('active');
      dropdown.classList.add('hidden');
      
      if (this.currentMapMode === 'index' && window.DashboardState.selectedField) {
        IndexManager.loadIndexLayer(window.DashboardState.selectedField);
      }
    });
    
    dropdown.querySelector('[data-index="RGB"]').classList.add('active');
  },

  setMapMode(mode) {
    if (mode === this.currentMapMode) return;
    this.layerTransitionInProgress = true;
    this.currentMapMode = mode;
    
    if (mode === 'satellite') {
      if (this.currentIndexLayer) {
        Notifications.show('Switching to satellite view...', 'info');
        if (this.map.hasLayer(this.currentIndexLayer)) {
          this.map.removeLayer(this.currentIndexLayer);
        }
        this.currentIndexLayer = null;
      }
      
      if (!this.map.hasLayer(this.baseLayer)) {
        this.baseLayer.addTo(this.map);
      }
      
      setTimeout(() => { this.layerTransitionInProgress = false; }, 200);
    } else if (mode === 'index') {
      if (!this.map.hasLayer(this.baseLayer)) {
        this.baseLayer.addTo(this.map);
      }
      
      const indexSelector = document.getElementById('indexSelector');
      indexSelector.classList.remove('hidden');
      indexSelector.style.display = 'flex';
      
      IndexManager.updateIndexLegend();
      
      if (window.DashboardState.selectedField) {
        IndexManager.loadIndexLayer(window.DashboardState.selectedField);
      } else {
        Notifications.show('Please select a field to view index data', 'info');
        this.layerTransitionInProgress = false;
      }
    }
  },

  getMap() {
    return this.map;
  }
};