// static/js/edit_listing.js

document.addEventListener('DOMContentLoaded', () => {
  // === [ 0. FALLBACK IMAGE HANDLER FOR MOCKUP THUMBS ] ===
  document.querySelectorAll('.mockup-thumb-img').forEach(img => {
    img.addEventListener('error', function handleError() {
      if (this.dataset.fallback && this.src !== this.dataset.fallback) {
        this.src = this.dataset.fallback;
      }
      this.onerror = null; // Prevent loop
    });
  });

  // === [ 1. MODAL CAROUSEL LOGIC ] ===
  const carousel = document.getElementById('mockup-carousel');
  const carouselImg = document.getElementById('carousel-img');
  const images = Array.from(document.querySelectorAll('.mockup-img-link, .main-thumb-link'));
  let currentIndex = 0;

  function showImage(index) {
    if (index >= 0 && index < images.length) {
      currentIndex = index;
      carouselImg.src = images[currentIndex].dataset.img;
      carousel.classList.add('active');
    }
  }

  function hideCarousel() {
    carousel.classList.remove('active');
  }

  images.forEach((link, index) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      showImage(index);
    });
  });

  if (carousel) {
    carousel.querySelector('#carousel-close').addEventListener('click', hideCarousel);
    carousel.querySelector('#carousel-prev').addEventListener('click', () => showImage((currentIndex - 1 + images.length) % images.length));
    carousel.querySelector('#carousel-next').addEventListener('click', () => showImage((currentIndex + 1) % images.length));
    
    carousel.addEventListener('click', (e) => {
        if (e.target === carousel) {
            hideCarousel();
        }
    });

    document.addEventListener('keydown', (e) => {
      if (carousel.classList.contains('active')) {
        if (e.key === 'ArrowLeft') showImage((currentIndex - 1 + images.length) % images.length);
        if (e.key === 'ArrowRight') showImage((currentIndex + 1) % images.length);
        if (e.key === 'Escape') hideCarousel();
      }
    });
  }

  // === [ 2. ASYNC MOCKUP SWAP LOGIC ] ===
  document.querySelectorAll('.swap-btn').forEach(button => {
    button.addEventListener('click', async (event) => {
      event.preventDefault();

      const mockupCard = button.closest('.mockup-card'); // Get the parent card
      if (mockupCard.classList.contains('swapping')) return; // Prevent double clicks

      const slotIndex = parseInt(button.dataset.index, 10);
      const controlsContainer = button.closest('.swap-controls');
      const select = controlsContainer.querySelector('select[name="new_category"]');
      const newCategory = select.value;
      
      const currentImg = document.getElementById(`mockup-img-${slotIndex}`);
      const currentSrc = currentImg ? currentImg.src : '';

      mockupCard.classList.add('swapping');

      try {
        const response = await fetch('/edit/swap-mockup-api', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            seo_folder: window.EDIT_INFO.seoFolder,
            slot_index: slotIndex,
            new_category: newCategory,
            aspect: window.EDIT_INFO.aspect,
            current_mockup_src: currentSrc.split('/').pop().split('?')[0]
          }),
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
          throw new Error(data.error || 'Failed to swap mockup.');
        }

        const timestamp = new Date().getTime();
        const mockupImg = document.getElementById(`mockup-img-${slotIndex}`);
        const mockupLink = document.getElementById(`mockup-link-${slotIndex}`);

        if (mockupImg) {
          mockupImg.src = `${data.new_thumb_url}?t=${timestamp}`;
          mockupImg.dataset.fallback = `${data.new_mockup_url}?t=${timestamp}`;
        }
        if (mockupLink) {
          mockupLink.href = `${data.new_mockup_url}?t=${timestamp}`;
          mockupLink.dataset.img = `${data.new_mockup_url}?t=${timestamp}`;
        }

      } catch (error) {
        console.error('Swap failed:', error);
        alert(`Error: ${error.message}`);
      } finally {
        mockupCard.classList.remove('swapping');
      }
    });
  });

  // === [ 3. ASYNC UPDATE IMAGE URLS ] ===
  const updateLinksBtn = document.getElementById('update-links-btn');
  if (updateLinksBtn) {
    updateLinksBtn.addEventListener('click', async () => {
      const originalText = updateLinksBtn.textContent;
      updateLinksBtn.textContent = 'Updating...';
      updateLinksBtn.disabled = true;

      try {
        const url = `/update-links/${window.EDIT_INFO.aspect}/${window.EDIT_INFO.seoFolder}.jpg`;
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Accept': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Server error');
        
        const joined = data.images.join('\n');
        document.getElementById('images-input').value = joined;
        const publicBox = document.getElementById('public-image-urls');
        if (publicBox) publicBox.value = joined;
      } catch (error) {
        alert(`Error updating image links: ${error.message}`);
      } finally {
        updateLinksBtn.textContent = originalText;
        updateLinksBtn.disabled = false;
      }
    });
  }
  
  // === [ 4. ASYNC GENERIC TEXT REWORDING ] ===
  const rewordContainer = document.getElementById('generic-text-reworder');
  if (rewordContainer) {
    const descriptionTextarea = document.getElementById('description-input');
    const spinner = document.getElementById('reword-spinner');
    const genericTextInput = document.getElementById('generic-text-input');
    const buttons = rewordContainer.querySelectorAll('button');

    rewordContainer.addEventListener('click', async (event) => {
      if (!event.target.matches('#reword-openai-btn, #reword-gemini-btn')) {
        return;
      }
      const button = event.target;
      const provider = button.dataset.provider;
      const genericText = genericTextInput.value;
      const currentDescription = descriptionTextarea.value;
      
      buttons.forEach(b => b.disabled = true);
      spinner.style.display = 'block';

      try {
          const response = await fetch('/api/reword-generic-text', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  provider: provider,
                  artwork_description: currentDescription,
                  generic_text: genericText
              })
          });

          const data = await response.json();
          if (!response.ok) throw new Error(data.error || 'Failed to reword text.');
          
          genericTextInput.value = data.reworded_text;

      } catch (error) {
          console.error('Reword failed:', error);
          alert(`Error: ${error.message}`);
      } finally {
          buttons.forEach(b => b.disabled = false);
          spinner.style.display = 'none';
      }
    });
  }

  // === [ 5. RE-ANALYZE MODAL TRIGGER ] ===
  const analyzeForm = document.querySelector('.analyze-form');
  if (analyzeForm) {
    analyzeForm.addEventListener('submit', () => {
      // Open the modal from analysis-modal.js when the form is submitted
      if (window.AnalysisModal) {
        window.AnalysisModal.open();
      }
    });
  }
});