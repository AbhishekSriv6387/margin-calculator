/* ==========================================================================
   Guided Demo: a step-by-step tour that runs on top of the real app.
   Two tracks, chosen on the Guided Demo tab (or on the sign-in page):
     own   Log in with your own account: create a team, upload an Excel file, experiment with every parameter.
     demo  Log in with a demo account: ready-made projects to click through, play with and explore.
   The tour is a card plus a spotlight. It never blocks the page, so people can click, drag and type for real.
   Each "Your turn" step notices when it has been done. Progress is kept in the browser, so a page reload or a
   pause (the x on the card) can be picked up again from the Guided Demo tab.
   Steps are plain data in STEPS below: to change the tour, edit the list, not the engine.
   ========================================================================== */
const TOUR_KEY='mc_tour',TOUR_AGE=12*36e5;   /* a saved tour is forgotten after 12 hours */
let tour=null,tourCtx={},tourTimer=0,tourBusy=false;
const $q=s=>document.querySelector(s);
const tourLoad=()=>{try{const t=JSON.parse(store.get(TOUR_KEY)||'null');return t&&Date.now()-t.at<TOUR_AGE?t:null}catch(e){return null}};
const tourSave=()=>{if(tour){tour.at=Date.now();store.set(TOUR_KEY,JSON.stringify(tour))}};

/* ---- helpers the steps use to notice what the person has done ---- */
const tsnap=()=>Object.fromEntries(T.map(m=>[m.id,{rate:m.rate,genus:m.genus,exp:m.exp,alloc:m.alloc,role:m.role,start_date:m.start_date,end_date:m.end_date}]));
const tchg=(ks,n=1)=>[].concat(ks).some(k=>T.filter(m=>tourCtx.snap?.[m.id]&&tourCtx.snap[m.id][k]!==m[k]).length>=n);   /* did n or more people change this field since the step began? */
const tslider=k=>()=>$('r-'+k)?.closest('.slider');
const tbtn=fn=>()=>$q(`.btn[onclick^="${fn}"]`);
async function tourResetAll(){   /* demo accounts are shared: put the open team back as found */
  if(uhTeam!==curTeam)UH=[];
  while(UH.length){const g=UH.pop();g.forEach((b,id)=>{const m=T.find(x=>x.id==id);if(m){Object.assign(m,b);persist(m)}})}
  uhT=0;undoBtn();
  T.filter(isEdited).forEach(m=>{Object.assign(m,{rate:m.base.rate,exp:m.base.exp,bracket:m.base.bracket});m.genus=m.base.genus;m.genus_override=!G[nk(m.role)];persist(m)});
  await flushAll();await loadPeriod(P.month);if(tab=='calc')draw();toast(`${teamName()} is back to its original numbers`)}
const tourFile=u=>{const a=document.createElement('a');a.href=u;a.download='';document.body.appendChild(a);a.click();a.remove()};

/* ---- the steps ----
   id       unique name (progress is saved by id)
   only     'own' or 'demo' (leave out for both);  admin:1 = administrators only
   tab      page to open first;  needsTeam / needsPeople: the step explains what to do first if the team or its people are missing
   target   CSS selector or function returning the element to spotlight (no target = centred card)
   place    preferred side for the card: right | left | below | above
   done     function: true once the person has done the thing;  hint = the "Your turn" text
   enter    setup that runs when the step opens;  actions = extra buttons on the card
   dlg      text to show inside a dialog the step opens, keyed by the dialog's heading */
