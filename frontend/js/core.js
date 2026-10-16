/* ==========================================================================
   Helpers
   ========================================================================== */
const $=id=>document.getElementById(id);
const nk=s=>(s||'').replace(/\s+/g,'').toUpperCase();
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const f=(n,d=0)=>n==null?'–':Number(n).toLocaleString('en-IN',{maximumFractionDigits:d,minimumFractionDigits:d});
const J=(u,o={})=>fetch(u,{headers:{'Content-Type':'application/json'},...o}).then(async r=>{
  if(r.status==401){showLogin();throw 0}
  if(!r.ok){const d=(await r.json().catch(()=>({}))).detail;toast(typeof d=='string'?d:'Something went wrong. Please try again.','err');throw 0}
  return r.json()});
const send=(u,m,b)=>J(u,{method:m,body:b?JSON.stringify(b):undefined});
const monthLabel=m=>new Date(m+'-01T00:00:00').toLocaleDateString('en-IN',{month:'long',year:'numeric'});
const dayLabel=d=>new Date(d+'T00:00:00').toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short',year:'numeric'});

/* icons (inline SVG, no external files) */
const IC={
  chat:'<path d="M21 11.5a8.5 8.5 0 0 1-12.4 7.5L3 20.5l1.5-5.1A8.5 8.5 0 1 1 21 11.5z"/>',
  book:'<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5M9 8h7"/>',
  target:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
  calc:'<rect x="5" y="3" width="14" height="18" rx="2.5"/><path d="M8.5 7.5h7M8.5 12h.01M12 12h.01M15.5 12h.01M8.5 16h.01M12 16h.01M15.5 16h.01"/>',
  genus:'<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
  hol:'<rect x="4" y="5" width="16" height="15" rx="2.5"/><path d="M8 3v4M16 3v4M4 10h16"/>',
  users:'<circle cx="9" cy="8" r="3.2"/><path d="M3.5 19c.6-3 2.8-4.8 5.5-4.8s4.9 1.8 5.5 4.8M16 5.2a3 3 0 0 1 0 5.6M18 14.6c1.6.6 2.6 2.1 3 4.4"/>',
  audit:'<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z"/><path d="M9 12l2 2 4-4"/>',
  search:'<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  upload:'<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>',
  download:'<path d="M12 4v12M7 11l5 5 5-5M5 20h14"/>',
  warn:'<path d="M12 4l9 16H3L12 4z"/><path d="M12 10v4M12 17h.01"/>',
  trash:'<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  reset:'<path d="M4 12a8 8 0 1 0 2.5-5.8M4 4v4.5h4.5"/>',
  undo:'<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  out:'<path d="M14 4h5v16h-5M10 8l-4 4 4 4M6 12h10"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  check:'<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  x:'<path d="M6 6l12 12M18 6L6 18"/>',
  chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  grid:'<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  edit:'<path d="M4 20h4L19 9l-4-4L4 16v4zM13.5 6.5l4 4"/>',
  compare:'<path d="M7 4v14M7 18l-3-3M7 18l3-3M17 20V6M17 6l-3 3M17 6l3 3"/>',
  chev:'<path d="M6 9l6 6 6-6"/>',
  play:'<circle cx="12" cy="12" r="9"/><path d="M10 8.5l5.5 3.5-5.5 3.5z"/>'
};
const I=(k,s=18)=>`<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[k]}</svg>`;

/* toast + dialog (replace the browser's alert / confirm / prompt) */
function toast(msg,kind='ok',ms=4500,act=null){
  const t=document.createElement('div');t.className='toast '+kind;t.setAttribute('role',kind=='err'?'alert':'status');
  t.innerHTML=I(kind=='err'?'warn':'check')+`<span>${esc(msg)}</span>`+(act?`<button class="toast-act">${esc(act.label)}</button>`:'');
  if(act)t.querySelector('.toast-act').onclick=()=>{t.remove();act.fn()};
  $('toasts').appendChild(t);while($('toasts').children.length>3)$('toasts').firstChild.remove();setTimeout(()=>t.remove(),ms)}
