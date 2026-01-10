/**
 * MOBILE DEVICE DETECTION
 * Detects mobile devices and shows appropriate overlay
 */

const MobileDetect = {
  init() {
    const mobileOverlay = document.getElementById('mobileOverlay');
    const continueButton = document.getElementById('continueAnyway');
    
    if (window.innerWidth < 1024) {
      mobileOverlay.style.display = 'flex';
      continueButton.addEventListener('click', () => {
        mobileOverlay.style.display = 'none';
      });
    }
    
    window.addEventListener('resize', () => {
      if (window.innerWidth < 1024) {
        mobileOverlay.style.display = 'flex';
      } else {
        mobileOverlay.style.display = 'none';
      }
    });
  }
};