const STEPS=[
{id:'welcome-own',only:'own',center:1,title:'Welcome. Let us build your own team',next:"Let's start",body:()=>`<p>You will set up a team in your own account, load it from an Excel file, and then change every parameter to see how the margin responds. It takes about 10 minutes.</p>
<ul><li><b>Create</b> a team: a project with its people and a holiday calendar.</li><li><b>Upload</b> an Excel team sheet. A sample is provided if you do not have one.</li><li><b>Experiment</b> with Rate Card, Genus Cost, Experience, Allocation, dates, months, scenarios and Insights.</li></ul>
<p class="tour-fine">This card never blocks the page, so click, drag and type for real. Leave any time with the cross at the top; you can resume from the Guided Demo tab.</p>`},
{id:'welcome-demo',only:'demo',center:1,title:'Welcome to the demo account',next:"Let's start",body:()=>`<p>You are signed in with a ready-made demo account. It already has sample projects with simulated people, so you can start playing straight away.</p>
<ul><li>Move every slider and watch the margin respond.</li><li>Save and compare scenarios, open Insights and visit the other pages.</li></ul>
<p class="tour-fine"><b>Good to know:</b> demo accounts are shared, so other people using the same account can see your changes. Use <b>Undo</b> and <b>Reset</b> as you go; the last step puts everything back in one click.</p>`},

/* --- own account: create, upload --- */
{id:'team',only:'own',tab:'teams',title:'Step 1: Create a team',hint:'Create a team to continue',
  target:()=>$q('.wbtns .btn.primary')||$q('.head-actions .btn.primary'),place:'below',
  body:()=>`<p>A <b>team</b> is a project: its people, their rates and costs, and a holiday calendar. Click <b>${curTeam==null?'Create my team':'New team'}</b>.</p>
<p>In the form give it a name, pick the <b>holiday calendar</b> for where the team works (it decides the working days in each month) and leave <b>Start with</b> on an empty team. Choose <b>Private</b> if administrators should not see this practice team.</p>`,
  done:()=>TM.length>tourCtx.teams0,actions:[{label:'Open the form for me',fn:()=>newTeam({name:'Guided demo team'})}],
  dlg:{'New team':'Guided demo: type a name, pick a holiday calendar, then click Create team.'}},
{id:'sheet',only:'own',tab:'calc',needsTeam:1,title:'Step 2: Get an Excel team sheet',target:tbtn('imp.click'),place:'below',
  body:()=>`<p>The <b>Import</b> button reads an Excel file with one row per person. These columns are used: <code>Team Member</code>, <code>Current Experience</code>, <code>Experience Bracket</code>, <code>Role per MSA</code>, <code>Rate Card</code>, <code>Genus Cost</code> and <code>Margin</code>.</p>
<p>No file at hand? Download the sample sheet: 8 invented people with real roles. Or use your own sheet with the same columns.</p>`,
  actions:[{label:'Download the sample sheet',fn:()=>tourFile('/api/demo/sample-sheet')}]},
{id:'import',only:'own',tab:'calc',needsTeam:1,title:'Step 3: Upload the file',target:tbtn('imp.click'),place:'below',hint:'Import your Excel file',
  body:()=>`<p>Click <b>Import</b> and choose the Excel file. Every row is checked, each role is matched to the Genus cost table, and anything odd gets a warning triangle.</p>
${tourCtx.people0?`<p class="tour-warn"><b>Careful:</b> ${esc(teamName())} already has ${tourCtx.people0} ${tourCtx.people0==1?'person':'people'}, and importing <b>replaces</b> them. Use the Team selector to switch to the empty team you just made first.</p>`:'<p>Importing replaces the people in the open team. That is safe here, because this team is empty.</p>'}`,
  done:()=>T.length>0&&(T.length!=tourCtx.people0||T[0].id!==tourCtx.first0),actions:[{label:'Choose Excel file…',fn:()=>$('imp')?.click()}],
  dlg:{'Replace the current team?':'Guided demo: make sure this is your empty practice team, then click Replace team.'}},

/* --- demo account: look around --- */
{id:'switch',only:'demo',tab:'calc',title:'Pick a project',target:()=>$('tsel')?.closest('label'),place:'below',hint:'Choose another team, then come back',
  body:()=>`<p>Your demo account has several simulated projects. The <b>Team</b> selector switches between them, and every number on the page belongs to the project you pick.</p>`,
  done:()=>curTeam!==tourCtx.team0},

/* --- both: the calculator --- */
{id:'summary',tab:'calc',needsTeam:1,needsPeople:1,title:'The team at a glance',target:'#kpis',place:'below',
  body:()=>`<p>This strip is the headline. <b>Team margin</b> is revenue minus cost, divided by revenue, for everyone together. It is <b>not</b> an average of people's percentages, so higher rates count for more.</p>
<ul><li>The coloured bar shows where the margin sits: Low, Medium or Good.</li><li><b>vs baseline</b> shows how far your experiments have moved it.</li><li><b>Per hour</b> and the month totals use each person's working days.</li></ul>`},
{id:'table',tab:'calc',needsTeam:1,needsPeople:1,title:'The people table',target:()=>$('tb')?.closest('.panel'),hint:'Try the Low filter, the search box or a column heading',
  body:()=>`<p>One row per person. The dot shows how healthy the margin is. A green dot beside a name means that person has been changed from the baseline.</p>
<ul><li>Click a column heading to <b>sort</b>; click again to reverse.</li><li><b>Search</b> by name or role, or use the filters, for example the <b>Low</b> chip.</li><li>The last row totals exactly the people shown.</li></ul>`,
  done:()=>JSON.stringify([flt,sort])!==tourCtx.flt0},
{id:'pick',tab:'calc',needsTeam:1,needsPeople:1,title:'Open a person',target:()=>$('tb')?.closest('.tbl-wrap'),hint:'Click a different person',
  body:()=>`<p>Click any row. The panel on the right shows that person's numbers and the sliders you will play with next. The up and down arrow keys also walk through the list.</p>`,
  done:()=>T.length<2||sel!==tourCtx.sel0,actions:[{label:'Pick someone for me',fn:()=>{const m=T.find(x=>x.id!=sel)||T[0];if(m)pick(m.id)}}]},
{id:'rate',tab:'calc',needsTeam:1,needsPeople:1,title:'Move the Rate Card',target:tslider('rate'),place:'left',hint:'Drag the slider or type a new rate',
  body:()=>`<p><b>Rate Card</b> is what the client pays per hour for this person. Drag the slider or type a number, and watch the <b>result card</b> above it update live.</p>
<ul><li>The small mark on the slider is the <b>baseline</b>; the text beside the label shows the change.</li><li>The reading under the margin says what it would take to reach a <b>Good</b> margin.</li></ul>`,
  done:()=>tchg('rate')},
{id:'target',tab:'calc',needsTeam:1,needsPeople:1,title:'Work backwards from a margin',target:tslider('tm'),place:'left',hint:'Drag Target margin %, for example to 35',
  body:()=>`<p>Instead of guessing a rate, drag <b>Target margin %</b> to the margin you want. The <b>rate follows</b> (rate = cost ÷ (1 − margin)).</p><p>The small mark shows where <b>Good</b> starts.</p>`,
  done:()=>tchg('rate')},
{id:'genus',tab:'calc',needsTeam:1,needsPeople:1,title:'What-if on cost',target:tslider('genus'),place:'left',hint:'Change the Genus Cost',
  body:()=>`<p><b>Genus Cost</b> is what the person costs the company per hour. It is looked up from their role, but you can override it to test a what-if, such as a cheaper mix or a cost increase.</p><p>A tag marks it <b>override</b> once you change it, and <b>Reset</b> brings it back.</p>`,
  done:()=>tchg('genus')},
{id:'role',tab:'calc',needsTeam:1,needsPeople:1,title:'Change the role',target:()=>$('f-role')?.closest('.field'),place:'left',hint:'Choose a different role in the box',
  body:()=>`<p><b>Role per MSA</b> is the role and level written in the client contract, such as <code>3.2-Java</code>. It is the key into the Genus table.</p><p>Click the box, type part of a role (for example <code>3.2 java</code>) and choose one. The Genus Cost updates to match.</p>`,
  done:()=>tchg('role')},
{id:'exp',tab:'calc',needsTeam:1,needsPeople:1,title:'Experience and bracket',target:tslider('exp'),place:'left',hint:'Move Experience across a bracket edge, such as 6 years',
  body:()=>`<p><b>Experience</b> in years sets the experience <b>bracket</b> (3-6, 6-9, 9-12, 12-15). You can also pick a bracket by hand; it is then marked <b>manual</b>.</p><p>Open <b>Person details</b> to watch the bracket change.</p>`,
  done:()=>tchg('exp')},
{id:'details',tab:'calc',needsTeam:1,needsPeople:1,title:'Allocation and dates',target:()=>$q('#calc details.fold'),place:'left',hint:'Set Allocation to 0.5, or pick a Starts / Ends date',
  enter:()=>{detOpen=true;drawCalc()},
  body:()=>`<p><b>Allocation</b> is the share of the person's time on this team (1 is full time, 0.5 is half). <b>Starts</b> and <b>Ends</b> limit which days count, which is how you model someone joining or rolling off.</p>`,
  done:()=>tchg(['alloc','start_date','end_date'])},
{id:'month',tab:'calc',needsTeam:1,needsPeople:1,title:'Choose a month',target:()=>$('mo')?.closest('label'),place:'below',hint:'Change the Period to another month',
  enter:()=>{monOpen=true;drawCalc()},
  body:()=>`<p>Rates and costs are per hour, so a month's revenue is <b>rate × hours per day × working days × allocation</b>. Working days leave out weekends, the team's holidays and days outside a person's Starts and Ends.</p>`,
  done:()=>P.month!==tourCtx.month0},
{id:'reference',tab:'calc',needsTeam:1,needsPeople:1,title:'Reference points',target:()=>$('res-more'),place:'left',hint:'Click Apply beside a reference rate',
  enter:()=>{monOpen=true;drawCalc()},
  body:()=>`<p>The month section of the person panel shows the monthly figures. <b>Reference</b> lists the baseline, the <b>break-even rate</b> (below it you lose money) and the rate needed for a <b>Good</b> margin.</p><p>The <b>Apply</b> links set the rate to those values in one click.</p>`,
  done:()=>tchg('rate')},
{id:'bulk',tab:'calc',needsTeam:1,needsPeople:1,title:'Change many people at once',target:tbtn('bulkAdjust'),place:'below',hint:'Use Bulk adjust, for example Rate Card +3',
  body:()=>`<p><b>Bulk adjust</b> changes everyone currently shown in the table. Filter first (for example to one level), then apply a percentage to the Rate Card or the Genus Cost.</p><p>Try <b>Rate Card</b> with <b>3</b>. An Undo button appears right after.</p>`,
  done:()=>T.length<2||tchg(['rate','genus'],2),dlg:{'Bulk adjust':'Guided demo: leave Rate Card selected, enter 3 and click Apply.'}},
{id:'undo',tab:'calc',needsTeam:1,needsPeople:1,title:'Undo and Reset',target:()=>$('undoBtn'),place:'below',hint:'Click Undo, or put everything back with the button below',
  body:()=>`<p>Every change can be taken back. <b>Undo</b> reverses the last edit, several steps back. <b>Reset</b> in the person panel returns one person to the baseline.</p>${U.demo?'<p>Demo accounts are shared, so please put things back before you leave.</p>':''}`,
  done:()=>tourCtx.edited0==0||T.filter(isEdited).length<tourCtx.edited0||UH.length<tourCtx.uh0,
  actions:[{label:'Put everything back',fn:tourResetAll}]},
{id:'scenario',tab:'calc',needsTeam:1,needsPeople:1,title:'Save a scenario',target:()=>$q('.sc-form'),place:'above',hint:'Name it and click Save current',
  body:()=>`<p>A <b>scenario</b> saves the current numbers so you can compare them later. Make a few changes first if you like, type a name and click <b>Save current</b>.</p>${U.demo?'<p>This demo team already has ready-made scenarios in the list below.</p>':''}`,
  done:()=>S.length>tourCtx.sc0,actions:[{label:'Suggest a name',fn:()=>{const i=$('sn');if(i){i.value='My what-if';i.focus()}}}]},
{id:'compare',tab:'calc',needsTeam:1,needsPeople:1,title:'Compare before and after',target:()=>$q('#sc tr:not(.base-row) .btn.sm')||$q('#sc .btn.sm'),place:'above',hint:'Click Compare',
  body:()=>`<p><b>Compare</b> lines two versions up person by person: the baseline, the current numbers, or any scenario. The summary on top shows the change in team margin and in the month's revenue and margin.</p><p>Switch the <b>From</b> and <b>To</b> lists, and turn on <b>Show everyone</b> to include people who did not change.</p>`,
  done:()=>tourCtx.cmp,actions:[{label:'Open Compare for me',fn:()=>compareS(S.length?String(S[S.length-1].id):'baseline','current')}],
  dlg:{'Compare numbers':'Guided demo: try other From / To choices, then close this window.'}},
{id:'insights',tab:'insights',needsTeam:1,needsPeople:1,title:'Insights',target:'.page-head',place:'below',
  body:()=>`<p>Insights turns the team into charts: how many people sit in each margin band, where the revenue goes, how scenarios compare, and what happens if you add, remove or swap someone.</p><p>Two tools worth a try: <b>Sensitivity</b> (what if rates or costs move 5 to 10%) and the <b>Target solver</b> (what would it take to reach 30%?).</p>`},

/* --- own account: share and finish --- */
{id:'export',only:'own',tab:'calc',needsTeam:1,title:'Export and share',target:tbtn('exportTeam'),place:'below',
  body:()=>`<p><b>Export Excel</b> downloads the current numbers with margin and margin %. Use <b>Share</b> at the top of the page to give a colleague access, either to edit or to view only.</p>`},

/* --- demo account: the rest of the app --- */
{id:'teams',only:'demo',tab:'teams',title:'All your projects side by side',target:'.kpis',place:'below',
  body:()=>`<p>The Teams page lines up every project you can see for one month, with a combined total. <b>Open</b> jumps into a project's calculator, and the icons rename, share or delete a team.</p>`},
{id:'genus-table',only:'demo',tab:'genus',title:'The cost table behind every margin',target:'.page-head',place:'below',
  body:()=>`<p>The Genus table lists the hourly cost for every role and level, and everyone's baseline cost comes from the <b>active</b> version. A new version is uploaded, checked against the active one (changes over 25% are flagged) and approved before it goes live.</p>`},
{id:'hol',only:'demo',admin:1,tab:'hol',title:'Holiday calendars',target:'.page-head',place:'below',body:()=>`<p>Administrators keep one holiday calendar per office or region. Holidays decide each month's working days, and so every monthly figure.</p>`},
{id:'users',only:'demo',admin:1,tab:'users',title:'Users and access',target:'.page-head',place:'below',body:()=>`<p>Administrators manage who can sign in and which teams each person can see. Private teams stay hidden from administrators.</p>`},
{id:'audit',only:'demo',admin:1,tab:'audit',title:'Audit log',target:'.page-head',place:'below',body:()=>`<p>Every sign-in, edit (with old and new values), import, scenario and approval is recorded here.</p>`},
{id:'guide',tab:'guide',title:'Help is always here',target:'.guide-page .jump',place:'below',
  body:()=>`<p>The <b>Guide</b> explains every page and every number, and you can search it. There is also a short slide deck for people who prefer slides.</p>`,
  actions:[{label:'Open the overview slides',fn:()=>tourFile(DECK)}]},

{id:'finish-own',only:'own',center:1,tab:'calc',title:'You are all set',next:'Finish',
  body:()=>`<p>You created a team, loaded it from Excel and tried every control. What next?</p><ul><li>Add or edit people with <b>Add person</b>, or import your real team sheet into a new team.</li><li><b>Share</b> the team with a colleague.</li><li>Delete the practice team from the <b>Teams</b> page when you are done with it.</li></ul>`,
  actions:[{label:'Send feedback',fn:()=>feedbackDlg()}]},
{id:'finish-demo',only:'demo',center:1,tab:'calc',title:'That is the tour. Keep exploring',next:'Finish',
  body:()=>`<p>Everything in the app is open to you. A few ideas:</p><ul><li>Switch projects and run the same experiments on a bigger team.</li><li>Open <b>Insights</b> and try the target solver and the team mix what-if.</li><li>Replay the tour with another demo role, such as the administrator.</li></ul><p class="tour-fine">Demo accounts are shared. Please put things back before you leave.</p>`,
  actions:[{label:'Put everything back',fn:tourResetAll},{label:'Try another demo role',fn:()=>{tourPause();go('demo')}},{label:'Send feedback',fn:()=>feedbackDlg()}]}
];
const tourList=(mode=tour?.mode,admin=U.role=='admin')=>STEPS.filter(s=>(!s.only||s.only==mode)&&(!s.admin||admin));
const tourStep=()=>tourList().find(s=>s.id==tour?.id)||tourList()[0];
const tourIdx=()=>Math.max(0,tourList().findIndex(s=>s.id==tour?.id));

