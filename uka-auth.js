/* UKA login v1: Supabase Auth. No secret/service_role key in browser. */
(()=>{
'use strict';
const PROJECT_URL='https://epssmmsrnewjshfkfqqu.supabase.co';
const PUBLISHABLE_KEY='sb_publishable_0kIE7B6XO3RDBxPzXh5qlQ_5jDeLfuc';
const btn=document.getElementById('ukaAuthButton');
if(!btn)return;
if(!window.supabase?.createClient){btn.textContent='Přihlášení nedostupné';btn.disabled=true;return;}
const client=window.supabase.createClient(PROJECT_URL,PUBLISHABLE_KEY,{auth:{autoRefreshToken:true,persistSession:true,detectSessionInUrl:true}});
let user=null, mode='login',busy=false,recoveryMode=false;
const labels={login:'Vítej zpátky.',signup:'Vytvoř si účet.',forgot:'Obnovit heslo',reset:'Nové heslo',account:'Můj účet'};
function safeMessage(err,context=''){
 const raw=String(err?.message||'');
 const msg=raw.toLowerCase();
 const code=String(err?.code||'').toLowerCase();
 const status=Number(err?.status||0);
 // Display a helpful, non-sensitive explanation; never echo server internals to users.
 if(/username|user_name|user name|uživatelsk|uzivatelsk|nickname|display.name/.test(msg)||/username/.test(code)){
  if(/already|taken|exists|duplicate|unique|occupied|unavailable|použív|obsazen/.test(msg+code))return 'Toto uživatelské jméno už někdo používá. Zvol jiné.';
  if(/invalid|format|character|pattern|length|short|long|regex|check|not allowed|reserved|forbidden|prohibited|blocked|nepovolen|zakáz/.test(msg+code))return 'Toto uživatelské jméno není povolené. Zvol jiné.';
  return 'Uživatelské jméno se nepodařilo přijmout. Zkus jiné.';
 }
 if(/invalid login credentials|invalid_credentials/.test(msg+code))return 'Nesprávný e-mail nebo heslo.';
 if(/email not confirmed|email_not_confirmed/.test(msg+code))return 'Nejdřív potvrď svůj e-mail pomocí odkazu, který jsme ti poslali.';
 if(/user already registered|email.*already|already.*email|user_already_exists/.test(msg+code))return 'Účet s tímto e-mailem už existuje. Zkus se přihlásit.';
 if(/invalid email|email_address_invalid|email.*invalid/.test(msg+code))return 'Zadej platnou e-mailovou adresu.';
 if(/rate limit|too many requests|over_email_send_rate_limit|over_request_rate_limit/.test(msg+code)||status===429)return 'Příliš mnoho pokusů. Zkus to později.';
 if(/password should|weak password|at least|password.*short|weak_password/.test(msg+code))return 'Zvol silnější heslo (alespoň 12 znaků).';
 if(/failed to fetch|network|fetch failed|networkerror|load failed|timeout/.test(msg+code))return 'Nepodařilo se připojit k serveru. Zkontroluj internet a zkus to znovu.';
 if(status>=500)return 'Server má momentálně potíže. Zkus to za chvíli.';
 if(context==='signup'&&status===422)return 'Registraci se nepodařilo dokončit. Zkontroluj údaje a zkus jiné uživatelské jméno.';
 return 'Operace se nepodařila. Zkus to znovu. Pokud problém trvá, kontaktuj podporu UKA.';
}
function usernameProblem(value){
 if(value.length<3||value.length>24)return 'Uživatelské jméno musí mít 3–24 znaků.';
 if(!/^[A-Za-z0-9_]+$/.test(value))return 'Uživatelské jméno může obsahovat jen písmena bez diakritiky, číslice a podtržítko.';
 return '';
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
  if(mode==='signup'){
   const username=field('username','Uživatelské jméno','text','username');username.minLength=3;username.maxLength=24;username.pattern='[A-Za-z0-9_]{3,24}';username.placeholder='např. H0tB0x3d';
   username.addEventListener('input',()=>{const problem=usernameProblem(username.value.trim());username.setCustomValidity(problem);username.setAttribute('aria-invalid',problem?'true':'false');const hint=document.getElementById('ukaUsernameHint');if(hint)hint.textContent=problem||'Jméno má povolený formát.';});
   const hint=document.createElement('small');hint.id='ukaUsernameHint';hint.textContent='3–24 znaků: písmena bez diakritiky, číslice a podtržítko.';form.append(hint);
  }
  if(mode!=='reset')field('email','E-mail','email','email');
  if(mode!=='forgot')field('password',mode==='reset'?'Nové heslo (min. 12 znaků)':'Heslo (min. 12 znaků)','password',mode==='signup'||mode==='reset'?'new-password':'current-password');
  if(mode==='reset'&&user&&!recoveryMode){field('currentPassword','Současné heslo','password','current-password');}
  if(mode==='signup')field('confirmPassword','Potvrď heslo','password','new-password');
 }
 const submit=document.createElement('button');submit.type='submit';submit.className='uka-auth-submit';submit.textContent=mode==='login'?'Přihlásit se':mode==='signup'?'Vytvořit účet':mode==='forgot'?'Poslat odkaz':mode==='reset'?'Změnit heslo':'Odhlásit se';form.append(submit);
 form.addEventListener('submit',async e=>{e.preventDefault();if(busy)return;const email=form.elements.email?.value.trim(),password=form.elements.password?.value;
  if(mode==='signup'){const username=form.elements.username.value.trim();const problem=usernameProblem(username);if(problem){message(problem);form.elements.username.focus();return;}if(password!==form.elements.confirmPassword.value){message('Hesla se neshodují.');return;}}
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
 }catch(err){console.error('UKA auth request failed:',{code:err?.code,status:err?.status,message:err?.message});message(safeMessage(err,mode))}finally{busy=false;submit.disabled=false}});
 panel.append(form);
 const links=document.createElement('div');links.className='uka-auth-links';
 const options=mode==='login'?[['signup','Vytvořit účet'],['forgot','Zapomenuté heslo?']]:mode==='signup'||mode==='forgot'?[['login','Zpět na přihlášení']]:mode==='account'?[['reset','Změnit heslo']]:[];
 for(const [next,label] of options){const a=document.createElement('button');a.type='button';a.textContent=label;a.addEventListener('click',()=>{mode=next;render()});links.append(a)}panel.append(links);
 const msg=document.createElement('div');msg.id='ukaAuthMessage';msg.className='uka-auth-msg';msg.setAttribute('role','status');msg.setAttribute('aria-live','polite');panel.append(msg);
 root.append(panel);
 // Close only when the pointer press AND release both happen on the backdrop.
 // Dragging from an input/panel to the backdrop must keep the dialog open.
 let backdropPress=false;
 root.addEventListener('pointerdown',e=>{backdropPress=e.target===root});
 root.addEventListener('pointercancel',()=>{backdropPress=false});
 root.addEventListener('click',e=>{
  const shouldClose=backdropPress&&e.target===root;
  backdropPress=false;
  if(shouldClose)close();
 });
 document.body.append(root);document.addEventListener('keydown',escapeHandler);panel.querySelector('input')?.focus();
}
function updateAuthButton(){btn.textContent=user?'@'+displayName():'Přihlásit se';btn.title=user?.email||'Přihlásit se'}
async function refreshUser(){const {data,error}=await client.auth.getUser();user=error?null:data.user;updateAuthButton();}
btn.addEventListener('click',()=>{mode=user?'account':'login';render()});
client.auth.onAuthStateChange((event,session)=>{user=session?.user||null;updateAuthButton();if(event==='PASSWORD_RECOVERY'){recoveryMode=true;mode='reset';render()}});
refreshUser();
})();
