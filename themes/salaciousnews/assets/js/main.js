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
})();
