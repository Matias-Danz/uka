(() => {
  'use strict';

  const state={
    user:null,profile:null,friends:[],incoming:[],outgoing:[],search:[],query:'',overview:[],
    route:{section:'social',profileId:null,friendId:null},viewedProfile:null,viewedFavorites:[],
    messages:[],loading:false,chatLoading:false,sending:false,error:'',editing:false,avatarBusy:false,
    removeCandidate:null,shareEvent:null,shareMessage:'',shareSent:new Set(),themeDialog:false,
    followStats:{followers:0,following:0,is_following:false},chatTheme:'default',chatDraft:'',emojiPicker:false,reactionPicker:null,
    realtime:null,reactionRealtime:null,realtimeUserId:null,realtimeReady:false,pollTimer:null
  };
  let authSubscribed=false,backgroundStarted=false;

  const esc=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const initials=profile=>String(profile?.display_name||profile?.username||'?').trim().slice(0,1).toUpperCase()||'?';
  const nameOf=profile=>profile?.display_name||profile?.username||'Uživatel';
  const usernameOf=profile=>profile?.username?`@${profile.username}`:'@bez-jmena';
  const icon=(id,cls='')=>`<svg class="icon ${cls}" aria-hidden="true"><use href="#i-${id}"/></svg>`;
  const CHAT_EMOJIS=['😀','😂','😍','🥰','😎','🥳','😭','😮','😅','🤝','👏','🙌','👍','👎','❤️','💚','🔥','✨','🎉','🎵','🎶','🫶','👀','💀','🤯','😈','🙏','✅','🚀','🍻'];
  const REACTION_EMOJIS=['❤️','😂','🔥','😍','😭','😮','👍','👏'];
  const CHAT_THEMES=[
    {id:'default',name:'UKA',hint:'Čistý výchozí vzhled'},
    {id:'midnight',name:'Midnight',hint:'Tmavě modrá'},
    {id:'aurora',name:'Aurora',hint:'Zelená záře'},
    {id:'sunset',name:'Sunset',hint:'Teplý gradient'},
    {id:'violet',name:'Violet',hint:'Fialový neon'}
  ];

  function page(){
    return `<section class="uka-online-page"><div class="container uka-online-container"><div id="ukaOnlineRoot" class="uka-online-root"><div class="uka-online-loading">Načítám…</div></div></div></section>`;
  }

  function parseRoute(){
    const raw=decodeURIComponent((location.hash||'#social').slice(1));
    const parts=raw.split('/');
    const base=parts[0]==='online'?'social':parts[0];
    if(base==='messages')return {section:'messages',friendId:parts[1]||null,profileId:null};
    return {section:'social',profileId:base==='social'?(parts[1]||null):null,friendId:null};
  }

  function goHash(value){
    const next=`#${value}`;
    if(location.hash===next)mount();
    else location.hash=value;
  }

  function avatar(profile,size='normal'){
    if(profile?.avatar_url){
      const url=String(profile.avatar_url);
      if(/^https:\/\//i.test(url))return `<img class="uka-online-avatar ${size==='small'?'is-small':''}" src="${esc(url)}" alt="Profilová fotka">`;
    }
    return `<span class="uka-online-avatar uka-online-avatar-fallback ${size==='small'?'is-small':''}" aria-hidden="true">${esc(initials(profile))}</span>`;
  }

  function friendRow(friendId){return state.friends.find(row=>row.friend_id===friendId)||null;}
  function overviewFor(friendId){return state.overview.find(row=>row.friend_id===friendId)||null;}
  function isFriend(userId){return !!friendRow(userId);}

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

  function eventInfo(id){return window.UKAEvents?.getAnyById?.(id)||window.UKAEvents?.getById?.(id)||null;}

  function previewFor(message){
    if(!message)return 'Napiš první zprávu';
    if(message.event_id&&message.body)return `Akce · ${message.body}`;
    if(message.event_id)return 'Poslal(a) akci';
    return message.body||'Zpráva';
  }

  function unreadTotal(){return state.overview.reduce((sum,row)=>sum+(Number(row.unread)||0),0);}
  function updateGlobalBadge(){
    const count=unreadTotal();
    for(const id of ['ukaMessagesBadgeDesktop','ukaMessagesBadgeMobile']){
      const badge=document.getElementById(id);if(!badge)continue;
      badge.hidden=count<=0;badge.textContent=count>99?'99+':String(count||'');
    }
  }

  function renderLoggedOut(){
    const messaging=state.route.section==='messages';
    return `<div class="uka-online-empty uka-online-login"><div class="uka-online-empty-icon">${icon(messaging?'message':'user')}</div><h2>${messaging?'Zprávy':'Tvůj profil'}</h2><p>Přihlas se a používej přátele, veřejně uložené akce a chat přímo v UKA.</p><button type="button" class="btn btn-primary" data-online-action="login">Přihlásit se</button></div>`;
  }

  function relationAction(profile){
    if(!profile?.id||profile.id===state.user?.id)return '';
    if(isFriend(profile.id))return `<button type="button" class="btn btn-primary btn-sm" data-online-action="open-chat" data-user-id="${esc(profile.id)}">Zpráva</button>`;
    const outgoing=state.outgoing.some(row=>row.receiver_id===profile.id);
    if(outgoing)return '<span class="uka-online-state">Žádost odeslána</span>';
    const incoming=state.incoming.find(row=>row.sender_id===profile.id);
    if(incoming)return `<button type="button" class="btn btn-primary btn-sm" data-online-action="accept" data-request-id="${esc(incoming.id)}">Přijmout</button>`;
    return `<button type="button" class="btn btn-primary btn-sm" data-online-action="add" data-user-id="${esc(profile.id)}">Přidat do spojení</button>`;
  }

  function followAction(profile){
    if(!profile?.id||profile.id===state.user?.id)return '';
    return state.followStats.is_following
      ? `<button type="button" class="btn btn-outline btn-sm" data-online-action="unfollow" data-user-id="${esc(profile.id)}">V okruhu</button>`
      : `<button type="button" class="btn btn-outline btn-sm" data-online-action="follow" data-user-id="${esc(profile.id)}">Sledovat</button>`;
  }

  function userRow(profile,actions=''){
    if(!profile)return '';
    return `<div class="uka-online-user"><button type="button" class="uka-online-user-open" data-online-action="open-profile" data-user-id="${esc(profile.id)}">${avatar(profile,'small')}<span class="uka-online-user-copy"><strong>${esc(nameOf(profile))}</strong><span>${esc(usernameOf(profile))}</span></span></button><div class="uka-online-user-actions">${actions}</div></div>`;
  }

  function renderSocialTopbar(other=false){
    return `<div class="uka-online-topbar">${other?`<button type="button" class="uka-profile-back" data-online-action="own-profile" aria-label="Zpět na můj profil">${icon('back')}</button>`:''}<div><h1>${other?'Profil':'Profil'}</h1></div><div class="uka-online-top-actions"><button type="button" class="uka-online-icon-button" data-online-action="focus-search" aria-label="Najít lidi" title="Najít lidi">${icon('search')}</button><button type="button" class="uka-online-icon-button" data-online-action="refresh" aria-label="Obnovit" title="Obnovit">↻</button></div></div>`;
  }

  function renderMessagesTopbar(){
    return `<div class="uka-online-topbar"><div><h1>Zprávy</h1></div><div class="uka-online-top-actions"><button type="button" class="uka-online-icon-button" data-online-action="refresh" aria-label="Obnovit" title="Obnovit">↻</button></div></div>`;
  }

  function renderEditor(){
    const p=state.profile||{};
    if(!state.editing)return '';
    return `<div class="uka-online-editor-wrap"><form id="ukaOnlineProfileForm" class="uka-online-profile-form"><div class="uka-online-editor-title"><strong>Upravit profil</strong><button type="button" class="uka-online-text-button" data-online-action="cancel-edit">Zrušit</button></div><label>Uživatelské jméno<input name="username" maxlength="30" autocomplete="username" value="${esc(p.username||'')}" placeholder="např. klara23"></label><label>Jméno<input name="display_name" maxlength="80" value="${esc(p.display_name||'')}" placeholder="Tvoje jméno"></label><label class="uka-online-wide">Bio<textarea name="bio" maxlength="300" rows="3" placeholder="Něco krátce o sobě">${esc(p.bio||'')}</textarea></label><div class="uka-online-wide uka-online-form-end"><span class="uka-online-help">3–30 znaků, bez mezer.</span><button class="btn btn-primary" type="submit">Uložit změny</button></div></form></div>`;
  }

  function renderProfileHeader(profile,isOwn){
    const savedCount=state.viewedFavorites.length;
    const followers=Number(state.followStats?.followers)||0;
    const following=Number(state.followStats?.following)||0;
    const avatarHtml=isOwn
      ? `<div class="uka-online-avatar-wrap"><button type="button" class="uka-online-avatar-button" data-online-action="choose-avatar" ${state.avatarBusy?'disabled':''} aria-label="Změnit profilovou fotku">${avatar(profile)}<span class="uka-online-avatar-edit">${state.avatarBusy?'…':'+'}</span></button><input id="ukaOnlineAvatarInput" type="file" accept="image/jpeg,image/png,image/webp" hidden></div>`
      : `<div class="uka-online-avatar-wrap">${avatar(profile)}</div>`;
    const stats=`<div class="uka-online-stats"><span class="uka-online-stat"><strong>${followers}</strong><span>Okruh</span></span><span class="uka-online-stat"><strong>${following}</strong><span>Objevuju</span></span><button type="button" data-online-action="focus-saved"><strong>${savedCount}</strong><span>Uložené</span></button></div>`;
    const actions=isOwn
      ? `<div class="uka-online-profile-actions"><button type="button" class="btn btn-outline btn-sm" data-online-action="edit-profile">Upravit profil</button><button type="button" class="btn btn-outline btn-sm" data-online-action="focus-search">Najít lidi</button>${profile?.avatar_url?'<button type="button" class="uka-online-text-button uka-online-remove-photo" data-online-action="remove-avatar">Odebrat fotku</button>':''}</div>`
      : `<div class="uka-online-profile-actions">${followAction(profile)}${relationAction(profile)}</div>`;
    return `<section class="uka-online-profile-shell"><div class="uka-online-profile-top">${avatarHtml}<div class="uka-online-profile-copy"><div class="uka-online-profile-name-row"><h2>${esc(nameOf(profile))}</h2><span>${esc(usernameOf(profile))}</span></div>${stats}${profile?.bio?`<p class="uka-online-bio">${esc(profile.bio)}</p>`:(isOwn?'<p class="uka-online-bio is-empty">Přidej krátké bio, ať tě lidi poznají.</p>':'')}${actions}</div></div>${isOwn?renderEditor():''}</section>`;
  }

  function renderSavedEvents(){
    const rows=state.viewedFavorites||[];
    const cards=rows.map(row=>{
      const e=eventInfo(row.event_id);if(!e)return '';
      const img=/^https:\/\//i.test(String(e.image_url||''))?`<img src="${esc(e.image_url)}" alt="">`:'<span>♫</span>';
      const where=[e.venue,e.city].filter(Boolean).join(' · ');
      return `<button type="button" class="uka-profile-event" data-open-event="${esc(e.id)}"><span class="uka-profile-event-media">${img}<em>${esc(formatEventDate(e.date))}</em></span><span class="uka-profile-event-copy"><strong>${esc(e.title||'Akce')}</strong><small>${esc(where)}</small></span></button>`;
    }).filter(Boolean).join('');
    return `<section id="ukaProfileSaved" class="uka-online-section uka-profile-saved"><div class="uka-online-section-head"><h3>Uložené akce</h3><span>${cards?state.viewedFavorites.length:0}</span></div>${cards?`<div class="uka-profile-event-grid">${cards}</div>`:'<div class="uka-online-soft-empty">Zatím tu nejsou žádné uložené akce.</div>'}</section>`;
  }

  function renderFriends(){
    if(!state.friends.length)return `<section id="ukaOnlineFriends" class="uka-online-section"><div class="uka-online-section-head"><h3>Spojení</h3></div><div class="uka-online-soft-empty">Zatím tu nikoho nemáš. Najdi si první spojení.</div></section>`;
    const items=state.friends.map(row=>{
      const p=row.profile||{};
      return `<div class="uka-online-friend"><button type="button" class="uka-online-friend-open" data-online-action="open-profile" data-user-id="${esc(row.friend_id)}"><div class="uka-online-friend-avatar">${avatar(p)}</div><strong>${esc(nameOf(p))}</strong><span>${esc(usernameOf(p))}</span></button><div class="uka-online-friend-actions"><button type="button" class="uka-online-friend-message" data-online-action="open-chat" data-user-id="${esc(row.friend_id)}">${icon('message')}<span>Zpráva</span></button><button type="button" class="uka-online-friend-menu" data-online-action="remove" data-user-id="${esc(row.friend_id)}" aria-label="Možnosti spojení" title="Odebrat">•••</button></div></div>`;
    }).join('');
    return `<section id="ukaOnlineFriends" class="uka-online-section"><div class="uka-online-section-head"><h3>Spojení</h3><span>${state.friends.length}</span></div><div class="uka-online-friends-strip">${items}</div></section>`;
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
      results=state.search.length?`<div class="uka-online-list uka-online-search-results">${state.search.map(profile=>userRow(profile,relationAction(profile))).join('')}</div>`:'<div class="uka-online-soft-empty">Nikdo nenalezen.</div>';
    }
    return `<section id="ukaOnlineSearch" class="uka-online-section uka-online-search-section"><div class="uka-online-section-head"><h3>Najít lidi</h3></div><form id="ukaOnlineSearchForm" class="uka-online-search"><span class="uka-online-search-icon">⌕</span><input id="ukaOnlineSearchInput" name="q" minlength="2" maxlength="30" value="${esc(state.query)}" placeholder="Hledat podle @username" autocomplete="off"><button class="btn btn-primary btn-sm" type="submit">Hledat</button></form>${results}</section>`;
  }

  function renderSocialPage(){
    const profile=state.viewedProfile||state.profile;
    const isOwn=!state.route.profileId||state.route.profileId===state.user?.id;
    if(!profile)return `${renderSocialTopbar(!isOwn)}<div class="uka-online-soft-empty">Profil se nepodařilo najít.</div>`;
    return `${renderSocialTopbar(!isOwn)}${state.error?`<div class="uka-online-error">${esc(state.error)}</div>`:''}${renderProfileHeader(profile,isOwn)}<div class="uka-online-content">${renderSavedEvents()}${isOwn?`${renderFriends()}${renderRequests()}${renderSearch()}`:''}</div>`;
  }

  function renderConversationRows(){
    if(!state.friends.length)return '<div class="uka-online-soft-empty">Nejdřív si přidej kamaráda. Pak si můžete psát a posílat akce.</div>';
    const ordered=[...state.friends].sort((a,b)=>{
      const am=overviewFor(a.friend_id)?.last_message?.created_at||'';
      const bm=overviewFor(b.friend_id)?.last_message?.created_at||'';
      if(am||bm)return bm.localeCompare(am);
      return nameOf(a.profile).localeCompare(nameOf(b.profile),'cs');
    });
    return `<div class="uka-conversation-list">${ordered.map(row=>{
      const p=row.profile||{},overview=overviewFor(row.friend_id),last=overview?.last_message,unread=Number(overview?.unread)||0;
      return `<button type="button" class="uka-conversation-row ${unread?'has-unread':''}" data-online-action="open-chat" data-user-id="${esc(row.friend_id)}">${avatar(p,'small')}<span class="uka-conversation-copy"><strong>${esc(nameOf(p))}</strong><span>${esc(previewFor(last))}</span></span><span class="uka-conversation-meta">${last?`<time>${esc(formatTime(last.created_at))}</time>`:''}${unread?`<b>${unread>99?'99+':unread}</b>`:''}</span></button>`;
    }).join('')}</div>`;
  }

  function renderMessagesPage(){
    return `${renderMessagesTopbar()}${state.error?`<div class="uka-online-error">${esc(state.error)}</div>`:''}<section class="uka-online-section uka-messages-page"><div class="uka-messages-intro"><div><strong>Konverzace</strong><span>${state.friends.length} spojení</span></div></div>${renderConversationRows()}</section>`;
  }

  function renderEventAttachment(eventId){
    const e=eventInfo(eventId);
    if(!e)return `<button type="button" class="uka-chat-event-card is-missing" data-open-event="${esc(eventId)}"><span class="uka-chat-event-thumb">♫</span><span class="uka-chat-event-copy"><small>Sdílená akce</small><strong>Akce už není v nabídce</strong><em>Detail už není dostupný</em></span></button>`;
    const img=/^https:\/\//i.test(String(e.image_url||''))?`<img src="${esc(e.image_url)}" alt="">`:'♫';
    const where=[e.venue,e.city].filter(Boolean).join(' · ');
    return `<button type="button" class="uka-chat-event-card" data-open-event="${esc(eventId)}"><span class="uka-chat-event-thumb">${img}</span><span class="uka-chat-event-copy"><small>${esc(formatEventDate(e.date))}${e.time?` · ${esc(e.time)}`:''}</small><strong>${esc(e.title||'Akce')}</strong>${where?`<em>${esc(where)}</em>`:''}</span><span class="uka-chat-event-arrow">›</span></button>`;
  }

  function renderReactionSummary(message){
    const rows=message.reactions||[];if(!rows.length)return '';
    const grouped=new Map();
    for(const row of rows){
      const item=grouped.get(row.emoji)||{emoji:row.emoji,count:0,mine:false};item.count+=1;if(row.user_id===state.user?.id)item.mine=true;grouped.set(row.emoji,item);
    }
    return `<div class="uka-message-reactions">${[...grouped.values()].map(item=>`<button type="button" class="uka-reaction-chip ${item.mine?'is-mine':''}" data-online-action="react-message" data-message-id="${esc(message.id)}" data-emoji="${esc(item.emoji)}"><span>${esc(item.emoji)}</span>${item.count>1?`<b>${item.count}</b>`:''}</button>`).join('')}</div>`;
  }

  function renderReactionPicker(message){
    if(state.reactionPicker!==message.id)return '';
    return `<div class="uka-reaction-picker" role="menu" aria-label="Reakce na zprávu">${REACTION_EMOJIS.map(emoji=>`<button type="button" data-online-action="react-message" data-message-id="${esc(message.id)}" data-emoji="${esc(emoji)}">${esc(emoji)}</button>`).join('')}</div>`;
  }

  function renderMessage(message){
    const mine=message.sender_id===state.user?.id;
    return `<div class="uka-chat-line ${mine?'is-mine':'is-theirs'}" data-message-id="${esc(message.id)}"><div class="uka-chat-message-stack"><div class="uka-chat-bubble-wrap"><div class="uka-chat-bubble" data-chat-bubble="${esc(message.id)}">${message.event_id?renderEventAttachment(message.event_id):''}${message.body?`<p>${esc(message.body)}</p>`:''}<time>${esc(formatTime(message.created_at))}</time></div><button type="button" class="uka-message-react-trigger" data-online-action="open-reactions" data-message-id="${esc(message.id)}" aria-label="Reagovat na zprávu">♡</button>${renderReactionPicker(message)}</div>${renderReactionSummary(message)}</div></div>`;
  }

  function chatBody(){
    const row=friendRow(state.route.friendId),p=row?.profile||{};
    if(state.chatLoading)return '<div class="uka-chat-loading">Načítám zprávy…</div>';
    if(state.messages.length)return state.messages.map(renderMessage).join('');
    return `<div class="uka-chat-empty"><div class="uka-chat-empty-avatar">${avatar(p)}</div><strong>${esc(nameOf(p))}</strong><span>${esc(usernameOf(p))}</span><p>Napiš první zprávu nebo pošli akci, která stojí za to.</p></div>`;
  }

  function renderEmojiPanel(){
    if(!state.emojiPicker)return '';
    return `<div class="uka-chat-emoji-panel" role="dialog" aria-label="Emoji">${CHAT_EMOJIS.map(emoji=>`<button type="button" data-online-action="insert-emoji" data-emoji="${esc(emoji)}">${esc(emoji)}</button>`).join('')}</div>`;
  }

  function renderChat(){
    const row=friendRow(state.route.friendId),p=row?.profile||{};
    if(!row)return `${renderMessagesTopbar()}<div class="uka-online-soft-empty">Tuhle konverzaci nemůžu otevřít. Uživatel už nejspíš není ve spojení.</div>`;
    return `<div class="uka-chat-shell"><div class="uka-chat-header"><button type="button" class="uka-chat-back" data-online-action="messages-home" aria-label="Zpět">${icon('back')}</button><button type="button" class="uka-chat-profile-link" data-online-action="open-profile" data-user-id="${esc(row.friend_id)}">${avatar(p,'small')}<span class="uka-chat-header-copy"><strong>${esc(nameOf(p))}</strong><span>${esc(usernameOf(p))}</span></span></button><div class="uka-chat-header-actions"><button type="button" class="uka-chat-theme-button" data-online-action="chat-theme" aria-label="Změnit pozadí chatu" title="Pozadí chatu">✦</button></div></div><div id="ukaChatMessages" class="uka-chat-messages" data-chat-theme="${esc(state.chatTheme)}">${chatBody()}</div><div class="uka-chat-composer-wrap">${renderEmojiPanel()}<form id="ukaChatForm" class="uka-chat-composer"><button type="button" class="uka-chat-emoji-button" data-online-action="toggle-emoji" aria-label="Emoji">☺</button><textarea id="ukaChatInput" name="message" rows="1" maxlength="2000" placeholder="Napiš zprávu…" autocomplete="off" ${state.sending?'disabled':''}>${esc(state.chatDraft)}</textarea><button type="submit" class="uka-chat-send" aria-label="Odeslat" ${state.sending?'disabled':''}>${icon('send')}</button></form></div></div>`;
  }

  function renderApp(){
    const root=document.getElementById('ukaOnlineRoot');if(!root)return;
    if(state.loading&&!state.user){root.innerHTML='<div class="uka-online-loading">Načítám…</div>';return;}
    if(!state.user){root.innerHTML=renderLoggedOut();return;}
    if(state.route.section==='messages'&&state.route.friendId)root.innerHTML=renderChat();
    else if(state.route.section==='messages')root.innerHTML=renderMessagesPage();
    else root.innerHTML=renderSocialPage();
    updateGlobalBadge();
    if(state.route.section==='messages'&&state.route.friendId)scrollChatBottom(false);
  }

  function renderChatMessagesOnly(forceBottom=false){
    const box=document.getElementById('ukaChatMessages');if(!box)return;
    const nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<100;
    box.innerHTML=chatBody();
    if(forceBottom||nearBottom)requestAnimationFrame(()=>box.scrollTo({top:box.scrollHeight,behavior:forceBottom?'smooth':'auto'}));
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

  function renderThemeDialog(){
    return `<div class="uka-social-overlay" data-social-close="true"><div class="uka-social-dialog uka-theme-dialog" role="dialog" aria-modal="true" aria-labelledby="ukaThemeTitle"><div class="uka-social-dialog-head"><div><small>VZHLED CHATU</small><h3 id="ukaThemeTitle">Pozadí konverzace</h3></div><button type="button" class="uka-social-close" data-online-action="close-dialog" aria-label="Zavřít">×</button></div><div class="uka-theme-grid">${CHAT_THEMES.map(theme=>`<button type="button" class="uka-theme-option ${state.chatTheme===theme.id?'is-active':''}" data-online-action="set-chat-theme" data-theme-value="${esc(theme.id)}"><span class="uka-theme-swatch" data-theme-preview="${esc(theme.id)}"></span><strong>${esc(theme.name)}</strong><small>${esc(theme.hint)}</small></button>`).join('')}</div></div></div>`;
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
    else if(state.themeDialog)root.innerHTML=renderThemeDialog();
    else root.innerHTML='';
    document.body.classList.toggle('uka-social-modal-open',!!(state.removeCandidate||state.shareEvent||state.themeDialog));
  }

  function closeDialogs(){state.removeCandidate=null;state.shareEvent=null;state.themeDialog=false;state.shareMessage='';state.shareSent=new Set();renderPortal();}
  function notify(message){if(typeof window.showToast==='function')window.showToast(message);else console.info('UKA:',message);}

  function sameMessages(a,b){
    if(a.length!==b.length)return false;
    for(let i=0;i<a.length;i++){
      const ar=(a[i].reactions||[]).map(row=>`${row.user_id}:${row.emoji}`).sort().join('|');
      const br=(b[i].reactions||[]).map(row=>`${row.user_id}:${row.emoji}`).sort().join('|');
      if(a[i].id!==b[i].id||a[i].seen_at!==b[i].seen_at||a[i].body!==b[i].body||a[i].event_id!==b[i].event_id||ar!==br)return false;
    }
    return true;
  }

  async function refreshOverview(render=true){
    if(!state.user||!window.UKASocial)return;
    try{
      state.overview=await window.UKASocial.getMessageOverview();updateGlobalBadge();
      if(render&&state.route.section==='messages'&&!state.route.friendId)renderApp();
    }catch(error){console.warn('UKA message overview failed',error);}
  }

  async function syncConversation(){
    const friendId=state.route.section==='messages'?state.route.friendId:null;
    if(!friendId||!state.user||!friendRow(friendId))return;
    try{
      const next=await window.UKASocial.getConversation(friendId);
      if(!sameMessages(state.messages,next)){
        const had=state.messages.length;state.messages=next;renderChatMessagesOnly(next.length>had);
      }
      await window.UKASocial.markConversationSeen(friendId);
      const overview=overviewFor(friendId);if(overview)overview.unread=0;
      updateGlobalBadge();
    }catch(error){console.warn('UKA chat sync failed',error);}
  }

  function startPolling(){
    if(state.pollTimer){clearInterval(state.pollTimer);state.pollTimer=null;}
    if(!state.user||state.route.section!=='messages')return;
    state.pollTimer=setInterval(async()=>{
      if(document.hidden)return;
      if(state.route.friendId)await syncConversation();
      await refreshOverview(!state.route.friendId);
    },1200);
  }

  async function handleRealtimeMessage(message){
    if(!message||!state.user)return;
    const friendId=message.sender_id===state.user.id?message.recipient_id:message.sender_id;
    if(!friendId)return;
    if(state.route.section==='messages'&&state.route.friendId===friendId){
      if(!state.messages.some(row=>row.id===message.id)){
        state.messages.push({...message,reactions:message.reactions||[]});renderChatMessagesOnly(true);
      }
      if(message.recipient_id===state.user.id)window.UKASocial.markConversationSeen(friendId).catch(()=>{});
    }
    await refreshOverview(state.route.section==='messages'&&!state.route.friendId);
  }

  async function handleRealtimeReaction(){
    if(state.route.section==='messages'&&state.route.friendId)await syncConversation();
  }

  async function ensureRealtime(){
    const api=window.UKASocial;if(!api||!state.user)return;
    if(state.realtime&&state.reactionRealtime&&state.realtimeUserId===state.user.id)return;
    if(state.realtime){await api.unsubscribeChannel(state.realtime);state.realtime=null;state.realtimeReady=false;}
    if(state.reactionRealtime){await api.unsubscribeChannel(state.reactionRealtime);state.reactionRealtime=null;}
    try{
      state.realtimeUserId=state.user.id;
      state.realtime=await api.subscribeDirectMessages(handleRealtimeMessage,status=>{state.realtimeReady=status==='SUBSCRIBED';});
      state.reactionRealtime=await api.subscribeMessageReactions(handleRealtimeReaction);
    }catch(error){console.warn('UKA realtime chat failed',error);}
  }

  async function loadRouteData(){
    const api=window.UKASocial;if(!api||!state.user)return;
    state.route=parseRoute();
    if(state.route.section==='social'){
      const targetId=state.route.profileId||state.user.id;
      state.viewedProfile=targetId===state.user.id?state.profile:await api.getProfile(targetId);
      const [favorites,followStats]=state.viewedProfile?await Promise.all([api.getPublicFavorites(targetId),api.getFollowStats(targetId)]):[[],{followers:0,following:0,is_following:false}];
      state.viewedFavorites=favorites;state.followStats=followStats;
      state.messages=[];state.chatLoading=false;state.emojiPicker=false;state.reactionPicker=null;
    }else if(state.route.friendId){
      state.viewedProfile=null;state.viewedFavorites=[];state.chatLoading=true;state.emojiPicker=false;state.reactionPicker=null;renderApp();
      if(friendRow(state.route.friendId)){
        const [messages,theme]=await Promise.all([api.getConversation(state.route.friendId),api.getChatPreference(state.route.friendId)]);
        state.messages=messages;state.chatTheme=theme||'default';
        await api.markConversationSeen(state.route.friendId);
        const overview=overviewFor(state.route.friendId);if(overview)overview.unread=0;
      }else state.messages=[];
      state.chatLoading=false;
    }else{
      state.viewedProfile=null;state.viewedFavorites=[];state.messages=[];state.chatLoading=false;
    }
  }

  async function load(){
    const api=window.UKASocial;state.error='';state.route=parseRoute();
    if(!api){state.user=null;state.loading=false;state.error='Sociální funkce se nenačetly.';renderApp();return;}
    state.loading=true;renderApp();
    try{
      const nextUser=await api.currentUser();
      if(state.user?.id&&nextUser?.id!==state.user.id){
        if(state.realtime)await api.unsubscribeChannel(state.realtime);
        if(state.reactionRealtime)await api.unsubscribeChannel(state.reactionRealtime);
        state.realtime=null;state.reactionRealtime=null;state.realtimeUserId=null;
      }
      state.user=nextUser;
      if(!state.user){state.profile=null;state.friends=[];state.incoming=[];state.outgoing=[];state.overview=[];state.viewedProfile=null;state.viewedFavorites=[];return;}
      const [profile,friends,requests,overview]=await Promise.all([api.getMyProfile(),api.getFriends(),api.getFriendRequests(),api.getMessageOverview()]);
      state.profile=profile;state.friends=friends;state.incoming=requests.incoming||[];state.outgoing=requests.outgoing||[];state.overview=overview||[];
      updateGlobalBadge();await ensureRealtime();await loadRouteData();
    }catch(error){console.warn('UKA social load failed',error);state.error=error?.message||'Sociální část se nepodařilo načíst.';}
    finally{state.loading=false;renderApp();startPolling();}
  }

  async function run(action,success,{reload=true}={}){
    try{
      state.error='';const result=await action();if(success)notify(success);
      if(reload)await load();else renderApp();return result;
    }catch(error){console.warn('UKA social action failed',error);state.error=error?.message||'Akce se nepovedla.';renderApp();return null;}
  }

  function focusSection(id){
    requestAnimationFrame(()=>{const target=document.getElementById(id);target?.scrollIntoView({behavior:'smooth',block:'center'});if(id==='ukaOnlineSearch')setTimeout(()=>document.getElementById('ukaOnlineSearchInput')?.focus(),350);});
  }

  function scrollChatBottom(smooth=true){requestAnimationFrame(()=>{const box=document.getElementById('ukaChatMessages');if(box)box.scrollTo({top:box.scrollHeight,behavior:smooth?'smooth':'auto'});});}

  function insertEmoji(emoji){
    const input=document.getElementById('ukaChatInput');if(!input)return;
    const start=input.selectionStart??input.value.length,end=input.selectionEnd??start;
    input.value=input.value.slice(0,start)+emoji+input.value.slice(end);
    state.chatDraft=input.value;
    const cursor=start+emoji.length;input.focus();input.setSelectionRange(cursor,cursor);
    input.dispatchEvent(new Event('input',{bubbles:true}));
  }

  async function setReaction(messageId,emoji){
    const message=state.messages.find(row=>row.id===messageId);if(!message)return;
    const mine=(message.reactions||[]).find(row=>row.user_id===state.user?.id);
    const next=mine?.emoji===emoji?null:emoji;
    state.reactionPicker=null;
    try{await window.UKASocial.reactToMessage(messageId,next);await syncConversation();}
    catch(error){notify(error?.message||'Reakci se nepodařilo uložit.');}
  }

  async function uploadAvatar(file){
    if(!file)return;state.avatarBusy=true;state.error='';renderApp();
    const profile=await run(()=>window.UKASocial.uploadAvatar(file),'Profilová fotka uložena.',{reload:false});
    if(profile){state.profile=profile;state.viewedProfile=profile;}state.avatarBusy=false;renderApp();
  }

  function subscribeAuth(){
    if(authSubscribed||!window.ukaSupabaseClient)return;authSubscribed=true;
    window.ukaSupabaseClient.auth.onAuthStateChange(()=>setTimeout(backgroundInit,0));
  }

  async function backgroundInit(){
    const api=window.UKASocial;if(!api)return;
    try{
      const user=await api.currentUser();state.user=user;
      if(!user){state.overview=[];updateGlobalBadge();return;}
      state.overview=await api.getMessageOverview();updateGlobalBadge();await ensureRealtime();
      if(['social','messages','online'].includes((location.hash||'').slice(1).split('/')[0]))await load();
    }catch(error){console.warn('UKA social background init failed',error);}
  }

  async function mount(){subscribeAuth();await load();}

  async function openShare(eventItem){
    const api=window.UKASocial;if(!api)return notify('Sociální funkce se nenačetly.');
    try{
      const user=state.user||await api.currentUser();if(!user){document.getElementById('ukaAuthButton')?.click();return;}
      state.user=user;if(!state.friends.length)state.friends=await api.getFriends();
      state.shareEvent={...eventItem};state.shareMessage='';state.shareSent=new Set();renderPortal();
    }catch(error){notify(error?.message||'Akci se nepodařilo připravit k odeslání.');}
  }

  document.addEventListener('click',event=>{
    const openEvent=event.target.closest('[data-open-event]');if(openEvent){window.UKAEvents?.open?.(openEvent.dataset.openEvent);return;}
    if(state.reactionPicker&&!event.target.closest('.uka-reaction-picker')&&!event.target.closest('.uka-message-react-trigger')&&!event.target.closest('.uka-reaction-chip')){state.reactionPicker=null;renderChatMessagesOnly(false);}
    if(event.target.matches('.uka-social-overlay[data-social-close="true"]')){closeDialogs();return;}
    const button=event.target.closest('[data-online-action]');if(!button)return;
    const action=button.dataset.onlineAction;
    if(action==='login'){document.getElementById('ukaAuthButton')?.click();return;}
    if(action==='refresh'){load();return;}
    if(action==='own-profile'){goHash('social');return;}
    if(action==='open-profile'){const id=button.dataset.userId;goHash(id===state.user?.id?'social':`social/${id}`);return;}
    if(action==='open-chat'){goHash(`messages/${button.dataset.userId}`);return;}
    if(action==='messages-home'){goHash('messages');return;}
    if(action==='edit-profile'){state.editing=true;renderApp();setTimeout(()=>document.querySelector('#ukaOnlineProfileForm input')?.focus(),0);return;}
    if(action==='cancel-edit'){state.editing=false;renderApp();return;}
    if(action==='choose-avatar'){document.getElementById('ukaOnlineAvatarInput')?.click();return;}
    if(action==='focus-search'){focusSection('ukaOnlineSearch');return;}
    if(action==='focus-friends'){focusSection('ukaOnlineFriends');return;}
    if(action==='focus-requests'){focusSection('ukaOnlineRequests');return;}
    if(action==='focus-saved'){focusSection('ukaProfileSaved');return;}
    if(action==='close-dialog'){closeDialogs();return;}
    if(action==='chat-theme'){state.themeDialog=true;renderPortal();return;}
    if(action==='toggle-emoji'){
      const input=document.getElementById('ukaChatInput');state.chatDraft=input?.value||state.chatDraft;state.emojiPicker=!state.emojiPicker;state.reactionPicker=null;renderApp();setTimeout(()=>document.getElementById('ukaChatInput')?.focus(),0);return;
    }
    if(action==='insert-emoji'){insertEmoji(button.dataset.emoji||'');return;}
    if(action==='open-reactions'){state.reactionPicker=state.reactionPicker===button.dataset.messageId?null:button.dataset.messageId;state.emojiPicker=false;renderChatMessagesOnly(false);return;}
    if(action==='react-message'){setReaction(button.dataset.messageId,button.dataset.emoji||'❤️');return;}
    const api=window.UKASocial;if(!api)return;
    if(action==='set-chat-theme'){
      const theme=button.dataset.themeValue||'default';api.setChatPreference(state.route.friendId,theme).then(()=>{state.chatTheme=theme;state.themeDialog=false;renderPortal();renderApp();}).catch(error=>notify(error?.message||'Pozadí se nepodařilo uložit.'));return;
    }
    if(action==='follow'){run(()=>api.followUser(button.dataset.userId),'Přidáno do okruhu.');return;}
    if(action==='unfollow'){run(()=>api.unfollowUser(button.dataset.userId),'Odebráno z okruhu.');return;}
    if(action==='remove-avatar')run(()=>api.removeAvatar(),'Profilová fotka odebrána.').then(()=>{state.avatarBusy=false;});
    if(action==='add')run(()=>api.sendFriendRequest(button.dataset.userId),'Žádost o přátelství odeslána.');
    if(action==='accept')run(()=>api.acceptFriendRequest(button.dataset.requestId),'Jste přátelé.');
    if(action==='decline')run(()=>api.declineFriendRequest(button.dataset.requestId),'Žádost odmítnuta.');
    if(action==='remove'){const row=friendRow(button.dataset.userId);if(!row)return;state.removeCandidate=row;renderPortal();return;}
    if(action==='confirm-remove'){
      const userId=button.dataset.userId;run(()=>api.removeFriend(userId),'Přítel odebrán.').then(()=>{closeDialogs();if(state.route.profileId===userId)load();});return;
    }
    if(action==='share-send'){
      const recipientId=button.dataset.userId;if(!state.shareEvent||state.shareSent.has(recipientId))return;button.disabled=true;
      api.sendDirectMessage(recipientId,state.shareMessage,state.shareEvent.id).then(()=>{state.shareSent.add(recipientId);notify('Akce odeslána.');renderPortal();refreshOverview(false);}).catch(error=>{button.disabled=false;notify(error?.message||'Akci se nepodařilo poslat.');});
    }
  });

  document.addEventListener('change',event=>{
    if(event.target?.id==='ukaOnlineAvatarInput'){const file=event.target.files?.[0];event.target.value='';uploadAvatar(file);}
  });

  document.addEventListener('input',event=>{
    if(event.target?.id==='ukaShareMessage')state.shareMessage=String(event.target.value||'').slice(0,500);
    if(event.target?.id==='ukaChatInput'){state.chatDraft=event.target.value;event.target.style.height='auto';event.target.style.height=`${Math.min(event.target.scrollHeight,120)}px`;}
  });

  document.addEventListener('keydown',event=>{
    if(event.target?.id==='ukaChatInput'&&event.key==='Enter'&&!event.shiftKey){event.preventDefault();event.target.form?.requestSubmit();}
    if(event.key==='Escape'&&(state.removeCandidate||state.shareEvent||state.themeDialog))closeDialogs();
    else if(event.key==='Escape'&&(state.emojiPicker||state.reactionPicker)){state.emojiPicker=false;state.reactionPicker=null;renderApp();}
  });

  document.addEventListener('dblclick',event=>{
    const bubble=event.target.closest('[data-chat-bubble]');if(!bubble)return;
    setReaction(bubble.dataset.chatBubble,'❤️');
  });

  document.addEventListener('submit',event=>{
    if(event.target.id==='ukaOnlineProfileForm'){
      event.preventDefault();const data=new FormData(event.target);
      (async()=>{const profile=await run(()=>window.UKASocial.updateMyProfile({username:data.get('username'),display_name:data.get('display_name'),bio:data.get('bio')}),'Profil uložen.',{reload:false});if(profile){state.profile=profile;state.viewedProfile=profile;state.editing=false;renderApp();}})();return;
    }
    if(event.target.id==='ukaOnlineSearchForm'){
      event.preventDefault();const data=new FormData(event.target);state.query=String(data.get('q')||'').trim();
      if(state.query.length<2){state.search=[];renderApp();return;}
      (async()=>{try{state.search=await window.UKASocial.searchUsers(state.query);state.error='';}catch(error){state.search=[];state.error=error?.message||'Hledání selhalo.';}renderApp();})();return;
    }
    if(event.target.id==='ukaChatForm'){
      event.preventDefault();const friendId=state.route.friendId;if(state.sending||!friendId)return;
      const input=document.getElementById('ukaChatInput'),text=String(input?.value||'').trim();if(!text)return;
      state.sending=true;if(input)input.disabled=true;
      window.UKASocial.sendDirectMessage(friendId,text,null).then(message=>{
        if(message&&!state.messages.some(row=>row.id===message.id))state.messages.push({...message,reactions:[]});
        state.chatDraft='';state.emojiPicker=false;
        if(input){input.value='';input.style.height='auto';input.disabled=false;input.focus();}
        state.sending=false;renderChatMessagesOnly(true);refreshOverview(false);
      }).catch(error=>{state.sending=false;if(input)input.disabled=false;notify(error?.message||'Zprávu se nepodařilo odeslat.');});
    }
  });

  window.UKAOnline={page,mount,openShare};
  window.addEventListener('load',()=>{
    subscribeAuth();
    if(!backgroundStarted){backgroundStarted=true;backgroundInit();}
    const base=(location.hash||'').slice(1).split('/')[0];
    if(['social','messages','online'].includes(base))window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
})();
