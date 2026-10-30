// Overstock Outlet Client-side Application Scripts

function showToast(message, type = 'info') {
  const toastEl = document.getElementById('liveToast');
  if (!toastEl) return;

  const msgEl = document.getElementById('toastMessage');
  const iconEl = document.getElementById('toastIcon');

  msgEl.textContent = message;

  // Set background colors and icon
  toastEl.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'bg-primary', 'bg-dark');
  iconEl.className = 'bi fs-5';

  if (type === 'success') {
    toastEl.classList.add('bg-success');
    iconEl.classList.add('bi-check-circle-fill');
  } else if (type === 'error' || type === 'danger') {
    toastEl.classList.add('bg-danger');
    iconEl.classList.add('bi-exclamation-triangle-fill');
  } else if (type === 'warning') {
    toastEl.classList.add('bg-warning', 'text-dark');
    iconEl.classList.add('bi-exclamation-circle-fill');
  } else {
    toastEl.classList.add('bg-primary');
    iconEl.classList.add('bi-info-circle-fill');
  }

  const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
  toast.show();
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
  } catch (err) {
    window.location.href = '/login';
  }
}

async function copyToClipboard(text, btnElement) {
  try {
    await navigator.clipboard.writeText(text);
    if (btnElement) {
      const originalHtml = btnElement.innerHTML;
      btnElement.innerHTML = '<i class="bi bi-check2"></i> Copied!';
      btnElement.classList.remove('btn-outline-primary', 'btn-outline-secondary');
      btnElement.classList.add('btn-success');
      setTimeout(() => {
        btnElement.innerHTML = originalHtml;
        btnElement.classList.remove('btn-success');
        btnElement.classList.add('btn-outline-primary');
      }, 2000);
    }
    showToast('Copied to clipboard!', 'success');
  } catch (err) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showToast('Copied to clipboard!', 'success');
  }
}

// Camera and File Upload Helper
let selectedFiles = [];

function setupImageUploader(dropZoneId, fileInputId, cameraInputId, previewContainerId) {
  const dropZone = document.getElementById(dropZoneId);
  const fileInput = document.getElementById(fileInputId);
  const cameraInput = document.getElementById(cameraInputId);
  const previewContainer = document.getElementById(previewContainerId);

  if (!dropZone || !fileInput) return;

  function handleFiles(files) {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (!file.type.startsWith('image/')) continue;
      selectedFiles.push(file);
    }
    renderPreviews();
  }

  function renderPreviews() {
    if (!previewContainer) return;
    previewContainer.innerHTML = '';

    selectedFiles.forEach((file, index) => {
      const box = document.createElement('div');
      box.className = `thumb-preview-box ${index === 0 ? 'is-primary' : ''}`;
      
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      box.appendChild(img);

      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'delete-btn';
      delBtn.innerHTML = '&times;';
      delBtn.onclick = (e) => {
        e.stopPropagation();
        selectedFiles.splice(index, 1);
        renderPreviews();
      };
      box.appendChild(delBtn);

      if (index === 0) {
        const badge = document.createElement('span');
        badge.className = 'badge bg-warning text-dark position-absolute bottom-0 start-0 m-1 fs-8';
        badge.textContent = 'Main';
        box.appendChild(badge);
      }

      previewContainer.appendChild(box);
    });
  }

  fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    fileInput.value = '';
  });

  if (cameraInput) {
    cameraInput.addEventListener('change', (e) => {
      handleFiles(e.target.files);
      cameraInput.value = '';
    });
  }

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  });
}

