document.addEventListener('DOMContentLoaded', () => {
  const modalBg = document.getElementById('final-modal-bg');
  const modalImg = document.getElementById('final-modal-img');
  const closeBtn = document.getElementById('final-modal-close');
  const grid = document.querySelector('.finalised-grid');
  const viewKey = grid ? grid.dataset.viewKey || 'view' : 'view';
  document.querySelectorAll('.final-img-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      if (modalBg && modalImg) {
        modalImg.src = link.dataset.img;
        modalBg.style.display = 'flex';
      }
    });
  });
  if (closeBtn) closeBtn.onclick = () => {
    modalBg.style.display = 'none';
    modalImg.src = '';
  };
  if (modalBg) modalBg.onclick = e => {
    if (e.target === modalBg) {
      modalBg.style.display = 'none';
      modalImg.src = '';
    }
  };
  document.querySelectorAll('.locked-delete-form').forEach(f => {
    f.addEventListener('submit', ev => {
      const val = prompt('This listing is locked and will be permanently deleted. Type DELETE to confirm');
      if (val !== 'DELETE') { ev.preventDefault(); }
      else { f.querySelector('input[name="confirm"]').value = 'DELETE'; }
    });
  });
  const gBtn = document.getElementById('grid-view-btn');
  const lBtn = document.getElementById('list-view-btn');
  function apply(v) {
    if (!grid) return;
    if (v === 'list') { grid.classList.add('list-view'); }
    else { grid.classList.remove('list-view'); }
  }
  if (gBtn) gBtn.addEventListener('click', () => { apply('grid'); localStorage.setItem(viewKey, 'grid'); });
  if (lBtn) lBtn.addEventListener('click', () => { apply('list'); localStorage.setItem(viewKey, 'list'); });
  apply(localStorage.getItem(viewKey) || 'grid');
});
