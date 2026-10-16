
/* ==========================================================================
   Calculator page
   ========================================================================== */
const shareBtn=()=>{const t=TM.find(x=>x.id==curTeam);return t&&(t.mine||U.role=='admin')?`<button class="btn" onclick="shareTeam(${t.id})">${I('users',16)}Share</button>`:''};
const isEdited=m=>m.rate!=m.base.rate||m.genus!=m.base.genus||m.exp!=m.base.exp;
const dBase=m=>(mg(m.rate,m.genus).p??0)-(mg(m.base.rate,m.base.genus).p??0);   /* margin points vs the baseline numbers */
let detOpen=false,monOpen=false;   /* folded sections of the person panel remember whether you opened them */
function drawCalcPage(){
  document.body.classList.toggle('ro',!canEdit());
  const lv=[...new Set(T.map(m=>lvl(m.role)).filter(Boolean))].sort();
  $('body').innerHTML=`${head('Calculator','<span id="pinfo"></span>',shareBtn())}${canEdit()?'':'<div class="ro-note" role="note"><b>View only.</b> This team was shared with you without edit rights, so you can look at everything but not change it.</div>'}
  ${ctx(`${teamSelect()}
     <label class="inline-field" for="mo"><span>Period</span><input type="month" id="mo" value="${P.month}" onchange="loadPeriod(this.value).then(draw)"></label>`)}
  <section class="panel summary" id="kpis" aria-label="Team summary"></section>
  <div class="calc-grid"><div class="col">
    <section class="panel">
      <div class="panel-head"><div><h2>People</h2><p id="cnt"></p></div>
        <div class="btns"><button class="btn need-edit" id="undoBtn" onclick="undoEdit()" title="Undo the last change to a person" ${UH.length?'':'disabled'}>${I('undo',16)}Undo</button><button class="btn need-edit" onclick="bulkAdjust()">${I('target',16)}Bulk adjust</button><button class="btn need-edit" onclick="imp.click()">${I('upload',16)}Import</button><button class="btn" onclick="exportTeam()">${I('download',16)}Export Excel</button><button class="btn primary need-edit" onclick="addP()">${I('plus',16)}Add person</button><input type="file" id="imp" hidden accept=".xlsx" onchange="impT(this)"></div></div>
      <div class="toolbar">
        <div class="search">${I('search',16)}<input id="fq" type="search" placeholder="Search name or role" aria-label="Search name or role" value="${esc(flt.q)}" oninput="searchIn(this.value)"></div>
        <select aria-label="Level" onchange="flt.lvl=this.value;drawTable()"><option value="">All levels</option>${lv.map(l=>`<option ${flt.lvl==l?'selected':''}>${l}</option>`).join('')}</select>
        <select aria-label="Experience bracket" onchange="flt.br=this.value;drawTable()"><option value="">All brackets</option>${BRACKETS.map(b=>`<option ${flt.br==b?'selected':''}>${b}</option>`).join('')}</select>
        <button class="btn ghost sm" id="clr" onclick="flt={q:'',lvl:'',br:'',band:'',warn:false};drawCalcPage()">Clear filters</button>
      </div>
      <div class="chips" id="chips" role="group" aria-label="Filter by margin"></div>
      <div class="tbl-wrap"><table class="tbl"><thead id="th"></thead><tbody id="tb"></tbody></table></div>
    </section>
    <section class="panel">
      <div class="panel-head"><div><h2>Scenarios</h2><p>Save the current numbers, compare them later, and load one back (a backup is kept).</p></div>
        <div class="sc-form need-edit"><input id="sn" placeholder="Scenario name" aria-label="Scenario name" maxlength="100" onkeydown="if(event.key==='Enter')saveS()"><button class="btn primary" onclick="saveS()">Save current</button></div></div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Name</th><th class="n">Margin %</th><th class="n">vs baseline</th><th></th></tr></thead><tbody id="sc"></tbody></table></div>
    </section>
  </div><aside class="panel detail" id="calc" aria-label="Selected person"></aside></div>`;
  draw()}
async function exportTeam(){await flushAll();location='/api/export?'+qs()}

/* draw() = everything; refresh() = everything except the input panel (so a slider being dragged is never replaced) */
const searchIn=v=>{flt.q=v;clearTimeout(searchIn.t);searchIn.t=setTimeout(drawTable,120)};   /* wait for a pause in typing */
function draw(){
  $('pinfo').textContent=`${P.business_days} working days${P.holidays.length?` (${P.holidays.length} holiday${P.holidays.length>1?'s':''} excluded)`:''} · ${P.hours_per_day*P.business_days} h per full-time person`;
  drawKpis();drawTable();drawCalc();drawS()}
/* while a slider is dragged only the figures that depend on it are redrawn, at most once per frame */
let rf=0;
function refresh(){if(rf)return;rf=requestAnimationFrame(()=>{rf=0;drawKpis();drawTable();drawResult()})}

