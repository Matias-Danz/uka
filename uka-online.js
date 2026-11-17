(() => {
  'use strict';

  const state={
    user:null,profile:null,friends:[],incoming:[],outgoing:[],search:[],query:'',
    overview:[],view:'home',activeFriendId:null,messages:[],
    loading:false,chatLoading:false,sending:false,error:'',editing:false,avatarBusy:false,
    removeCandidate:null,shareEvent:null,shareMessage:'',shareSent:new Set(),realtime:null
  };
  let authSubscribed=false;

  const esc=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const initials=profile=>String(profile?.display_name||profile?.username||'?').trim().slice(0,1).toUpperCase()||'?';
  const nameOf=profile=>profile?.display_name||profile?.username||'Uživatel';
  const usernameOf=profile=>profile?.username?`@${profile.username}`:'@bez-jmena';
  const icon=(id,cls='')=>`<svg class="icon ${cls}" aria-hidden="true"><use href="#i-${id}"/></svg>`;

  function page(){
    return `<section class="uka-online-page"><div class="container uka-online-container"><div id="ukaOnlineRoot" class="uka-online-root"><div class="uka-online-loading">Načítám přátele…</div></div></div></section>`;
  }

  function avatar(profile,size='normal'){
    if(profile?.avatar_url){
      const url=String(profile.avatar_url);
      if(/^https:\/\//i.test(url))return `<img class="uka-online-avatar ${size==='small'?'is-small':''}" src="${esc(url)}" alt="Profilová fotka">`;
    }
    return `<span class="uka-online-avatar uka-online-avatar-fallback ${size==='small'?'is-small':''}" aria-hidden="true">${esc(initials(profile))}</span>`;
  }

  function friendRow(friendId){return state.friends.find(row=>row.friend_id===friendId)||null;}
  function friendProfile(friendId){return friendRow(friendId)?.profile||null;}
  function overviewFor(friendId){return state.overview.find(row=>row.friend_id===friendId)||null;}

  function formatTime(value){
    if(!value)return '';
    const d=new Date(value);if(Number.isNaN(d.getTime()))return '';
    const now=new Date();
    if(d.toDateString()===now.toDateString())return d.toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit'});
    return d.toLocaleDateString('cs-CZ',{day:'numeric',month:'numeric'});
  }

  function formatEventDate(value){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(String(value||'')))return '';
    const [y,m,d]=value.split('-').map(Number);
    return new Date(y,m-1,d).toLocaleDateString('cs-CZ',{day:'numeric',month:'short'});
  }

  function eventInfo(id){return window.UKAEvents?.getById?.(id)||null;}

  function previewFor(message){
    if(!message)return 'Napiš první zprávu';
    if(message.event_id&&message.body)return `Akce · ${message.body}`;
    if(message.event_id)return 'Poslal(a) akci';
    return message.body||'Zpráva';
  }

  function renderLoggedOut(){
    return `<div class="uka-online-empty uka-online-login"><div class="uka-online-empty-icon">${icon('message')}</div><h2>Přátelé a zprávy</h2><p>Přihlas se, přidej si přátele a posílej si koncerty přímo přes UKA.</p><button type="button" class="btn btn-primary" data-online-action="login">Přihlásit se</button></div>`;
  }

  function relationAction(profile){
    if(!profile?.id)return '';
    const friend=state.friends.some(row=>row.friend_id===profile.id);
    if(friend)return `<button type="button" class="btn btn-outline btn-sm" data-online-action="open-chat" data-user-id="${esc(profile.id)}">Zpráva</button>`;
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

  function renderTopbar(){
    const unread=state.overview.reduce((sum,row)=>sum+(Number(row.unread)||0),0);
    return `<div class="uka-online-topbar"><div><span class="uka-online-kicker">UKA SOCIAL</span><h1>Přátelé</h1></div><div class="uka-online-top-actions"><button type="button" class="uka-online-icon-button" data-online-action="focus-messages" aria-label="Zprávy" title="Zprávy">${icon('message')}${unread?`<span class="uka-online-icon-badge">${unread>99?'99+':unread}</span>`:''}</button><button type="button" class="uka-online-icon-button" data-online-action="refresh" aria-label="Obnovit" title="Obnovit">↻</button></div></div>`;
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

  function renderMessages(){
    if(!state.friends.length){
      return `<section id="ukaOnlineMessages" class="uka-online-section uka-online-messages-section"><div class="uka-online-section-head"><h3>Zprávy</h3></div><div class="uka-online-soft-empty">Nejdřív si přidej kamaráda. Pak si můžete normálně psát a posílat akce.</div></section>`;
    }
    const ordered=[...state.friends].sort((a,b)=>{
      const am=overviewFor(a.friend_id)?.last_message?.created_at||'';
      const bm=overviewFor(b.friend_id)?.last_message?.created_at||'';
      if(am||bm)return bm.localeCompare(am);
      return nameOf(a.profile).localeCompare(nameOf(b.profile),'cs');
    });
    const rows=ordered.map(row=>{
      const p=row.profile||{},overview=overviewFor(row.friend_id),last=overview?.last_message,unread=Number(overview?.unread)||0;
      return `<button type="button" class="uka-conversation-row ${unread?'has-unread':''}" data-online-action="open-chat" data-user-id="${esc(row.friend_id)}">${avatar(p,'small')}<span class="uka-conversation-copy"><strong>${esc(nameOf(p))}</strong><span>${esc(previewFor(last))}</span></span><span class="uka-conversation-meta">${last?`<time>${esc(formatTime(last.created_at))}</time>`:''}${unread?`<b>${unread>99?'99+':unread}</b>`:''}</span></button>`;
    }).join('');
    return `<section id="ukaOnlineMessages" class="uka-online-section uka-online-messages-section"><div class="uka-online-section-head"><h3>Zprávy</h3><span>${state.friends.length}</span></div><div class="uka-conversation-list">${rows}</div></section>`;
  }

  function renderFriends(){
    if(!state.friends.length){
      return `<section id="ukaOnlineFriends" class="uka-online-section"><div class="uka-online-section-head"><h3>Přátelé</h3></div><div class="uka-online-soft-empty">Zatím tu nikoho nemáš. Najdi si prvního člověka.</div></section>`;
    }
    const items=state.friends.map(row=>{
      const p=row.profile||{};
      return `<div class="uka-online-friend"><button type="button" class="uka-online-friend-open" data-online-action="open-chat" data-user-id="${esc(row.friend_id)}"><div class="uka-online-friend-avatar">${avatar(p)}</div><strong>${esc(nameOf(p))}</strong><span>${esc(usernameOf(p))}</span></button><button type="button" class="uka-online-friend-menu" data-online-action="remove" data-user-id="${esc(row.friend_id)}" aria-label="Odebrat přítele" title="Odebrat">×</button></div>`;
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

  function renderEventAttachment(eventId){
    const e=eventInfo(eventId);
    if(!e)return `<button type="button" class="uka-chat-event-card is-missing" data-open-event="${esc(eventId)}"><span class="uka-chat-event-thumb">♫</span><span><small>Sdílená akce</small><strong>Akce už není v nabídce</strong></span></button>`;
    const img=/^https:\/\//i.test(String(e.image_url||''))?`<img src="${esc(e.image_url)}" alt="">`:'♫';
    const where=[e.venue,e.city].filter(Boolean).join(' · ');
    return `<button type="button" class="uka-chat-event-card" data-open-event="${esc(eventId)}"><span class="uka-chat-event-thumb">${img}</span><span class="uka-chat-event-copy"><small>${esc(formatEventDate(e.date))}${e.time?` · ${esc(e.time)}`:''}</small><strong>${esc(e.title||'Akce')}</strong>${where?`<em>${esc(where)}</em>`:''}</span><span class="uka-chat-event-arrow">›</span></button>`;
  }

  function renderMessage(message){
    const mine=message.sender_id===state.user?.id;
    return `<div class="uka-chat-line ${mine?'is-mine':'is-theirs'}" data-message-id="${esc(message.id)}"><div class="uka-chat-bubble">${message.event_id?renderEventAttachment(message.event_id):''}${message.body?`<p>${esc(message.body)}</p>`:''}<time>${esc(formatTime(message.created_at))}</time></div></div>`;
  }

  function renderChat(){
    const row=friendRow(state.activeFriendId),p=row?.profile||{};
    if(!row){state.view='home';return renderHome();}
    const body=state.chatLoading
      ? '<div class="uka-chat-loading">Načítám zprávy…</div>'
      : state.messages.length?state.messages.map(renderMessage).join(''):'<div class="uka-chat-empty"><div class="uka-chat-empty-avatar">'+avatar(p)+'</div><strong>'+esc(nameOf(p))+'</strong><span>'+esc(usernameOf(p))+'</span><p>Napiš první zprávu nebo mu pošli akci, která stojí za to.</p></div>';
    return `<div class="uka-chat-shell"><div class="uka-chat-header"><button type="button" class="uka-chat-back" data-online-action="back-home" aria-label="Zpět">${icon('back')}</button>${avatar(p,'small')}<div class="uka-chat-header-copy"><strong>${esc(nameOf(p))}</strong><span>${esc(usernameOf(p))}</span></div></div><div id="ukaChatMessages" class="uka-chat-messages">${body}</div><form id="ukaChatForm" class="uka-chat-composer"><textarea id="ukaChatInput" name="message" rows="1" maxlength="2000" placeholder="Napiš zprávu…" autocomplete="off" ${state.sending?'disabled':''}></textarea><button type="submit" class="uka-chat-send" aria-label="Odeslat" ${state.sending?'disabled':''}>${icon('send')}</button></form></div>`;
  }

  function renderHome(){
    return `${renderTopbar()}${state.error?`<div class="uka-online-error">${esc(state.error)}</div>`:''}${renderProfile()}<div class="uka-online-content">${renderMessages()}${renderFriends()}${renderRequests()}${renderSearch()}</div>`;
  }

  function renderApp(){
    const root=document.getElementById('ukaOnlineRoot');
    if(!root)return;
    if(state.loading&&!state.user){root.innerHTML='<div class="uka-online-loading">Načítám přátele…</div>';return;}
    if(!state.user){root.innerHTML=renderLoggedOut();return;}
    root.innerHTML=state.view==='chat'?renderChat():renderHome();
    if(state.view==='chat')scrollChatBottom(false);
  }

  function ensurePortal(){
    let root=document.getElementById('ukaSocialPortal');
    if(!root){root=document.createElement('div');root.id='ukaSocialPortal';document.body.appendChild(root);}
    return root;
  }

  function renderRemoveDialog(){
    const p=state.removeCandidate?.profile||{};
    return `<div class="uka-social-overlay" data-social-close="true"><div class="uka-social-dialog uka-remove-dialog" role="dialog" aria-modal="true" aria-labelledby="ukaRemoveTitle"><div class="uka-social-dialog-avatar">${avatar(p)}</div><h3 id="ukaRemoveTitle">Odebrat z přátel?</h3><p>Opravdu chceš odebrat <strong>${esc(nameOf(p))}</strong> z přátel?</p><div class="uka-social-dialog-actions"><button type="button" class="uka-social-danger-button" data-online-action="confirm-remove" data-user-id="${esc(state.removeCandidate?.friend_id||'')}">Ano, odebrat</button><button type="button" class="uka-social-cancel-button" data-online-action="close-dialog">Ne</button></div></div></div>`;
  }

  function renderShareDialog(){
    const e=state.shareEvent;
    const img=/^https:\/\//i.test(String(e?.image_url||''))?`<img src="${esc(e.image_url)}" alt="">`:'♫';
    const rows=state.friends.length?state.friends.map(row=>{
      const p=row.profile||{},sent=state.shareSent.has(row.friend_id);
      return `<div class="uka-share-person">${avatar(p,'small')}<div><strong>${esc(nameOf(p))}</strong><span>${esc(usernameOf(p))}</span></div><button type="button" class="${sent?'is-sent':''}" data-online-action="share-send" data-user-id="${esc(row.friend_id)}" ${sent?'disabled':''}>${sent?'Odesláno':'Poslat'}</button></div>`;
    }).join(''):'<div class="uka-online-soft-empty">Nemáš zatím žádné přátele, kterým by šla akce poslat.</div>';
    return `<div class="uka-social-overlay" data-social-close="true"><div class="uka-social-dialog uka-share-dialog" role="dialog" aria-modal="true" aria-labelledby="ukaShareTitle"><div class="uka-social-dialog-head"><div><small>POSLAT AKCI</small><h3 id="ukaShareTitle">Komu ji pošleš?</h3></div><button type="button" class="uka-social-close" data-online-action="close-dialog" aria-label="Zavřít">×</button></div><div class="uka-share-event-preview"><span class="uka-share-event-thumb">${img}</span><div><strong>${esc(e?.title||'Akce')}</strong><span>${esc([formatEventDate(e?.date),e?.venue,e?.city].filter(Boolean).join(' · '))}</span></div></div><label class="uka-share-note"><span>Přidat zprávu</span><input id="ukaShareMessage" maxlength="500" value="${esc(state.shareMessage)}" placeholder="Třeba: Na tohle musíme! 🔥"></label><div class="uka-share-list">${rows}</div></div></div>`;
  }

  function renderPortal(){
    const root=ensurePortal();
    if(state.removeCandidate)root.innerHTML=renderRemoveDialog();
    else if(state.shareEvent)root.innerHTML=renderShareDialog();
    else root.innerHTML='';
    document.body.classList.toggle('uka-social-modal-open',!!(state.removeCandidate||state.shareEvent));
  }

  function closeDialogs(){state.removeCandidate=null;state.shareEvent=null;state.shareMessage='';state.shareSent=new Set();renderPortal();}

  function notify(message){
    if(typeof window.showToast==='function')window.showToast(message);
    else console.info('UKA:',message);
  }

  async function ensureRealtime(){
    const api=window.UKASocial;
    if(!api||!state.user||state.realtime)return;
    try{
      state.realtime=await api.subscribeDirectMessages(async message=>{
        const friendId=message.sender_id===state.user?.id?message.recipient_id:message.sender_id;
        if(!friendId)return;
        if(state.view==='chat'&&state.activeFriendId===friendId){
          if(!state.messages.some(row=>row.id===message.id))state.messages.push(message);
          renderApp();
          scrollChatBottom(true);
          if(message.recipient_id===state.user.id)api.markConversationSeen(friendId).catch(()=>{});
        }
        refreshOverview();
      });
    }catch(error){console.warn('UKA realtime chat failed',error);}
  }

  async function refreshOverview(){
    if(!state.user||!window.UKASocial)return;
    try{state.overview=await window.UKASocial.getMessageOverview();if(state.view==='home')renderApp();}
    catch(error){console.warn('UKA message overview failed',error);}
  }

  async function load(){
    const api=window.UKASocial;
    state.error='';
    if(!api){state.user=null;state.loading=false;state.error='Sociální funkce se nenačetly.';renderApp();return;}
    state.loading=true;renderApp();
    try{
      const nextUser=await api.currentUser();
      if(state.user?.id&&nextUser?.id!==state.user.id&&state.realtime){await api.unsubscribeChannel(state.realtime);state.realtime=null;}
      state.user=nextUser;
      if(!state.user){state.profile=null;state.friends=[];state.incoming=[];state.outgoing=[];state.overview=[];state.view='home';return;}
      const [profile,friends,requests,overview]=await Promise.all([api.getMyProfile(),api.getFriends(),api.getFriendRequests(),api.getMessageOverview()]);
      state.profile=profile;state.friends=friends;state.incoming=requests.incoming||[];state.outgoing=requests.outgoing||[];state.overview=overview||[];
      if(state.activeFriendId&&!friendRow(state.activeFriendId)){state.activeFriendId=null;state.view='home';}
      await ensureRealtime();
    }catch(error){
      console.warn('UKA social load failed',error);
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
      console.warn('UKA social action failed',error);
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

  function scrollChatBottom(smooth=true){
    requestAnimationFrame(()=>{const box=document.getElementById('ukaChatMessages');if(box)box.scrollTo({top:box.scrollHeight,behavior:smooth?'smooth':'auto'});});
  }

  async function openChat(friendId){
    const row=friendRow(friendId);if(!row)return;
    state.view='chat';state.activeFriendId=friendId;state.messages=[];state.chatLoading=true;state.error='';renderApp();
    try{
      state.messages=await window.UKASocial.getConversation(friendId);
      await window.UKASocial.markConversationSeen(friendId);
      const overview=overviewFor(friendId);if(overview)overview.unread=0;
    }catch(error){state.error=error?.message||'Zprávy se nepodařilo načíst.';}
    finally{state.chatLoading=false;renderApp();scrollChatBottom(false);setTimeout(()=>document.getElementById('ukaChatInput')?.focus(),60);}
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

  async function openShare(eventItem){
    const api=window.UKASocial;
    if(!api)return notify('Sociální funkce se nenačetly.');
    try{
      const user=state.user||await api.currentUser();
      if(!user){document.getElementById('ukaAuthButton')?.click();return;}
      state.user=user;
      if(!state.friends.length)state.friends=await api.getFriends();
      state.shareEvent={...eventItem};state.shareMessage='';state.shareSent=new Set();renderPortal();
    }catch(error){notify(error?.message||'Akci se nepodařilo připravit k odeslání.');}
  }

  document.addEventListener('click',event=>{
    const openEvent=event.target.closest('[data-open-event]');
    if(openEvent){window.UKAEvents?.open?.(openEvent.dataset.openEvent);return;}
    if(event.target.matches('.uka-social-overlay[data-social-close="true"]')){closeDialogs();return;}
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
    if(action==='focus-messages'){focusSection('ukaOnlineMessages');return;}
    if(action==='open-chat'){openChat(button.dataset.userId);return;}
    if(action==='back-home'){state.view='home';state.activeFriendId=null;state.messages=[];renderApp();return;}
    if(action==='close-dialog'){closeDialogs();return;}
    const api=window.UKASocial;if(!api)return;
    if(action==='remove-avatar')run(()=>api.removeAvatar(),'Profilová fotka odebrána.').then(()=>{state.avatarBusy=false;});
    if(action==='add')run(()=>api.sendFriendRequest(button.dataset.userId),'Žádost o přátelství odeslána.');
    if(action==='accept')run(()=>api.acceptFriendRequest(button.dataset.requestId),'Jste přátelé.');
    if(action==='decline')run(()=>api.declineFriendRequest(button.dataset.requestId),'Žádost odmítnuta.');
    if(action==='remove'){
      const row=friendRow(button.dataset.userId);if(!row)return;
      state.removeCandidate=row;renderPortal();return;
    }
    if(action==='confirm-remove'){
      const userId=button.dataset.userId;
      run(()=>api.removeFriend(userId),'Přítel odebrán.').then(()=>closeDialogs());return;
    }
    if(action==='share-send'){
      const recipientId=button.dataset.userId;if(!state.shareEvent||state.shareSent.has(recipientId))return;
      button.disabled=true;
      api.sendDirectMessage(recipientId,state.shareMessage,state.shareEvent.id).then(()=>{
        state.shareSent.add(recipientId);notify('Akce odeslána.');renderPortal();refreshOverview();
      }).catch(error=>{button.disabled=false;notify(error?.message||'Akci se nepodařilo poslat.');});
    }
  });

  document.addEventListener('change',event=>{
    if(event.target?.id==='ukaOnlineAvatarInput'){
      const file=event.target.files?.[0];event.target.value='';uploadAvatar(file);
    }
  });

  document.addEventListener('input',event=>{
    if(event.target?.id==='ukaShareMessage')state.shareMessage=String(event.target.value||'').slice(0,500);
    if(event.target?.id==='ukaChatInput'){
      event.target.style.height='auto';event.target.style.height=`${Math.min(event.target.scrollHeight,120)}px`;
    }
  });

  document.addEventListener('keydown',event=>{
    if(event.target?.id==='ukaChatInput'&&event.key==='Enter'&&!event.shiftKey){event.preventDefault();event.target.form?.requestSubmit();}
    if(event.key==='Escape'&&(state.removeCandidate||state.shareEvent))closeDialogs();
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
      return;
    }
    if(event.target.id==='ukaChatForm'){
      event.preventDefault();
      if(state.sending||!state.activeFriendId)return;
      const input=document.getElementById('ukaChatInput');const text=String(input?.value||'').trim();if(!text)return;
      state.sending=true;if(input)input.disabled=true;
      window.UKASocial.sendDirectMessage(state.activeFriendId,text,null).then(message=>{
        if(message&&!state.messages.some(row=>row.id===message.id))state.messages.push(message);
        if(input){input.value='';input.style.height='auto';}
        state.sending=false;renderApp();scrollChatBottom(true);refreshOverview();
      }).catch(error=>{state.sending=false;notify(error?.message||'Zprávu se nepodařilo odeslat.');renderApp();});
    }
  });

  window.UKAOnline={page,mount,openShare};
  window.addEventListener('load',()=>{
    subscribeAuth();
    if(location.hash==='#online')window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
})();
