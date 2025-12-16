/**
 * UI MANAGER
 * Handles UI interactions, tabs, mobile menu
 */

const UIManager = {
  init() {
    this.initPanelTabs();
    this.initMobileMenu();
    this.initDateRangeButtons();
    this.initComingSoonHandlers();
  },

  initPanelTabs() {
    const tabs = document.querySelectorAll('[data-tab]');
    
    tabs.forEach(tab => {
      tab.addEventListener('click', function() {
        const tabName = this.getAttribute('data-tab');
        
        tabs.forEach(t => {
          t.classList.remove('text-secondary', 'dark:text-white', 'border-primary');
          t.classList.add('text-gray-600', 'dark:text-gray-300', 'border-transparent');
        });
        
        this.classList.remove('text-gray-600', 'dark:text-gray-300', 'border-transparent');
        this.classList.add('text-secondary', 'dark:text-white', 'border-primary');
        
        document.getElementById('currentTab').classList.add('hidden');
        document.getElementById('forecastTab').classList.add('hidden');
        document.getElementById('historicalTab').classList.add('hidden');
        document.getElementById('indicesTab').classList.add('hidden');
        
        document.getElementById(`${tabName}Tab`).classList.remove('hidden');
        
        if (tabName === 'indices' && window.DashboardState.selectedField && !window.DashboardState.selectedField.properties.indexValue) {
          IndexManager.calculateFieldIndex(window.DashboardState.selectedField);
        }
      });
    });
  },

  initMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const panel = document.getElementById('panel');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const panelOverlay = document.getElementById('panelOverlay');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const panelToggle = document.getElementById('panelToggle');
    
    sidebarToggle.addEventListener('click', function() {
      sidebar.classList.toggle('active');
      sidebarOverlay.classList.toggle('active');
      panel.classList.remove('active');
      panelOverlay.classList.remove('active');
    });
    
    panelToggle.addEventListener('click', function() {
      panel.classList.toggle('active');
      panelOverlay.classList.toggle('active');
      sidebar.classList.remove('active');
      sidebarOverlay.classList.remove('active');
    });
    
    sidebarOverlay.addEventListener('click', function() {
      sidebar.classList.remove('active');
      this.classList.remove('active');
    });
    
    panelOverlay.addEventListener('click', function() {
      panel.classList.remove('active');
      this.classList.remove('active');
    });
  },

  initDateRangeButtons() {
    document.getElementById('applyDates').addEventListener('click', () => {
      const fromDate = document.getElementById('fromDate').value;
      const toDate = document.getElementById('toDate').value;
      
      if (!fromDate || !toDate) {
        Notifications.show('Please select valid dates', 'warning');
        return;
      }
      
      if (new Date(fromDate) > new Date(toDate)) {
        Notifications.show('From date must be earlier than to date', 'warning');
        return;
      }
      
      window.DashboardState.dateRange.start = fromDate;
      window.DashboardState.dateRange.end = toDate;
      
      Notifications.show('Date range updated', 'success');
      
      if (window.DashboardState.selectedField) {
        WeatherManager.fetchWeatherData(window.DashboardState.selectedField);
        
        if (MapManager.currentMapMode === 'index') {
          MapManager.layerTransitionInProgress = true;
          IndexManager.lastIndexResponse = null;
          IndexManager.preloadedIndexData = null;
          
          try {
            if (MapManager.currentIndexLayer && MapManager.getMap().hasLayer(MapManager.currentIndexLayer)) {
              MapManager.getMap().removeLayer(MapManager.currentIndexLayer);
            }
            MapManager.currentIndexLayer = null;
          } catch (e) {
            console.error("Error removing index layer:", e);
          }
          
          IndexManager.loadIndexLayer(window.DashboardState.selectedField);
        }
      }
    });
    
    document.getElementById('resetDates').addEventListener('click', () => {
      const defaultRange = Utils.getDefaultDateRange(CONFIG.DATE.DEFAULT_RANGE_DAYS);
      document.getElementById('fromDate').value = defaultRange.start;
      document.getElementById('toDate').value = defaultRange.end;
      window.DashboardState.dateRange = defaultRange;
      
      Notifications.show('Date range reset', 'info');
      
      if (window.DashboardState.selectedField) {
        WeatherManager.fetchWeatherData(window.DashboardState.selectedField);
        if (MapManager.currentMapMode === 'index') {
          IndexManager.loadIndexLayer(window.DashboardState.selectedField);
        }
      }
    });
  },

  initComingSoonHandlers() {
    const comingSoonItems = document.querySelectorAll('[data-coming-soon]');
    const comingSoonOverlay = document.getElementById('comingSoonOverlay');
    const comingSoonMessage = document.getElementById('comingSoonMessage');
    const closeComingSoonBtn = document.getElementById('closeComingSoon');
    
    const comingSoonMessages = {
      'crop-signature': 'Machine-learning based crop mapping will provide automated crop type identification and monitoring using satellite imagery and AI algorithms.'
    };
    
    comingSoonItems.forEach(item => {
      item.addEventListener('click', function() {
        const featureKey = this.getAttribute('data-coming-soon');
        const message = comingSoonMessages[featureKey] || 'This feature is currently under development and will be available soon.';
        
        comingSoonMessage.textContent = message;
        comingSoonOverlay.classList.remove('hidden');
      });
    });
    
    closeComingSoonBtn.addEventListener('click', function() {
      comingSoonOverlay.classList.add('hidden');
    });
    
    comingSoonOverlay.addEventListener('click', function(e) {
      if (e.target === comingSoonOverlay) {
        comingSoonOverlay.classList.add('hidden');
      }
    });
  }
};