/* dlg: confirm (default), single text input (input) or several fields (fields: [{name,label,type:'text'|'select',options:[[value,label]],value,placeholder}]) */
function dlg({title,body='',ok='OK',cancel='Cancel',danger=false,input=null,fields=null}){
  return new Promise(res=>{
    const d=document.createElement('dialog');d.className='dlg';
    const fs=fields||(input?[{name:'v',...input}]:[]);
    const fh=fs.map((x,i)=>x.type=='checks'
      ?`<fieldset class="dlg-f chk" data-name="${x.name}"><legend>${esc(x.label||'')}</legend><div class="chk-list">${x.options.map(([v,l,c,sub])=>`<label class="chk"><input type="checkbox" value="${esc(v)}" ${c?'checked':''}><span>${esc(l)}${sub?`<small>${esc(sub)}</small>`:''}</span></label>`).join('')||'<p class="mu">Nothing to choose from yet.</p>'}</div></fieldset>`
      :`<label class="dlg-f">${esc(x.label||'')}${x.type=='select'
      ?`<select name="${x.name}">${x.options.map(([v,l])=>`<option value="${esc(v)}" ${String(v)==String(x.value??'')?'selected':''}>${esc(l)}</option>`).join('')}</select>`
      :`<input name="${x.name}" autocomplete="off" ${i==0?'autofocus':''} value="${esc(x.value??'')}" placeholder="${esc(x.placeholder||'')}">`}</label>`).join('');
    d.innerHTML=`<form method="dialog" class="dlg-in"><h2>${esc(title)}</h2>${body?`<p class="dlg-body">${esc(body).replace(/\n/g,'<br>')}</p>`:''}${fh}
      <div class="dlg-act">${cancel?`<button type="button" class="btn" data-cancel>${esc(cancel)}</button>`:''}<button type="submit" class="btn ${danger?'danger-solid':'primary'}">${esc(ok)}</button></div></form>`;
    document.body.appendChild(d);
    let val=fs.length?null:false;
    d.querySelector('form').addEventListener('submit',()=>{
      if(!fs.length){val=true;return}
      const o=Object.fromEntries(fs.map(x=>[x.name,x.type=='checks'?[...d.querySelectorAll(`fieldset[data-name=${x.name}] input:checked`)].map(i=>i.value):d.querySelector(`[name=${x.name}]`).value]));
      val=input?o.v:o});
    d.querySelector('[data-cancel]')?.addEventListener('click',()=>d.close());
    d.addEventListener('close',()=>{d.remove();res(val)});
    d.showModal()})}

/* ==========================================================================
   State and business rules (unchanged)
   ========================================================================== */
let C={},U={},G={},T=[],S=[],P={},sel=null,tab='calc',sort={k:'name',d:1},flt={q:'',lvl:'',br:'',band:'',warn:false};
let TM=[],CAL=[],curTeam=null,curCal=null;                                      /* teams + holiday calendars */
let teamMonth='',insMonth='',insData=null,insTab='overview',insTarget=35;   /* Teams / Insights page state */
const store={get:k=>{try{return localStorage.getItem(k)}catch(e){return null}},set:(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}}};
const thisMonth=()=>new Date().toISOString().slice(0,7);
const canEdit=()=>TM.find(t=>t.id==curTeam)?.can_edit!==false;   /* false = shared with you as view only */
const teamName=()=>TM.find(t=>t.id==curTeam)?.name||'Team';
const teamSelect=()=>{
  const g={};TM.forEach(t=>(g[t.unit||'']=g[t.unit||'']||[]).push(t));
  const opt=t=>`<option value="${t.id}" ${t.id==curTeam?'selected':''}>${esc(t.name)}</option>`,keys=Object.keys(g).sort((a,b)=>(a===''?1:0)-(b===''?1:0)||a.localeCompare(b));
  const body=keys.length==1&&keys[0]===''?TM.map(opt).join(''):keys.map(k=>`<optgroup label="${esc(k||'No business unit')}">${g[k].map(opt).join('')}</optgroup>`).join('');
  return `<label class="inline-field" for="tsel"><span>Team</span><select id="tsel" class="auto" onchange="switchTeam(+this.value)">${body}</select></label>`};
/* chart colour per margin band (muted, one family; tokens live in :root) */
const colOf=b=>({loss:'var(--bar-loss)',red:'var(--bar-low)',amber:'var(--bar-mid)',green:'var(--bar-good)'}[b]||'var(--bar-neutral)');
/* change vs a reference: signed number, signed percentage points, and the text colour class for it */
const dnum=v=>v==null?'–':(v>0?'+':v<0?'\u2212':'')+f(Math.abs(v));
const dpts=v=>v==null?'–':(v>0?'+':v<0?'\u2212':'')+f(Math.abs(v),2)+' pts';
const dcls=v=>v==null||Math.abs(v)<1e-9?'':v>0?'green':'red';
const pct2=v=>v==null?'–':f(v,2)+'%';   /* margin % to two decimals, used by Insights */
/* compact money for charts: lakh / crore, matching en-IN number style */
const short=v=>{const a=Math.abs(v),s=v<0?'-':'';return a>=1e7?s+f(a/1e7,2)+' Cr':a>=1e5?s+f(a/1e5,1)+' L':s+f(a)};
const rngs={rate:[500,6000,10],genus:[500,4000,10],exp:[0,20,0.1]};
const mg=(r,g)=>({a:r-g,p:r?(r-g)/r*100:null});
const bandOf=p=>p==null?'red':p<0?'loss':p<C.margin_warn_below?'red':p<C.margin_good_from?'amber':'green';
const BL={loss:'Loss',red:'Low',amber:'Medium',green:'Good'};
const br=y=>y<6?'3-6':y<9?'6-9':y<12?'9-12':'12-15';
const BRACKETS=['3-6','6-9','9-12','12-15'];
const mBand=m=>bandOf(mg(m.rate,m.genus).p);
const lvl=r=>(String(r).match(/^\d\.\d/)||[''])[0];
const roll=a=>{const r=a.reduce((s,m)=>s+m.rate*m.alloc,0),c=a.reduce((s,m)=>s+m.genus*m.alloc,0);return{r,c,...mg(r,c)}};
/* each person's working days in the selected month honour their start / end dates (server computes them) */
const daysOf=m=>P.days?.[m.id]??P.business_days;
const mult=m=>P.hours_per_day*daysOf(m);
const rollM=a=>{let r=0,c=0;a.forEach(m=>{const k=mult(m)*m.alloc;r+=m.rate*k;c+=(m.genus??0)*k});return{r,c,a:r-c}};
const chip=b=>`<span class="chip ${b}">${BL[b]}</span>`;

