
/* ==========================================================================
   Guide: a short, searchable help page for new users
   ========================================================================== */
const GUIDE=[
{id:'start',t:'Getting started',h:`<p>This tool answers one question: <b>how much margin do we keep on each person, each project and the whole team, and what happens if something changes?</b></p>
<p>Just looking around? On the sign-in page pick a <b>demo account</b> (project manager, delivery manager or administrator). Sample projects are already set up, so you can skip the steps below.</p>
<ol><li><b>Sign in</b> with your work email. The first time, your account is created automatically.</li>
<li><b>Create your team.</b> Click <b>Create my team</b>, name it, and pick the holiday calendar for where the team works. Or click <b>Try a sample team</b> to practise with invented people first.</li>
<li><b>Add people.</b> Use <b>Add person</b> one by one, or <b>Import</b> an Excel sheet (see "Import and export").</li>
<li><b>Click a person</b> in the table. Drag a slider or type a number for Rate Card, Experience or Genus Cost. The margin updates instantly.</li>
<li>Want to keep a set of changes? <b>Save current</b> as a scenario, then <b>Compare</b> it later.</li></ol>
<p class="g-tip">Changes save automatically a moment after you stop typing. There is no Save button for a person.</p>
<p>A colleague can also <b>share a team with you</b>. It then appears in your Team list, marked <b>Shared</b>. See "Sharing and privacy".</p>`},
{id:'demo',t:'Guided Demo',h:`<p>The <b>Guided Demo</b> tab teaches the tool by doing. A small card walks you through real steps on the real screens, spotlights what to click, and notices when you have done it. It never blocks the page, so you can also explore freely.</p>
<ol><li><b>Log in with your own account:</b> create a team, upload an Excel file (a sample sheet is provided) and experiment with every parameter: Rate Card, Target margin, Genus Cost, role, experience, allocation, dates, months, bulk adjust, scenarios, Compare and Insights.</li>
<li><b>Log in with a demo account:</b> pick a demo role and walk through ready-made sample projects, playing with the parameters and visiting Teams, Genus tables and the rest of the app.</li></ol>
<p class="g-tip">Click the cross on the card to pause; the Guided Demo tab then offers <b>Resume</b>. Demo accounts are shared, so use <b>Undo</b> or the <b>Put everything back</b> button before you leave.</p>`},
{id:'calc',t:'The Calculator page',h:`<h3>The people table (left)</h3>
<ul><li><b>Margin % column:</b> a colour dot shows how healthy each margin is (the same colours as the filter buttons above the table). Click any heading to sort.</li>
<li><b>vs baseline:</b> how many margin points a person has moved since the original numbers. A <b>green dot</b> beside a name means that person has been changed from the baseline.</li>
<li><b>Total row:</b> the last row adds up exactly the people shown (rate and cost x allocation, per hour). Filter to <b>Low</b> and it tells you what the low-margin group earns and costs.</li>
<li><b>Keyboard:</b> click a row, then use the <b>Up</b> and <b>Down</b> arrow keys to move through people. The panel on the right follows.</li>
<li><b>Bulk adjust</b> (above the table) changes everyone currently shown, for example <i>Rate Card +3%</i> for all 3.2 people (filter first, then click). It skips values outside the allowed range and offers <b>Undo</b>.</li></ul>
<h3>The person panel (right)</h3>
<ul><li><b>Result card:</b> the live margin, how far it is from the baseline, and a one-line <b>reading</b> of what would move it (for example how much to raise the rate to reach Good, or how much room is left).</li>
<li><b>Rate Card, Experience, Genus Cost:</b> drag a slider or type a number. The small <b>mark on each slider</b> is the baseline value, and the text beside the label shows the change, for example +120 (+4.5%). Changing Genus Cost marks it <b>override</b>; experience sets the bracket, and you can pick another bracket by hand (<b>manual</b>).</li>
<li><b>Target margin:</b> drag the margin you want and the <b>rate follows</b> (rate = cost / (1 - margin)). The mark shows where Good starts. Moving the rate moves this slider too.</li>
<li><b>Quick buttons:</b> Rate -5%, Rate +5%, <b>Break-even</b> (rate = cost) and <b>Reach 30%</b> (the lowest rate that gives a Good margin). The <b>Apply</b> links under Reference do the same.</li>
<li><b>Person details</b> (name, role, bracket, allocation, dates) and <b>This month</b> (monthly figures and reference points) are folded sections: click to open. Person details opens by itself for a new person or a role that is not in the table.</li>
<li><b>Role per MSA:</b> the role written in the client contract, for example <code>3.1-Java</code>. Click the box to see every role, or type to search. Choosing a role fills in the Genus Cost. A role that is not in the table shows a warning and you enter the cost yourself.</li>
<li><b>Allocation:</b> the share of the person's time on this team, from 0 to 1. <b>Starts / Ends:</b> optional dates that limit which days count. If they leave no working days in the chosen month, the monthly figures show 0 and the panel says why.</li>
<li><b>Reset</b> puts a person back to their original baseline numbers. <b>Delete</b> removes them from the team.</li></ul>
<p class="g-tip">The team summary on top also shows the team margin against the baseline and how many people you have edited.</p>
<p class="g-tip">If a team was shared with you as <b>View only</b>, a note appears and everything is read-only.</p>`},
{id:'numbers',t:'How the numbers are worked out',h:`<table class="tbl g-t"><thead><tr><th>Number</th><th>How it is calculated</th></tr></thead><tbody>
<tr><td>Margin</td><td>Rate Card minus Genus Cost</td></tr><tr><td>Margin %</td><td>Margin divided by Rate Card, times 100</td></tr>
<tr><td>Break-even rate</td><td>The Genus Cost. Below it you make a loss.</td></tr><tr><td>Team margin %</td><td>(Total revenue minus total cost) divided by total revenue. It is <b>not</b> the average of people's percentages, so higher rates count for more.</td></tr></tbody></table>
<p><b>Example:</b> a <code>3.1-Java</code> person at rate 2,694 with Genus Cost 1,800 has a margin of 894, which is <b>33.18%</b>. Lower the rate to 2,500 and it becomes <b>28.00%</b>.</p>
<p><b>Colours:</b> <span class="green">green</span> is a good margin, <span class="amber">amber</span> is medium, <span class="red">red</span> is low or a loss. The cut-offs (20% and 30%) are placeholders until real targets are agreed. Margin shows <b>n/a</b> when the rate is 0.</p>
<p class="g-tip">This is margin before overheads, bench time and benefits. It is not company profit.</p>`},
{id:'months',t:'Choosing a month',h:`<p>Rate and cost are per hour, so the monthly figures are worked out like this:</p>
<p class="g-eq">Monthly revenue = Rate × hours per day × working days × allocation</p>
<ul><li><b>Working days</b> are Monday to Friday, minus the holidays in the team's holiday calendar, and only the days between a person's Starts and Ends dates.</li><li><b>Hours per day</b> is a company setting (currently 8).</li><li>Change the <b>Month</b> at the top of the Calculator, Teams or Insights page to see that month.</li></ul>
<p><b>Example:</b> rate 2,694 at full time. A month with 21 working days gives 2,694 × 8 × 21 = <b>4,52,592</b>. A month with 20 working days gives <b>4,31,040</b>. The margin % is the same in both.</p>
<p class="g-tip">Months differ only by working days, holidays and start / end dates. The margin % stays the same unless you change a rate, cost or allocation.</p>`},
{id:'find',t:'Search, sort and filter',h:`<ul><li><b>Sort:</b> click a column heading. Click again to reverse.</li><li><b>Search:</b> type part of a name or role.</li><li><b>Filter:</b> by level, bracket or margin band, or show only people with warnings.</li><li><b>Warnings (⚠):</b> an unknown role, a rate below cost, a bracket that does not match experience, or an imported value that differs from the table. Open the person to read the details.</li></ul>`},
{id:'scenarios',t:'Scenarios: compare before and after',h:`<ol><li>Change some numbers, for example raise several rates by 3%.</li><li>Under <b>Scenarios</b>, type a name and click <b>Save current</b>.</li><li>Click <b>Compare</b> to see the baseline, today's numbers or a scenario against each other, per person and in total.</li><li><b>Load</b> puts a scenario's numbers back on the team. A backup is saved first, so you can click <b>Undo</b>.</li></ol>
<p>If you deleted someone by mistake, Compare lists them as removed and you can <b>Restore</b> them with their original numbers.</p>
<p class="g-tip">The <b>baseline</b> is the original data you started with. Your experiments never overwrite it.</p>`},
{id:'teams',t:'Teams',h:`<ul><li>A <b>team</b> is a project, with its own people and holiday calendar. Use the <b>Team</b> selector at the top of a page to switch.</li><li>The <b>Teams</b> page shows all your teams side by side for one month, with a combined total.</li><li><b>New team</b> creates one. You can start empty or copy the people from a team you already have, and you can mark it <b>Private</b> (see "Sharing and privacy").</li><li>Teams shared with you carry a <b>Shared</b> tag. Only an administrator can delete a team or change another person's access in <b>Users</b>; you can delete a private team you created yourself.</li></ul>`},
{id:'share',t:'Sharing and privacy',h:`<h3>Share a team</h3>
<ol><li>Open the team and click <b>Share</b> at the top of the Calculator, or the people icon on the <b>Teams</b> page.</li><li>Type a colleague's work email, choose <b>Can edit</b> or <b>View only</b>, and click <b>Share</b>. If they have not signed in yet, their account is created for them.</li><li>Change a person's access or <b>Remove</b> them any time in the same window.</li></ol>
<ul><li>Only the person who created a team (or an administrator) can share it. People you share with cannot share it further.</li><li><b>View only</b> people see every number but cannot change anything: no edits, imports, scenarios or deletes.</li><li>Sharing and un-sharing are recorded in the audit log.</li></ul>
<h3>Private teams</h3>
<ul><li>By default administrators can see every team. Choose <b>Private</b> when creating a team (or later with Edit, if you created it) and administrators cannot see it at all, not even in the audit log details. Only you and the people you share it with can open it.</li><li>This is an application setting. Anyone with direct access to the server's database could still read it, so keep real data out until IT has approved this tool.</li></ul>
<p class="g-tip">Sign-in uses your email and does not verify who you are. Do not put confidential data in the tool until company single sign-on is switched on.</p>`},
{id:'insights',t:'Insights',h:`<ul><li><b>Charts:</b> how many people are in each margin band, where the revenue goes, and how your scenarios compare.</li><li><b>Team mix:</b> headcount and margin by level, role and bracket. The what-if form shows the effect of adding, removing or swapping a person. Nothing is saved.</li><li><b>Sensitivity:</b> what happens to margin if rates or costs move 5 to 10%, and whose rate change would help most.</li><li><b>Target solver:</b> enter a margin % for the team (say 30). It suggests ways to get there and shows the rupee trade-off. These are options, not decisions.</li></ul>`},
{id:'genus',t:'Genus tables',h:`<p>The Genus table lists the cost for every role and level. Each <b>country</b> has its own table, in its own currency. A team is priced from the table of its country and all its figures are in that currency, so Indian teams use INR and a German team uses EUR. Everyone's baseline cost comes from the <b>active</b> version for their team's country.</p>
<ol><li>Click <b>Upload new table</b> and choose an Excel file with the columns <code>ServiceRegion, Country, ServiceLocation, Genus, Currency, Genus Cost</code>. One sheet can hold several countries: each becomes its own pending table, and each Genus can appear once per country. Outside the default country every row needs a currency, and a country keeps the same currency from one version to the next.</li><li>The upload becomes the <b>active</b> table for that country straight away (no approval step; other countries are not affected). Bad rows are rejected with a reason.</li><li>To undo a mistake, open an older version and click <b>Roll back to this</b>.</li><li>Click <b>Re-price</b> to update existing people to the new costs, each team from its own country's table. Costs you changed by hand are left alone.</li></ol>`},
{id:'files',t:'Import and export',h:`<ul><li><b>Import</b> reads an Excel sheet with the columns <code>Team Member, Current Experience, Experience Bracket, Role per MSA, Rate Card, Genus Cost, Margin</code>. Experience can be written as "7 years 7 months", "8.4 years" or "5".</li><li>Import <b>replaces</b> the team's people, so export first if you want a copy.</li><li>If a person appears on several rows, only the <b>first</b> row is kept, and a warning says so.</li><li>The Margin column in your file is only used as a check. The app always recalculates it.</li><li><b>Export Excel</b> downloads the current numbers with margin and margin %.</li></ul>`},
{id:'admin',admin:1,t:'For administrators',h:`<ul><li><b>Administrator sign-in</b> is not shown on the sign-in page. Add <code>?admin</code> to the address (for example <code>http://server/?admin</code>) to reveal it. It needs <code>ADMIN_EMAILS</code> and <code>ADMIN_PASSWORD</code> to be set on the server.</li><li><b>Users:</b> change roles, deactivate accounts, and choose which teams each person can see. Managers create their own accounts by signing in with their email, or when a colleague shares a team with them. You cannot change your own role. Demo accounts are fixed and cannot be edited.</li><li><b>Private teams</b> are hidden from you everywhere, and you cannot grant access to them. Re-pricing from the Genus page skips them (their owner can re-price).</li><li><b>Holidays:</b> one calendar per office or region. Add company and regional holidays here, because they change each month's working days.</li><li><b>Audit log:</b> who did what and when, with old and new values for every edit, plus imports, scenarios, sharing and approvals. Rows about a private team show only that something happened.</li></ul>`},
{id:'faq',t:'Questions and fixes',h:`<dl class="g-faq"><dt>Why does margin show "n/a"?</dt><dd>The rate is 0, so a percentage cannot be calculated.</dd>
<dt>Why is there a ⚠ next to a person?</dt><dd>Open them to read the warning. Most come from imported data that disagrees with the Genus table.</dd>
<dt>My role is not in the dropdown.</dt><dd>Type it and choose the "not in table" option, then enter the cost. Or ask an administrator to update the Genus table.</dd>
<dt>I cannot see a team a colleague mentioned.</dt><dd>You only see teams you created or were given. Ask an administrator for access.</dd>
<dt>Every month shows the same margin %.</dt><dd>That is expected. See "Choosing a month".</dd>
<dt>What does "Hide cost" do?</dt><dd>It hides cost and margin on screen, which helps when sharing your screen. It is a display setting, not a security control.</dd>
<dt>How do I share a team?</dt><dd>Open the team and click <b>Share</b>. See "Sharing and privacy".</dd>
<dt>Why can I not change anything in a team?</dt><dd>It was shared with you as <b>View only</b>. Ask the owner to switch you to <b>Can edit</b>.</dd>
<dt>What is the green dot beside a name?</dt><dd>That person's rate, cost or experience differs from the baseline. The <b>vs baseline</b> column shows the margin change in points.</dd>
<dt>The monthly figures are 0.</dt><dd>The person has no working days in that month, usually because of their Starts / Ends dates. Change the Period at the top.</dd>
<dt>Where is the administrator sign-in?</dt><dd>It is hidden. Administrators add <code>?admin</code> to the address.</dd>
<dt>Can an administrator see my team?</dt><dd>Yes, unless you marked it <b>Private</b>. Private teams are hidden from the Teams list, the audit details and every screen of the administrators. Anyone with direct access to the server's database could still read it, so keep real data out until IT has approved this tool.</dd>
<dt>Are my changes saved?</dt><dd>Yes, a moment after you stop typing. Scenarios are saved when you click Save current.</dd></dl>
<h3>Words used in this app</h3><dl class="g-faq"><dt>Rate Card</dt><dd>What the client pays per hour for a person.</dd><dt>Genus Cost</dt><dd>What the person costs the company per hour, for their role and level.</dd><dt>Role per MSA</dt><dd>The role and level written in the client's agreement, such as 3.2-Devops.</dd><dt>Baseline</dt><dd>The original numbers, before your experiments.</dd><dt>FTE</dt><dd>Full-time equivalent. 1 means full time, 0.5 means half time.</dd></dl>`}];
let guideQ='';
/* icon, one-line subtitle and short "jump to" label for each topic */
const GUIDE_META={
  demo:['play','Learn by doing, with your own account or a demo account','Guided Demo'],
  start:['target','Sign in, set up a team and see your first result','Getting started'],
  calc:['calc','What every part of the main screen does','Calculator'],
  numbers:['chart','Where each figure comes from','The numbers'],
  months:['hol','Working days, holidays, and start and end dates','Months'],
  find:['search','Find the right people quickly','Search'],
  scenarios:['compare','Try a change, then compare it with the baseline','Scenarios'],
  teams:['grid','Projects and switching between them','Teams'],
  insights:['target','Distribution, team mix, sensitivity and the target solver','Insights'],
  genus:['genus','The cost table behind every margin','Genus tables'],
  files:['download','Excel in, Excel out','Import / export'],
  admin:['users','Users, team access, approvals and the audit log','Administrators'],
  share:['users','Give colleagues access, view only or edit, and keep a team private','Sharing'],
  assistant:['chat','Ask questions in plain English (coming soon)','Chatbot (soon)'],
  faq:['info','Quick answers to common problems','Questions']};
