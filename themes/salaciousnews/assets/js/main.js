(function () {
  // Mobile nav drawer toggle
  var menuBtn = document.getElementById('tbm-menu-toggle');
  var drawer = document.getElementById('tbm-drawer');
  if (menuBtn && drawer) {
    menuBtn.addEventListener('click', function () {
      var isOpen = drawer.classList.toggle('is-open');
      menuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  // Sticky anchor dismissal (persisted for the session)
  function setupAnchor(anchorId, btnId, storageKey) {
    var anchor = document.getElementById(anchorId);
    var btn = document.getElementById(btnId);
    if (!anchor || !btn) return;
    if (sessionStorage.getItem(storageKey) === '1') {
      anchor.classList.add('is-dismissed');
      return;
    }
    btn.addEventListener('click', function () {
      anchor.classList.add('is-dismissed');
      sessionStorage.setItem(storageKey, '1');
    });
  }
  setupAnchor('tb-anchor', 'tb-anchor-close', 'anchorDismissed');
  setupAnchor('tbm-anchor', 'tbm-anchor-close', 'anchorDismissed');
})();