/* margin meter: where a margin % sits against the warn / good thresholds from config.json */
function meter(p){
  const w=C.margin_warn_below,g=C.margin_good_from,lo=-10,hi=Math.max(60,g+20),pc=v=>(v-lo)/(hi-lo)*100;
  const pos=p==null?null:Math.min(hi,Math.max(lo,p));
  return `<div class="meter" role="img" title="Low below ${w}%, good from ${g}%" aria-label="Margin ${p==null?'not available':f(p,1)+'%'}. Low below ${w}%, good from ${g}%.">
    <div class="zones"><i class="loss" style="width:${pc(0)}%"></i><i class="red" style="width:${pc(w)-pc(0)}%"></i><i class="amber" style="width:${pc(g)-pc(w)}%"></i><i class="green" style="width:${100-pc(g)}%"></i></div>
    ${pos==null?'':`<span class="pin" style="left:${pc(pos)}%"></span>`}
    <div class="ticks"><span style="left:${pc(0)}%">0%</span><span style="left:${pc(w)}%">${w}%</span><span style="left:${pc(g)}%">${g}%</span></div></div>`}

/* ==========================================================================
   Session helpers and the edit queue
   ========================================================================== */
const qs=()=>`team_id=${curTeam}`;
async function loadPeriod(m){P=await J(`/api/period?month=${m}&${qs()}`)}
/* edits are saved shortly after the last change; flushAll() sends anything still waiting (before saving a scenario, comparing, switching page) */
let pt={},pending={};
const FIELDS=['name','role','exp','rate','bracket','bracket_override','genus','genus_override','alloc','start_date','end_date'];
let saveMsg=['',0];   /* what the "saved" indicator in the person panel says */
const setSave=(t,err=0)=>{saveMsg=[t,err];const el=$('savestate');if(el){el.textContent=t;el.classList.toggle('err',!!err)}};
const sendPatch=m=>{pending[m.id]=false;setSave('Saving…');
  return send('/api/team/'+m.id,'PATCH',Object.fromEntries(FIELDS.map(k=>[k,m[k]])))
    .then(r=>{if(!Object.values(pending).some(Boolean))setSave('All changes saved');return r})
    .catch(async()=>{setSave('Not saved',1);T=await J('/api/team?'+qs());draw()})};
const persist=m=>{clearTimeout(pt[m.id]);pending[m.id]=true;setSave('Unsaved changes');pt[m.id]=setTimeout(()=>sendPatch(m),600)};
/* Undo: remembers the person's numbers just before each edit. Edits made within a second of each other (a slider drag, a bulk change) count as one step. */
let UH=[],uhT=0,uhTeam=null;
function undoBtn(){const b=$('undoBtn');if(b)b.disabled=!UH.length}
function hist(m,ov){
  const now=Date.now(),b={...Object.fromEntries(FIELDS.map(k=>[k,m[k]])),...(ov||{})};
  if(uhTeam!==curTeam){UH=[];uhTeam=curTeam}
  if(UH.length&&now-uhT<1000){const g=UH[UH.length-1];if(!g.has(m.id))g.set(m.id,b)}
  else{UH.push(new Map([[m.id,b]]));if(UH.length>50)UH.shift()}
  uhT=now;undoBtn()}
async function undoEdit(){
  if(uhTeam!==curTeam)UH=[];
  let n=0;
  while(UH.length&&!n){const g=UH.pop();
    g.forEach((b,id)=>{const m=T.find(x=>x.id==id);if(m){Object.assign(m,b);persist(m);n++}})}
  uhT=0;undoBtn();
  if(!n){toast('Nothing to undo.','err');return}
  await flushAll();await loadPeriod(P.month);draw();toast('Last change undone')}
async function flushAll(){await Promise.all(Object.keys(pending).filter(id=>pending[id]).map(id=>{clearTimeout(pt[id]);const m=T.find(x=>x.id==id);return m?sendPatch(m):0}))}
