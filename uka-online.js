(() => {
  'use strict';

  const state={
    user:null,profile:null,friends:[],incoming:[],outgoing:[],search:[],query:'',
    loading:false,error:'',editing:false,avatarBusy:false
  };
  let authSubscribed=false;

  const esc=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const initials=profile=>String(profile?.display_name||profile?.username||'?').trim().slice(0,1).toUpperCase()||'?';
  const nameOf=profile=>profile?.display_name||profile?.username||'Uživatel';
  const usernameOf=profile=>profile?.username?`@${profile.username}`:'@bez-jmena';

  function page(){
    return `<section class="uka-online-page"><div class="container uka-online-container"><div class="uka-online-topbar"><div><h1>Profil</h1></div><button type="button" class="uka-online-icon-button" data-online-action="refresh" aria-label="Obnovit" title="Obnovit">↻</button></div><div id="ukaOnlineRoot" class="uka-online-root"><div class="uka-online-loading">Načítám profil…</div></div></div></section>`;
  }

  function avatar(profile,size='normal'){
    if(profile?.avatar_url){
      const url=String(profile.avatar_url);
      if(/^https:\/\//i.test(url))return `<img class="uka-online-avatar ${size==='small'?'is-small':''}" src="${esc(url)}" alt="Profilová fotka">`;
    }
    return `<span class="uka-online-avatar uka-online-avatar-fallback ${size==='small'?'is-small':''}" aria-hidden="true">${esc(initials(profile))}</span>`;
  }

  function renderLoggedOut(){
    return `<div class="uka-online-empty uka-online-login"><div class="uka-online-empty-icon">◎</div><h2>Přátelé na UKA</h2><p>Přihlas se, vytvoř si profil a spoj se s lidmi, se kterými chceš chodit na koncerty.</p><button type="button" class="btn btn-primary" data-online-action="login">Přihlásit se</button></div>`;
  }

  function relationAction(profile){
    if(!profile?.id)return '';
    const friend=state.friends.some(row=>row.friend_id===profile.id);
    if(friend)return '<span class="uka-online-state">Přátelé</span>';
    const outgoing=state.outgoing.some(row=>row.receiver_id===profile.id);
    if(outgoing)return '<span class="uka-online-state">Odesláno</span>';
    const incoming=state.incoming.find(row=>row.sender_id===profile.id);
    if(incoming)return `<button type="button" class="btn btn-primary btn-sm" data-online-action="accept" data-request-id="${esc(incoming.id)}">Přijmout</button>`;
    return `<button type="button" class="btn btn-primary btn-sm" data-online-action="add" data-user-id="${esc(profile.id)}">Přidat</button>`;
  }

  function userRow(profile,actions=''){
    if(!profile)return '';
    return `<div class="uka-online-user">${avatar(profile,'small')}<div class="uka-online-user-copy"><strong>${esc(nameOf(profile))}</strong><span>${esc(usernameOf(profile))}</span></div><div class="uka-online-user-actions">${actions}</div></div>`;
  }

  function renderEditor(){
    const p=state.profile||{};
    if(!state.editing)return '';
    return `<div class="uka-online-editor-wrap"><form id="ukaOnlineProfileForm" class="uka-online-profile-form"><div class="uka-online-editor-title"><strong>Upravit profil</strong><button type="button" class="uka-online-text-button" data-online-action="cancel-edit">Zrušit</button></div><label>Uživatelské jméno<input name="username" maxlength="30" autocomplete="username" value="${esc(p.username||'')}" placeholder="např. klara23"></label><label>Jméno<input name="display_name" maxlength="80" value="${esc(p.display_name||'')}" placeholder="Tvoje jméno"></label><label class="uka-online-wide">Bio<textarea name="bio" maxlength="300" rows="3" placeholder="Něco krátce o sobě">${esc(p.bio||'')}</textarea></label><div class="uka-online-wide uka-online-form-end"><span class="uka-online-help">3–30 znaků, bez mezer.</span><button class="btn btn-primary" type="submit">Uložit změny</button></div></form></div>`;
  }

  function renderProfile(){
    const p=state.profile||{};
    const requestCount=state.incoming.length;
    return `<section class="uka-online-profile-shell"><div class="uka-online-profile-top"><div class="uka-online-avatar-wrap"><button type="button" class="uka-online-avatar-button" data-online-action="choose-avatar" ${state.avatarBusy?'disabled':''} aria-label="Změnit profilovou fotku">${avatar(p)}<span class="uka-online-avatar-edit">${state.avatarBusy?'…':'+'}</span></button><input id="ukaOnlineAvatarInput" type="file" accept="image/jpeg,image/png,image/webp" hidden></div><div class="uka-online-profile-copy"><div class="uka-online-profile-name-row"><h2>${esc(nameOf(p))}</h2><span>${esc(usernameOf(p))}</span></div><div class="uka-online-stats"><button type="button" data-online-action="focus-friends"><strong>${state.friends.length}</strong><span>přátel</span></button><button type="button" data-online-action="focus-requests"><strong>${requestCount}</strong><span>žádostí</span></button></div>${p.bio?`<p class="uka-online-bio">${esc(p.bio)}</p>`:'<p class="uka-online-bio is-empty">Přidej krátké bio, ať tě přátelé poznají.</p>'}<div class="uka-online-profile-actions"><button type="button" class="btn btn-outline btn-sm" data-online-action="edit-profile">Upravit profil</button><button type="button" class="btn btn-outline btn-sm" data-online-action="focus-search">Najít lidi</button>${p.avatar_url?'<button type="button" class="uka-online-text-button uka-online-remove-photo" data-online-action="remove-avatar">Odebrat fotku</button>':''}</div></div></div>${renderEditor()}</section>`;
  }

  function renderFriends(){
    if(!state.friends.length){
      return `<section id="ukaOnlineFriends" class="uka-online-section"><div class="uka-online-section-head"><h3>Přátelé</h3></div><div class="uka-online-soft-empty">Zatím tu nikoho nemáš. Najdi si prvního člověka.</div></section>`;
    }
    const items=state.friends.map(row=>{
      const p=row.profile||{};
      return `<div class="uka-online-friend"><div class="uka-online-friend-avatar">${avatar(p)}</div><strong>${esc(nameOf(p))}</strong><span>${esc(usernameOf(p))}</span><button type="button" class="uka-online-friend-menu" data-online-action="remove" data-user-id="${esc(row.friend_id)}" aria-label="Odebrat přítele" title="Odebrat">×</button></div>`;
    }).join('');
    return `<section id="ukaOnlineFriends" class="uka-online-section"><div class="uka-online-section-head"><h3>Přátelé</h3><span>${state.friends.length}</span></div><div class="uka-online-friends-strip">${items}</div></section>`;
  }

  function renderRequests(){
    if(!state.incoming.length&&!state.outgoing.length)return '';
    const incoming=state.incoming.map(row=>userRow(row.profile,`<button type="button" class="btn btn-primary btn-sm" data-online-action="accept" data-request-id="${esc(row.id)}">Přijmout</button><button type="button" class="uka-online-text-button" data-online-action="decline" data-request-id="${esc(row.id)}">Odmítnout</button>`)).join('');
    const outgoing=state.outgoing.map(row=>userRow(row.profile,'<span class="uka-online-state">Čeká</span>')).join('');
    return `<section id="ukaOnlineRequests" class="uka-online-section"><div class="uka-online-section-head"><h3>Žádosti</h3>${state.incoming.length?`<span class="uka-online-badge">${state.incoming.length}</span>`:''}</div><div class="uka-online-list">${incoming}${outgoing?`<div class="uka-online-list-label">Odeslané</div>${outgoing}`:''}</div></section>`;
  }

  function renderSearch(){
    let results='';
    if(state.query){
      results=state.search.length
        ? `<div class="uka-online-list uka-online-search-results">${state.search.map(profile=>userRow(profile,relationAction(profile))).join('')}</div>`
        : '<div class="uka-online-soft-empty">Nikdo nenalezen.</div>';
    }
    return `<section id="ukaOnlineSearch" class="uka-online-section uka-online-search-section"><div class="uka-online-section-head"><h3>Najít lidi</h3></div><form id="ukaOnlineSearchForm" class="uka-online-search"><span class="uka-online-search-icon">⌕</span><input id="ukaOnlineSearchInput" name="q" minlength="2" maxlength="30" value="${esc(state.query)}" placeholder="Hledat podle @username" autocomplete="off"><button class="btn btn-primary btn-sm" type="submit">Hledat</button></form>${results}</section>`;
  }

  function renderApp(){
    const root=document.getElementById('ukaOnlineRoot');
    if(!root)return;
    if(state.loading&&!state.user){root.innerHTML='<div class="uka-online-loading">Načítám profil…</div>';return;}
    if(!state.user){root.innerHTML=renderLoggedOut();return;}
    root.innerHTML=`${state.error?`<div class="uka-online-error">${esc(state.error)}</div>`:''}${renderProfile()}<div class="uka-online-content">${renderFriends()}${renderRequests()}${renderSearch()}</div>`;
  }

  function notify(message){
    if(typeof window.showToast==='function')window.showToast(message);
    else console.info('UKA Online:',message);
  }

  async function load(){
    const api=window.UKASocial;
    state.error='';
    if(!api){state.user=null;state.loading=false;state.error='Sociální funkce se nenačetly.';renderApp();return;}
    state.loading=true;renderApp();
    try{
      state.user=await api.currentUser();
      if(!state.user){state.profile=null;state.friends=[];state.incoming=[];state.outgoing=[];return;}
      const [profile,friends,requests]=await Promise.all([api.getMyProfile(),api.getFriends(),api.getFriendRequests()]);
      state.profile=profile;state.friends=friends;state.incoming=requests.incoming||[];state.outgoing=requests.outgoing||[];
    }catch(error){
      console.warn('UKA Online load failed',error);
      state.error=error?.message||'Sociální část se nepodařilo načíst.';
    }finally{state.loading=false;renderApp();}
  }

  async function run(action,success,{reload=true}={}){
    try{
      state.error='';
      const result=await action();
      if(success)notify(success);
      if(reload)await load();else renderApp();
      return result;
    }catch(error){
      console.warn('UKA Online action failed',error);
      state.error=error?.message||'Akce se nepovedla.';
      renderApp();
      return null;
    }
  }

  function focusSection(id){
    requestAnimationFrame(()=>{
      const target=document.getElementById(id);
      target?.scrollIntoView({behavior:'smooth',block:'center'});
      if(id==='ukaOnlineSearch')setTimeout(()=>document.getElementById('ukaOnlineSearchInput')?.focus(),350);
    });
  }

  async function uploadAvatar(file){
    if(!file)return;
    state.avatarBusy=true;state.error='';renderApp();
    const profile=await run(()=>window.UKASocial.uploadAvatar(file),'Profilová fotka uložena.',{reload:false});
    if(profile)state.profile=profile;
    state.avatarBusy=false;renderApp();
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
    if(action==='edit-profile'){state.editing=true;renderApp();setTimeout(()=>document.querySelector('#ukaOnlineProfileForm input')?.focus(),0);return;}
    if(action==='cancel-edit'){state.editing=false;renderApp();return;}
    if(action==='choose-avatar'){document.getElementById('ukaOnlineAvatarInput')?.click();return;}
    if(action==='focus-search'){focusSection('ukaOnlineSearch');return;}
    if(action==='focus-friends'){focusSection('ukaOnlineFriends');return;}
    if(action==='focus-requests'){focusSection('ukaOnlineRequests');return;}
    const api=window.UKASocial;if(!api)return;
    if(action==='remove-avatar')run(()=>api.removeAvatar(),'Profilová fotka odebrána.').then(()=>{state.avatarBusy=false;});
    if(action==='add')run(()=>api.sendFriendRequest(button.dataset.userId),'Žádost o přátelství odeslána.');
    if(action==='accept')run(()=>api.acceptFriendRequest(button.dataset.requestId),'Jste přátelé.');
    if(action==='decline')run(()=>api.declineFriendRequest(button.dataset.requestId),'Žádost odmítnuta.');
    if(action==='remove'){
      if(confirm('Odebrat tohoto člověka z přátel?'))run(()=>api.removeFriend(button.dataset.userId),'Přítel odebrán.');
    }
  });

  document.addEventListener('change',event=>{
    if(event.target?.id==='ukaOnlineAvatarInput'){
      const file=event.target.files?.[0];
      event.target.value='';
      uploadAvatar(file);
    }
  });

  document.addEventListener('submit',event=>{
    if(event.target.id==='ukaOnlineProfileForm'){
      event.preventDefault();
      const data=new FormData(event.target);
      (async()=>{
        const profile=await run(()=>window.UKASocial.updateMyProfile({username:data.get('username'),display_name:data.get('display_name'),bio:data.get('bio')}),'Profil uložen.',{reload:false});
        if(profile){state.profile=profile;state.editing=false;renderApp();}
      })();
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