/* ---- engine ---- */
function tourDom(){
  if(!$('tour-card')){
    const h=document.createElement('div');h.id='tour-hole';h.className='tour-hole';h.hidden=true;
    const c=document.createElement('aside');c.id='tour-card';c.className='tour-card';c.setAttribute('role','region');c.setAttribute('aria-label','Guided demo');c.setAttribute('aria-live','polite');
    document.body.append(h,c)}
  if(!tourTimer)tourTimer=setInterval(tourTick,300)}
function tourHide(){clearInterval(tourTimer);tourTimer=0;$('tour-card')?.remove();$('tour-hole')?.remove()}
function tourClear(){tour=null;store.set(TOUR_KEY,'');tourHide()}
function tourPause(){if(!tour)return;tour.paused=true;tourSave();tourHide()}
function tourExit(){if(!tour)return;tourPause();toast('Guided demo paused. Resume it any time from the Guided Demo tab.','ok',7000,{label:'Open tab',fn:()=>go('demo')})}
function tourDone(){if(!tour)return;store.set('mc_tour_done_'+tour.mode,'1');tourClear();toast('Guided demo complete. Well done!')}
function tourPre(mode){tour={mode,id:tourList(mode,false)[0].id,at:Date.now(),paused:false};tourSave()}   /* set before signing in; start-up picks it up */
function tourStart(mode){tourPre(mode);tourEnter()}
function tourResume(){const t=tourLoad();tour=null;if(!t||t.paused)return;if((t.mode=='demo')!==!!U.demo)return;tour=t;tourEnter()}   /* called by start-up after the first screen is drawn */
function tourContinue(){const t=tourLoad();if(!t)return;tour=t;tour.paused=false;tourSave();tourEnter()}
async function tourGoId(id){const s=tourList().find(x=>x.id==id);if(s){tour.id=id;tourSave();await tourEnter()}}
async function tourNext(){const L=tourList(),i=tourIdx();if(i>=L.length-1){tourDone();return}tour.id=L[i+1].id;tourSave();await tourEnter()}
async function tourBack(){const L=tourList(),i=tourIdx();if(i<1)return;tour.id=L[i-1].id;tourSave();await tourEnter()}

