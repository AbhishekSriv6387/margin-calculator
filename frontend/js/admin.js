
/* ==========================================================================
   Administration pages
   ========================================================================== */
const stChip=s=>`<span class="chip ${({active:'green',pending:'amber',rejected:'red'})[s]||'plain'}">${esc(s[0].toUpperCase()+s.slice(1))}</span>`;

let GV=[];   /* the versions on screen, so the approve dialog can name the country */
async function drawGenus(){
  const v=await J('/api/genus/versions'),AP=!!C.genus_approval,A=U.role=='admin'||!AP;GV=v;   /* A: may activate / roll back (everyone who can upload, unless approval is switched on) */
  $('body').innerHTML=`${head('Genus tables',`Cost tables used to price every role. Each country has its own table in its own currency, shared by all teams in that country. ${AP?'New uploads stay pending until a different admin approves them.':'An uploaded table becomes active for its country straight away.'}`,
    `<button class="btn" onclick="reprice()">${I('reset',16)}Re-price ${U.role=='admin'?'all teams':'my teams'}</button><button class="btn primary" onclick="gimp.click()">${I('upload',16)}Upload new table</button><input type="file" id="gimp" hidden accept=".xlsx" onchange="gUp(this)">`)}
  <section class="panel"><div class="panel-head"><div><h2>Versions</h2><p>Costs are only as verified as the file that was uploaded. To roll back, activate an older version.</p></div></div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Version</th><th>Country</th><th>Status</th><th class="n">Rows</th><th>Uploaded by</th><th>Report</th><th></th></tr></thead><tbody>
    ${v.map(x=>`<tr><td class="wrap"><b>#${x.id}</b> ${esc(x.label)}<span class="sub-line">${esc(x.at.slice(0,16).replace('T',' '))}</span></td>
      <td class="role">${esc(x.country)} <span class="tag ccy">${esc(x.currency)}</span>${x.locations&&x.locations.length?`<span class="sub-line">${esc(x.locations.slice(0,4).join(', '))}${x.locations.length>4?` +${x.locations.length-4} more`:''}</span>`:''}</td><td>${stChip(x.status)}${x.decided_by?`<span class="sub-line">by ${esc(x.decided_by)}</span>`:''}</td><td class="n">${x.rows}</td><td>${esc(x.by)}</td>
      <td>${x.report?.rejected_count?`<span class="amber">${x.report.rejected_count} rows rejected</span>`:'<span class="mu">Clean</span>'}</td>
      <td class="n">${x.status=='pending'||x.status=='archived'?`<button class="btn sm" onclick="diffV(${x.id})">Compare with active</button>`:''}
        ${A&&x.status=='pending'?` <button class="btn sm primary" onclick="decide(${x.id},'approve')">Approve</button> <button class="btn sm" onclick="decide(${x.id},'reject')">Reject</button>`:''}
        ${A&&x.status=='archived'?` <button class="btn sm" onclick="decide(${x.id},'approve')">Roll back to this</button>`:''}</td></tr>`).join('')}
    </tbody></table></div></section><div id="dif"></div>`}
async function gUp(i){
  if(!i.files[0])return;const fd=new FormData();fd.append('file',i.files[0]);
  const r=await fetch('/api/genus/upload',{method:'POST',body:fd}),j=await r.json().catch(()=>({}));i.value='';
  if(!r.ok)toast(typeof j.detail=='string'?j.detail:'Upload failed','err');
  else{const vs=j.versions||[],multi=vs.length>1,st=j.approval_required?'pending (waiting for approval)':'active now',sv=j.approval_required?'Uploaded as pending':'Uploaded and active';
    if(j.rejected_count)await dlg({title:'Upload received',body:`${multi?`${vs.length} tables were created, one per country (${st}):\n${vs.map(x=>`${x.country} (${x.currency}): ${x.accepted} rows`).join('\n')}\n\n`:`${j.accepted} rows accepted${vs[0]?` for ${vs[0].country} (${vs[0].currency})`:''}, ${st}. `}${j.rejected_count} rows were rejected.\n\nFirst rejected rows:\n${j.rejected.slice(0,5).join('\n')}`,ok:'Close',cancel:null});
    else toast(multi?`${sv}: ${vs.length} countries, ${j.accepted} rows`:`${sv}: ${j.accepted} rows accepted${vs[0]?` for ${vs[0].country} (${vs[0].currency})`:''}`);
    if(!j.approval_required&&j.stale_lines)await dlg({title:'Team costs are out of date',body:`${j.stale_lines} team lines now have a different table cost. Use Re-price to update them.`,ok:'Got it',cancel:null})}
  drawGenus()}
