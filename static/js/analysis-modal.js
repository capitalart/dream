// In static/js/analysis-modal.js

document.addEventListener('DOMContentLoaded', function() {
  const modal = document.getElementById('analysis-modal');
  if (!modal) return; // Exit if the modal isn't on the page

  const bar = document.getElementById('analysis-bar');
  const statusEl = document.getElementById('analysis-status');
  const closeBtn = document.getElementById('analysis-close');
  const timerEl = document.getElementById('analysis-timer'); // Get the timer element
  const statusUrl = document.body.dataset.analysisStatusUrl;

  let pollStatus;
  let timerInterval;
  let secondsElapsed = 0;

  // --- Timer Functions ---
  function startTimer() {
    if (timerEl) {
        secondsElapsed = 0;
        timerEl.textContent = '0s';
        timerInterval = setInterval(() => {
            secondsElapsed++;
            timerEl.textContent = `${secondsElapsed}s`;
        }, 1000);
    }
  }

  function stopTimer() {
    clearInterval(timerInterval);
  }

  // --- Modal Control Functions ---
  function openModal(opts = {}) {
    modal.classList.add('active');
    statusEl.textContent = 'Starting...';
    bar.style.width = '0%';
    startTimer(); // Start the timer when the modal opens
    
    if (opts.message) {
      statusEl.textContent = opts.message;
      stopTimer(); // Stop timer if it's just a message
    } else {
      fetchStatus();
      pollStatus = setInterval(fetchStatus, 1500);
    }
  }

  function closeModal() {
    modal.classList.remove('active');
    stopTimer(); // Stop the timer when the modal closes
    clearInterval(pollStatus);
  }

  function fetchStatus() {
    if (!statusUrl) return;
    fetch(statusUrl)
      .then(r => r.json())
      .then(d => {
        const pct = d.percent || 0;
        bar.style.width = pct + '%';
        
        if (d.status === 'failed') {
          statusEl.textContent = 'FAILED: ' + (d.error || 'Unknown error');
          stopTimer();
          clearInterval(pollStatus);
        } else if (d.status === 'complete') {
          statusEl.textContent = 'Complete';
          stopTimer();
          clearInterval(pollStatus);
        } else {
          statusEl.textContent = d.step || 'Analyzing...';
        }
      });
  }
  
  function setMessage(msg) {
      if(statusEl) statusEl.textContent = msg;
      stopTimer();
      clearInterval(pollStatus);
  }

  // --- Event Listeners ---
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  modal.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { e.preventDefault(); closeModal(); }
  });

  // Make the modal functions globally accessible
  window.AnalysisModal = { open: openModal, close: closeModal, setMessage: setMessage };
});