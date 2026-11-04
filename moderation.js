(()=>{'use strict';
// Uses the same public project settings as uka-auth.js. Never use service_role here.
const url=supabase.createClient('https://orofwgbqlqyvfndvdxrk.supabase.co','sb_publishable_gZqr_a9ExZpbObLyHN_sTw_jeszsism');
const client=supabase.createClient(url,key),status=document.getElementById('status'),items=document.getElementById('items'),login=document.getElementById('login'),logout=document.getElementById('logout');
const say=t=>{status.textContent=t};
async function refresh(){const {data:{user}}=await client.auth.getUser();login.hidden=!!user;logout.hidden=!user;items.replaceChildren();if(!user){say('Nejdřív se přihlas.');return;}
const {data:moderator,error:checkError}=await client.from('uka_moderators').select('user_id').eq('user_id',user.id).maybeSingle();if(checkError||!moderator){say('Tento účet nemá oprávnění administrátora.');return;}
const {data,error}=await client.from('event_submissions').select('id,title,artist,venue,city,event_date,event_time,ticket_url,description,created_at').eq('status','pending').order('created_at',{ascending:true}).limit(100);
if(error){say('Nepodařilo se načíst návrhy.');return;}say(`Čekající návrhy: ${data.length}`);
for(const event of data){const card=document.createElement('article');const h=document.createElement('h2');h.textContent=event.title;card.append(h);for(const v of [event.artist,`${event.venue}, ${event.city}`,`${event.event_date} ${event.event_time||''}`,event.description]){const p=document.createElement('p');p.textContent=v||'';card.append(p)}if(event.ticket_url){const a=document.createElement('a');a.href=event.ticket_url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Odkaz na vstupenky';card.append(a)}
for(const [approved,label] of [[true,'Schválit'],[false,'Zamítnout']]){const b=document.createElement('button');b.textContent=label;b.addEventListener('click',async()=>{if(!confirm(`${label}: ${event.title}?`))return;b.disabled=true;const {error}=await client.rpc('uka_review_submission',{p_id:event.id,p_approve:approved});if(error){say('Akci nelze vyřídit.');b.disabled=false;return;}await refresh()});card.append(b)}items.append(card)} }
login.addEventListener('submit',async e=>{e.preventDefault();const {error}=await client.auth.signInWithPassword({email:document.getElementById('email').value,password:document.getElementById('password').value});if(error){say('Přihlášení se nezdařilo.');return;}document.getElementById('password').value='';refresh()});logout.addEventListener('click',async()=>{await client.auth.signOut();refresh()});refresh();
})();
