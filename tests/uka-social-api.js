(() => {
  'use strict';

  const PROFILE_FIELDS='id,username,display_name,avatar_url,bio,is_private,created_at,updated_at';

  function db(){
    const client=window.ukaSupabaseClient;
    if(!client)throw new Error('UKA účet ještě není připravený.');
    return client;
  }

  function fail(error,fallback='Operace se nepovedla.'){
    if(!error)return;
    const message=error.message||fallback;
    const out=new Error(message);
    out.code=error.code;
    throw out;
  }

  async function currentUser(){
    const client=db();
    const {data:{session},error}=await client.auth.getSession();
    fail(error,'Nepodařilo se načíst přihlášení.');
    return session?.user||null;
  }

  async function requireUser(){
    const user=await currentUser();
    if(!user)throw new Error('Nejdřív se přihlas.');
    return user;
  }

  async function profilesByIds(ids){
    const unique=[...new Set((ids||[]).filter(Boolean))];
    if(!unique.length)return new Map();
    const {data,error}=await db().from('profiles').select(PROFILE_FIELDS).in('id',unique);
    fail(error,'Profily se nepodařilo načíst.');
    return new Map((data||[]).map(profile=>[profile.id,profile]));
  }

  async function getMyProfile(){
    const user=await requireUser();
    const {data,error}=await db().from('profiles').select(PROFILE_FIELDS).eq('id',user.id).maybeSingle();
    fail(error,'Profil se nepodařilo načíst.');
    return data||null;
  }

  async function getProfile(userId){
    if(typeof userId!=='string'||!userId)return null;
    await requireUser();
    const {data,error}=await db().from('profiles').select(PROFILE_FIELDS).eq('id',userId).maybeSingle();
    fail(error,'Profil se nepodařilo načíst.');
    return data||null;
  }

  async function updateMyProfile(changes={}){
    const user=await requireUser();
    const payload={id:user.id};
    if(Object.hasOwn(changes,'username')){
      const username=String(changes.username||'').trim().replace(/^@/,'');
      if(!/^[A-Za-z0-9._-]{3,30}$/.test(username))throw new Error('Uživatelské jméno musí mít 3–30 znaků a může obsahovat písmena, čísla, tečku, pomlčku a podtržítko.');
      payload.username=username;
    }
    if(Object.hasOwn(changes,'display_name'))payload.display_name=String(changes.display_name||'').trim().slice(0,80)||null;
    if(Object.hasOwn(changes,'bio'))payload.bio=String(changes.bio||'').trim().slice(0,300)||null;
    if(Object.hasOwn(changes,'avatar_url'))payload.avatar_url=changes.avatar_url?String(changes.avatar_url).trim():null;
    if(Object.hasOwn(changes,'is_private'))payload.is_private=!!changes.is_private;
    payload.updated_at=new Date().toISOString();
    const {data,error}=await db().from('profiles').upsert(payload,{onConflict:'id'}).select(PROFILE_FIELDS).single();
    fail(error,'Profil se nepodařilo uložit.');
    return data;
  }

  function avatarObjectPath(url,userId){
    if(!url||!userId)return null;
    try{
      const parsed=new URL(url);
      const marker='/storage/v1/object/public/avatars/';
      const pos=parsed.pathname.indexOf(marker);
      if(pos<0)return null;
      const path=decodeURIComponent(parsed.pathname.slice(pos+marker.length));
      return path.startsWith(`${userId}/`)?path:null;
    }catch{return null;}
  }

  async function uploadAvatar(file){
    const user=await requireUser();
    if(!(file instanceof Blob))throw new Error('Vyber obrázek.');
    const allowed={'image/jpeg':'jpg','image/png':'png','image/webp':'webp'};
    const ext=allowed[file.type];
    if(!ext)throw new Error('Použij JPG, PNG nebo WebP.');
    if(file.size>5*1024*1024)throw new Error('Profilová fotka může mít maximálně 5 MB.');
    const current=await getMyProfile();
    const oldPath=avatarObjectPath(current?.avatar_url,user.id);
    const path=`${user.id}/avatar-${Date.now()}.${ext}`;
    const {error:uploadError}=await db().storage.from('avatars').upload(path,file,{cacheControl:'3600',upsert:false,contentType:file.type});
    fail(uploadError,'Fotku se nepodařilo nahrát.');
    const {data:publicData}=db().storage.from('avatars').getPublicUrl(path);
    const publicUrl=publicData?.publicUrl;
    if(!publicUrl){
      await db().storage.from('avatars').remove([path]);
      throw new Error('Nepodařilo se vytvořit adresu profilové fotky.');
    }
    try{
      const profile=await updateMyProfile({avatar_url:publicUrl});
      if(oldPath&&oldPath!==path)await db().storage.from('avatars').remove([oldPath]);
      return profile;
    }catch(error){
      await db().storage.from('avatars').remove([path]);
      throw error;
    }
  }

  async function removeAvatar(){
    const user=await requireUser();
    const current=await getMyProfile();
    const oldPath=avatarObjectPath(current?.avatar_url,user.id);
    const profile=await updateMyProfile({avatar_url:null});
    if(oldPath)await db().storage.from('avatars').remove([oldPath]);
    return profile;
  }

  async function searchUsers(query,limit=20){
    const user=await requireUser();
    const q=String(query||'').trim().replace(/^@/,'');
    if(q.length<2)return [];
    const safe=q.replace(/[^A-Za-z0-9._-]/g,'').slice(0,30);
    if(safe.length<2)return [];
    const {data,error}=await db().from('profiles').select(PROFILE_FIELDS).ilike('username',`%${safe}%`).neq('id',user.id).limit(Math.max(1,Math.min(Number(limit)||20,30)));
    fail(error,'Hledání uživatelů selhalo.');
    return data||[];
  }

  async function sendFriendRequest(receiverId){
    await requireUser();
    if(typeof receiverId!=='string'||!receiverId)throw new Error('Neplatný uživatel.');
    const {data,error}=await db().rpc('uka_send_friend_request',{p_receiver:receiverId});
    fail(error,'Žádost se nepodařilo poslat.');
    return data;
  }

  async function acceptFriendRequest(requestId){
    await requireUser();
    const {data,error}=await db().rpc('uka_accept_friend_request',{p_request_id:requestId});
    fail(error,'Žádost se nepodařilo přijmout.');
    return data;
  }

  async function declineFriendRequest(requestId){
    await requireUser();
    const {data,error}=await db().rpc('uka_decline_friend_request',{p_request_id:requestId});
    fail(error,'Žádost se nepodařilo odmítnout.');
    return data;
  }

  async function getFriendRequests(){
    const user=await requireUser();
    const client=db();
    const [incomingResult,outgoingResult]=await Promise.all([
      client.from('friend_requests').select('id,sender_id,receiver_id,created_at').eq('receiver_id',user.id).order('created_at',{ascending:false}),
      client.from('friend_requests').select('id,sender_id,receiver_id,created_at').eq('sender_id',user.id).order('created_at',{ascending:false})
    ]);
    fail(incomingResult.error,'Žádosti se nepodařilo načíst.');
    fail(outgoingResult.error,'Žádosti se nepodařilo načíst.');
    const incoming=incomingResult.data||[],outgoing=outgoingResult.data||[];
    const profiles=await profilesByIds([...incoming.map(x=>x.sender_id),...outgoing.map(x=>x.receiver_id)]);
    return {
      incoming:incoming.map(row=>({...row,profile:profiles.get(row.sender_id)||null})),
      outgoing:outgoing.map(row=>({...row,profile:profiles.get(row.receiver_id)||null}))
    };
  }

  async function getFriends(){
    const user=await requireUser();
    const {data,error}=await db().from('friendships').select('user_a,user_b,created_at').or(`user_a.eq.${user.id},user_b.eq.${user.id}`).order('created_at',{ascending:false});
    fail(error,'Přátelé se nepodařili načíst.');
    const rows=data||[];
    const friendIds=rows.map(row=>row.user_a===user.id?row.user_b:row.user_a);
    const profiles=await profilesByIds(friendIds);
    return rows.map((row,index)=>({
      ...row,
      friend_id:friendIds[index],
      profile:profiles.get(friendIds[index])||null
    }));
  }

  async function removeFriend(friendId){
    const user=await requireUser();
    if(typeof friendId!=='string'||!friendId)throw new Error('Neplatný uživatel.');
    const {error}=await db().from('friendships').delete().or(`and(user_a.eq.${user.id},user_b.eq.${friendId}),and(user_a.eq.${friendId},user_b.eq.${user.id})`);
    fail(error,'Přítele se nepodařilo odebrat.');
    return true;
  }


  async function getPublicFavorites(userId){
    await requireUser();
    if(typeof userId!=='string'||!userId)throw new Error('Neplatný profil.');
    const {data,error}=await db().rpc('uka_get_profile_saved_events',{p_user:userId});
    fail(error,'Uložené akce se nepodařilo načíst.');
    return data||[];
  }

  async function likeEvent(eventId){
    const user=await requireUser();
    const id=String(eventId||'').trim();
    if(!id||id.length>200)throw new Error('Neplatná akce.');
    const {error}=await db().from('event_likes').insert({user_id:user.id,event_id:id});
    if(error&&error.code!=='23505')fail(error,'Like se nepodařilo uložit.');
    return true;
  }

  async function unlikeEvent(eventId){
    const user=await requireUser();
    const {error}=await db().from('event_likes').delete().eq('user_id',user.id).eq('event_id',String(eventId||''));
    fail(error,'Like se nepodařilo odebrat.');
    return true;
  }

  async function getEventLikes(eventId){
    await requireUser();
    const {data,error}=await db().from('event_likes').select('user_id,created_at').eq('event_id',String(eventId||''));
    fail(error,'Liky se nepodařilo načíst.');
    return data||[];
  }

  async function getComments(eventId){
    await requireUser();
    const {data,error}=await db().from('event_comments').select('id,event_id,user_id,body,created_at,updated_at').eq('event_id',String(eventId||'')).order('created_at',{ascending:true});
    fail(error,'Komentáře se nepodařilo načíst.');
    const rows=data||[];
    const profiles=await profilesByIds(rows.map(row=>row.user_id));
    return rows.map(row=>({...row,profile:profiles.get(row.user_id)||null}));
  }

  async function addComment(eventId,body){
    const user=await requireUser();
    const text=String(body||'').trim();
    if(!text||text.length>1000)throw new Error('Komentář musí mít 1–1000 znaků.');
    const {data,error}=await db().from('event_comments').insert({event_id:String(eventId||''),user_id:user.id,body:text}).select('id,event_id,user_id,body,created_at,updated_at').single();
    fail(error,'Komentář se nepodařilo přidat.');
    return data;
  }

  async function editComment(commentId,body){
    const user=await requireUser();
    const text=String(body||'').trim();
    if(!text||text.length>1000)throw new Error('Komentář musí mít 1–1000 znaků.');
    const {data,error}=await db().from('event_comments').update({body:text,updated_at:new Date().toISOString()}).eq('id',commentId).eq('user_id',user.id).select('id,event_id,user_id,body,created_at,updated_at').single();
    fail(error,'Komentář se nepodařilo upravit.');
    return data;
  }

  async function deleteComment(commentId){
    const user=await requireUser();
    const {error}=await db().from('event_comments').delete().eq('id',commentId).eq('user_id',user.id);
    fail(error,'Komentář se nepodařilo smazat.');
    return true;
  }

  async function shareEvent(recipientId,eventId,message=''){
    const user=await requireUser();
    const text=String(message||'').trim();
    if(text.length>500)throw new Error('Zpráva může mít maximálně 500 znaků.');
    const {data,error}=await db().from('event_shares').insert({sender_id:user.id,recipient_id:recipientId,event_id:String(eventId||''),message:text||null}).select('id,sender_id,recipient_id,event_id,message,created_at,seen_at').single();
    fail(error,'Akci se nepodařilo poslat.');
    return data;
  }

  async function getInbox(){
    const user=await requireUser();
    const {data,error}=await db().from('event_shares').select('id,sender_id,recipient_id,event_id,message,created_at,seen_at').eq('recipient_id',user.id).order('created_at',{ascending:false});
    fail(error,'Doručené akce se nepodařilo načíst.');
    const rows=data||[];
    const profiles=await profilesByIds(rows.map(row=>row.sender_id));
    return rows.map(row=>({...row,sender:profiles.get(row.sender_id)||null}));
  }

  async function getUnreadCount(){
    const user=await requireUser();
    const {count,error}=await db().from('event_shares').select('id',{count:'exact',head:true}).eq('recipient_id',user.id).is('seen_at',null);
    fail(error,'Počet zpráv se nepodařilo načíst.');
    return count||0;
  }

  async function markShareSeen(shareId){
    await requireUser();
    const {data,error}=await db().rpc('uka_mark_share_seen',{p_share_id:shareId});
    fail(error,'Zprávu se nepodařilo označit jako přečtenou.');
    return data;
  }


  async function getFollowStats(userId){
    const user=await requireUser();
    if(typeof userId!=='string'||!userId)throw new Error('Neplatný profil.');
    const client=db();
    const [followersResult,followingResult,mineResult]=await Promise.all([
      client.from('profile_follows').select('follower_id',{count:'exact',head:true}).eq('followed_id',userId),
      client.from('profile_follows').select('followed_id',{count:'exact',head:true}).eq('follower_id',userId),
      user.id===userId?Promise.resolve({data:null,error:null}):client.from('profile_follows').select('followed_id').eq('follower_id',user.id).eq('followed_id',userId).maybeSingle()
    ]);
    // Starší deployment bez migrace V6 nesmí shodit celý profil.
    const missing=[followersResult.error,followingResult.error,mineResult.error].find(error=>error&&error.code==='42P01');
    if(missing)return {followers:0,following:0,is_following:false};
    fail(followersResult.error,'Počet sledujících se nepodařilo načíst.');
    fail(followingResult.error,'Počet sledovaných se nepodařilo načíst.');
    fail(mineResult.error,'Stav sledování se nepodařilo načíst.');
    return {followers:followersResult.count||0,following:followingResult.count||0,is_following:!!mineResult.data};
  }

  async function followUser(userId){
    const user=await requireUser();
    if(typeof userId!=='string'||!userId||userId===user.id)throw new Error('Neplatný profil.');
    const {error}=await db().from('profile_follows').insert({follower_id:user.id,followed_id:userId});
    if(error&&error.code!=='23505')fail(error,'Profil se nepodařilo sledovat.');
    return true;
  }

  async function unfollowUser(userId){
    const user=await requireUser();
    if(typeof userId!=='string'||!userId)throw new Error('Neplatný profil.');
    const {error}=await db().from('profile_follows').delete().eq('follower_id',user.id).eq('followed_id',userId);
    fail(error,'Sledování se nepodařilo zrušit.');
    return true;
  }

  const CHAT_THEMES=new Set(['default','clean','graphite','midnight','ocean','sky','aurora','forest','sunset','rose','violet','sand']);

  async function getChatPreference(friendId){
    const user=await requireUser();
    if(typeof friendId!=='string'||!friendId)return 'default';
    const {data,error}=await db().from('chat_preferences').select('theme').eq('user_id',user.id).eq('friend_id',friendId).maybeSingle();
    if(error?.code==='42P01')return 'default';
    fail(error,'Vzhled chatu se nepodařilo načíst.');
    return CHAT_THEMES.has(data?.theme)?data.theme:'default';
  }

  async function setChatPreference(friendId,theme){
    const user=await requireUser();
    const selected=String(theme||'default');
    if(typeof friendId!=='string'||!friendId||friendId===user.id)throw new Error('Neplatná konverzace.');
    if(!CHAT_THEMES.has(selected))throw new Error('Neplatné pozadí chatu.');
    const {error}=await db().from('chat_preferences').upsert({user_id:user.id,friend_id:friendId,theme:selected,updated_at:new Date().toISOString()},{onConflict:'user_id,friend_id'});
    fail(error,'Pozadí chatu se nepodařilo uložit.');
    return selected;
  }

  async function getMessageReactions(messageIds){
    await requireUser();
    const ids=[...new Set((messageIds||[]).filter(Boolean))];
    if(!ids.length)return new Map();
    const {data,error}=await db().from('direct_message_reactions').select('message_id,user_id,emoji,created_at').in('message_id',ids);
    if(error?.code==='42P01')return new Map();
    fail(error,'Reakce se nepodařilo načíst.');
    const grouped=new Map();
    for(const row of data||[]){
      if(!grouped.has(row.message_id))grouped.set(row.message_id,[]);
      grouped.get(row.message_id).push(row);
    }
    return grouped;
  }

  async function reactToMessage(messageId,emoji=null){
    await requireUser();
    if(typeof messageId!=='string'||!messageId)throw new Error('Neplatná zpráva.');
    const value=emoji==null?null:String(emoji);
    const {data,error}=await db().rpc('uka_react_to_message',{p_message:messageId,p_emoji:value});
    fail(error,'Reakci se nepodařilo uložit.');
    return data;
  }


  async function sendDirectMessage(recipientId,body='',eventId=null){
    await requireUser();
    if(typeof recipientId!=='string'||!recipientId)throw new Error('Neplatný příjemce.');
    const text=String(body||'').trim();
    const event=eventId==null?null:String(eventId||'').trim();
    if(text.length>2000)throw new Error('Zpráva může mít maximálně 2000 znaků.');
    if(event&&event.length>200)throw new Error('Neplatná akce.');
    if(!text&&!event)throw new Error('Napiš zprávu.');
    const {data,error}=await db().rpc('uka_send_direct_message',{
      p_recipient:recipientId,
      p_body:text||null,
      p_event_id:event||null
    });
    fail(error,'Zprávu se nepodařilo odeslat.');
    return data||null;
  }

  async function getConversation(friendId,limit=120){
    const user=await requireUser();
    if(typeof friendId!=='string'||!friendId)throw new Error('Neplatný uživatel.');
    const size=Math.max(1,Math.min(Number(limit)||120,250));
    const {data,error}=await db().from('direct_messages')
      .select('id,sender_id,recipient_id,body,event_id,created_at,seen_at')
      .or(`and(sender_id.eq.${user.id},recipient_id.eq.${friendId}),and(sender_id.eq.${friendId},recipient_id.eq.${user.id})`)
      .order('created_at',{ascending:false})
      .limit(size);
    fail(error,'Zprávy se nepodařilo načíst.');
    const messages=(data||[]).reverse();
    const reactions=await getMessageReactions(messages.map(row=>row.id));
    return messages.map(row=>({...row,reactions:reactions.get(row.id)||[]}));
  }

  async function getMessageOverview(limit=500){
    const user=await requireUser();
    const size=Math.max(1,Math.min(Number(limit)||500,1000));
    const {data,error}=await db().from('direct_messages')
      .select('id,sender_id,recipient_id,body,event_id,created_at,seen_at')
      .or(`sender_id.eq.${user.id},recipient_id.eq.${user.id}`)
      .order('created_at',{ascending:false})
      .limit(size);
    fail(error,'Konverzace se nepodařilo načíst.');
    const byFriend=new Map();
    for(const row of data||[]){
      const friendId=row.sender_id===user.id?row.recipient_id:row.sender_id;
      let item=byFriend.get(friendId);
      if(!item){
        item={friend_id:friendId,last_message:row,unread:0};
        byFriend.set(friendId,item);
      }
      if(row.recipient_id===user.id&&row.seen_at==null)item.unread+=1;
    }
    return [...byFriend.values()];
  }

  async function markConversationSeen(friendId){
    await requireUser();
    if(typeof friendId!=='string'||!friendId)return 0;
    const {data,error}=await db().rpc('uka_mark_conversation_seen',{p_friend:friendId});
    fail(error,'Zprávy se nepodařilo označit jako přečtené.');
    return Number(data)||0;
  }

  async function subscribeDirectMessages(handler,statusHandler){
    const user=await requireUser();
    if(typeof handler!=='function')throw new Error('Chybí obsluha zpráv.');
    const client=db();
    const deliver=payload=>{const row=payload?.new;if(row)handler(row);};
    const channel=client.channel(`uka-direct-${user.id}-${Date.now()}`)
      .on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages',filter:`recipient_id=eq.${user.id}`},deliver)
      .on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages',filter:`sender_id=eq.${user.id}`},deliver)
      .subscribe(status=>{if(typeof statusHandler==='function')statusHandler(status);});
    return channel;
  }

  async function subscribeMessageReactions(handler,statusHandler){
    await requireUser();
    if(typeof handler!=='function')throw new Error('Chybí obsluha reakcí.');
    const client=db();
    const channel=client.channel(`uka-reactions-${Date.now()}`)
      .on('postgres_changes',{event:'*',schema:'public',table:'direct_message_reactions'},payload=>handler(payload))
      .subscribe(status=>{if(typeof statusHandler==='function')statusHandler(status);});
    return channel;
  }

  async function unsubscribeChannel(channel){
    if(!channel)return;
    try{await db().removeChannel(channel);}catch{}
  }

  window.UKASocial={
    currentUser,getMyProfile,getProfile,updateMyProfile,uploadAvatar,removeAvatar,searchUsers,
    sendFriendRequest,acceptFriendRequest,declineFriendRequest,getFriendRequests,getFriends,removeFriend,getPublicFavorites,
    getFollowStats,followUser,unfollowUser,
    likeEvent,unlikeEvent,getEventLikes,getComments,addComment,editComment,deleteComment,
    shareEvent,getInbox,getUnreadCount,markShareSeen,
    getChatPreference,setChatPreference,reactToMessage,
    sendDirectMessage,getConversation,getMessageOverview,markConversationSeen,subscribeDirectMessages,subscribeMessageReactions,unsubscribeChannel
  };
})();
