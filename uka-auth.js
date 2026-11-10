/* UKA login v1: Supabase Auth. No secret/service_role key in browser. */
(()=>{
'use strict';
const PROJECT_URL='https://orofwgbqlqyvfndvdxrk.supabase.co';
const PUBLISHABLE_KEY='sb_publishable_gZqr_a9ExZpbObLyHN_sTw_jeszsism';
const btn=document.getElementById('ukaAuthButton');
if(!btn)return;
if(!window.supabase?.createClient){btn.textContent='Přihlášení nedostupné';btn.disabled=true;return;}
const client=window.supabase.createClient(PROJECT_URL,PUBLISHABLE_KEY,{auth:{autoRefreshToken:true,persistSession:true,detectSessionInUrl:true}});
window.ukaSupabaseClient=client;
let user=null, mode='login',busy=false,recoveryMode=false;
const labels={login:'Vítej zpátky.',signup:'Vytvoř si účet.',forgot:'Obnovit heslo',reset:'Nové heslo',account:'Můj účet'};
// Client-side feedback is only UX; Supabase must enforce the same rule server-side.
function usernameProblem(value){
 const name=String(value||'').trim();
 if(!/^[A-Za-z0-9_]{3,24}$/.test(name))return 'Uživatelské jméno musí mít 3–24 znaků: písmena bez diakritiky, čísla nebo podtržítko.';
 const normalized=name.toLowerCase().replace(/0/g,'o').replace(/1/g,'i').replace(/3/g,'e').replace(/4/g,'a').replace(/5/g,'s').replace(/7/g,'t').replace(/8/g,'b').replace(/9/g,'g').replace(/_/g,'');
 if(/nigg|n1gg|fagg|kike|spic|chink|retard|nazi|hitler/.test(normalized))return 'Toto uživatelské jméno není povolené. Zvol jiné.';
 return '';
}
function safeMessage(err){
 const msg=String(err?.message||'');const code=String(err?.code||'');
 if(/username_not_allowed|username not allowed|username is not allowed/i.test(msg+' '+code))return 'Toto uživatelské jméno není povolené. Zvol jiné.';
 if(/username_taken|username already exists|username unavailable/i.test(msg+' '+code))return 'Toto uživatelské jméno je již obsazené.';
 if(/invalid login credentials/i.test(msg))return 'Nesprávný e-mail nebo heslo.';
 if(/email not confirmed/i.test(msg))return 'Přihlášení se nezdařilo. Zkontroluj údaje a potvrzení e-mailu.';
 if(/rate limit|too many requests|over_email_send_rate_limit|over_request_rate_limit|email rate limit/i.test(msg+' '+code))return 'Supabase teď dočasně omezuje registrace nebo odesílání e-mailů. Počkej chvíli a zkus to znovu. Neznamená to, že máš špatné uživatelské jméno.';
 if(/invalid email|email address is invalid|email_address_invalid/i.test(msg+' '+code))return 'Zadej platnou e-mailovou adresu.';
 if(/password should|weak password|at least/i.test(msg))return 'Zvol silnější heslo (alespoň 12 znaků).';
 if(/failed to fetch|network/i.test(msg))return 'Nepodařilo se připojit k serveru. Zkontroluj internet a zkus to znovu.';
 return 'Registraci se nepodařilo dokončit. Zkontroluj údaje a zkus to znovu.';
}
function displayName(){return user?.user_metadata?.username||user?.email?.split('@')[0]||'Uživatel'}
function overlay(){return document.getElementById('ukaAuthOverlay')}
function close(){overlay()?.remove();document.removeEventListener('keydown',escapeHandler)}
function escapeHandler(e){if(e.key==='Escape')close()}
function message(text,ok=false){const e=document.getElementById('ukaAuthMessage');if(e){e.textContent=text;e.className='uka-auth-msg '+(ok?'ok':'error')}}
function render(){
 close();const root=document.createElement('div');root.id='ukaAuthOverlay';root.className='uka-auth-overlay';root.setAttribute('role','presentation');
 const panel=document.createElement('section');panel.className='uka-auth-panel';panel.setAttribute('role','dialog');panel.setAttribute('aria-modal','true');panel.setAttribute('aria-label',labels[mode]);
 const x=document.createElement('button');x.className='uka-auth-close';x.type='button';x.setAttribute('aria-label','Zavřít');x.textContent='×';x.addEventListener('click',close);panel.append(x);
 const title=document.createElement('h2');title.textContent=labels[mode];panel.append(title);
 const desc=document.createElement('p');desc.textContent=mode==='signup'?'Ulož si své oblíbené koncerty. Registrace je zdarma.':mode==='forgot'?'Pošleme ti odkaz pro změnu hesla.':mode==='reset'?'Nastav si bezpečné nové heslo.':mode==='account'?'Jsi přihlášený do UKA.':'Objevuj hudbu. Ulož si, co tě baví.';panel.append(desc);
 const form=document.createElement('form');form.noValidate=true;
 function field(name,label,type,auto){const lab=document.createElement('label');lab.htmlFor='uka-auth-'+name;lab.textContent=label;const input=document.createElement('input');input.id=lab.htmlFor;input.name=name;input.type=type;input.autocomplete=auto;input.required=true;if(type==='password')input.minLength=12;form.append(lab,input);return input}
 if(mode==='account'){
  const name=document.createElement('p');name.style.fontWeight='800';name.textContent='@'+displayName();form.append(name);
  const em=document.createElement('p');em.textContent=user?.email||'';form.append(em);
 }else{
  if(mode==='signup'){const username=field('username','Uživatelské jméno','text','username');username.minLength=3;username.maxLength=24;username.pattern='[A-Za-z0-9_]{3,24}';username.placeholder='např. hudebnifan23';}
  if(mode!=='reset')field('email','E-mail','email','email');
  if(mode!=='forgot')field('password',mode==='reset'?'Nové heslo (min. 12 znaků)':'Heslo (min. 12 znaků)','password',mode==='signup'||mode==='reset'?'new-password':'current-password');
  if(mode==='reset'&&user&&!recoveryMode){field('currentPassword','Současné heslo','password','current-password');}
  if(mode==='signup')field('confirmPassword','Potvrď heslo','password','new-password');
 }
 const submit=document.createElement('button');submit.type='submit';submit.className='uka-auth-submit';submit.textContent=mode==='login'?'Přihlásit se':mode==='signup'?'Vytvořit účet':mode==='forgot'?'Poslat odkaz':mode==='reset'?'Změnit heslo':'Odhlásit se';form.append(submit);
 form.addEventListener('submit',async e=>{e.preventDefault();if(busy)return;const email=form.elements.email?.value.trim(),password=form.elements.password?.value;
  if(mode==='signup'){const username=form.elements.username.value.trim();const problem=usernameProblem(username);if(problem){message(problem);return;}if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email||'')){message('Zadej platnou e-mailovou adresu.');return;}if(password!==form.elements.confirmPassword.value){message('Hesla se neshodují.');return;}}
  if(mode==='signup'||mode==='reset'){if(!password||password.length<12){message('Heslo musí mít alespoň 12 znaků.');return;}}
  busy=true;submit.disabled=true;message('');try{
  let result;
  if(mode==='login')result=await client.auth.signInWithPassword({email,password});
  else if(mode==='signup')result=await client.auth.signUp({email,password,options:{emailRedirectTo:location.origin+location.pathname,data:{username:form.elements.username.value.trim()}}});
  else if(mode==='forgot')result=await client.auth.resetPasswordForEmail(email,{redirectTo:location.origin+location.pathname});
  else if(mode==='reset'){if(user&&!recoveryMode){const old=form.elements.currentPassword?.value;if(!old){message('Zadej současné heslo.');return;}const check=await client.auth.signInWithPassword({email:user.email,password:old});if(check.error)throw new Error('invalid login credentials');}result=await client.auth.updateUser({password});}
  else result=await client.auth.signOut();
  if(result.error)throw result.error;
  if(mode==='signup')message('Pokud je registrace možná, přijde ti potvrzovací e-mail. Zkontroluj i spam.',true);
  else if(mode==='forgot')message('Pokud účet existuje, přijde ti e-mail s odkazem.',true);
  else if(mode==='reset'){recoveryMode=false;message('Heslo bylo změněno.',true);setTimeout(()=>{mode='account';render()},800)}
  else{close();await refreshUser()}
 }catch(err){message(safeMessage(err))}finally{busy=false;submit.disabled=false}});
 panel.append(form);
 const links=document.createElement('div');links.className='uka-auth-links';
 const options=mode==='login'?[['signup','Vytvořit účet'],['forgot','Zapomenuté heslo?']]:mode==='signup'||mode==='forgot'?[['login','Zpět na přihlášení']]:mode==='account'?[['reset','Změnit heslo']]:[];
 for(const [next,label] of options){const a=document.createElement('button');a.type='button';a.textContent=label;a.addEventListener('click',()=>{mode=next;render()});links.append(a)}panel.append(links);
 const msg=document.createElement('div');msg.id='ukaAuthMessage';msg.className='uka-auth-msg';msg.setAttribute('role','status');msg.setAttribute('aria-live','polite');panel.append(msg);
 root.append(panel);let pressedBackdrop=false;root.addEventListener('pointerdown',e=>{pressedBackdrop=e.target===root});root.addEventListener('pointerup',e=>{if(pressedBackdrop&&e.target===root)close();pressedBackdrop=false});root.addEventListener('pointercancel',()=>{pressedBackdrop=false});document.body.append(root);document.addEventListener('keydown',escapeHandler);panel.querySelector('input')?.focus();
}
let resolveAuthReady;
let authReadyDone=false;

window.ukaAuthReady=new Promise(resolve=>{
  resolveAuthReady=resolve;
});

function updateAuthButton(){
  btn.textContent=user?'@'+displayName():'Přihlásit se';
  btn.title=user?.email||'Přihlásit se';
  btn.style.visibility='visible';
}

function finishAuthReady(){
  if(authReadyDone)return;
  authReadyDone=true;
  resolveAuthReady(user);

  window.dispatchEvent(new CustomEvent('uka-auth-ready',{
    detail:{user}
  }));
}

async function initAuth(){
  const {data,error}=await client.auth.getSession();

  user=error?null:(data.session?.user||null);

  updateAuthButton();
  finishAuthReady();
}

btn.addEventListener('click',()=>{
  mode=user?'account':'login';
  render();
});

client.auth.onAuthStateChange((event,session)=>{
  user=session?.user||null;updateAuthButton();
  finishAuthReady();

  window.dispatchEvent(new CustomEvent('uka-auth-changed',{
    detail:{user,event}
  }));

  if(event==='PASSWORD_RECOVERY'){
    recoveryMode=true;
    mode='reset';
    render();
  }
});

initAuth();
})();