async function tourEnter(){
  if(!tour||tourBusy)return;tourBusy=true;
  try{
    const st=tourStep();tour.id=st.id;tour.paused=false;tourSave();
    tourCtx={ok:false,lost:false,cmp:false,blocked:''};tourDom();
    $('tour-hole').hidden=true;
    if(st.tab&&tab!==st.tab)await go(st.tab);
    tourCtx.blocked=st.needsTeam&&curTeam==null?'team':st.needsPeople&&!T.length?'people':'';
    Object.assign(tourCtx,{snap:tsnap(),teams0:TM.length,team0:curTeam,people0:T.length,first0:T[0]?.id,sel0:sel,month0:P?.month,sc0:S.length,flt0:JSON.stringify([flt,sort]),uh0:UH.length,edited0:T.filter(isEdited).length});
    if(!tourCtx.blocked)try{await st.enter?.()}catch(e){console.error(e)}
    tourRender();
    setTimeout(()=>{const el=tourCtx.blocked?null:tourTarget(st);if(el){const r=el.getBoundingClientRect();if(r.top<70||r.bottom>innerHeight)el.scrollIntoView({block:r.height>innerHeight*.7?'start':'center',behavior:'smooth'})}tourTick()},150)
  }finally{tourBusy=false}}

const tourBlockMsg=b=>b=='team'?'<p>This step needs a team. Create one first (step 1) and come back.</p>':'<p>This team has no people yet. Import the sample sheet (steps 2 and 3) and come back.</p>';
function tourRender(){
  const st=tourStep(),card=$('tour-card');if(!st||!card)return;
  const L=tourList(),i=tourIdx(),ok=tourCtx.ok,bl=tourCtx.blocked,last=i==L.length-1;
  const body=bl?tourBlockMsg(bl):typeof st.body=='function'?st.body():st.body,acts=bl?[{label:bl=='team'?'Take me to the first step':'Take me to the sheet step',fn:()=>tourGoId(bl=='team'?'team':'sheet')}]:typeof st.actions=='function'?st.actions():st.actions||[];
  const wait=st.done&&!bl&&!ok;
  card.innerHTML=`<div class="tour-top"><span class="tour-count">Step ${i+1} of ${L.length}</span><span class="tour-who">${tour.mode=='demo'?'Demo account':'Your account'}</span><button class="tour-x" type="button" aria-label="Pause the guided demo" title="Pause (you can resume later)" onclick="tourExit()">${I('x',16)}</button></div>
    <div class="tour-prog" role="progressbar" aria-valuemin="1" aria-valuemax="${L.length}" aria-valuenow="${i+1}"><i style="width:${(i+1)/L.length*100}%"></i></div>
    <h3>${bl?'One thing first':esc(st.title)}</h3><div class="tour-body">${body}</div>
    ${tourCtx.lost?`<p class="tour-lost">This step points at another page. <button class="linkbtn" type="button" onclick="tourEnter()">Show me</button></p>`:''}
    ${st.done&&!bl?`<p class="tour-hint ${ok?'ok':''}">${ok?`${I('check',15)}<span>Done. Click <b>Next</b> when you are ready.</span>`:`<span><b>Your turn:</b> ${esc(st.hint||'')}</span>`}</p>`:''}
    ${acts.length?`<div class="tour-acts">${acts.map((a,k)=>`<button class="btn sm" type="button" data-a="${k}">${esc(a.label)}</button>`).join('')}</div>`:''}
    <div class="tour-nav"><button class="btn sm ghost" type="button" data-nav="back" ${i?'':'disabled'}>Back</button><button class="btn sm ${wait?'ghost':'primary'}" type="button" data-nav="next">${last?(st.next||'Finish'):wait||bl?'Skip this step':st.next||'Next'}</button></div>`;
  card.querySelectorAll('[data-a]').forEach(b=>b.onclick=()=>acts[b.dataset.a].fn());
  card.querySelector('[data-nav=back]').onclick=tourBack;card.querySelector('[data-nav=next]').onclick=tourNext}