function drawKpis(){
  const stat=(l,v,c)=>`<div class="stat ${c=='cost'?'cost':''}"><span>${l}</span><b class="${c&&c!='cost'?c:''}">${v}</b></div>`,rm=rollM(T);
  const R=roll(T),b=bandOf(R.p),has=T.length>0,B0=roll(T.map(m=>({...m,...m.base}))),dB=(R.p??0)-(B0.p??0),ed=T.filter(isEdited).length;
  $('kpis').innerHTML=`<div class="sum-main"><div class="sum-lab"><span class="mu">Team margin</span>${has?chip(b):''}</div>
      <div class="sum-row"><div class="big ${has?b:''}">${has&&R.p!=null?f(R.p,2)+'%':'–'}</div>${has?`<div class="sum-delta"><span class="delta ${dB>0.0049?'up':dB<-0.0049?'down':''}">${dpts(dB)}</span> vs baseline<br>${ed?`${ed} edited`:'no changes yet'}</div>`:'<span class="mu">No people in this team yet</span>'}</div>${meter(has?R.p:null)}</div>
    <div class="sum-block"><h3>Per hour</h3><div class="stats">${stat('Revenue',f(R.r))}${stat('Cost',f(R.c),'cost')}${stat('Margin',f(R.a),b)}</div></div>
    <div class="sum-block"><h3>${monthLabel(P.month)}</h3><div class="stats">${stat('Revenue',f(rm.r))}${stat('Cost',f(rm.c),'cost')}${stat('Margin',f(rm.a),b)}</div></div>`}

/* team table */
const mbar=(p,b)=>`<span class="mbar" aria-hidden="true"><i class="${b}" style="width:${p==null?0:Math.max(0,Math.min(100,p/60*100))}%"></i></span>`;
const dcell=m=>{const d=dBase(m);return isEdited(m)&&Math.abs(d)>=0.005?`<span class="delta ${d>0?'up':'down'}">${d>0?'+':''}${f(d,2)}</span>`:'<span class="mu">–</span>'};
function totRow(v){   /* totals for exactly the people shown, so filtering to "Low" shows what the Low group costs and earns */
  const R=roll(v),B=roll(v.map(m=>({...m,...m.base}))),b=bandOf(R.p),d=(R.p??0)-(B.p??0),avg=v.reduce((a,m)=>a+m.exp,0)/v.length;
  return `<tr class="tot-row"><td colspan="2"><b>${v.length==T.length?'Team total':'Shown total'}</b><span class="sub-line">per hour, rate and cost × allocation</span></td><td class="n hide-m" title="Average experience">${f(avg,1)}</td><td class="n">${f(R.r)}</td><td class="n cost">${f(R.c,2)}</td><td class="n"><i class="bdot ${b}" title="${BL[b]}"></i><span class="pct ${b}">${R.p==null?'–':f(R.p,2)+'%'}</span></td><td class="n">${Math.abs(d)<0.005?'<span class="mu">–</span>':`<span class="delta ${d>0?'up':'down'}">${d>0?'+':''}${f(d,2)}</span>`}</td></tr>`}
function rowKey(e,el){   /* Enter / Space opens, arrow keys walk the list */
  if(e.key==='Enter'||e.key===' '){e.preventDefault();pick(el.dataset.id,true)}
  else if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const n=e.key==='ArrowDown'?el.nextElementSibling:el.previousElementSibling;if(n&&n.classList.contains('r'))pick(n.dataset.id,true)}}
/* change many people at once: everyone currently shown in the table (filters respected), with Undo */
async function bulkAdjust(){
  const v=view();if(!v.length){toast('No people match the current filters.','err');return}
  const r=await dlg({title:'Bulk adjust',body:`Changes everyone currently shown in the table (${v.length} ${v.length==1?'person':'people'}; filters are respected). Use a negative number to reduce. You can undo it right after.`,ok:'Apply',
    fields:[{name:'field',label:'What to change',type:'select',options:[['rate','Rate Card'],['genus','Genus Cost']]},{name:'pct',label:'Change in % (for example 3 or -5)',placeholder:'3'}]});
  if(!r)return;const p=Number(String(r.pct).replace(',','.'));
  if(!String(r.pct).trim()||!Number.isFinite(p)||p<-90||p>100){toast('Enter a percentage between -90 and 100.','err');return}
  const k=r.field,max=C['max_'+k],undo=[];let n=0,skip=0;
  v.forEach(m=>{const nv=Math.round(m[k]*(1+p/100)*100)/100;if(nv<=0||nv>max||nv===m[k]){skip++;return}
    undo.push({id:m.id,k,val:m[k],ov:m.genus_override});hist(m);m[k]=nv;if(k=='genus')m.genus_override=true;persist(m);n++});
  draw();
  toast(`${k=='rate'?'Rate Card':'Genus Cost'} ${p>0?'+':''}${p}% applied to ${n} ${n==1?'person':'people'}${skip?` (${skip} skipped, outside the allowed range)`:''}`,'ok',12000,n?{label:'Undo',fn:()=>{undo.forEach(u=>{const m=T.find(x=>x.id==u.id);if(m){m[u.k]=u.val;if(u.k=='genus')m.genus_override=u.ov;persist(m)}});draw();toast('Undone')}}:null)}
function view(){
  const q=flt.q.toLowerCase();
  const a=T.filter(m=>(!q||(m.name+' '+m.role).toLowerCase().includes(q))&&(!flt.lvl||lvl(m.role)==flt.lvl)&&(!flt.br||m.bracket==flt.br)&&(!flt.band||mBand(m)==flt.band)&&(!flt.warn||m.warnings?.length));
  const key={name:m=>m.name.toLowerCase(),role:m=>m.role.toLowerCase(),exp:m=>m.exp,rate:m=>m.rate,genus:m=>m.genus,mp:m=>mg(m.rate,m.genus).p??-1e9,dv:m=>dBase(m)}[sort.k];
  return a.sort((x,y)=>(key(x)>key(y)?1:key(x)<key(y)?-1:0)*sort.d)}
