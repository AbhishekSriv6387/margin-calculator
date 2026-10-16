
/* ==========================================================================
   Teams overview
   ========================================================================== */
async function drawTeams(){
  const A=U.role=='admin';teamMonth=teamMonth||P.month||thisMonth();
  [TM,CAL]=await Promise.all([J('/api/teams?month='+teamMonth),J('/api/calendars')]);
  const tot=TM.reduce((a,t)=>({r:a.r+t.revenue,c:a.c+(t.cost||0),n:a.n+t.people}),{r:0,c:0,n:0}),tp=tot.r?(tot.r-tot.c)/tot.r*100:null;
  $('body').innerHTML=`${head('Teams',`${A?'Every team that is not private':'The teams you have access to'}, side by side for ${monthLabel(teamMonth)}. Each team has its own people and holiday calendar.`,`<button class="btn primary" onclick="newTeam()">${I('plus',16)}New team</button>`)}
  ${ctx(`<label class="inline-field" for="tm"><span>Month</span><input type="month" id="tm" value="${teamMonth}" onchange="teamMonth=this.value;drawTeams()"></label>`)}
  <div class="kpis"><div class="kpi"><span>${A?'Teams':'Your teams'}</span><b>${TM.length}</b></div><div class="kpi"><span>People</span><b>${f(tot.n)}</b></div><div class="kpi"><span>Revenue</span><b>${f(tot.r)}</b><small>${monthLabel(teamMonth)}</small></div><div class="kpi"><span>Margin %</span><b>${tp==null?'–':f(tp,2)+'%'}</b><small>all teams combined</small></div></div>
  <section class="panel"><div class="tbl-wrap full"><table class="tbl"><thead><tr><th>Team</th><th>Business unit</th><th>Holiday calendar</th><th class="n">People</th><th class="n">Revenue</th><th class="n cost">Cost</th><th class="n">Margin %</th><th></th></tr></thead><tbody>
  ${TM.slice().sort((a,b)=>(a.unit===''?1:0)-(b.unit===''?1:0)||a.unit.localeCompare(b.unit)||a.name.localeCompare(b.name)).map(t=>`<tr class="${t.id==curTeam?'sel':''}"><td><b>${esc(t.name)}</b>${t.id==curTeam?' <span class="tag cur">open</span>':''}${!t.mine&&t.owner&&!A?` <span class="tag" title="Shared by ${esc(t.owner)}">Shared${t.can_edit?'':' · view only'}</span>`:''}${t.private?' <span class="tag lock" title="Administrators cannot see this team">Private</span>':''}</td><td class="role">${esc(t.unit)||'<span class="mu">None</span>'}</td><td class="role">${esc(t.calendar)}</td><td class="n">${t.people}</td><td class="n">${f(t.revenue)}</td>
    <td class="n cost">${f(t.cost)}</td><td class="n"><span class="pct ${t.band}">${t.margin_pct==null?'–':f(t.margin_pct,2)+'%'}</span>${chip(t.band)}</td>
    <td class="n"><button class="btn sm" onclick="openTeam(${t.id})">Open</button> ${t.can_edit?`<button class="btn sm icon ghost" aria-label="Edit ${esc(t.name)}" title="Rename, change calendar or privacy" onclick="editTeam(${t.id})">${I('edit',16)}</button>`:''}${t.mine||A?` <button class="btn sm icon ghost" aria-label="Share ${esc(t.name)}" title="Share with colleagues" onclick="shareTeam(${t.id})">${I('users',16)}</button>`:''}${A||(t.private&&t.mine)?` <button class="btn sm icon ghost danger" aria-label="Delete ${esc(t.name)}" title="Delete team" onclick="delTeam(${t.id})">${I('trash',16)}</button>`:''}</td></tr>`).join('')}
  <tr class="base-row"><td><b>${A?'All teams':'Your teams'}</b></td><td></td><td></td><td class="n">${tot.n}</td><td class="n">${f(tot.r)}</td><td class="n cost">${f(tot.c)}</td><td class="n"><span class="pct">${tp==null?'–':f(tp,2)+'%'}</span></td><td></td></tr>
  </tbody></table></div></section>`}
