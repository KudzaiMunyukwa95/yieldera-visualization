/**
 * YIELDERA DASHBOARD UTILITIES
 * Common utility functions used across the application
 */

const Utils = {
  /**
   * Format date for display
   * @param {string} dateStr - ISO date string
   * @returns {string} Formatted date
   */
  formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  },

  /**
   * Format user name to proper case
   * @param {string} fullName - Full name of user
   * @returns {string} Properly formatted name
   */
  formatUserName(fullName) {
    if (!fullName) return 'User';
    const nameParts = fullName.trim().split(/\s+/);
    const formattedParts = nameParts.map(part => 
      part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()
    );
    return formattedParts.join(' ');
  },

  /**
   * Generate initials from user name
   * @param {string} fullName - Full name of user
   * @returns {string} User initials
   */
  generateInitials(fullName) {
    if (!fullName) return 'U';
    const nameParts = fullName.trim().split(/\s+/);
    if (nameParts.length === 1) {
      return nameParts[0].charAt(0).toUpperCase();
    }
    return (nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0)).toUpperCase();
  },

  /**
   * Debug logging function
   * @param {string} message - Debug message
   * @param {*} data - Optional data to log
   */
  debugLog(message, data) {
    console.log(`[DEBUG] ${message}`, data || '');
  },

  /**
   * Get weather icon class based on weather code
   * @param {number} code - WMO weather code
   * @returns {string} FontAwesome icon class
   */
  getWeatherIconClass(code) {
    switch(true) {
      case code === 0:
      case code === 1:
        return 'fas fa-sun text-yellow-500';
      case code === 2:
        return 'fas fa-cloud-sun text-yellow-400';
      case code === 3:
        return 'fas fa-cloud text-gray-400';
      case [45, 48].includes(code):
        return 'fas fa-smog text-gray-400';
      case [51, 53, 55, 56, 57].includes(code):
        return 'fas fa-cloud-rain text-blue-300';
      case [61, 63, 65, 66, 67].includes(code):
        return 'fas fa-cloud-showers-heavy text-blue-500';
      case [71, 73, 75, 77].includes(code):
        return 'fas fa-snowflake text-blue-200';
      case [80, 81, 82].includes(code):
        return 'fas fa-cloud-showers-heavy text-blue-600';
      case [85, 86].includes(code):
        return 'fas fa-snowflake text-blue-300';
      case [95, 96, 99].includes(code):
        return 'fas fa-bolt text-yellow-500';
      default:
        return 'fas fa-cloud text-gray-400';
    }
  },

  /**
   * Get weather description from WMO code
   * @param {number} code - WMO weather code
   * @returns {string} Weather description
   */
  getWeatherDescription(code) {
    const weatherCodes = {
      0: "Clear sky",
      1: "Mainly clear",
      2: "Partly cloudy",
      3: "Overcast",
      45: "Fog",
      48: "Depositing rime fog",
      51: "Light drizzle",
      53: "Moderate drizzle",
      55: "Dense drizzle",
      56: "Light freezing drizzle",
      57: "Dense freezing drizzle",
      61: "Slight rain",
      63: "Moderate rain",
      65: "Heavy rain",
      66: "Light freezing rain",
      67: "Heavy freezing rain",
      71: "Slight snow fall",
      73: "Moderate snow fall",
      75: "Heavy snow fall",
      77: "Snow grains",
      80: "Slight rain showers",
      81: "Moderate rain showers",
      82: "Violent rain showers",
      85: "Slight snow showers",
      86: "Heavy snow showers",
      95: "Thunderstorm",
      96: "Thunderstorm with slight hail",
      99: "Thunderstorm with heavy hail"
    };
    return weatherCodes[code] || `Code ${code}`;
  },

  /**
   * Update loading progress
   * @param {number} percent - Progress percentage (0-100)
   * @param {string} message - Optional status message
   */
  updateLoadingProgress(percent, message) {
    const progressBar = document.getElementById('loadingProgress');
    const loadingMessage = document.getElementById('loadingMessage');
    
    if (progressBar) {
      progressBar.style.width = `${percent}%`;
    }
    
    if (message && loadingMessage) {
      loadingMessage.textContent = message;
    }
  },

  /**
   * Hide loading overlay with fade effect
   */
  hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
      overlay.style.opacity = '0';
      overlay.style.transition = 'opacity 0.5s';
      setTimeout(() => {
        overlay.style.display = 'none';
      }, 500);
    }
  },

  /**
   * Set default date range (today and N days ago)
   * @param {number} daysAgo - Number of days back from today
   * @returns {Object} Object with start and end date strings
   */
  getDefaultDateRange(daysAgo = 14) {
    const today = new Date();
    const startDate = new Date();
    startDate.setDate(today.getDate() - daysAgo);
    
    return {
      start: startDate.toISOString().split('T')[0],
      end: today.toISOString().split('T')[0]
    };
  }
};

// Export utilities
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Utils;
}