function sortBy(k){sort=sort.k==k?{k,d:-sort.d}:{k,d:1};drawTable()}
function setBand(b){flt.band=b;drawTable()}
function pick(id,kb){
  sel=id;drawTable();drawCalc();
  if(kb)document.querySelector(`tr.r[data-id="${CSS.escape(String(id))}"]`)?.focus();
  if(innerWidth<=1100)$('calc').scrollIntoView({block:'start',behavior:'smooth'})}

function drawChips(){
  const cnt={};T.forEach(m=>{const b=mBand(m);cnt[b]=(cnt[b]||0)+1});
  const defs=[['','All'],['green','Good'],['amber','Medium'],['red','Low'],['loss','Loss']];
  $('chips').innerHTML=defs.map(([k,l])=>`<button class="fchip ${flt.band==k?'on':''}" aria-pressed="${flt.band==k}" onclick="setBand('${k}')">${k?`<i class="bdot ${k}"></i>`:''}${l}<b>${k===''?T.length:(cnt[k]||0)}</b></button>`).join('')
    +`<button class="fchip ${flt.warn?'on':''}" aria-pressed="${flt.warn}" onclick="flt.warn=!flt.warn;drawTable()">${I('warn',14)}Warnings<b>${T.filter(m=>m.warnings?.length).length}</b></button>`}

function drawTable(){
  const H=[['name','Name',''],['role','Role',''],['exp','Exp. (yrs)','n hide-m'],['rate','Rate','n'],['genus','Genus','n cost'],['mp','Margin %','n'],['dv','vs baseline','n']];
  $('th').innerHTML='<tr>'+H.map(([k,l,c])=>`<th class="${c}" aria-sort="${sort.k==k?(sort.d>0?'ascending':'descending'):'none'}"><button class="th-btn" onclick="sortBy('${k}')">${l}${sort.k==k?`<span class="arr">${sort.d>0?'▲':'▼'}</span>`:''}</button></th>`).join('')+'</tr>';
  const v=view();
  $('tb').innerHTML=v.length?v.map(m=>{
    const b=mBand(m),x=mg(m.rate,m.genus);
    return `<tr class="r ${m.id==sel?'sel':''}" tabindex="0" data-id="${esc(m.id)}" onclick="pick(this.dataset.id)" onkeydown="rowKey(event,this)">
      <td>${isEdited(m)?'<i class="edot" title="Changed from baseline"></i>':''}<span class="clip" title="${esc(m.name)}">${esc(m.name)}</span>${m.warnings?.length?`<span class="warn-ic" title="${esc(m.warnings.join('\n'))}">${I('warn',15)}</span>`:''}</td>
      <td class="role">${esc(m.role)}</td><td class="n hide-m">${f(m.exp,1)}</td><td class="n">${f(m.rate)}</td>
      <td class="n cost">${f(m.genus,2)}</td>
      <td class="n"><i class="bdot ${b}" title="${BL[b]}"></i><span class="pct ${b}">${f(x.p,2)}${x.p==null?'':'%'}</span></td><td class="n">${dcell(m)}</td></tr>`}).join('')+totRow(v)
    :`<tr class="empty-row"><td colspan="${H.length}">${T.length?'No one matches these filters.':'No one in this team yet. Use Add person, or Import a team sheet.'}</td></tr>`;
  $('cnt').textContent=`Showing ${v.length} of ${T.length} people`;
  drawChips();$('clr').style.display=(flt.q||flt.lvl||flt.br||flt.band||flt.warn)?'':'none'}

/* detail panel */
/* how far a slider is from the baseline, as text and a colour (a higher rate is good, a higher cost is not) */
const dSlide=(k,m)=>{const d=m[k]-m.base[k];if(Math.abs(d)<1e-9)return{t:'',c:''};
  const p=m.base[k]?d/m.base[k]*100:0,good=k=='rate'?d>0:k=='genus'?d<0:null;
  return{t:`${d>0?'+':'\u2212'}${f(Math.abs(d),k=='rate'?0:k=='exp'?1:2)} (${p>0?'+':'\u2212'}${f(Math.abs(p),1)}%)`,c:good==null?'':good?'up':'down'}};
function row(k,l,v,e){
  const m=T.find(x=>x.id==sel),[mn,mx,st]=rngs[k],max=Math.max(mx,v*1.2,m.base[k]*1.2),pc=x=>Math.max(0,Math.min(100,(x-mn)/(max-mn)*100)),d=dSlide(k,m);
  return `<div class="slider ${k=='genus'?'cost':''}"><div class="s-top"><label for="n-${k}">${l}${e||''}</label><span class="sd ${d.c}" id="d-${k}" title="Change from the baseline">${d.t}</span><input id="n-${k}" type="number" step="${st}" min="${k=='rate'?1:0}" max="${C['max_'+k]}" value="${v}" onchange="upd('${k}',this.value,1)"></div>
    <div class="track" style="--b:${pc(m.base[k])}%" title="The small mark shows the baseline value"><input id="r-${k}" type="range" aria-label="${l}" min="${mn}" max="${max}" step="${st}" value="${v}" style="--p:${pc(v)}%" oninput="upd('${k}',this.value)"></div></div>`}
/* "Target margin": drag the margin you want and the rate follows (rate = cost / (1 - margin)) */
function targetRow(m){
  const p=mg(m.rate,m.genus).p,v=p==null?0:Math.round(p*100)/100,max=Math.max(60,Math.ceil(v)),pc=x=>Math.max(0,Math.min(100,x/max*100));
  return `<div class="slider cost"><div class="s-top"><label for="n-tm" title="Drag to set the rate that gives this margin">Target margin %</label><input id="n-tm" type="number" step="0.5" min="0" max="95" value="${v}" onchange="setTarget(this.value)"></div>
    <div class="track" style="--b:${pc(C.margin_good_from)}%" title="The small mark shows where Good starts"><input id="r-tm" type="range" aria-label="Target margin percent" min="0" max="${max}" step="0.5" value="${Math.max(0,v)}" style="--p:${pc(Math.max(0,v))}%" oninput="setTarget(this.value)"></div></div>`}
