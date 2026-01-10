/**
 * AUTHENTICATION CHECK
 * Handles user authentication and redirects
 * 
 * FIXED: Added proper timing and retry logic to prevent race conditions
 */

(function() {
  // Prevent multiple auth checks
  if (window.authCheckInProgress) {
    return;
  }
  window.authCheckInProgress = true;

  // Function to update user information in UI
  function updateUserInfo() {
    if (window.currentUser) {
      const displayName = Utils.formatUserName(window.currentUser.name);
      const initials = Utils.generateInitials(window.currentUser.name);
      
      let entityDisplay = 'User';
      if (window.currentUser.entity_name) {
        entityDisplay = window.currentUser.entity_name;
      } else if (window.currentUser.entity_type) {
        entityDisplay = window.currentUser.entity_type.charAt(0).toUpperCase() + window.currentUser.entity_type.slice(1);
      } else if (window.currentUser.role) {
        entityDisplay = window.currentUser.role.charAt(0).toUpperCase() + window.currentUser.role.slice(1);
      }
      
      const userAvatar = document.getElementById('userAvatar');
      const userName = document.getElementById('userName');
      const userEntity = document.getElementById('userEntity');
      
      if (userAvatar) userAvatar.textContent = initials;
      if (userName) userName.textContent = displayName;
      if (userEntity) userEntity.textContent = entityDisplay;
      
      console.log(`User role: ${window.currentUser.role}, Entity type: ${window.currentUser.entity_type}, Entity ID: ${window.currentUser.entity_id}, Entity name: ${window.currentUser.entity_name || 'N/A'}`);
      
      const adminMenu = document.getElementById('adminMenu');
      if (adminMenu) {
        adminMenu.style.display = window.currentUser.role === 'admin' ? 'block' : 'none';
      }
    }
  }

  // Check authentication with retry logic
  function checkAuthentication(retryCount = 0) {
    const maxRetries = 3;
    const retryDelay = 500; // ms
    
    fetch('../api/auth/check-login.php', {
      method: 'GET',
      credentials: 'same-origin', // Ensure cookies are sent
      cache: 'no-cache',
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    })
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        console.log('Auth check response:', data);
        
        if (!data.success) {
          // Only redirect if we're certain user is not logged in
          if (data.error || retryCount >= maxRetries) {
            console.log('User not authenticated, redirecting to login...');
            const currentPath = window.location.pathname;
            window.location.href = '../login.html?returnUrl=' + encodeURIComponent(currentPath);
          } else {
            // Retry if uncertain
            console.log(`Auth check uncertain, retrying (${retryCount + 1}/${maxRetries})...`);
            setTimeout(() => {
              checkAuthentication(retryCount + 1);
            }, retryDelay);
          }
        } else {
          // User is authenticated
          console.log('User authenticated successfully');
          
          window.currentUser = {
            id: data.user_id,
            email: data.user_email,
            role: data.user_role,
            entity_type: data.entity_type,
            entity_id: data.entity_id,
            name: data.user_name || data.user_email?.split('@')[0] || 'User',
            entity_name: data.entity_name,
            entity_type_display: data.entity_type_display
          };
          
          // Update UI when DOM is ready
          if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', updateUserInfo);
          } else {
            updateUserInfo();
          }
          
          // Make body visible
          document.body.style.visibility = 'visible';
          window.authCheckInProgress = false;
        }
      })
      .catch(err => {
        console.error('Authentication check failed:', err);
        
        // Retry on network errors
        if (retryCount < maxRetries) {
          console.log(`Network error, retrying (${retryCount + 1}/${maxRetries})...`);
          setTimeout(() => {
            checkAuthentication(retryCount + 1);
          }, retryDelay);
        } else {
          // After max retries, redirect to login
          console.log('Max retries reached, redirecting to login...');
          window.location.href = '../login.html';
        }
      });
  }

  // Wait for DOM to be ready before checking auth
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      // Small delay to ensure cookies/session are available
      setTimeout(() => {
        checkAuthentication();
      }, 100);
    });
  } else {
    // DOM already loaded
    setTimeout(() => {
      checkAuthentication();
    }, 100);
  }
})();