function tourTarget(st=tourStep()){
  if(!st?.target)return null;const el=typeof st.target=='function'?st.target():$q(st.target);
  if(!el||!el.isConnected)return null;const r=el.getBoundingClientRect();return r.width||r.height?el:null}
function tourNote(dlgEl,st){   /* instruction inside a dialog the step opened (the card is hidden behind a modal) */
  const msg=st.dlg?.[dlgEl.querySelector('h2')?.textContent.trim()],host=dlgEl.querySelector('.dlg-in');
  if(msg&&host&&!host.querySelector('.tour-note')){const n=document.createElement('p');n.className='tour-note';n.textContent=msg;host.insertBefore(n,host.children[1]||null)}}
function tourTick(){
  const st=tour&&tourStep(),card=$('tour-card'),hole=$('tour-hole');if(!st||!card)return;
  const d=document.querySelector('dialog[open]');if(d?.querySelector('.cmp-head'))tourCtx.cmp=true;
  if(d){card.hidden=hole.hidden=true;tourNote(d,st);return}
  if(tab=='demo'){card.hidden=hole.hidden=true;return}   /* the Guided Demo page has its own resume banner */
  card.hidden=false;
  let ok=false;try{ok=!!st.done?.()}catch(e){}
  if(tourCtx.blocked)ok=false;
  const el=tourCtx.blocked||st.center?null:tourTarget(st),lost=!!st.target&&!el&&!st.center&&!tourCtx.blocked;
  if(ok!==tourCtx.ok||lost!==tourCtx.lost){tourCtx.ok=ok;tourCtx.lost=lost;tourRender()}
  tourPlace(el)}