function setTarget(v){
  const m=T.find(x=>x.id==sel);v=+v;
  if(!m.genus){toast('Set a Genus cost first, the target margin works from it.','err');syncInputs(m);return}
  if(!Number.isFinite(v)||v<0||v>=95){toast('Target margin must be between 0 and 95%.','err');syncInputs(m);return}
  const r=Math.round(m.genus/(1-v/100)*100)/100;
  if(r>C.max_rate){toast(`That margin needs a rate above the maximum (${f(C.max_rate)}).`,'err');syncInputs(m);return}
  upd('rate',r)}
function setRate(v){v=Math.round(v*100)/100;if(!(v>0&&v<=C.max_rate)){toast(`Rate must be between 1 and ${f(C.max_rate)}.`,'err');return}upd('rate',v)}
const nudge=p=>{const m=T.find(x=>x.id==sel);setRate(Math.round(m.rate*(1+p/100)))};
const hitGood=()=>{const m=T.find(x=>x.id==sel);setRate(Math.ceil(m.genus/(1-C.margin_good_from/100)))};
const breakEven=()=>setRate(T.find(x=>x.id==sel).genus);
/* a plain-words reading of where this person stands and what would move them */
function coach(m){
  const x=mg(m.rate,m.genus),tg=C.margin_good_from;if(!m.rate)return '';
  const up=Math.ceil(m.genus/(1-tg/100))-m.rate,per=mg(m.rate+100,m.genus).p-x.p;let t;
  if(x.p<0)t=`Below cost by ${f(m.genus-m.rate)}. Break-even needs a rate of ${f(m.genus)}; ${tg}% needs ${f(Math.ceil(m.genus/(1-tg/100)))}.`;
  else if(x.p<tg)t=`To reach ${tg}% (Good): raise the rate by ${f(up)} (${f(up/m.rate*100,1)}%) or cut the cost by ${f(m.genus-m.rate*(1-tg/100))}.`;
  else t=`Good. The rate can fall by ${f(m.rate-m.genus/(1-tg/100))} before the margin drops below ${tg}%.`;
  return `<div class="coach cost">${t}</div>`}

function drawCalc(){
  const m=T.find(x=>x.id==sel),el=$('calc');
  if(!m){el.innerHTML='<div class="empty"><b>Select a person</b><p>Choose someone from the team list to try different rates, experience and Genus cost.</p></div>';return}
  const g=G[nk(m.role)];
  el.innerHTML=`<div class="detail-head"><h2>${esc(m.name)}</h2><p>${[m.role&&esc(m.role),`${f(m.exp,1)} yrs experience`].filter(Boolean).join(' · ')}</p></div>
    <div class="detail-body">
      <div id="res-card">${resultCard(m)}</div>
      <div class="sliders">${row('rate','Rate Card',m.rate)}${targetRow(m)}${row('genus','Genus Cost',m.genus,`<span class="tag" id="tag-genus" ${m.genus_override?'':'hidden'}>override</span>`)}${row('exp','Experience (yrs)',m.exp)}</div>
      <div class="field"><label for="f-role">Role per MSA</label>
        <div class="combo"><input id="f-role" type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="role-list" autocomplete="off" spellcheck="false" maxlength="100" placeholder="Search roles, e.g. 3.2 crm" value="${esc(m.role)}" data-cur="${esc(m.role)}" onfocus="roleFocus()" onclick="if(!$('role-list'))roleFocus()" onmouseup="if(roleSel){roleSel=false;event.preventDefault()}" oninput="roleType()" onkeydown="roleKey(event)" onblur="roleBlur()">${I('search',16)}</div></div>
      ${!g?'<div class="field-note">This role is not in the Genus table. Enter the Genus cost manually.</div>':''}
      <details class="fold" ${detOpen||!g||!m.role?'open':''} ontoggle="detOpen=this.open"><summary>Person details</summary>
      <div class="field"><label for="f-name">Name</label><input id="f-name" maxlength="100" value="${esc(m.name)}" onchange="fld('name',this.value)"></div>
      <div class="two"><div class="field"><label for="f-br">Bracket<span class="tag" id="tag-br" ${m.bracket_override?'':'hidden'}>manual</span></label><select id="f-br" onchange="setB(this.value)">${BRACKETS.map(b=>`<option ${b==m.bracket?'selected':''}>${b}</option>`).join('')}</select></div>
        <div class="field"><label for="f-alloc">Allocation (FTE)</label><input id="f-alloc" type="number" step="0.1" min="0" max="${C.max_alloc}" value="${m.alloc}" onchange="setAlloc(this.value)"></div></div>
      <div class="two"><div class="field"><label for="f-sd">Starts</label><input id="f-sd" type="date" value="${m.start_date||''}" onchange="setDate('start_date',this.value)"></div>
        <div class="field"><label for="f-ed">Ends</label><input id="f-ed" type="date" value="${m.end_date||''}" onchange="setDate('end_date',this.value)"></div></div>
        <p class="hint">Leave empty if open-ended. Revenue and cost count only the days someone is on the team.</p></details>
      <div id="res-more">${resultMore(m)}</div>
    </div>
    <div class="detail-foot"><button class="btn" onclick="reset()" title="Put this person back to the baseline numbers">${I('reset',16)}Reset</button><span class="save-state ${saveMsg[1]?'err':''}" id="savestate" aria-live="polite">${esc(saveMsg[0])}</span><button class="btn danger" onclick="del()" title="Delete this person from the team">${I('trash',16)}Delete</button></div>`;
  if(!canEdit())el.querySelectorAll('.sliders,.field,.two,.quick,.hint,.detail-foot .btn,#res-more .linkbtn').forEach(e=>{e.inert=true;e.classList.add('locked')})}
