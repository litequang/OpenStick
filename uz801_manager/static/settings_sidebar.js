// One read-only menu controller for the four management cards and child pages.
// No network requests, preference writes or device-side actions.
(() => {
  const legacy={
    '/setup#saved-wifi':'/setup/saved','/setup#usb-ap-settings':'/setup/ap',
    '/setup#ap-clients':'/setup/clients','/setup#setup-status-panel':'/setup/ap',
    '/manage#manage-access':'/settings/access','/manage#lan-manage':'/settings/access',
    '/overview#sim-usage-details':'/sim/usage','/quick#quick-usb':'/quick/usb',
    '/website#web-pane-files':'/website/files','/website#web-pane-uploads':'/website/uploads',
    '/website#web-pane-domains':'/website/domains'};
  const destination=legacy[location.pathname+location.hash];
  if(destination){location.replace(destination+location.search);return;}
  if(location.pathname==='/website/uploads'&&document.querySelector('.website-leaf')){location.replace('/website/files'+location.search);return;}
  function currentLink(root) {
    const path=window.location.pathname, hash=window.location.hash;
    const links=[...root.querySelectorAll('.settings-category-item')];
    const match=a=> {
      const u=new URL(a.getAttribute('href'), window.location.href);
      return u.pathname===path && u.hash===hash;
    };
    return links.find(match) || links.find(a=> {
      const u=new URL(a.getAttribute('href'), window.location.href);
      return u.pathname===path && !u.hash;
    }) || null;
  }
  function activateWebsiteTab() {
    if(!window.location.pathname.startsWith('/website')) return;
    const tabs={'#web-pane-files':'files','#web-pane-uploads':'uploads','#web-pane-domains':'domains'};
    const tab=({'/website/files':'files','/website/uploads':'uploads','/website/domains':'domains'})[location.pathname]||tabs[window.location.hash];
    if(!tab) return;
    const button=document.querySelector('[data-web-tab="'+tab+'"]');
    if(button && button.getAttribute('aria-pressed')!=='true') button.click();
  }
  function sync() {
    for(const root of document.querySelectorAll('.settings-category-tree')) {
      const active=currentLink(root);
      for(const a of root.querySelectorAll('.settings-category-item')) a.removeAttribute('aria-current');
      if(!active) continue;
      active.setAttribute('aria-current','page');
      const group=active.closest('.settings-category');
      if(group) {
        group.open=true;
        root.dataset.currentGroup=group.dataset.settingsSection;
      }
      const current=document.getElementById('settings-current-item');
      if(current) current.textContent=active.querySelector('strong')?.textContent.trim() || 'Chọn chức năng';
    }
    activateWebsiteTab();
  }
  function init() {
    const root=document.querySelector('.settings-category-tree');
    if(!root) return;
    const drawer=document.getElementById('settings-submenu-toggle');
    if(drawer) {
      let mobile=null;
      const update=()=>{
        const next=window.matchMedia('(max-width:759px)').matches;
        if(mobile!==next) {drawer.open=!next;mobile=next;}
      };
      update();
      window.addEventListener('resize',update);
      drawer.querySelectorAll('.settings-category-item').forEach(a=> {
        a.addEventListener('click',()=>{if(window.matchMedia('(max-width:759px)').matches)drawer.open=false;});
      });
    } else if(root.classList.contains('settings-category-tree--hub') &&
              window.matchMedia('(max-width:759px)').matches) {
      // The hub stays usable without JavaScript. Collapse categories only
      // in the enhanced small-screen view to shorten the landing page.
      root.querySelectorAll('.settings-category').forEach(item=>{item.open=false;});
    }
    sync();
    window.addEventListener('hashchange',sync);
    document.querySelectorAll('[data-web-tab]').forEach(button=> {
      button.addEventListener('click',()=> {
        const hash='#web-pane-'+button.dataset.webTab;
        if(window.location.hash!==hash) history.replaceState(null,'',hash);
        sync();
      });
    });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
