/* ==========================================================================
   App: sign-in, start-up and the page shell (header, navigation, footer).
   Loaded last, so every screen it opens already exists.
   ========================================================================== */

/* ---- overview presentation + feedback (added) ---- */
const DECK='/static/docs/Margin_Calculator_Overview.pptx';   /* the slide version of this tool, for people who would rather read slides than open the app */
async function feedbackDlg(){
  const d=document.createElement('dialog');d.className='dlg';
  d.innerHTML=`<form method="dialog" class="dlg-in"><h2>Send feedback</h2>
    <p class="dlg-body">Found something confusing, or have an idea to make this tool better? It goes straight to the team that maintains it.</p>
    <label class="dlg-f">What is it about?<select name="kind"><option value="idea">An improvement idea</option><option value="bug">Something is not working</option><option value="other">Other feedback</option></select></label>
    <label class="dlg-f">Your feedback<textarea name="message" rows="6" maxlength="4000" required placeholder="Tell us what you would change, and why."></textarea></label>
    <p class="lerr" id="fberr" role="alert"></p>
    <div class="dlg-act"><button type="button" class="btn" data-cancel>Cancel</button><button type="submit" class="btn primary">Send</button></div></form>`;
  document.body.appendChild(d);
  const form=d.querySelector('form'),err=d.querySelector('#fberr');
  d.querySelector('[data-cancel]').onclick=()=>d.close();
  d.addEventListener('close',()=>d.remove());
  form.addEventListener('submit',async e=>{
    e.preventDefault();const kind=form.kind.value,message=form.message.value.trim(),btn=form.querySelector('[type=submit]');
    if(message.length<5){err.textContent='Please write a few words about your feedback.';return}
    btn.disabled=true;err.textContent='';
    try{
      const r=await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,message,page:tab})});
      if(r.status==401){d.close();showLogin();return}
      const j=await r.json().catch(()=>({}));
      if(!r.ok){err.textContent=typeof j.detail=='string'?j.detail:'Could not send. Please try again.';btn.disabled=false;return}
      d.close();
      if(j.emailed)toast('Thank you. Your feedback has been sent.');
      else{   /* no mail server on this installation: it is saved on the server, and an email can be sent from the user's own mail program */
        toast('Thank you. Your feedback is saved. Click to also email it.','ok',12000,{label:'Email it',fn:()=>{location.href='mailto:'+encodeURIComponent(j.to||'')+'?subject='+encodeURIComponent('[Margin Calculator] Feedback')+'&body='+encodeURIComponent(message)}})}
    }catch(x){err.textContent='Could not send. Check your connection and try again.';btn.disabled=false}});
  d.showModal();form.message.focus()}

/* ---- sign-in ---- */
let loginBusy=false;
async function showLogin(){tourHide();if(loginBusy)return;loginBusy=true;try{await drawLogin()}finally{loginBusy=false}}
async function drawLogin(){
  const c=await fetch('/auth/config').then(r=>r.json()),dom=c.domain||'company.com',showAdm=/[?&]admin\b/.test(location.search);   /* administrator sign-in is hidden unless the address ends in ?admin */
  const body=c.mode=='dev'
    ?`<p>Local test mode. Choose a test user to continue.</p>${c.users.map(u=>`<button class="user-opt" data-email="${esc(u.email)}" onclick="devLogin(this.dataset.email)"><span>${esc(u.email)}</span><span class="chip plain ${u.role=='admin'?'admin':''}">${esc(u.role)}</span></button>`).join('')}`
    :c.mode=='email'
    ?`<p>Enter your work email to start. No password and no set-up needed.</p>
      <form onsubmit="emailLogin(event)"><label for="le">Work email</label><input id="le" type="email" autocomplete="email" required placeholder="name@${esc(dom)}" value="${esc(store.get('mc_email')||'')}">
      <button class="btn primary block" type="submit">Continue</button><p class="lerr" id="lerr" role="alert"></p></form>
      ${c.demo?.length?`<div class="or"><span>or just explore</span></div><p class="mu demo-intro">Pick a ready-made demo account. Sample projects are already set up.</p><div class="demo-grid">${c.demo.map(u=>`<button class="user-opt" type="button" data-email="${esc(u.email)}" title="${esc(u.note)}" onclick="demoLogin(this.dataset.email)"><span><b>${esc(u.label)}</b><small>${esc(u.note)}</small></span><span class="chip plain ${u.role=='admin'?'admin':''}">${esc(u.role)}</span></button>`).join('')}</div>`:''}
      ${showAdm?`<details class="adm"><summary>Administrator sign-in</summary>${c.admin_login?`<form onsubmit="adminLogin(event)"><label for="ae">Email</label><input id="ae" type="email" required><label for="ap">Password</label><input id="ap" type="password" required><button class="btn block" type="submit">Sign in as administrator</button><p class="lerr" id="aerr" role="alert"></p></form>`:'<p class="mu">Not set up on this server. Set ADMIN_EMAILS and ADMIN_PASSWORD to enable it.</p>'}</details>`:''}`
    :`<p>Use your company account to continue.</p><a class="btn primary block" href="/auth/login">Sign in with company SSO</a>`;
  const lead=c.mode=='email'?'Welcome':'Sign in';
  $('app').innerHTML=`<div class="auth">
    <aside class="auth-brand"><img class="logo" src="/static/img/nagarro-logo.png" alt="Nagarro">
      <h1>Margin<em>What-If Calculator</em></h1>
      <p>See the margin on every person, project and team, and test what happens when a rate, a cost or an allocation changes.</p>
      <ul class="auth-points">${[['calc','Instant margin for every person and team'],['compare','Save scenarios and compare before and after'],['target','Insights, sensitivity and a target solver'],['chat','Chatbot assistant (coming soon)']].map(([i,t])=>`<li><i>${I(i,15)}</i>${t}</li>`).join('')}</ul>
      <button class="deck-link" type="button" onclick="demoHubPublic()">${I('play',15)}New here? Take the guided demo</button>
      <a class="deck-link" href="${DECK}" target="_blank" rel="noopener" download>${I('download',15)}Prefer slides? Open the overview presentation (PPT)</a>
      <small>Internal tool · ©${new Date().getFullYear()} Nagarro</small></aside>
    <section class="auth-form"><div class="login"><h2>${lead}</h2>${body}</div></section></div>`;
  $(c.mode=='email'?'le':'app').focus?.()}
