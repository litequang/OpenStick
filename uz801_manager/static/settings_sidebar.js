// Presentation-only settings navigation: no API calls, saved preferences or mutations.
(() => {
  function sync() {
    const root=document.querySelector('.settings-workspace');
    if (!root) return;
    const path=window.location.pathname, hash=window.location.hash;
    const links=[...root.querySelectorAll('.settings-submenu-links a')];
    let selected=links.find(a => {
      const url=new URL(a.getAttribute('href'), window.location.href);
      return url.pathname===path && !!hash && url.hash===hash;
    });
    if (!selected) selected=links.find(a => {
      const url=new URL(a.getAttribute('href'), window.location.href);
      return url.pathname===path && !url.hash;
    });
    if (!selected) return;
    const key=selected.dataset.settingsLink;
    for(const a of links) {
      if(a.dataset.settingsLink===key) a.setAttribute('aria-current','location');
      else a.removeAttribute('aria-current');
    }
    const current=document.getElementById('settings-current-item');
    if(current) current.textContent=selected.textContent.trim();
  }

  function init() {
    const root=document.querySelector('.settings-workspace');
    if(!root) return;
    sync();
    window.addEventListener('hashchange',sync);
    const drawer=document.getElementById('settings-submenu-toggle');
    if(drawer) for(const a of drawer.querySelectorAll('a')) {
      a.addEventListener('click', () => {drawer.open=false;});
    }
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
