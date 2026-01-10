/**
 * NAVIGATION HIGHLIGHTING
 * Manages active navigation state
 */

document.addEventListener('DOMContentLoaded', function () {
  const pageMapping = {
    'dashboard.html': 'dashboard',
    'field_management.html': 'fields',
    'weather.html': 'weather',
    'estimator.html': 'estimator',
    'wrsi.html': 'wrsi',
    'frost.html': 'frost',
    'map.html': 'map',
    'pricing.html': 'pricing',
    'alerts.html': 'alerts',
    'settings.html': 'settings',
    'visualization.html': 'visualization',
    'visualization': 'visualization',
    'data.html': 'data',
    'data': 'data'
  };

  const navMapping = {
    'dashboard': 'a[href="dashboard.html"]',
    'fields': 'a[href="field_management.html"]',
    'weather': 'a[href="weather.html"]',
    'estimator': 'a[href="estimator.html"]',
    'wrsi': 'a[href="wrsi.html"]',
    'frost': 'a[href="frost.html"]',
    'map': 'a[href="map.html"]',
    'pricing': 'a[href="pricing.html"]',
    'alerts': 'a[href="alerts.html"]',
    'settings': 'a[href="settings.html"]',
    'visualization': 'a[href="visualization"]',
    'data': 'a[href="data"]'
  };

  function highlightCurrentPage() {
    try {
      document.querySelectorAll('.sidebar-nav-item').forEach(item => {
        item.classList.remove('active');
      });

      const path = window.location.pathname;
      const filename = path.split('/').pop() || 'dashboard.html';
      const currentPageKey = pageMapping[filename] || 'dashboard';
      const selector = navMapping[currentPageKey];

      if (selector) {
        const navItem = document.querySelector(selector);
        if (navItem && navItem.classList.contains('sidebar-nav-item')) {
          navItem.classList.add('active');
        }
      }
    } catch (error) {
      console.error('Navigation highlighting failed:', error);
    }
  }

  highlightCurrentPage();
});
