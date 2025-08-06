/* ================================
   ArtNarrator Upload JS (XMLHttpRequest for Progress)
   ================================ */

document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  
  // Modal elements
  const modal = document.getElementById('upload-modal');
  const progressBar = document.getElementById('upload-bar');
  const statusEl = document.getElementById('upload-status');
  const filenameEl = document.getElementById('upload-filename');

  function uploadFile(file) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('images', file);

      xhr.upload.addEventListener('progress', e => {
        if (e.lengthComputable) {
          const percentComplete = Math.round((e.loaded / e.total) * 100);
          progressBar.style.width = percentComplete + '%';
          statusEl.textContent = `${percentComplete}%`;
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.responseText);
        } else {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Upload failed due to a network error.')));
      xhr.addEventListener('abort', () => reject(new Error('Upload was aborted.')));

      xhr.open('POST', '/upload', true);
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.send(formData);
    });
  }

  async function uploadFiles(files) {
    if (!files || !files.length) return;
    
    modal.classList.add('active');

    for (const file of Array.from(files)) {
      filenameEl.textContent = `Uploading: ${file.name}`;
      progressBar.style.width = '0%';
      statusEl.textContent = '0%';
      
      try {
        await uploadFile(file);
        statusEl.textContent = 'Complete!';
      } catch (error) {
        statusEl.textContent = `Error: ${error.message}`;
        await new Promise(res => setTimeout(res, 2000)); // Show error for 2s
      }
    }

    // Redirect after all files are processed
    modal.classList.remove('active');
    window.location.href = '/artworks';
  }

  if (dropzone) {
    ['dragenter', 'dragover'].forEach(evt => {
      dropzone.addEventListener(evt, e => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });
    });
    ['dragleave', 'drop'].forEach(evt => {
      dropzone.addEventListener(evt, () => dropzone.classList.remove('dragover'));
    });
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      uploadFiles(e.dataTransfer.files);
    });
    dropzone.addEventListener('click', () => fileInput.click());
  }

  if (fileInput) {
    fileInput.addEventListener('change', () => uploadFiles(fileInput.files));
  }
});