function tourPlace(el){
  const card=$('tour-card'),hole=$('tour-hole'),vw=innerWidth,vh=innerHeight,m=14,st=tourStep();
  if(!el){card.className='tour-card center';card.style.left=card.style.top='';hole.className='tour-hole dim';hole.style.cssText='';hole.hidden=false;return}
  const r=el.getBoundingClientRect(),t=Math.max(r.top-6,4),l=Math.max(r.left-6,4),b=Math.min(r.bottom+6,vh-4),rt=Math.min(r.right+6,vw-4);
  hole.className='tour-hole';hole.hidden=false;Object.assign(hole.style,{top:t+'px',left:l+'px',width:Math.max(0,rt-l)+'px',height:Math.max(0,b-t)+'px'});
  if(vw<760){card.className='tour-card dock';card.style.left=card.style.top='';return}
  card.className='tour-card';
  const W=card.offsetWidth,H=card.offsetHeight,room={right:vw-rt-m-W>=m,left:l-m-W>=m,below:vh-b-m-H>=m,above:t-m-H>=m};
  const side=[st.place,'right','left','below','above'].find(s=>s&&room[s]);let x,y;
  if(side=='right'){x=rt+m;y=t}else if(side=='left'){x=l-m-W;y=t}else if(side=='below'){x=l;y=b+m}else if(side=='above'){x=l;y=t-m-H}else{x=vw-W-20;y=vh-H-20}
  card.style.left=Math.max(m,Math.min(x,vw-W-m))+'px';card.style.top=Math.max(68,Math.min(y,vh-H-m))+'px'}

