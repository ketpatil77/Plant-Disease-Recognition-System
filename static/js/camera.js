// Helper that falls back to a simple key if language.js isn't ready yet
async function t(key) {
  if (typeof window.getTranslation === 'function') {
    return window.getTranslation(key);
  }
  // Fallback: manual fetch
  const lang = localStorage.getItem('agro-lang') || 'mr';
  const file = lang === 'en' ? 'eng' : 'mar';
  try {
    const res = await fetch(`/static/lang/${file}.json`);
    if (!res.ok) return key;
    const dict = await res.json();
    return dict[key] ?? key;
  } catch {
    return key;
  }
}

export function initScannerPage() {
  const fileInput  = document.getElementById('scannerInput');
  const preview    = document.querySelector('[data-scanner-preview]');
  const placeholder = document.querySelector('[data-preview-placeholder]');
  const status     = document.querySelector('[data-scanner-status]');
  const captureBtn = document.querySelector('[data-camera-capture]');
  const galleryBtn = document.querySelector('[data-camera-gallery]');
  const analyzeBtn = document.querySelector('[data-analyze-btn]');
  const analyzeLabel = analyzeBtn?.querySelector('[data-i18n]');
  const form       = document.querySelector('[data-scanner-form]');
  const fileNameEl = document.querySelector('[data-scanner-file-name]');
  const fileMetaEl = document.querySelector('[data-scanner-file-meta]');
  const clearBtn   = document.querySelector('[data-clear-selection]');
  let currentFile = null;

  function updateStatus(msg) {
    if (status) status.textContent = msg;
  }

  async function setPreview(src) {
    if (!preview) return;
    // Remove old img if any
    const old = preview.querySelector('img[data-preview-img]');
    if (old) old.remove();
    const img = document.createElement('img');
    img.src = src;
    img.dataset.previewImg = '';
    img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:inherit;position:absolute;inset:0;';
    img.alt = await t('scanner.preview.alt');
    preview.appendChild(img);
    if (placeholder) placeholder.hidden = true;
  }

  function clearPreview() {
    if (!preview) return;
    preview.querySelectorAll('img[data-preview-img]').forEach(img => img.remove());
    if (placeholder) placeholder.hidden = false;
  }

  async function setFileMeta(file) {
    if (!fileNameEl || !fileMetaEl) return;
    if (!file) {
      fileNameEl.textContent = await t('scanner.file.empty');
      fileMetaEl.textContent = await t('scanner.file.meta.empty');
      return;
    }
    const metaTemplate = await t('scanner.file.meta.template');
    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    const type = (file.type || 'image').replace('image/', '').toUpperCase();
    fileNameEl.textContent = file.name;
    fileMetaEl.textContent = (metaTemplate || '{size} MB · {type}')
      .replace('{size}', sizeMb)
      .replace('{type}', type);
  }

  function enableAnalyze(enabled) {
    if (!analyzeBtn) return;
    analyzeBtn.disabled = !enabled;
  }

  function readFile(file) {
    // Validate size (2MB = 2,097,152 bytes)
    if (file.size > 2 * 1024 * 1024) {
      t('scanner.upload.size_error').then(msg => updateStatus(msg || 'File too large (max 2MB).'));
      fileInput.value = '';
      currentFile = null;
      setFileMeta(null);
      clearPreview();
      enableAnalyze(false);
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      setPreview(event.target.result);
      t('scanner.preview_ready').then(updateStatus);
      setFileMeta(file);
      enableAnalyze(true);
    };
    reader.readAsDataURL(file);
  }

  fileInput?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (!file) {
      currentFile = null;
      clearPreview();
      setFileMeta(null);
      enableAnalyze(false);
      return;
    }
    if (!file.type.startsWith('image/')) {
      t('scanner.upload.type_error').then(updateStatus);
      fileInput.value = '';
      currentFile = null;
      clearPreview();
      setFileMeta(null);
      enableAnalyze(false);
      return;
    }
    currentFile = file;
    readFile(file);
  });

  captureBtn?.addEventListener('click', () => {
    if (!fileInput) return;
    fileInput.setAttribute('capture', 'environment');
    fileInput.click();
    t('scanner.camera_triggered').then(updateStatus);
  });

  galleryBtn?.addEventListener('click', () => {
    if (!fileInput) return;
    fileInput.removeAttribute('capture');
    fileInput.click();
    t('scanner.gallery_open').then(updateStatus);
  });

  // Show a loading state on form submit
  form?.addEventListener('submit', () => {
    if (analyzeBtn) {
      analyzeBtn.disabled = true;
      if (analyzeLabel) {
        t('scanner.button.analyzing').then(msg => { analyzeLabel.textContent = msg; });
      }
    }
  });

  clearBtn?.addEventListener('click', async () => {
    if (fileInput) fileInput.value = '';
    currentFile = null;
    clearPreview();
    enableAnalyze(false);
    await setFileMeta(null);
    t('scanner.select_photo').then(updateStatus);
  });

  // Init camera access check
  async function initCameraAccess() {
    if (!navigator.mediaDevices?.getUserMedia) {
      t('scanner.camera_unavailable').then(updateStatus);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      // Stop stream immediately – just testing permission
      stream.getTracks().forEach(track => track.stop());
      t('scanner.camera_ready').then(updateStatus);
    } catch {
      t('scanner.camera_denied').then(updateStatus);
    }
  }

  setFileMeta(null);
  initCameraAccess();
  document.addEventListener('agro:languagechange', async () => {
    await setFileMeta(currentFile);
    if (!currentFile && placeholder) placeholder.hidden = false;
  });
}