async function diffV(id){
  const d=await J(`/api/genus/versions/${id}/diff`),fl=d.changed.filter(c=>c.flag).length;
  $('dif').innerHTML=`<section class="panel"><div class="panel-head"><div><h2>Changes compared with the active ${esc(d.country)} table (${esc(d.currency)})</h2><p>Changes above ${C.genus_change_flag_pct}% are flagged for review.</p></div></div>
    <div class="stat-trio"><div class="stat"><span>Added</span><b>${d.added.length}</b></div><div class="stat"><span>Removed</span><b>${d.removed.length}</b></div><div class="stat"><span>Changed</span><b>${d.changed.length}</b></div><div class="stat"><span>Flagged</span><b class="${fl?'red':''}">${fl}</b></div></div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Genus</th><th class="n">Old</th><th class="n">New</th><th class="n">Change</th></tr></thead><tbody>
    ${d.changed.slice(0,60).map(c=>`<tr><td>${esc(c.key)}</td><td class="n">${f(c.old,2)}</td><td class="n">${f(c.new,2)}</td><td class="n ${c.flag?'red':''}">${c.pct>0?'+':''}${c.pct}%${c.flag?` <span class="warn-ic">${I('warn',15)}</span>`:''}</td></tr>`).join('')||'<tr class="empty-row"><td colspan="4">No cost changes.</td></tr>'}
    </tbody></table></div>${d.changed.length>60?`<p class="note pad">Showing the first 60 of ${d.changed.length} changes.</p>`:''}</section>`;
  $('dif').scrollIntoView({behavior:'smooth',block:'nearest'})}
async function decide(id,a){
  const ap=a=='approve',x=GV.find(y=>y.id==id)||{},cn=x.country||'this country';
  if(!await dlg({title:ap?`Make this the active ${cn} Genus table?`:'Reject this upload?',body:ap?`New calculations for ${cn} teams will use this version${x.currency?`, in ${x.currency}`:''}. The current ${cn} table is archived. Other countries are not affected.`:'This version will not be used.',ok:ap?'Make active':'Reject upload',danger:!ap}))return;
  const r=await send(`/api/genus/versions/${id}/${a}`,'POST');
  if(ap){G=await J('/api/genus'+gq());if(r.stale_lines)await dlg({title:'Team costs are out of date',body:`${r.stale_lines} team lines in ${r.country} teams now have a different table cost. Use Re-price team to update them.`,ok:'Got it',cancel:null})}
  drawGenus()}
async function reprice(){
  if(!await dlg({title:U.role=='admin'?'Re-price all teams?':'Re-price your teams?',body:`Updates Genus cost and baseline for everyone in ${U.role=='admin'?'every team':'the teams you can see'} whose cost is not overridden, using the active Genus table of that team's country.`,ok:'Re-price'}))return;
  const r=await send('/api/team/reprice','POST');UH=[];T=await J('/api/team?'+qs());toast(`${r.changed} ${r.changed==1?'person':'people'} re-priced`)}