function drawGuide(){
  const secs=GUIDE.filter(s=>!s.admin||U.role=='admin'),meta=s=>GUIDE_META[s.id]||['book','',s.t];
  $('body').innerHTML=`<div class="guide-page">${head('Guide','Everything you need to find a margin, test a change and compare the result. Written for project managers and delivery managers.')}
  <div class="jump" role="navigation" aria-label="Guide topics"><span>Jump to</span>${secs.map(s=>`<button data-g="${s.id}" onclick="guideGo('${s.id}')">${meta(s)[2]}</button>`).join('')}<input type="search" id="gq" placeholder="Search the guide" value="${esc(guideQ)}" oninput="guideFilter(this.value)" aria-label="Search the guide"></div>
  <section class="panel g-sec g-extra"><div class="g-text"><p><b>Prefer slides?</b> A short presentation explains what the tool does, how margin is worked out and who can see what. <a href="${DECK}" target="_blank" rel="noopener" download>Open the overview presentation (PPT)</a>. Have an idea or found a problem? <button class="linkbtn" type="button" onclick="feedbackDlg()">Send feedback</button>.</p></div></section>
  ${secs.map(s=>{const [ic,sub]=meta(s);return `<section class="panel g-sec" id="g-${s.id}"><div class="g-head"><span class="g-ic">${I(ic,20)}</span><div><h2>${s.t}</h2>${sub?`<p>${sub}</p>`:''}</div></div><div class="g-text">${s.h}</div></section>`}).join('')}
  <div class="panel g-none" id="g-none" hidden><p class="mu">Nothing matches your search. Try a simpler word, such as "rate" or "month".</p></div></div>`;
  guideFilter(guideQ)}
function guideGo(id){const el=$('g-'+id);if(el){el.hidden=false;el.scrollIntoView({behavior:'smooth',block:'start'})}}
function guideFilter(q){guideQ=q;const w=q.trim().toLowerCase().split(/\s+/).filter(Boolean);let n=0;
  document.querySelectorAll('.g-sec').forEach(s=>{const ok=!w.length||w.every(x=>s.textContent.toLowerCase().includes(x));s.hidden=!ok;if(ok)n++});
  document.querySelectorAll('.jump button').forEach(b=>{const s=$('g-'+b.dataset.g);b.style.display=s&&s.hidden?'none':''});$('g-none').hidden=n>0}
