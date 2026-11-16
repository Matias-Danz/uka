(()=>{
'use strict';

const PROFILE_FIELDS='id,username,display_name,avatar_url,bio,is_private,created_at,updated_at';

function fail(message,code='UKA_SOCIAL_ERROR'){
  const error=new Error(message);
  error.code=code;
  throw error;
}

async function client(){
  const started=Date.now();

  while(!window.ukaSupabaseClient){
    if(Date.now()-started>5000){
      fail('Supabase není dostupný.','SUPABASE_UNAVAILABLE');
    }
    await new Promise(resolve=>setTimeout(resolve,25));
  }

  return window.ukaSupabaseClient;
}

async function currentUser(required=true){
  const db=await client();
  const {data,error}=await db.auth.getSession();

  if(error)throw error;

  const user=data.session?.user||null;

  if(required&&!user){
    fail('Pro tuto akci musí být uživatel přihlášený.','AUTH_REQUIRED');
  }

  return user;
}

function cleanUsername(value){
  const username=String(value||'')
    .trim()
    .replace(/^@/,'')
    .toLowerCase();

  if(!/^[a-z0-9._]{3,30}$/.test(username)){
    fail(
      'Username musí mít 3–30 znaků a může obsahovat pouze písmena, čísla, tečku a podtržítko.',
      'INVALID_USERNAME'
    );
  }

  return username;
}

function cleanEventId(value){
  const id=String(value||'').trim();

  if(!id||id.length>200){
    fail('Neplatné ID akce.','INVALID_EVENT_ID');
  }

  return id;
}

async function profilesByIds(ids){
  const unique=[...new Set(ids.filter(Boolean))];

  if(!unique.length)return {};

  const db=await client();

  const {data,error}=await db
    .from('profiles')
    .select(PROFILE_FIELDS)
    .in('id',unique);

  if(error)throw error;

  return Object.fromEntries(
    (data||[]).map(profile=>[profile.id,profile])
  );
}


/* =========================================================
   PROFILY
   ========================================================= */

async function getMyProfile(){
  const db=await client();
  const user=await currentUser();

  const {data,error}=await db
    .from('profiles')
    .select(PROFILE_FIELDS)
    .eq('id',user.id)
    .maybeSingle();

  if(error)throw error;

  return data||null;
}

async function getProfile(userId){
  const db=await client();

  const {data,error}=await db
    .from('profiles')
    .select(PROFILE_FIELDS)
    .eq('id',userId)
    .maybeSingle();

  if(error)throw error;

  return data||null;
}

async function updateMyProfile(changes={}){
  const db=await client();
  const user=await currentUser();

  const update={
    updated_at:new Date().toISOString()
  };

  if(Object.hasOwn(changes,'username')){
    update.username=cleanUsername(changes.username);
  }

  if(Object.hasOwn(changes,'display_name')){
    const value=String(changes.display_name||'').trim();

    if(value.length>60){
      fail('Jméno může mít maximálně 60 znaků.','INVALID_DISPLAY_NAME');
    }

    update.display_name=value||null;
  }

  if(Object.hasOwn(changes,'bio')){
    const value=String(changes.bio||'').trim();

    if(value.length>300){
      fail('Bio může mít maximálně 300 znaků.','INVALID_BIO');
    }

    update.bio=value||null;
  }

  if(Object.hasOwn(changes,'avatar_url')){
    const value=String(changes.avatar_url||'').trim();

    if(value&&!/^https:\/\//i.test(value)){
      fail('Avatar musí používat HTTPS.','INVALID_AVATAR_URL');
    }

    update.avatar_url=value||null;
  }

  if(Object.hasOwn(changes,'is_private')){
    update.is_private=!!changes.is_private;
  }

  const {data,error}=await db
    .from('profiles')
    .update(update)
    .eq('id',user.id)
    .select(PROFILE_FIELDS)
    .single();

  if(error)throw error;

  return data;
}

async function searchUsers(query,limit=20){
  const db=await client();
  const user=await currentUser();

  const q=String(query||'')
    .trim()
    .replace(/^@/,'');

  if(q.length<2)return [];

  const safeLimit=Math.max(1,Math.min(Number(limit)||20,50));

  const [byUsername,byName]=await Promise.all([
    db
      .from('profiles')
      .select(PROFILE_FIELDS)
      .ilike('username',`%${q}%`)
      .neq('id',user.id)
      .limit(safeLimit),

    db
      .from('profiles')
      .select(PROFILE_FIELDS)
      .ilike('display_name',`%${q}%`)
      .neq('id',user.id)
      .limit(safeLimit)
  ]);

  if(byUsername.error)throw byUsername.error;
  if(byName.error)throw byName.error;

  const merged=new Map();

  for(const profile of [
    ...(byUsername.data||[]),
    ...(byName.data||[])
  ]){
    merged.set(profile.id,profile);
  }

  return [...merged.values()].slice(0,safeLimit);
}


/* =========================================================
   PŘÁTELÉ
   ========================================================= */

async function sendFriendRequest(receiverId){
  const db=await client();
  await currentUser();

  const {data,error}=await db.rpc(
    'uka_send_friend_request',
    {p_receiver:receiverId}
  );

  if(error)throw error;

  return data;
}

async function acceptFriendRequest(requestId){
  const db=await client();
  await currentUser();

  const {error}=await db.rpc(
    'uka_accept_friend_request',
    {p_request_id:requestId}
  );

  if(error)throw error;

  return true;
}

async function declineFriendRequest(requestId){
  const db=await client();
  await currentUser();

  const {error}=await db.rpc(
    'uka_decline_friend_request',
    {p_request_id:requestId}
  );

  if(error)throw error;

  return true;
}

async function getFriendRequests(){
  const db=await client();
  const user=await currentUser();

  const [incoming,outgoing]=await Promise.all([
    db
      .from('friend_requests')
      .select('id,sender_id,receiver_id,created_at')
      .eq('receiver_id',user.id)
      .order('created_at',{ascending:false}),

    db
      .from('friend_requests')
      .select('id,sender_id,receiver_id,created_at')
      .eq('sender_id',user.id)
      .order('created_at',{ascending:false})
  ]);

  if(incoming.error)throw incoming.error;
  if(outgoing.error)throw outgoing.error;

  const ids=[
    ...(incoming.data||[]).map(x=>x.sender_id),
    ...(outgoing.data||[]).map(x=>x.receiver_id)
  ];

  const profiles=await profilesByIds(ids);

  return {
    incoming:(incoming.data||[]).map(row=>({
      ...row,
      profile:profiles[row.sender_id]||null
    })),

    outgoing:(outgoing.data||[]).map(row=>({
      ...row,
      profile:profiles[row.receiver_id]||null
    }))
  };
}

async function getFriends(){
  const db=await client();
  const user=await currentUser();

  const [left,right]=await Promise.all([
    db
      .from('friendships')
      .select('user_a,user_b,created_at')
      .eq('user_a',user.id),

    db
      .from('friendships')
      .select('user_a,user_b,created_at')
      .eq('user_b',user.id)
  ]);

  if(left.error)throw left.error;
  if(right.error)throw right.error;

  const rows=[
    ...(left.data||[]),
    ...(right.data||[])
  ];

  const ids=rows.map(row=>
    row.user_a===user.id
      ? row.user_b
      : row.user_a
  );

  const profiles=await profilesByIds(ids);

  return rows.map(row=>{
    const friendId=
      row.user_a===user.id
        ? row.user_b
        : row.user_a;

    return {
      user_id:friendId,
      created_at:row.created_at,
      profile:profiles[friendId]||null
    };
  });
}

async function removeFriend(otherUserId){
  const db=await client();
  const user=await currentUser();

  const first=await db
    .from('friendships')
    .delete()
    .eq('user_a',user.id)
    .eq('user_b',otherUserId);

  if(first.error)throw first.error;

  const second=await db
    .from('friendships')
    .delete()
    .eq('user_a',otherUserId)
    .eq('user_b',user.id);

  if(second.error)throw second.error;

  return true;
}


/* =========================================================
   LIKES
   ========================================================= */

async function likeEvent(eventId){
  const db=await client();
  const user=await currentUser();

  const id=cleanEventId(eventId);

  const {error}=await db
    .from('event_likes')
    .insert({
      user_id:user.id,
      event_id:id
    });

  if(error&&error.code!=='23505')throw error;

  return true;
}

async function unlikeEvent(eventId){
  const db=await client();
  const user=await currentUser();

  const {error}=await db
    .from('event_likes')
    .delete()
    .eq('user_id',user.id)
    .eq('event_id',cleanEventId(eventId));

  if(error)throw error;

  return true;
}

async function getEventLikes(eventId){
  const db=await client();
  const user=await currentUser(false);

  const id=cleanEventId(eventId);

  const countResult=await db
    .from('event_likes')
    .select('*',{
      count:'exact',
      head:true
    })
    .eq('event_id',id);

  if(countResult.error)throw countResult.error;

  let likedByMe=false;

  if(user){
    const mine=await db
      .from('event_likes')
      .select('event_id')
      .eq('event_id',id)
      .eq('user_id',user.id)
      .maybeSingle();

    if(mine.error)throw mine.error;

    likedByMe=!!mine.data;
  }

  return {
    count:countResult.count||0,
    likedByMe
  };
}


/* =========================================================
   KOMENTÁŘE
   ========================================================= */

async function getComments(eventId,limit=100){
  const db=await client();

  const {data,error}=await db
    .from('event_comments')
    .select(
      'id,event_id,user_id,body,created_at,updated_at'
    )
    .eq('event_id',cleanEventId(eventId))
    .order('created_at',{ascending:true})
    .limit(
      Math.max(1,Math.min(Number(limit)||100,200))
    );

  if(error)throw error;

  const profiles=await profilesByIds(
    (data||[]).map(row=>row.user_id)
  );

  return (data||[]).map(row=>({
    ...row,
    profile:profiles[row.user_id]||null
  }));
}

async function addComment(eventId,body){
  const db=await client();
  const user=await currentUser();

  const text=String(body||'').trim();

  if(!text||text.length>1000){
    fail(
      'Komentář musí mít 1–1000 znaků.',
      'INVALID_COMMENT'
    );
  }

  const {data,error}=await db
    .from('event_comments')
    .insert({
      event_id:cleanEventId(eventId),
      user_id:user.id,
      body:text
    })
    .select(
      'id,event_id,user_id,body,created_at,updated_at'
    )
    .single();

  if(error)throw error;

  return data;
}

async function editComment(commentId,body){
  const db=await client();
  const user=await currentUser();

  const text=String(body||'').trim();

  if(!text||text.length>1000){
    fail(
      'Komentář musí mít 1–1000 znaků.',
      'INVALID_COMMENT'
    );
  }

  const {data,error}=await db
    .from('event_comments')
    .update({
      body:text,
      updated_at:new Date().toISOString()
    })
    .eq('id',commentId)
    .eq('user_id',user.id)
    .select(
      'id,event_id,user_id,body,created_at,updated_at'
    )
    .single();

  if(error)throw error;

  return data;
}

async function deleteComment(commentId){
  const db=await client();
  const user=await currentUser();

  const {error}=await db
    .from('event_comments')
    .delete()
    .eq('id',commentId)
    .eq('user_id',user.id);

  if(error)throw error;

  return true;
}


/* =========================================================
   SDÍLENÍ AKCÍ / INBOX
   ========================================================= */

async function shareEvent(recipientId,eventId,message=''){
  const db=await client();
  const user=await currentUser();

  const text=String(message||'').trim();

  if(text.length>500){
    fail(
      'Zpráva může mít maximálně 500 znaků.',
      'INVALID_MESSAGE'
    );
  }

  const {data,error}=await db
    .from('event_shares')
    .insert({
      sender_id:user.id,
      recipient_id:recipientId,
      event_id:cleanEventId(eventId),
      message:text||null
    })
    .select(
      'id,sender_id,recipient_id,event_id,message,created_at,seen_at'
    )
    .single();

  if(error)throw error;

  return data;
}

async function getInbox(limit=100){
  const db=await client();
  const user=await currentUser();

  const {data,error}=await db
    .from('event_shares')
    .select(
      'id,sender_id,recipient_id,event_id,message,created_at,seen_at'
    )
    .eq('recipient_id',user.id)
    .order('created_at',{ascending:false})
    .limit(
      Math.max(1,Math.min(Number(limit)||100,200))
    );

  if(error)throw error;

  const profiles=await profilesByIds(
    (data||[]).map(row=>row.sender_id)
  );

  return (data||[]).map(row=>({
    ...row,
    sender:profiles[row.sender_id]||null
  }));
}

async function getUnreadCount(){
  const db=await client();
  const user=await currentUser();

  const {count,error}=await db
    .from('event_shares')
    .select('*',{
      count:'exact',
      head:true
    })
    .eq('recipient_id',user.id)
    .is('seen_at',null);

  if(error)throw error;

  return count||0;
}

async function markShareSeen(shareId){
  const db=await client();
  const user=await currentUser();

  const {error}=await db
    .from('event_shares')
    .update({
      seen_at:new Date().toISOString()
    })
    .eq('id',shareId)
    .eq('recipient_id',user.id);

  if(error)throw error;

  return true;
}


/* =========================================================
   VEŘEJNÉ API
   ========================================================= */

window.UKASocial=Object.freeze({
  currentUser,

  getMyProfile,
  getProfile,
  updateMyProfile,
  searchUsers,

  sendFriendRequest,
  acceptFriendRequest,
  declineFriendRequest,
  getFriendRequests,
  getFriends,
  removeFriend,

  likeEvent,
  unlikeEvent,
  getEventLikes,

  getComments,
  addComment,
  editComment,
  deleteComment,

  shareEvent,
  getInbox,
  getUnreadCount,
  markShareSeen
});

})();
