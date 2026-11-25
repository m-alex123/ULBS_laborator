(function () {
  const docRoot = document.documentElement;
  const themeBtn = document.getElementById('theme-btn');
  const themeSymbol = document.getElementById('theme-symbol');
  const themeName = document.getElementById('theme-name');

  const handleSneakerImgError =
    window.handleSneakerImgError ||
    function (img) {
      if (!img || img.dataset.fallbackApplied) return;
      img.dataset.fallbackApplied = 'true';
      img.hidden = true;
      const box = img.closest('.card-photo-box');
      if (!box) return;
      box.classList.add('is-offline');
      const fallback = box.querySelector('.photo-offline-fallback');
      if (fallback) fallback.hidden = false;
      const sourceBadge = box.querySelector('.photo-source-badge');
      if (sourceBadge) sourceBadge.textContent = 'MOD OFFLINE';
    };
  window.handleSneakerImgError = handleSneakerImgError;

  function applyTheme(theme) {
    docRoot.setAttribute('data-theme', theme);
    if (themeBtn) {
      themeBtn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    }
    if (themeSymbol && themeName) {
      if (theme === 'dark') {
        themeSymbol.textContent = '☀️';
        themeName.textContent = 'Luminos';
      } else {
        themeSymbol.textContent = '🌙';
        themeName.textContent = 'Întunecat';
      }
    }
    try {
      localStorage.setItem('p23_theme', theme);
    } catch (_) {
      /* ignore storage access errors */
    }
  }

  const currentTheme = docRoot.getAttribute('data-theme') || 'light';
  applyTheme(currentTheme);

  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const current = docRoot.getAttribute('data-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sneaker-photo').forEach((img) => {
      img.addEventListener('error', () => handleSneakerImgError(img));
      if (img.complete && img.naturalWidth === 0) {
        handleSneakerImgError(img);
      }
    });

    const sortSelect = document.getElementById('sort-select');
    if (sortSelect && sortSelect.form) {
      sortSelect.addEventListener('change', () => sortSelect.form.submit());
    }

    document.querySelectorAll('[data-demo-email]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const emailEl = document.getElementById('email');
        const passEl = document.getElementById('password');
        if (emailEl) emailEl.value = btn.dataset.demoEmail || '';
        if (passEl) passEl.value = btn.dataset.demoPassword || '';
      });
    });
  });
})();
