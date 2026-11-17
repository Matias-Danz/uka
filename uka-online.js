(() => {
  'use strict';

  const state={user:null,profile:null,friends:[],incoming:[],outgoing:[],search:[],query:'',loading:false,error:''};
  let authSubscribed=false;

  const esc=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const initials=profile=>String(profile?.display_name||profile?.username||'?').trim().slice(0,1).toUpperCase()||'?';
  const nameOf=profile=>profile?.display_name||profile?.username||'Uživatel';
  const usernameOf=profile=>profile?.username?`@${profile.username}`:'@bez-jmena';

  function page(){
    return `<section class="uka-online-page"><div class="container"><div class="uka-online-head"><div><span class="uka-online-kicker">UKA Online</span><h1>Hudba je lepší s lidmi.</h1><p>Najdi přátele, propojte se a později si tu budete posílat koncerty, komentovat je a reagovat na ně.</p></div><button type="button" class="btn btn-outline uka-online-refresh" data-online-action="refresh">Obnovit</button></div><div id="ukaOnlineRoot" class="uka-online-root"><div class="uka-online-loading">Načítám UKA Online…</div></div></div></section>`;
  }

  function avatar(profile,size='normal'){
    if(profile?.avatar_url){
      const url=String(profile.avatar_url);
      if(/^https:\/\//i.test(url))return `<img class="uka-online-avatar ${size==='small'?'is-small':''}" src="${esc(url)}" alt="">`;
    }
    return `<span class="uka-online-avatar uka-online-avatar-fallback ${size==='small'?'is-small':''}" aria-hidden="true">${esc(initials(profile))}</span>`;
  }

  function userRow(profile,actions=''){
    if(!profile)return '';
    return `<div class="uka-online-user">${avatar(profile,'small')}<div class="uka-online-user-copy"><strong>${esc(nameOf(profile))}</strong><span>${esc(usernameOf(profile))}</span></div><div class="uka-online-user-actions">${actions}</div></div>`;
  }

  function renderLoggedOut(){
    return `<div class="uka-online-empty uka-online-login"><div class="uka-online-empty-icon">◎</div><h2>Přihlas se do UKA</h2><p>Online profil, přátelé a žádosti jsou dostupné po přihlášení.</p><button type="button" class="btn btn-primary" data-online-action="login">Přihlásit se</button></div>`;
  }

  function renderProfile(){
    const p=state.profile||{};
    return `<section class="uka-online-card uka-online-profile"><div class="uka-online-card-title"><h2>Tvůj profil</h2><span>${esc(usernameOf(p))}</span></div><div class="uka-online-profile-main">${avatar(p)}<div><strong>${esc(nameOf(p))}</strong><p>${p.bio?esc(p.bio):'Zatím bez bio.'}</p></div></div><form id="ukaOnlineProfileForm" class="uka-online-profile-form"><label>Uživatelské jméno<input name="username" maxlength="30" autocomplete="username" value="${esc(p.username||'')}" placeholder="např. klara23"></label><label>Jméno<input name="display_name" maxlength="80" value="${esc(p.display_name||'')}" placeholder="Jak se máš zobrazovat"></label><label class="uka-online-wide">Bio<textarea name="bio" maxlength="300" rows="3" placeholder="Napiš něco o sobě">${esc(p.bio||'')}</textarea></label><div class="uka-online-wide uka-online-form-end"><span class="uka-online-help">Username: 3–30 znaků, bez mezer.</span><button class="btn btn-primary" type="submit">Uložit profil</button></div></form></section>`;
  }

  function renderSearch(){
    const results=state.search.length
      ? `<div class="uka-online-list">${state.search.map(profile=>userRow(profile,`<button type="button" class="btn btn-outline btn-sm" data-online-action="add" data-user-id="${esc(profile.id)}">Přidat</button>`)).join('')}</div>`
      : state.query?'<div class="uka-online-mini-empty">Nikdo nenalezen.</div>':'<div class="uka-online-mini-empty">Hledej podle @username.</div>';
    return `<section class="uka-online-card"><div class="uka-online-card-title"><h2>Najít lidi</h2></div><form id="ukaOnlineSearchForm" class="uka-online-search"><input id="ukaOnlineSearchInput" name="q" minlength="2" maxlength="30" value="${esc(state.query)}" placeholder="@uživatelské_jméno" autocomplete="off"><button class="btn btn-primary" type="submit">Hledat</button></form>${results}</section>`;
  }

  function renderRequests(){
    const incoming=state.incoming.length?state.incoming.map(row=>userRow(row.profile,`<button type="button" class="btn btn-primary btn-sm" data-online-action="accept" data-request-id="${esc(row.id)}">Přijmout</button><button type="button" class="btn btn-outline btn-sm" data-online-action="decline" data-request-id="${esc(row.id)}">Odmítnout</button>`)).join(''):'<div class="uka-online-mini-empty">Žádné nové žádosti.</div>';
    const outgoing=state.outgoing.length?`<div class="uka-online-subtitle">Odeslané</div>${state.outgoing.map(row=>userRow(row.profile,'<span class="uka-online-pending">Čeká na přijetí</span>')).join('')}`:'';
    return `<section class="uka-online-card"><div class="uka-online-card-title"><h2>Žádosti</h2>${state.incoming.length?`<span class="uka-online-count">${state.incoming.length}</span>`:''}</div><div class="uka-online-list">${incoming}${outgoing}</div></section>`;
  }

  function renderFriends(){
    const rows=state.friends.length?state.friends.map(row=>userRow(row.profile,`<button type="button" class="uka-online-danger" data-online-action="remove" data-user-id="${esc(row.friend_id)}">Odebrat</button>`)).join(''):'<div class="uka-online-mini-empty">Zatím tu nikoho nemáš. Najdi si prvního člověka nahoře.</div>';
    return `<section class="uka-online-card"><div class="uka-online-card-title"><h2>Přátelé</h2><span>${state.friends.length}</span></div><div class="uka-online-list">${rows}</div></section>`;
  }

  function renderApp(){
    const root=document.getElementById('ukaOnlineRoot');
    if(!root)return;
    if(state.loading&&!state.user){root.innerHTML='<div class="uka-online-loading">Načítám UKA Online…</div>';return;}
    if(!state.user){root.innerHTML=renderLoggedOut();return;}
    root.innerHTML=`${state.error?`<div class="uka-online-error">${esc(state.error)}</div>`:''}<div class="uka-online-grid"><div class="uka-online-col">${renderProfile()}${renderSearch()}</div><div class="uka-online-col">${renderRequests()}${renderFriends()}</div></div>`;
  }

  function notify(message){
    if(typeof window.showToast==='function')window.showToast(message);
    else console.info('UKA Online:',message);
  }

  async function load(){
    const api=window.UKASocial;
    state.error='';
    if(!api){state.user=null;state.loading=false;state.error='Online služba se nenačetla.';renderApp();return;}
    state.loading=true;renderApp();
    try{
      state.user=await api.currentUser();
      if(!state.user){state.profile=null;state.friends=[];state.incoming=[];state.outgoing=[];return;}
      const [profile,friends,requests]=await Promise.all([api.getMyProfile(),api.getFriends(),api.getFriendRequests()]);
      state.profile=profile;state.friends=friends;state.incoming=requests.incoming||[];state.outgoing=requests.outgoing||[];
    }catch(error){
      console.warn('UKA Online load failed',error);
      state.error=error?.message||'Online režim se nepodařilo načíst.';
    }finally{state.loading=false;renderApp();}
  }

  async function run(action,success){
    try{state.error='';await action();if(success)notify(success);await load();}
    catch(error){console.warn('UKA Online action failed',error);state.error=error?.message||'Akce se nepovedla.';renderApp();}
  }

  function subscribeAuth(){
    if(authSubscribed||!window.ukaSupabaseClient)return;
    authSubscribed=true;
    window.ukaSupabaseClient.auth.onAuthStateChange(()=>{
      if(location.hash==='#online')setTimeout(load,0);
    });
  }

  async function mount(){subscribeAuth();await load();}

  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-online-action]');
    if(!button)return;
    const action=button.dataset.onlineAction;
    if(action==='login'){document.getElementById('ukaAuthButton')?.click();return;}
    if(action==='refresh'){if(location.hash==='#online')load();return;}
    const api=window.UKASocial;if(!api)return;
    if(action==='add')run(()=>api.sendFriendRequest(button.dataset.userId),'Žádost o přátelství odeslána.');
    if(action==='accept')run(()=>api.acceptFriendRequest(button.dataset.requestId),'Jste přátelé.');
    if(action==='decline')run(()=>api.declineFriendRequest(button.dataset.requestId),'Žádost odmítnuta.');
    if(action==='remove'){
      if(confirm('Odebrat tohoto člověka z přátel?'))run(()=>api.removeFriend(button.dataset.userId),'Přítel odebrán.');
    }
  });

  document.addEventListener('submit',event=>{
    if(event.target.id==='ukaOnlineProfileForm'){
      event.preventDefault();
      const data=new FormData(event.target);
      run(()=>window.UKASocial.updateMyProfile({username:data.get('username'),display_name:data.get('display_name'),bio:data.get('bio')}),'Profil uložen.');
      return;
    }
    if(event.target.id==='ukaOnlineSearchForm'){
      event.preventDefault();
      const data=new FormData(event.target);state.query=String(data.get('q')||'').trim();
      if(state.query.length<2){state.search=[];renderApp();return;}
      (async()=>{
        try{state.search=await window.UKASocial.searchUsers(state.query);state.error='';}
        catch(error){state.search=[];state.error=error?.message||'Hledání selhalo.';}
        renderApp();
      })();
    }
  });

  window.UKAOnline={page,mount};
  window.addEventListener('load',()=>{
    subscribeAuth();
    if(location.hash==='#online')window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
})();