function welcome(){
  $('body').innerHTML=`${head('Welcome',"Let's set up your first team.")}
  <section class="panel"><div class="empty"><b>You do not have a team yet</b><p>A team is a project: its people, their rates and costs, and a holiday calendar. Create yours to see the margin, or try a sample team with practice data first. You can delete or ignore it later.</p>
  <div class="wbtns"><button class="btn primary" onclick="newTeam()">${I('plus',16)}Create my team</button><button class="btn" onclick="sampleTeam()">Try a sample team</button><button class="btn" onclick="go('demo')">${I('play',16)}Take the guided demo</button></div></div></section>
  <div class="welcome-steps">${[['Create a team','Name it and pick the holiday calendar for where the team works.'],['Add people','One by one, or import an Excel team sheet.'],['See the margin','Click a person and move the sliders. Save scenarios to compare.']].map(([h,p],i)=>`<div class="wstep"><i>${i+1}</i><b>${h}</b><p>${p}</p></div>`).join('')}</div>`}
async function sampleTeam(){const r=await send('/api/teams/sample','POST');await switchTeam(r.id,'calc');toast('Sample team ready. Click a person and move the sliders.')}
async function openTeam(id){await switchTeam(id,'calc')}
const calOpts=()=>CAL.map(c=>[c.id,c.name]);
async function newTeam(pre={}){
  const v=await dlg({title:'New team',body:'Pick the holiday calendar that matches where the team works. You can start empty or copy the people from a team you can see. As the creator you keep access to it. Choose Private if administrators should not see its data.',ok:'Create team',
    fields:[{name:'name',label:'Team name',placeholder:'e.g. Pune delivery',value:pre.name||''},{name:'unit',label:'Business unit (optional)',placeholder:'e.g. Data & AI'},{name:'calendar_id',label:'Holiday calendar',type:'select',options:calOpts()},{name:'private',label:'Who can see this team',type:'select',options:[['0','You and administrators'],['1','Private: only you (and people you are given access to), not administrators']]},{name:'copy_from',label:'Start with',type:'select',options:[['','No people (empty team)'],...TM.map(t=>[t.id,'Copy people from '+t.name])]}]});
  if(!v)return;
  const r=await send('/api/teams','POST',{name:v.name,unit:v.unit,calendar_id:+v.calendar_id,copy_from:v.copy_from?+v.copy_from:null,private:v.private=='1'});
  await switchTeam(r.id,'calc');toast(v.copy_from?'Team created with a copy of the people.':'Team created. Add people or import a team sheet.')}
async function editTeam(id){
  const t=TM.find(x=>x.id==id);
  const v=await dlg({title:'Edit team',ok:'Save',fields:[{name:'name',label:'Team name',value:t.name},{name:'unit',label:'Business unit (optional)',value:t.unit},{name:'calendar_id',label:'Holiday calendar',type:'select',options:calOpts(),value:t.calendar_id},...(t.mine?[{name:'private',label:'Who can see this team',type:'select',options:[['0','You and administrators'],['1','Private: only you (and people you are given access to), not administrators']],value:t.private?'1':'0'}]:[])]});
  if(!v)return;await send('/api/teams/'+id,'PATCH',{name:v.name,unit:v.unit,calendar_id:+v.calendar_id,...(t.mine?{private:v.private=='1'}:{})});
  if(id==curTeam)await loadPeriod(P.month);await drawTeams();toast('Team updated')}
async function delTeam(id){
  const t=TM.find(x=>x.id==id);
  if(!await dlg({title:`Delete “${t.name}”?`,body:`This permanently removes the team, its ${t.people} ${t.people==1?'person':'people'} and its saved scenarios. This cannot be undone.`,ok:'Delete team',danger:true}))return;
  await send('/api/teams/'+id,'DELETE');
  if(id==curTeam){const rest=await J('/api/teams');await switchTeam(rest[0].id)}
  await drawTeams();toast(`Deleted “${t.name}”`)}


/* ==========================================================================
   Assistant (chatbot): coming soon. A placeholder page, so people know it is planned.
   ========================================================================== */
