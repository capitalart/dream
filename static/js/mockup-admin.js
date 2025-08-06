document.addEventListener('DOMContentLoaded', () => {
    // --- Element Definitions ---
    const mockupGrid = document.getElementById('mockup-grid');
    const arSelector = document.getElementById('aspect-ratio-selector');
    const perPageSelector = document.getElementById('per-page-selector');
    const sortSelector = document.getElementById('sort-selector');
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const imageModal = document.getElementById('image-modal');
    const duplicatesModal = document.getElementById('duplicates-modal');
    const uploadModal = document.getElementById('upload-modal');
    const uploadModalContent = `
        <div class="analysis-box">
            <img src="/static/icons/svg/light/upload-light.svg" class="progress-icon" alt="">
            <h3>Uploading Mockups...</h3>
            <div id="upload-filename" class="analysis-status"></div>
            <div class="analysis-progress">
                <div id="upload-bar" class="analysis-progress-bar"></div>
            </div>
            <div id="upload-status" class="analysis-status">0%</div>
        </div>`;

    // --- Page Controls ---
    function updateUrlParams() {
        const aspect = arSelector.value;
        const perPage = perPageSelector.value;
        const sortBy = sortSelector.value;
        const urlParams = new URLSearchParams(window.location.search);
        const category = urlParams.get('category') || 'All';
        window.location.href = `/admin/mockups/${aspect}?per_page=${perPage}&category=${category}&sort=${sortBy}`;
    }

    if (arSelector) arSelector.addEventListener('change', updateUrlParams);
    if (perPageSelector) perPageSelector.addEventListener('change', updateUrlParams);
    if (sortSelector) sortSelector.addEventListener('change', updateUrlParams);

    function selectOptionByText(selectEl, textToFind) {
        const text = (textToFind || '').trim().toLowerCase();
        for (let i = 0; i < selectEl.options.length; i++) {
            const option = selectEl.options[i];
            if (option.text.trim().toLowerCase() === text) {
                selectEl.selectedIndex = i;
                return;
            }
        }
    }

    // --- Main Grid Event Delegation ---
    if (mockupGrid) {
        mockupGrid.addEventListener('click', async (e) => {
            const card = e.target.closest('.gallery-card');
            if (!card) return;

            const filename = card.dataset.filename;
            const originalCategory = card.dataset.category;
            const overlay = card.querySelector('.card-overlay');
            const button = e.target;
            const currentAspect = arSelector.value;

            if (button.classList.contains('card-img-top')) {
                const fullSizeUrl = button.dataset.fullsizeUrl;
                if (fullSizeUrl && imageModal) {
                    imageModal.querySelector('.modal-img').src = fullSizeUrl;
                    imageModal.style.display = 'flex';
                }
                return;
            }

            const actionsContainer = card.querySelector('.categorize-actions');
            if (actionsContainer) {
                if (button.classList.contains('btn-categorize')) {
                    const selectElement = actionsContainer.querySelector('select');
                    overlay.innerHTML = `<span class="spinner"></span> Asking AI...`;
                    overlay.classList.remove('hidden');
                    button.disabled = true;
                    try {
                        const response = await fetch("/admin/mockups/suggest-category", {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ filename: filename, aspect: currentAspect })
                        });
                        const result = await response.json();
                        if (result.success) {
                            selectOptionByText(selectElement, result.suggestion);
                        } else {
                            alert(`Error: ${result.error}`);
                        }
                    } catch (err) {
                        alert('A network error occurred.');
                    } finally {
                        overlay.classList.add('hidden');
                        button.disabled = false;
                    }
                }

                if (button.classList.contains('btn-save-move')) {
                    const newCategory = actionsContainer.querySelector('select').value;
                    if (!newCategory) {
                        alert('Please select a category.');
                        return;
                    }
                    overlay.innerHTML = `<span class="spinner"></span> Moving...`;
                    overlay.classList.remove('hidden');

                    const response = await fetch("/admin/mockups/move-mockup", {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ filename, aspect: currentAspect, original_category: originalCategory, new_category: newCategory })
                    });
                    const result = await response.json();
                    if (result.success) {
                        card.remove(); 
                    } else {
                        overlay.textContent = `Error: ${result.error}`;
                    }
                }
            }
            
            if (button.classList.contains('btn-delete')) {
                if (!confirm(`Are you sure you want to permanently delete "${filename}"?`)) return;
                overlay.innerHTML = `<span class="spinner"></span> Deleting...`;
                overlay.classList.remove('hidden');

                const response = await fetch("/admin/mockups/delete-mockup", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ filename, aspect: currentAspect, category: originalCategory })
                });
                const result = await response.json();
                if (result.success) {
                    card.remove();
                } else {
                    overlay.textContent = `Error: ${result.error}`;
                }
            }
        });
    }

    // --- Modal Logic ---
    [imageModal, duplicatesModal].forEach(modal => {
        if (modal) {
            const closeBtn = modal.querySelector('.modal-close');
            if(closeBtn) closeBtn.addEventListener('click', () => modal.style.display = 'none');
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
        }
    });

    // --- Find Duplicates Logic ---
    const findDuplicatesBtn = document.getElementById('find-duplicates-btn');
    if (findDuplicatesBtn) {
        findDuplicatesBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const btn = e.target;
            const originalText = btn.textContent;
            btn.textContent = 'Scanning...';
            btn.disabled = true;

            try {
                const response = await fetch(btn.dataset.url);
                const data = await response.json();
                const listEl = document.getElementById('duplicates-list');
                listEl.innerHTML = '';

                if (data.duplicates.length > 0) {
                    const ul = document.createElement('ul');
                    data.duplicates.forEach(pair => {
                        const li = document.createElement('li');
                        li.innerHTML = `<strong>${pair.original}</strong><br>is a duplicate of<br><em>${pair.duplicate}</em>`;
                        ul.appendChild(li);
                    });
                    listEl.appendChild(ul);
                } else {
                    listEl.innerHTML = '<p>No duplicates found. Good job!</p>';
                }
                duplicatesModal.style.display = 'flex';
            } catch (error) {
                alert('Failed to check for duplicates.');
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    }

    // --- Drag & Drop Upload Logic ---
    if (dropzone && fileInput && uploadModal) {
        function uploadFile(file) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                const formData = new FormData();
                const currentAspect = arSelector.value;
                formData.append('mockup_files', file);

                xhr.upload.addEventListener('progress', e => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        const progressBar = uploadModal.querySelector('#upload-bar');
                        const statusEl = uploadModal.querySelector('#upload-status');
                        if(progressBar) progressBar.style.width = percent + '%';
                        if(statusEl) statusEl.textContent = `${percent}%`;
                    }
                });
                xhr.addEventListener('load', () => xhr.status < 400 ? resolve() : reject(new Error(`Server responded with ${xhr.status}`)));
                xhr.addEventListener('error', () => reject(new Error('Network error during upload.')));
                xhr.open('POST', `/admin/mockups/upload/${currentAspect}`, true);
                xhr.send(formData);
            });
        }

        async function uploadFiles(files) {
            if (!files || !files.length) return;
            uploadModal.innerHTML = uploadModalContent;
            uploadModal.classList.add('active');
            
            const progressBar = uploadModal.querySelector('#upload-bar');
            const statusEl = uploadModal.querySelector('#upload-status');
            const filenameEl = uploadModal.querySelector('#upload-filename');

            for (const file of Array.from(files)) {
                if(filenameEl) filenameEl.textContent = `Uploading: ${file.name}`;
                if(progressBar) progressBar.style.width = '0%';
                if(statusEl) statusEl.textContent = '0%';
                try {
                    await uploadFile(file);
                    if(statusEl) statusEl.textContent = 'Complete!';
                } catch (error) {
                    if(statusEl) statusEl.textContent = `Error uploading ${file.name}.`;
                    await new Promise(res => setTimeout(res, 2000));
                }
            }
            window.location.reload();
        }

        ['dragenter', 'dragover'].forEach(evt => dropzone.addEventListener(evt, e => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        }));
        ['dragleave', 'drop'].forEach(evt => dropzone.addEventListener(evt, () => dropzone.classList.remove('dragover')));
        dropzone.addEventListener('drop', e => {
            e.preventDefault();
            uploadFiles(e.dataTransfer.files);
        });
        dropzone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => uploadFiles(fileInput.files));
    }
});