function drawResult(){const m=T.find(x=>x.id==sel);if(!m||!$('res-card'))return;$('res-card').innerHTML=resultCard(m);$('res-more').innerHTML=resultMore(m)}

/* top of the panel: the live result, so it stays in view while a slider is moved */
function resultCard(m){
  const x=mg(m.rate,m.genus),b=bandOf(x.p),d=dBase(m),ed=isEdited(m);
  return `<div class="result"><div class="res-top"><div><span class="mu">Margin</span><div class="big sm ${b}">${x.p==null?'n/a':f(x.p,2)+'%'}</div><div class="res-delta">${ed&&Math.abs(d)>=0.005?`<span class="delta ${d>0?'up':'down'}">${dpts(d)}</span> vs baseline`:ed?'Changed, same margin as baseline':'At baseline'}</div></div>${chip(b)}</div>${meter(x.p)}
    <dl class="kv"><div><dt>Margin per hour</dt><dd class="${b}">${f(x.a,2)}</dd></div></dl>${coach(m)}</div>`}

/* below the inputs: monthly figures, reference points, warnings */
function resultMore(m){
  const mm=mult(m),x=mg(m.rate,m.genus),b=bandOf(x.p),tg=C.margin_good_from,k=mm*m.alloc;
  return `<details class="fold" ${monOpen?'open':''} ontoggle="monOpen=this.open"><summary>${monthLabel(P.month)} · ${daysOf(m)} working day${daysOf(m)==1?'':'s'}</summary>${daysOf(m)==0?`<p class="hint">No working days in ${monthLabel(P.month)} because of the Starts / Ends dates (or the calendar), so the monthly figures are 0. Change the Period at the top to see another month.</p>`:''}
    <div class="mini"><div><span>Revenue</span><b>${f(m.rate*k)}</b></div><div class="cost"><span>Cost</span><b>${f(m.genus*k)}</b></div><div><span>Margin</span><b class="${b}">${f(x.a*k)}</b></div></div>
    <h3 class="sub">Reference</h3>
    <dl class="kv sm"><div><dt>Baseline</dt><dd>Rate ${f(m.base.rate)}<span class="cost">, Genus ${f(m.base.genus,2)}</span> → ${f(mg(m.base.rate,m.base.genus).p,2)}%</dd></div>
      <div class="cost"><dt>Break-even rate</dt><dd>${f(m.genus,2)}<button class="linkbtn" onclick="breakEven()">Apply</button></dd></div>
      <div class="cost"><dt>Rate for ${tg}% margin</dt><dd>${f(m.genus/(1-tg/100),2)}<button class="linkbtn" onclick="hitGood()">Apply</button></dd></div></dl></details>
    ${(m.warnings||[]).map(w=>`<div class="alert">${I('warn',16)}<span>${esc(w)}</span></div>`).join('')}`}

/* edits: update the model, then sync the visible inputs in place (never re-create the slider being dragged) */
function syncInputs(m){
  for(const k of ['rate','exp','genus']){
    const n=$('n-'+k),r=$('r-'+k);if(!n||!r)continue;const v=m[k];
    if(document.activeElement!==n)n.value=v;
    if(document.activeElement!==r){r.max=Math.max(rngs[k][1],v*1.2,m.base[k]*1.2,+r.max);r.value=v}
    const pc=x=>Math.max(0,Math.min(100,(x-r.min)/(r.max-r.min)*100));
    r.style.setProperty('--p',pc(r.value)+'%');r.parentElement.style.setProperty('--b',pc(m.base[k])+'%');
    const d=dSlide(k,m),dl=$('d-'+k);if(dl){dl.textContent=d.t;dl.className='sd '+d.c}}
  const tn=$('n-tm'),tr=$('r-tm');
  if(tn&&tr){const p=mg(m.rate,m.genus).p,v=p==null?0:Math.round(p*100)/100;
    if(document.activeElement!==tn)tn.value=v;
    if(document.activeElement!==tr){tr.max=Math.max(60,Math.ceil(v));tr.value=Math.max(0,v)}
    tr.style.setProperty('--p',Math.max(0,Math.min(100,tr.value/tr.max*100))+'%');tr.parentElement.style.setProperty('--b',C.margin_good_from/tr.max*100+'%')}
  if($('f-br'))$('f-br').value=m.bracket;
  if($('tag-br'))$('tag-br').hidden=!m.bracket_override;
  if($('tag-genus'))$('tag-genus').hidden=!m.genus_override}
const LIM={rate:['Rate card',1,'max_rate'],exp:['Experience',0,'max_exp'],genus:['Genus cost',0,'max_genus']};
function upd(k,v,num){
  const m=T.find(x=>x.id==sel);v=+v;
  if(num){const [l,lo,hk]=LIM[k],hi=C[hk];
    if(!Number.isFinite(v)||v<lo||v>hi){toast(`${l} must be between ${f(lo)} and ${f(hi)}.`,'err');$('n-'+k).value=m[k];return}}
  hist(m);
  if(k=='exp'){m.exp=v;if(!m.bracket_override)m.bracket=br(v)}else if(k=='genus'){m.genus=v;m.genus_override=true}else m[k]=v;
  persist(m);
  syncInputs(m);refresh()}
