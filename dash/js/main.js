/**
 * MAIN INITIALIZATION
 * Orchestrates all modules and initializes the dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize global state
  window.DashboardState = {
    map: null,
    selectedField: null,
    fieldsData: [],
    weatherData: [],
    indexData: [],
    forecastData: [],
    currentIndexType: 'RGB',
    dateRange: { start: '', end: '' },
    userRole: '',
    userEntityId: 0,
    userEntityType: ''
  };

  // Initialize dashboard
  function initDashboard() {
    Utils.updateLoadingProgress(5, 'Starting dashboard initialization...');
    
    try {
      // Initialize modules in correct order
      MobileDetect.init();
      window.DashboardState.map = MapManager.init();
      
      // Set default date range
      const dateRange = Utils.getDefaultDateRange(CONFIG.DATE.DEFAULT_RANGE_DAYS);
      window.DashboardState.dateRange = dateRange;
      document.getElementById('fromDate').value = dateRange.start;
      document.getElementById('toDate').value = dateRange.end;
      
      Utils.updateLoadingProgress(50, 'Setting date range...');
      
      UIManager.init();
      ReportGenerator.init();
      
      Utils.updateLoadingProgress(70, 'Initializing UI components...');
      
      // Set user vars from auth
      if (window.currentUser) {
        window.DashboardState.userRole = window.currentUser.role || '';
        window.DashboardState.userEntityId = window.currentUser.entity_id || 0;
        window.DashboardState.userEntityType = window.currentUser.entity_type || '';
      }
      
      FieldManager.init();
      Utils.updateLoadingProgress(90, 'Loading field data...');
      
    } catch (error) {
      console.error('Error initializing dashboard:', error);
      document.getElementById('loadingMessage').textContent = 'Error initializing dashboard: ' + error.message;
      document.getElementById('loadingProgress').style.backgroundColor = '#ef4444';
      Utils.hideLoadingOverlay();
    }
  }

  // Logout functionality
  document.getElementById('logout-link').addEventListener('click', function(e) {
    e.preventDefault();
    
    const loadingOverlay = document.getElementById('loadingOverlay');
    document.getElementById('loadingMessage').textContent = 'Logging out...';
    loadingOverlay.style.display = 'flex';
    loadingOverlay.style.opacity = '1';
    
    fetch('../api/auth/logout.php')
      .then(() => {
        window.location.href = '../login.html';
      })
      .catch(err => {
        console.error('Logout error:', err);
        window.location.href = '../login.html';
      });
  });

  // Start the dashboard
  initDashboard();
});