async function drawHol(){
  CAL=await J('/api/calendars');if(!CAL.find(c=>c.id==curCal))curCal=CAL[0].id;
  const h=await J('/api/holidays?calendar_id='+curCal),c=CAL.find(x=>x.id==curCal);
  $('body').innerHTML=`${head('Holidays','Each team uses one holiday calendar, so regional teams get the right working days. Weekends are always excluded. Only fixed-date national holidays are pre-loaded, so add your company and regional holidays here.',
    `<button class="btn" onclick="newCal()">${I('plus',16)}New calendar</button>`)}
  <section class="panel"><div class="panel-head"><div><label class="inline-field" for="cal"><span>Calendar</span><select id="cal" class="auto" onchange="curCal=+this.value;drawHol()">${CAL.map(x=>`<option value="${x.id}" ${x.id==curCal?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label>
      <p>${c.teams.length?`Used by ${c.teams.map(esc).join(', ')}.`:'Not used by any team yet.'}</p></div>
      <button class="btn danger" onclick="delCal()">${I('trash',16)}Delete calendar</button></div>
    <div class="form-row"><input type="date" id="hd" aria-label="Date"><input id="hn" class="grow" maxlength="100" placeholder="Holiday name" aria-label="Holiday name" onkeydown="if(event.key==='Enter')addH()"><button class="btn primary" onclick="addH()">${I('plus',16)}Add holiday</button></div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Date</th><th>Name</th><th></th></tr></thead><tbody>
    ${h.length?h.map(x=>`<tr><td title="${x.day}">${dayLabel(x.day)}</td><td>${esc(x.name)}</td><td class="n"><button class="btn sm icon ghost danger" aria-label="Delete ${esc(x.name)}" title="Delete" onclick="delH(${x.id})">${I('trash',16)}</button></td></tr>`).join(''):'<tr class="empty-row"><td colspan="3">No holidays in this calendar yet.</td></tr>'}
    </tbody></table></div></section>`}
async function newCal(){
  const v=await dlg({title:'New holiday calendar',ok:'Create calendar',fields:[{name:'name',label:'Calendar name',placeholder:'e.g. India, Pune office'},{name:'copy_from',label:'Start with',type:'select',options:[['','An empty calendar'],...CAL.map(c=>[c.id,'Copy holidays from '+c.name])]}]});
  if(!v)return;const r=await send('/api/calendars','POST',{name:v.name,copy_from:v.copy_from?+v.copy_from:null});curCal=r.id;drawHol()}
async function delCal(){
  const c=CAL.find(x=>x.id==curCal);
  if(!await dlg({title:`Delete “${c.name}”?`,body:'This removes the calendar and all its holidays. Calendars that a team uses cannot be deleted.',ok:'Delete calendar',danger:true}))return;
  await send('/api/calendars/'+curCal,'DELETE');curCal=null;drawHol()}
async function addH(){if(!$('hd').value){toast('Choose a date first.','err');return}await send('/api/holidays','POST',{calendar_id:curCal,day:$('hd').value,name:$('hn').value});await loadPeriod(P.month||thisMonth());drawHol()}
async function delH(i){await send('/api/holidays/'+i,'DELETE');await loadPeriod(P.month||thisMonth());drawHol()}

async function drawUsers(){
  const [u,tm]=await Promise.all([J('/api/users'),J('/api/teams?month='+thisMonth())]);TM=tm;  // admins get every team
  const names=Object.fromEntries(tm.map(t=>[t.id,t.name]));
  const access=x=>x.role=='admin'?'<span class="mu">All teams</span>':!x.team_ids.length?'<span class="chip amber plain">No teams yet</span>'
    :x.team_ids.slice(0,3).map(i=>`<span class="chip plain team-chip" title="${esc(names[i])}">${esc((names[i]||'').split(':')[0])}</span>`).join(' ')+(x.team_ids.length>3?` <span class="mu">+${x.team_ids.length-3} more</span>`:'');
  $('body').innerHTML=`${head('Users and roles','Control who can see cost data, who can approve Genus tables, and which teams each person can see.')}
  <section class="panel"><div class="panel-head"><div><h2>Roles</h2></div></div>
    <div class="roles"><div><b>Admin</b><span>Everything in every team, plus approvals, users, team access, holidays and the audit log.</span></div><div><b>Manager</b><span>Full data and editing, but only for the teams assigned to them. Cannot approve Genus tables.</span></div></div></section>
  <section class="panel"><div class="panel-head"><div><h2>People with access</h2><p>Managers see nothing until you assign them teams. They cannot see, open or guess other teams.</p></div></div>
    <div class="form-row"><input type="email" id="ue" class="grow" placeholder="name@company.com" aria-label="Email"><select id="ur" class="auto" aria-label="Role"><option>manager</option><option>admin</option></select><button class="btn primary" onclick="addU()">${I('plus',16)}Add user</button></div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Email</th><th>Role</th><th>Teams they can see</th><th>Active</th></tr></thead><tbody>
    ${u.map(x=>`<tr><td>${esc(x.email)}</td><td><select class="auto" aria-label="Role for ${esc(x.email)}" onchange="patU(${x.id},{role:this.value})">${['manager','admin'].map(r=>`<option ${r==x.role?'selected':''}>${r}</option>`).join('')}</select></td>
      <td class="wrap"><span class="team-cell">${access(x)}${x.role=='admin'?'':` <button class="btn sm ghost" aria-label="Edit team access for ${esc(x.email)}" onclick="editAccess(${x.id})">${I('edit',15)}Edit</button>`}</span></td>
      <td><label class="switch"><input type="checkbox" aria-label="Active: ${esc(x.email)}" ${x.active?'checked':''} onchange="patU(${x.id},{active:this.checked})"><i></i></label></td></tr>`).join('')}
    </tbody></table></div></section>`}
async function editAccess(uid,isNew){
  const [users,tm]=await Promise.all([J('/api/users'),J('/api/teams?month='+thisMonth())]),x=users.find(z=>z.id==uid);
  const opts=tm.slice().sort((a,b)=>(a.unit===''?1:0)-(b.unit===''?1:0)||a.unit.localeCompare(b.unit)||a.name.localeCompare(b.name)).map(t=>[t.id,t.name,x.team_ids.includes(t.id),t.unit||'']);
  const v=await dlg({title:isNew?`Which teams can ${x.email} see?`:`Team access for ${x.email}`,body:'Only the ticked teams will be visible to this person. Changes take effect immediately.',ok:'Save access',cancel:isNew?'Skip for now':'Cancel',fields:[{name:'team_ids',label:'Teams',type:'checks',options:opts}]});
  if(!v)return drawUsers();
  await send(`/api/users/${uid}/teams`,'PUT',{team_ids:v.team_ids.map(Number)});toast(`Access updated for ${x.email}`);drawUsers()}
async function addU(){
  const role=$('ur').value,r=await send('/api/users','POST',{email:$('ue').value,role});await drawUsers();
  if(role!='admin')editAccess(r.id,true)}
async function patU(i,b){try{await send('/api/users/'+i,'PATCH',b)}catch(e){}drawUsers()}

const fv=v=>Array.isArray(v)&&v.length==2?`${esc(v[0])} → ${esc(v[1])}`:(v&&typeof v=='object')?Object.entries(v).map(([k,x])=>`${esc(k)}: ${fv(x)}`).join(', '):esc(v);
const fmtDetails=d=>d&&typeof d=='object'?Object.entries(d).map(([k,v])=>`<span class="kvp"><em>${esc(k)}</em>${fv(v)}</span>`).join(''):esc(d??'');
async function drawAudit(){
  const a=await J('/api/audit');
  $('body').innerHTML=`${head('Audit log','The latest 300 events: sign-ins, edits with old and new values, imports, scenarios and approvals.')}
  <section class="panel"><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Time (UTC)</th><th>User</th><th>Action</th><th>Details</th></tr></thead><tbody>
  ${a.map(x=>`<tr><td>${esc(x.ts.slice(0,19).replace('T',' '))}</td><td>${esc(x.user)}</td><td>${esc(x.action)}</td><td class="audit-d">${fmtDetails(x.details)}</td></tr>`).join('')}
  </tbody></table></div></section>`}