function fld(k,v){
  const m=T.find(x=>x.id==sel);
  if(k=='name'){v=v.trim();if(!v){toast('Name cannot be empty.','err');$('f-name').value=m.name;return}}
  hist(m);m[k]=v;persist(m);if(k=='name'){drawTable();const h=document.querySelector('.detail-head h2');if(h)h.textContent=v}}
function setAlloc(v){
  const m=T.find(x=>x.id==sel),n=+v;
  if(v===''||!Number.isFinite(n)||n<0||n>C.max_alloc){toast(`Allocation must be between 0 and ${C.max_alloc} FTE.`,'err');$('f-alloc').value=m.alloc;return}
  fld('alloc',n);draw()}
async function setDate(k,v){
  const m=T.find(x=>x.id==sel),old=m[k];v=v||null;m[k]=v;
  if(m.start_date&&m.end_date&&m.end_date<m.start_date){m[k]=old;toast('The end date cannot be before the start date.','err');drawCalc();return}
  hist(m,{[k]:old});
  try{await flushAll();await send('/api/team/'+m.id,'PATCH',{[k]:v})}catch(e){m[k]=old;drawCalc();return}
  await loadPeriod(P.month);draw()}
/* Role per MSA: a search box over the Genus table (type any part, e.g. "3.2 crm"; arrow keys + Enter, or click) */
let roleHi=-1,roleItems=[],roleCustom='',roleTyped=false;
let rolesFor=null,rolesList=[];   /* sorted once per Genus table, not on every keystroke */
const roleAll=()=>{if(rolesFor!==G){rolesFor=G;rolesList=Object.values(G).map(v=>v.genus).sort((x,y)=>parseFloat(x)-parseFloat(y)||x.localeCompare(y))}return rolesList};
function roleMatch(q){const t=q.toLowerCase().split(/[\s-]+/).filter(Boolean);return roleAll().filter(r=>{const l=r.toLowerCase();return t.every(w=>l.includes(w))})}
function roleDraw(){
  const inp=$('f-role');if(!inp)return;
  const q=roleTyped?inp.value.trim():'',cur=inp.dataset.cur;
  roleItems=roleMatch(q);roleCustom=q&&!roleAll().some(r=>nk(r)==nk(q))&&(!roleItems.length||/^\d\.\d-\S/.test(q))?q:'';
  const n=roleItems.length+(roleCustom?1:0);if(roleHi>=n)roleHi=n-1;
  let el=$('role-list');
  if(!el){el=document.createElement('div');el.id='role-list';el.className='combo-list';el.setAttribute('role','listbox');el.addEventListener('mousedown',e=>e.preventDefault());document.body.appendChild(el)}
  el.innerHTML=roleItems.map((r,i)=>`<div class="combo-opt ${i==roleHi?'hi':''} ${nk(r)==nk(cur)?'cur':''}" role="option" id="ro-${i}" aria-selected="${i==roleHi}" data-v="${esc(r)}" onclick="rolePick(this.dataset.v)">${esc(r)}</div>`).join('')
    +(roleCustom?`<div class="combo-opt custom ${roleHi==roleItems.length?'hi':''}" role="option" id="ro-${roleItems.length}" aria-selected="${roleHi==roleItems.length}" data-v="${esc(roleCustom)}" onclick="rolePick(this.dataset.v)">Use “${esc(roleCustom)}” <span class="mu">not in the Genus table, enter the cost yourself</span></div>`:'')
    ||'<div class="combo-empty">No matching roles</div>';
  inp.setAttribute('aria-expanded','true');inp.setAttribute('aria-activedescendant',roleHi>=0?'ro-'+roleHi:'');
  rolePlace();
  const hi=el.querySelector('.hi');if(hi){const t=hi.offsetTop,b=t+hi.offsetHeight;if(t<el.scrollTop)el.scrollTop=Math.max(0,t-4);else if(b>el.scrollTop+el.clientHeight)el.scrollTop=b-el.clientHeight+4}}
function rolePlace(){
  const inp=$('f-role'),el=$('role-list');if(!inp||!el)return;
  const r=inp.getBoundingClientRect(),h=el.offsetHeight;el.style.left=r.left+'px';el.style.width=r.width+'px';
  el.style.top=((r.bottom+4+h>innerHeight-8&&r.top-4-h>8)?r.top-4-h:r.bottom+4)+'px'}
function roleClose(){$('role-list')?.remove();roleHi=-1;const i=$('f-role');if(i){i.setAttribute('aria-expanded','false');i.removeAttribute('aria-activedescendant')}}
let roleSel=false;
function roleFocus(){const i=$('f-role');roleTyped=false;i.select();roleSel=true;roleHi=Math.max(-1,roleAll().findIndex(r=>nk(r)==nk(i.dataset.cur)));roleDraw()}
function roleType(){roleTyped=true;roleHi=0;roleDraw()}
function roleBlur(){roleClose();const i=$('f-role');if(i)i.value=i.dataset.cur}
function roleKey(e){
  const n=roleItems.length+(roleCustom?1:0);
  if(e.key=='ArrowDown'||e.key=='ArrowUp'){e.preventDefault();if(!$('role-list')){roleFocus();return}if(!n)return;roleHi=(roleHi+(e.key=='ArrowDown'?1:-1)+n)%n;roleDraw()}
  else if(e.key=='Enter'){e.preventDefault();if(roleHi>=0)rolePick(roleHi<roleItems.length?roleItems[roleHi]:roleCustom)}
  else if(e.key=='Escape'){if($('role-list')){e.preventDefault();e.stopPropagation();roleBlur()}}}