/* ==========================================================================
   The Guided Demo page (a tab) and the same two choices on the sign-in page
   ========================================================================== */
const DEMO_OWN_LIST=['Create a team','Upload an Excel file','Experiment with every parameter'];
const DEMO_ACC_LIST=['Sample projects are ready to use','Play with every slider and setting','Explore scenarios, Insights and the other pages'];
async function drawDemo(){
  const c=await fetch('/auth/config').then(r=>r.json()).catch(()=>({demo:[]})),isDemo=!!U.demo,saved=tourLoad();
  const nOwn=tourList('own',false).length,nDemo=tourList('demo',false).length;
  const pm=c.demo?.find(u=>/demo1projectmanager/.test(u.email))?.email,done=m=>store.get('mc_tour_done_'+m)=='1'?'<span class="tag cur">Completed</span>':'';
  const banner=saved&&(saved.mode=='demo')===isDemo?`<section class="panel demo-resume"><div><b>You have a tour in progress</b><span>${saved.mode=='demo'?'Demo account':'Your own account'} · step ${Math.max(1,tourList(saved.mode).findIndex(s=>s.id==saved.id)+1)} of ${tourList(saved.mode).length}</span></div><div class="btns"><button class="btn primary" onclick="tourContinue()">Resume</button><button class="btn" onclick="tourStart('${saved.mode}')">Start over</button></div></section>`:'';
  $('body').innerHTML=`${head('Guided Demo','Learn the calculator by doing. Choose how you would like to try it: with your own account, or with a ready-made demo account.')}${banner}
  <div class="demo-hub">
    <section class="panel demo-opt" id="demo-own"><div class="demo-opt-head"><span class="demo-num">1</span><div><h2>Log in with your own account ${done('own')}</h2><p>Build a real team from scratch</p></div></div>
      <ol class="demo-list">${DEMO_OWN_LIST.map(t=>`<li>${t}</li>`).join('')}</ol>
      <p class="demo-meta">${nOwn} short steps · about 10 minutes</p>
      <p class="demo-note">The team you create stays in your account. You can delete it from the Teams page when you are done.</p>
      <div class="demo-act">${isDemo?`<p class="demo-warn">You are signed in with a demo account right now. This tour needs your own work email.</p><button class="btn primary" onclick="demoOwnSignIn()">Sign out and use my own account</button>`:`<button class="btn primary" onclick="tourStart('own')">${I('play',16)}Start the tour</button>`}</div></section>
    <section class="panel demo-opt" id="demo-acc"><div class="demo-opt-head"><span class="demo-num">2</span><div><h2>Log in with a demo account ${done('demo')}</h2><p>Explore ready-made sample projects</p></div></div>
      <ol class="demo-list">${DEMO_ACC_LIST.map(t=>`<li>${t}</li>`).join('')}</ol>
      <p class="demo-meta">${nDemo} short steps · about 10 minutes</p>
      <p class="demo-note">Demo accounts hold simulated data and are shared, so changes can be seen by others. ${isDemo?'':'Starting this signs you out of your own account; you can sign back in any time.'}</p>
      <div class="demo-act">${c.demo?.length?`<label class="inline-field" for="dsel"><span>Role</span><select id="dsel" class="auto">${c.demo.map(u=>`<option value="${esc(u.email)}" ${(isDemo?u.email==U.email:u.email==pm)?'selected':''}>${esc(u.label)}</option>`).join('')}</select></label><button class="btn primary" onclick="demoStart($('dsel').value)">${I('play',16)}Start with a demo account</button>`:'<p class="mu">Demo accounts are switched off on this server.</p>'}</div></section>
  </div>
  <p class="demo-foot">Prefer to read? The <button class="linkbtn" onclick="go('guide')">Guide</button> explains every page, and there is an <a href="${DECK}" target="_blank" rel="noopener" download>overview presentation</a>.</p>`}