async function loginPost(url,b,errId){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});
  if(!r.ok){$(errId).textContent=(await r.json().catch(()=>({}))).detail||'Could not sign in.';return false}return true}
async function emailLogin(e){e.preventDefault();const email=$('le').value.trim();if(await loginPost('/auth/email-login',{email},'lerr')){store.set('mc_email',email);init()}}
async function demoLogin(e){if(await loginPost('/auth/demo-login',{email:e},'lerr'))init()}
async function adminLogin(e){e.preventDefault();if(await loginPost('/auth/admin-login',{email:$('ae').value,password:$('ap').value},'aerr'))init()}
async function devLogin(e){await send('/auth/dev-login','POST',{email:e});init()}
async function logout(){await send('/auth/logout','POST');tourHide();showLogin()}

/* ---- start-up: everything the first screen needs is requested in parallel ---- */
async function init(){
  try{
    const month=$('mo')?.value||thisMonth();
    [U,C]=await Promise.all([J('/auth/me'),J('/api/config')]);
    TM=await J('/api/teams?month='+month);
    const saved=+store.get('mc_team');curTeam=TM.find(t=>t.id==saved)?.id??TM[0]?.id;
    if(curTeam==null){  // nothing assigned to this user yet
      [G,CAL]=await Promise.all([J('/api/genus'),J('/api/calendars')]);
      T=[];S=[];P={month,team_id:null,business_days:0,holidays:[],days:{},hours_per_day:C.hours_per_day};sel=null;tab='calc';await render();tourResume();return}
    [T,G,S,P]=await Promise.all([J('/api/team?'+qs()),J('/api/genus'),J('/api/scenarios?'+qs()),J(`/api/period?month=${month}&${qs()}`)]);
    sel=T[0]?.id;tab='calc';await render();tourResume()
  }catch(e){
    if(e!==0)console.error(e);
    if(!loginBusy&&!$('app').children.length)$('app').innerHTML=`<div class="panel load-error"><b>The calculator could not load</b><p class="mu">Check your connection and try again.</p><button class="btn primary" onclick="init()">Try again</button></div>`}}
async function switchTeam(id,toTab){
  await flushAll();curTeam=id;store.set('mc_team',id);const m=P.month||thisMonth();
  [TM,T,S,P]=await Promise.all([J('/api/teams?month='+m),J('/api/team?'+qs()),J('/api/scenarios?'+qs()),J(`/api/period?month=${m}&${qs()}`)]);
  sel=T[0]?.id;flt={q:'',lvl:'',br:'',band:'',warn:false};await go(toTab||tab)}