function rolePick(v){
  roleClose();const m=T.find(x=>x.id==sel),i=$('f-role');v=(v||'').trim();
  if(!m||!v)return;
  if(nk(v)==nk(m.role)){if(i)i.value=m.role;return}
  if(v.length>100){toast('Role must be 100 characters or fewer.','err');if(i)i.value=m.role;return}
  setRole(v)}
function setRole(v){
  const m=T.find(x=>x.id==sel),g=G[nk(v)];hist(m);m.role=g?g.genus:v;
  if(g){m.genus=g.cost;m.genus_override=false}else m.genus_override=true;
  persist(m);draw()}
window.addEventListener('resize',rolePlace);
document.addEventListener('scroll',e=>{if(!(e.target.closest&&e.target.closest('#role-list')))rolePlace()},true);
function setB(v){const m=T.find(x=>x.id==sel);hist(m);m.bracket=v;m.bracket_override=v!=br(m.exp);persist(m);syncInputs(m)}
function reset(){
  const m=T.find(x=>x.id==sel);hist(m);Object.assign(m,{rate:m.base.rate,exp:m.base.exp,bracket:m.base.bracket});
  m.genus=m.base.genus;m.genus_override=!G[nk(m.role)];persist(m);draw()}
async function addP(){detOpen=true;const m=await send('/api/team?'+qs(),'POST');T.push(m);sel=m.id;draw();toast('Person added. Fill in their details on the right.')}
async function del(){
  const m=T.find(x=>x.id==sel);
  if(!await dlg({title:'Delete this person?',body:`${m?.name||'This person'} will be removed from the team. This cannot be undone.`,ok:'Delete person',danger:true}))return;
  await send('/api/team/'+sel,'DELETE');T=T.filter(x=>x.id!=sel);sel=T[0]?.id;draw()}
async function impT(i){
  if(!i.files[0])return;
  if(!await dlg({title:'Replace the current team?',body:`Importing replaces everyone currently in ${teamName()} with the rows from this file. Other teams are not affected.`,ok:'Replace team',danger:true})){i.value='';return}
  const fd=new FormData();fd.append('file',i.files[0]);
  const r=await fetch('/api/team/import?'+qs(),{method:'POST',body:fd});
  if(!r.ok){toast((await r.json().catch(()=>({}))).detail||'Import failed','err');i.value='';return}
  UH=[];T=await r.json();sel=T[0]?.id;i.value='';await loadPeriod(P.month);draw();toast(`Imported ${T.length} people into ${teamName()}`)}

/* scenarios */
async function saveS(){
  await flushAll();const n=$('sn').value.trim();
  await send('/api/scenarios?'+qs(),'POST',{name:n});$('sn').value='';S=await J('/api/scenarios?'+qs());drawS();toast(n?`Saved “${n}”`:'Scenario saved')}
async function loadS(i){
  const s=S.find(x=>x.id==i);
  if(!await dlg({title:'Load this scenario?',body:`“${s?.name}” will replace the current numbers for ${teamName()}. A backup of your current numbers is saved first, so you can undo this.`,ok:'Load scenario'}))return;
  await flushAll();const r=await send(`/api/scenarios/${i}/apply`,'POST');UH=[];T=r.team;S=await J('/api/scenarios?'+qs());sel=T.find(x=>x.id==sel)?.id??T[0]?.id;draw();
  toast(`Loaded “${s?.name}”`,'ok',12000,{label:'Undo',fn:()=>undoS(r.undo_id)})}
async function undoS(id){
  const r=await send(`/api/scenarios/${id}/apply?backup=false`,'POST');UH=[];T=r.team;S=await J('/api/scenarios?'+qs());draw();toast('Your previous numbers are back')}
async function delS(i){await send('/api/scenarios/'+i,'DELETE');S=await J('/api/scenarios?'+qs());drawS()}
function drawS(){
  const b=roll(T.map(m=>({...m,...m.base})));
  $('sc').innerHTML=`<tr class="base-row"><td><b>Baseline</b><span class="sub-line">Rates and costs as first loaded</span></td><td class="n">${f(b.p,2)}%</td><td class="n">–</td>
      <td class="n"><button class="btn sm" onclick="compareS('baseline','current')">${I('compare',15)}Compare</button></td></tr>`
   +(S.length?S.slice().reverse().map(s=>{const d=s.margin_pct-b.p;return `<tr><td class="wrap">${esc(s.name)}${s.auto?'<span class="tag auto">auto backup</span>':''}<span class="sub-line">${esc(s.by)}, ${esc((s.at||'').replace('T',' '))}</span></td><td class="n ${bandOf(s.margin_pct)}">${f(s.margin_pct,2)}%</td>
     <td class="n"><span class="delta ${d>0?'up':d<0?'down':''}">${d>=0?'+':''}${f(d,2)} pts</span></td>
     <td class="n"><button class="btn sm" onclick="compareS('${s.id}','current')">${I('compare',15)}Compare</button> <button class="btn sm need-edit" onclick="loadS(${s.id})">Load</button> <button class="btn sm icon ghost danger need-edit" aria-label="Delete scenario ${esc(s.name)}" title="Delete" onclick="delS(${s.id})">${I('trash',16)}</button></td></tr>`}).join('')
   :`<tr class="empty-row"><td colspan="4">No saved scenarios yet. Adjust the numbers for someone, then choose Save current.</td></tr>`)}