async function demoStart(email){
  if(U.demo&&U.email==email){tourStart('demo');return}
  await flushAll();
  const r=await fetch('/auth/demo-login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
  if(!r.ok){toast('Could not open the demo account.','err');return}
  tourPre('demo');UH=[];await init()}
async function demoOwnSignIn(){await send('/auth/logout','POST');tourHide();await showLogin();demoHubPublic()}

/* the same two choices before signing in */
async function demoHubPublic(){
  const box=document.querySelector('.login');if(!box)return;
  const c=await fetch('/auth/config').then(r=>r.json()),dom=c.domain||'company.com',pm=c.demo?.find(u=>/demo1projectmanager/.test(u.email))?.email;
  const own=c.mode=='email'?`<form onsubmit="hubOwn(event)"><label for="he">Work email</label><input id="he" type="email" autocomplete="email" required placeholder="name@${esc(dom)}" value="${esc(store.get('mc_email')||'')}"><button class="btn primary block" type="submit">Log in and start the tour</button><p class="lerr" id="herr" role="alert"></p></form>`
    :c.mode=='dev'?`<form onsubmit="hubDev(event)"><label for="hu">Test user</label><select id="hu">${c.users.map(u=>`<option>${esc(u.email)}</option>`).join('')}</select><button class="btn primary block" type="submit">Log in and start the tour</button></form>`
    :`<a class="btn primary block" href="/auth/login" onclick="tourPre('own')">Sign in with company SSO and start</a>`;
  const acc=c.demo?.length?`<form onsubmit="hubDemo(event)"><label for="hd">Demo account</label><select id="hd">${c.demo.map(u=>`<option value="${esc(u.email)}" ${u.email==pm?'selected':''}>${esc(u.label)}: ${esc(u.note)}</option>`).join('')}</select><button class="btn block" type="submit">Log in with this demo account</button><p class="lerr" id="derr" role="alert"></p></form>`:'<p class="mu">Demo accounts are switched off on this server.</p>';
  box.className='login hub';
  box.innerHTML=`<button class="linkbtn hub-back" type="button" onclick="showLogin()">← Back to sign in</button><h2>Guided demo</h2><p>Learn the calculator step by step. Choose how to log in.</p>
    <div class="hub-opt"><h3><i>1</i>Log in with your own account</h3><p>Create a team, upload an Excel file and experiment with every parameter.</p>${own}</div>
    <div class="hub-opt"><h3><i>2</i>Log in with a demo account</h3><p>Sample projects are ready. Play with the parameters and explore the other features.</p>${acc}</div>`;
  (c.mode=='email'?$('he'):null)?.focus()}
async function hubOwn(e){e.preventDefault();const email=$('he').value.trim();if(await loginPost('/auth/email-login',{email},'herr')){store.set('mc_email',email);tourPre('own');init()}}
async function hubDev(e){e.preventDefault();await send('/auth/dev-login','POST',{email:$('hu').value});tourPre('own');init()}
async function hubDemo(e){e.preventDefault();if(await loginPost('/auth/demo-login',{email:$('hd').value},'derr')){tourPre('demo');init()}}