/* ---- shell: every page is  header > (optional) context bar > panels ---- */
const NAV_MAIN=[['calc','Calculator','calc'],['insights','Insights','target'],['teams','Teams','grid'],['genus','Genus tables','genus'],['assistant','Assistant','chat'],['demo','Guided Demo','play'],['guide','Guide','book']];
const NAV_ADMIN=[['hol','Holidays','hol'],['users','Users','users'],['audit','Audit log','audit']];
const PAGES={calc:()=>drawCalcPage(),demo:()=>drawDemo(),guide:()=>drawGuide(),assistant:()=>drawAssistant(),insights:()=>drawInsights(),teams:()=>drawTeams(),genus:()=>drawGenus(),hol:()=>drawHol(),users:()=>drawUsers(),audit:()=>drawAudit()};
const head=(t,sub='',act='')=>`<header class="page-head"><div><h1>${t}</h1>${sub?`<p>${sub}</p>`:''}</div>${act?`<div class="head-actions">${act}</div>`:''}</header>`;
const ctx=h=>`<div class="ctx" role="group" aria-label="View options">${h}</div>`;   /* the controls that decide what the page shows */
const hideCost=()=>store.get('mc_hide')=='1';
function setHideCost(on){document.body.classList.toggle('hide-cost',on);store.set('mc_hide',on?'1':'');const c=$('hc');if(c)c.checked=on}
const initials=e=>{const p=String(e||'?').split('@')[0].split(/[._-]+/).filter(Boolean);return((p[0]?.[0]||'?')+(p[1]?.[0]||'')).toUpperCase()};
function render(){
  document.body.classList.toggle('hide-cost',hideCost());
  const item=([k,l,i])=>`<button class="nav-item" data-tab="${k}" title="${l}" onclick="go('${k}')">${I(i,17)}<span>${l}</span>${k=='assistant'?'<em class="soon">Soon</em>':''}</button>`,adm=U.role=='admin';
  $('app').innerHTML=`<div class="app-shell">
    <header class="topbar"><div class="topbar-in">
      <a class="brand" href="/" onclick="event.preventDefault();go('calc')" aria-label="Margin Calculator, home"><img class="logo" src="/static/img/nagarro-logo.png" alt="Nagarro"><span class="brand-name">Margin Calculator</span></a>
      <nav class="nav" aria-label="Main">${NAV_MAIN.map(item).join('')}${adm?`<span class="nav-sep" aria-hidden="true"></span>${NAV_ADMIN.map(item).join('')}`:''}</nav>
      <div class="top-right">
        <label class="switch top-switch" title="Hide cost and margin figures on screen"><input type="checkbox" id="hc" ${hideCost()?'checked':''} onchange="setHideCost(this.checked)"><i></i><span>Hide cost</span></label>
        <div class="user-menu"><button class="avatar" id="avatar" aria-haspopup="menu" aria-expanded="false" aria-label="Account menu" onclick="toggleMenu()"><b>${esc(initials(U.email))}</b>${I('chev',14)}</button></div>
      </div></div></header>
    <main class="content" id="body"></main>
    <footer class="footer"><div class="footer-in"><img class="logo" src="/static/img/nagarro-logo.png" alt="Nagarro"><span>©${new Date().getFullYear()} Nagarro</span><button onclick="go('demo')">Guided Demo</button><button onclick="go('guide')">Guide</button><a href="${DECK}" target="_blank" rel="noopener" download>Overview (PPT)</a><button onclick="feedbackDlg()">Send feedback</button><span class="note-f">Margin is shown before overheads, bench time and benefits.</span></div></footer></div>`;
  return go(tab)}
function toggleMenu(force){
  const open=$('umenu');
  if(open||force===false){open?.remove();$('avatar')?.setAttribute('aria-expanded','false');return}
  const d=document.createElement('div');d.className='menu';d.id='umenu';d.setAttribute('role','menu');
  d.innerHTML=`<div class="menu-who"><span class="em" title="${esc(U.email)}">${esc(U.email)}</span><span class="chip plain ${U.role=='admin'?'admin':''}">${esc(U.role)}</span></div><button role="menuitem" onclick="toggleMenu(false);feedbackDlg()">${I('chat',16)}Send feedback</button><a class="menu-link" role="menuitem" href="${DECK}" target="_blank" rel="noopener" download>${I('download',16)}Overview presentation (PPT)</a><button role="menuitem" onclick="logout()">${I('out',16)}Sign out</button>`;
  document.querySelector('.user-menu').appendChild(d);$('avatar').setAttribute('aria-expanded','true');d.querySelector('button').focus()}
document.addEventListener('click',e=>{if($('umenu')&&!e.target.closest('.user-menu'))toggleMenu(false)});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('umenu')){toggleMenu(false);$('avatar')?.focus()}});
async function go(t){
  tab=t;
  const label=[...NAV_MAIN,...NAV_ADMIN].find(x=>x[0]==t)?.[1]||'';document.title=(label?label+' · ':'')+'Margin Calculator';
  document.querySelectorAll('.nav-item').forEach(b=>{const on=b.dataset.tab==t;b.classList.toggle('on',on);on?b.setAttribute('aria-current','page'):b.removeAttribute('aria-current')});
  toggleMenu(false);await flushAll();
  if(curTeam==null&&['calc','teams','insights'].includes(t)){welcome();return}
  if(t!='calc'&&t!='guide')$('body').innerHTML='<div class="loading" role="status">Loading…</div>';   /* pages that fetch data show this until they are ready */
  await (PAGES[t]||PAGES.audit)();
  window.scrollTo(0,0)}

/* J() throws 0 after it has already shown the user an error message; keep that out of the console */
window.addEventListener('unhandledrejection',e=>{if(e.reason===0)e.preventDefault()});
init().catch(()=>{});