function drawAssistant(){
  $('body').innerHTML=`${head('Assistant','Coming soon: ask questions about your team in plain English.')}
  <section class="panel"><div class="empty"><b>Chatbot assistant <span class="soon">Coming soon</span></b>
  <p>You will be able to ask things like “Which people are below 20% margin?” or “What happens to the team margin if I raise all 3.2 rates by 3%?” and get an answer from your own team's numbers.</p>
  <div class="chat-mock" aria-hidden="true"><input disabled placeholder="Ask about your team… (coming soon)"><button class="btn primary" disabled>Send</button></div>
  <div class="soon-grid">
    <article class="soon-card"><h3>The full history of every client and employee</h3>
      <p>We will keep the complete history of our clients and our people, so every conversation about rates starts from facts instead of memory.</p>
      <ul>
        <li><b>Clients:</b> every rate agreed, each revision and renewal, and how the relationship has grown over time.</li>
        <li><b>Employees:</b> cost, experience, role and allocation as they have changed, project by project.</li>
        <li><b>Stronger bargaining:</b> see what a client has accepted before, where a rate has fallen behind, and how much room there is to ask for more.</li>
      </ul></article>
    <article class="soon-card"><h3>Models that help maximise the margin</h3>
      <p>Several models will work on that history and on your live numbers to show where the margin can be improved.</p>
      <ul>
        <li><b>Rate recommendation:</b> a suggested rate for a client and role, based on what the history supports.</li>
        <li><b>Team mix:</b> the combination of levels and allocations that reaches a target margin.</li>
        <li><b>Forecasting:</b> how the margin is likely to move as rates, costs and allocations change.</li>
        <li><b>Early warning:</b> people and clients whose margin is slipping towards a loss, flagged before it happens.</li>
      </ul></article>
  </div></div></section>`}

/* ==========================================================================
   Share a team: give colleagues access, as "Can edit" or "View only"
   ========================================================================== */
async function shareTeam(id){
  await flushAll();const t=TM.find(x=>x.id==id)||{name:'Team'};
  const d=document.createElement('dialog');d.className='dlg wide';document.body.appendChild(d);d.addEventListener('close',()=>d.remove());
  const call=async(method,url,body)=>{const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
    return r.ok?null:((await r.json().catch(()=>({}))).detail||'Something went wrong.')};
  const draw=async(msg='')=>{
    const r=await fetch(`/api/teams/${id}/shares`);if(!r.ok){d.close();toast((await r.json().catch(()=>({}))).detail||'Could not load sharing.','err');return}
    const L=await r.json();
    d.innerHTML=`<div class="dlg-in cmp"><div class="cmp-head"><h2>Share “${esc(t.name)}”</h2><button class="btn ghost sm icon" aria-label="Close" onclick="this.closest('dialog').close()">${I('x',16)}</button></div>
      <p class="dlg-body">People you add can open this team and see its people, rates and costs. Choose <b>Can edit</b> or <b>View only</b>. Anyone who signs in with that email gets access.${t.private?' This team is private, so administrators still cannot see it.':''}</p>
      <form class="share-add" id="shf"><input id="she" type="email" required placeholder="colleague@company.com" aria-label="Email to share with" autocomplete="off"><select id="shp" aria-label="Permission"><option value="1">Can edit</option><option value="0">View only</option></select><button class="btn primary" type="submit">Share</button></form>
      <p class="lerr" id="sherr" role="alert">${esc(msg)}</p>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Person</th><th>Access</th><th></th></tr></thead><tbody>${L.map(x=>`<tr><td>${esc(x.email)}${x.owner?' <span class="tag">owner</span>':''}</td><td>${x.owner?'Full access':`<select class="shsel" data-e="${esc(x.email)}" aria-label="Access for ${esc(x.email)}"><option value="1" ${x.edit?'selected':''}>Can edit</option><option value="0" ${x.edit?'':'selected'}>View only</option></select>`}</td><td class="n">${x.owner?'':`<button class="btn sm danger" data-rm="${esc(x.email)}">Remove</button>`}</td></tr>`).join('')||'<tr class="empty-row"><td colspan="3">Not shared with anyone yet.</td></tr>'}</tbody></table></div></div>`;
    d.querySelector('#shf').onsubmit=async e=>{e.preventDefault();const err=await call('PUT',`/api/teams/${id}/shares`,{email:d.querySelector('#she').value.trim(),edit:d.querySelector('#shp').value=='1'});await draw(err||'')};
    d.querySelectorAll('.shsel').forEach(sl=>sl.onchange=async()=>{const err=await call('PUT',`/api/teams/${id}/shares`,{email:sl.dataset.e,edit:sl.value=='1'});await draw(err||'')});
    d.querySelectorAll('[data-rm]').forEach(b=>b.onclick=async()=>{const err=await call('DELETE',`/api/teams/${id}/shares?email=${encodeURIComponent(b.dataset.rm)}`);await draw(err||'')})};
  d.showModal();await draw()}
