// In static/js/artworks.js

document.addEventListener('DOMContentLoaded', () => {
  // --- Event Listener for all "Analyze" buttons ---
  document.querySelectorAll('.btn-analyze').forEach(btn => {
    btn.addEventListener('click', ev => {
      ev.preventDefault();
      const card = btn.closest('.gallery-card');
      if (!card) return;
      
      const provider = btn.dataset.provider;
      const filename = card.dataset.filename;
      
      if (!filename || !provider) {
        alert('Error: Missing filename or provider information.');
        return;
      }
      
      // Call the function to run the analysis
      runAnalyze(card, provider, filename);
    });
  });

  // --- Event Listener for all "Sign Artwork" buttons ---
  document.querySelectorAll('.btn-sign').forEach(btn => {
    btn.addEventListener('click', ev => {
      ev.preventDefault();
      const card = btn.closest('.gallery-card');
      if (!card) return;
      
      const baseName = btn.dataset.base;
      if (!baseName) {
        alert('Error: Missing artwork base name.');
        return;
      }

      showOverlay(card, 'Signing…');
      
      fetch(`/sign-artwork/${baseName}`, { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
          if (data.success) {
            // Success! Reload the thumbnail to show the signed version
            const thumb = card.querySelector('.card-img-top');
            thumb.src = `${thumb.src.split('?')[0]}?t=${new Date().getTime()}`;
            btn.textContent = 'Signed ✔';
            btn.disabled = true;
          } else {
            alert(`Signing failed: ${data.error}`);
          }
        })
        .catch(error => {
          console.error('Signing error:', error);
          alert(`An error occurred: ${error.error || 'Check console for details.'}`);
        })
        .finally(() => {
          hideOverlay(card);
        });
    });
  });
});

// --- Helper function to show a loading overlay on a card ---
function showOverlay(card, text) {
  let ov = card.querySelector('.card-overlay');
  if (!ov) {
    ov = document.createElement('div');
    ov.className = 'card-overlay';
    card.appendChild(ov);
  }
  ov.innerHTML = `<span class="spinner"></span> ${text}`;
  ov.classList.remove('hidden');
}

// --- Helper function to hide a loading overlay ---
function hideOverlay(card) {
  const ov = card.querySelector('.card-overlay');
  if (ov) ov.classList.add('hidden');
}

// --- Main function to handle the analysis process ---
function runAnalyze(card, provider, filename) {
  // Check if the provider API is configured
  const isConfigured = document.body.dataset[`${provider}Ok`] === 'true';
  if (!isConfigured) {
    alert(`${provider.charAt(0).toUpperCase() + provider.slice(1)} API Key is not configured. Please contact the administrator.`);
    return;
  }

  // Show the analysis modal and the card overlay
  if (window.AnalysisModal) window.AnalysisModal.open();
  showOverlay(card, `Analyzing…`);

  // Get the aspect ratio from the card's data attribute
  const aspect = card.dataset.aspect;
  // Build the correct URL
  const actionUrl = `/analyze/${encodeURIComponent(aspect)}/${encodeURIComponent(filename)}`;

  const formData = new FormData();
  formData.append('provider', provider);

  fetch(actionUrl, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    body: formData
  })
  .then(resp => {
    if (!resp.ok) {
      return resp.json().then(errData => Promise.reject(errData));
    }
    return resp.json();
  })
  .then(data => {
    if (data.success && data.redirect_url) {
      if (window.AnalysisModal) window.AnalysisModal.setMessage('Complete! Redirecting...');
      // Wait a moment before redirecting
      setTimeout(() => {
        window.location.href = data.redirect_url;
      }, 1200);
    } else {
      throw new Error(data.error || 'Analysis failed to return a valid redirect URL.');
    }
  })
  .catch(error => {
    console.error('Analysis fetch error:', error);
    if (window.AnalysisModal) window.AnalysisModal.setMessage(`Error: ${error.error || 'A server error occurred.'}`);
    hideOverlay(card);
  });
}