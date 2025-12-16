/**
 * NOTIFICATION SYSTEM
 * Handles all toast notifications
 */

const Notifications = {
  show(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    const notification = document.createElement('div');
    
    let bgColor, textColor, icon;
    switch(type) {
      case 'success':
        bgColor = 'bg-green-500'; textColor = 'text-white'; icon = 'fa-check-circle';
        break;
      case 'error':
        bgColor = 'bg-red-500'; textColor = 'text-white'; icon = 'fa-exclamation-circle';
        break;
      case 'warning':
        bgColor = 'bg-yellow-500'; textColor = 'text-white'; icon = 'fa-exclamation-triangle';
        break;
      default:
        bgColor = 'bg-secondary'; textColor = 'text-white'; icon = 'fa-info-circle';
    }
    
    notification.className = `notification ${bgColor} ${textColor} px-4 py-3 rounded flex items-center`;
    notification.innerHTML = `
      <i class="fas ${icon} mr-3 flex-shrink-0"></i>
      <span class="flex-grow">${message}</span>
      <button class="ml-2 text-white opacity-70 hover:opacity-100 flex-shrink-0">
        <i class="fas fa-times"></i>
      </button>
    `;
    
    const closeBtn = notification.querySelector('button');
    closeBtn.addEventListener('click', () => this.hide(notification, container));
    
    container.appendChild(notification);
    setTimeout(() => this.hide(notification, container), CONFIG.UI.NOTIFICATION_DURATION);
  },

  hide(notification, container) {
    if (notification.parentNode) {
      notification.classList.add('hide');
      setTimeout(() => {
        if (notification.parentNode) {
          container.removeChild(notification);
        }
      }, 300);
    }
  }
};
