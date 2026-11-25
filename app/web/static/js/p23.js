(function () {
  const docRoot = document.documentElement;
  const themeBtn = document.getElementById('theme-btn');
  const themeSymbol = document.getElementById('theme-symbol');
  const themeName = document.getElementById('theme-name');

  function applyTheme(theme) {
    docRoot.setAttribute('data-theme', theme);
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

  let initialTheme = 'light';
  try {
    initialTheme =
      localStorage.getItem('p23_theme') ||
      (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  } catch (_) {
    initialTheme = 'light';
  }
  applyTheme(initialTheme);

  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const current = docRoot.getAttribute('data-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sneaker-photo').forEach((img) => {
      if (img.complete && img.naturalWidth === 0 && typeof window.handleSneakerImgError === 'function') {
        window.handleSneakerImgError(img);
      }
    });
  });
})();