/* compare any two states (a scenario, the current numbers, or the baseline) person by person */
async function compareS(a,b){
  await flushAll();
  const d=document.createElement('dialog');d.className='dlg wide';document.body.appendChild(d);d.addEventListener('close',()=>d.remove());
  let A=a,B=b,all=false;
  const opts=sel=>[['current','Current numbers'],['baseline','Baseline'],...S.slice().reverse().map(s=>[String(s.id),s.name+(s.auto?' (auto backup)':'')])].map(([v,l])=>`<option value="${esc(v)}" ${v==sel?'selected':''}>${esc(l)}</option>`).join('');
  const dl=(x,y,dp=2,u='')=>{const v=y-x;return `<span class="delta ${v>0.0049?'up':v<-0.0049?'down':''}">${v>=0?'+':''}${f(v,dp)}${u}</span>`};
  const render=async()=>{
    const r=await J(`/api/scenarios/compare?a=${A}&b=${B}&${qs()}&month=${P.month}`),rows=all?r.rows:r.rows.filter(x=>x.changed),pa=r.a.margin_pct,pb=r.b.margin_pct;
    const fid=d.querySelector(':focus')?.id;   /* keep keyboard focus when the dialog redraws */
    d.innerHTML=`<div class="dlg-in cmp"><div class="cmp-head"><h2>Compare numbers</h2><button class="btn ghost sm icon" aria-label="Close" onclick="this.closest('dialog').close()">${I('x',16)}</button></div>
      <div class="cmp-pick"><label>From<select id="cA">${opts(A)}</select></label><label>To<select id="cB">${opts(B)}</select></label>
        <label class="switch"><input type="checkbox" id="cAll" ${all?'checked':''}><i></i><span>Show everyone</span></label></div>
      <div class="cmp-sum">
        <div class="stat"><span>Team margin</span><b>${pa==null?'–':f(pa,2)+'%'} <small>to</small> ${pb==null?'–':f(pb,2)+'%'}</b><span>${pa!=null&&pb!=null?dl(pa,pb,2,' pts'):''}</span></div>
        <div class="stat"><span>Revenue, ${monthLabel(r.month)}</span><b>${f(r.a.revenue)} <small>to</small> ${f(r.b.revenue)}</b><span>${dl(r.a.revenue,r.b.revenue,0)}</span></div>
        <div class="stat"><span>Margin, ${monthLabel(r.month)}</span><b>${f(r.a.margin)} <small>to</small> ${f(r.b.margin)}</b><span>${dl(r.a.margin,r.b.margin,0)}</span></div></div>
      <div class="tbl-wrap cmp-t"><table class="tbl"><thead><tr><th>Name</th><th class="n">Rate</th><th class="n cost">Genus</th><th class="n">Allocation</th><th class="n">Margin %</th><th class="n">Change</th></tr></thead><tbody>
      ${rows.length?rows.map(x=>{const p=(k,dp=0)=>x.a[k]==x.b[k]?`<span class="mu">${f(x.a[k],dp)}</span>`:`${f(x.a[k],dp)} to ${f(x.b[k],dp)}`;
        const one=!x.a||!x.b,v=(o,k,dp)=>o?f(o[k],dp):'–',pc=o=>!o||o.margin_pct==null?'–':f(o.margin_pct,1)+'%';
        return `<tr><td><span class="clip" title="${esc(x.role)}">${esc(x.name)}</span></td><td class="n">${one?`${v(x.a,'rate',0)} to ${v(x.b,'rate',0)}`:p('rate')}</td><td class="n cost">${one?`${v(x.a,'genus',2)} to ${v(x.b,'genus',2)}`:p('genus',2)}</td><td class="n">${one?`${v(x.a,'alloc',1)} to ${v(x.b,'alloc',1)}`:p('alloc',1)}</td>
        <td class="n">${pc(x.a)} to ${pc(x.b)}</td><td class="n">${x.status?`<span class="tag">${x.status=='removed'?'Removed':'Added'}</span>${x.restorable?` <button class="btn sm" data-restore="${esc(x.id)}">Restore</button>`:''}`:x.a.margin_pct!=null&&x.b.margin_pct!=null?dl(x.a.margin_pct,x.b.margin_pct,1,' pts'):'–'}</td></tr>`}).join('')
       :`<tr class="empty-row"><td colspan="6">No differences between these two versions.</td></tr>`}</tbody></table></div>
      </div>`;
    d.querySelector('#cA').onchange=e=>{A=e.target.value;render()};d.querySelector('#cB').onchange=e=>{B=e.target.value;render()};d.querySelector('#cAll').onchange=e=>{all=e.target.checked;render()};
    if(fid)d.querySelector('#'+fid)?.focus();
    d.querySelectorAll('[data-restore]').forEach(btn=>btn.onclick=async()=>{btn.disabled=true;
      try{const p=await send(`/api/team/restore/${btn.dataset.restore}?${qs()}`,'POST');UH=[];T=await J('/api/team?'+qs());S=await J('/api/scenarios?'+qs());sel=p.id;draw();toast(`${p.name} is back in the team.`);await render()}
      catch(e){btn.disabled=false;toast(e.message||'Could not restore this person.','err')}})};
  d.showModal();await render()}

document.addEventListener('click',e=>{const m=$('moremenu');if(m&&m.open&&(!m.contains(e.target)||e.target.closest('.menu-pop button')))m.open=false});
