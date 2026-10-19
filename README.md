# Margin What-If Calculator

An internal tool for project managers to see how **rate, cost and experience** change the margin on each person, each project and the whole team, and to compare "before" and "after" scenarios. Python (FastAPI) + SQLAlchemy (SQLite by default, PostgreSQL for a shared server) with a single-page UI. Business logic: `backend/app/calc.py` (margins, working days) and `backend/app/analysis.py` (Insights). The repository has two folders: `backend/` (the FastAPI server, tests, data and settings) and `frontend/` (the page, CSS and scripts). The backend serves the frontend, so it is still one app to deploy.

## Quick start (about 2 minutes)
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload
Open http://127.0.0.1:8000, enter any work email, then click **Create my team** or **Try a sample team**. The **Guide** tab explains everything.
To use the administrator pages, set `ADMIN_EMAILS` and `ADMIN_PASSWORD` before starting. Every setting (sign-in mode, `DATABASE_URL`, `OIDC_*`, `DEMO_DATA`, `ALLOW_SELF_APPROVAL` and more) is listed and explained in `.env.example`: copy it to `backend/.env`.

Tests (run inside `backend/`): `pip install -r requirements-dev.txt`, then `pytest` (GitLab CI runs the same two commands on every push, see `.gitlab-ci.yml`).

## Signing in (`AUTH_MODE`)
| Mode | Use it for | How it works |
|---|---|---|
| `email` (default) | Internal demos and pilots | A manager types their work email and starts. The first time, a manager account is created. **The email is not verified**, so anyone can use anyone's (non-admin) email. Keep real confidential data out. Optional `ALLOWED_EMAIL_DOMAIN`. |
| `oidc` | Real use | Company single sign-on (Azure AD / Okta / Google). Needs `OIDC_*` values from IT. New users become `DEFAULT_ROLE` (manager) and see only the teams they create or are given. *Written but not yet tested against a real identity provider.* |
| `dev` | Your own laptop | Test picker with seeded users. Never on a server. |

**Administrators** are never created by sign-in. They are listed in `ADMIN_EMAILS` and sign in with `ADMIN_PASSWORD` (the link is hidden: open the app with `?admin` on the end of the address, for example `http://server/?admin`; 5 wrong attempts per 10 minutes per address, then a pause). Without a password, no one can sign in as administrator.
The session secret is created once in `data/.session_secret` unless you set `SESSION_SECRET`.

## Demo accounts (for showcases)
On the sign-in page (email mode) a **demo account** list appears: `demoadmin@demo.example`, `demo1projectmanager@`, `demo2projectmanager@`, `demo1delmanager@` and `demo2delmanager@` (all `@demo.example`). One click signs in, with sample projects already assigned, so a viewer never has to create teams or users. Delivery managers are managers with their own sample projects.
- The demo administrator has **no password** and sees every team. That is deliberate for demos. **Set `DEMO_DATA=0` before real data goes in**: it removes the demo sign-in buttons and stops the demo accounts from signing in.
- Demo accounts are shared and cannot be edited. Changes to a demo account are shared by everyone using it. To reset the demo, stop the app and delete `data/app.db`.

## Roles and teams
- **admin:** sees every team; approves Genus tables; manages users, holiday calendars and access; deletes teams; reads the audit log.
- **manager:** creates their own teams (a creator keeps access), edits people, saves scenarios, uploads Genus tables (pending approval). Sees **only** their own teams: other teams do not exist for them (404). The same team name can be used by different managers.
- **Private teams:** when creating a team (or later via Edit, by its creator only) choose *Private*. Administrators then cannot see it anywhere: not in Teams, Calculator, Insights, Users or the audit details (those rows show only that something happened). Admins also cannot grant access to it. Only the creator, and people the creator was given access alongside, can open it; the creator can delete it. This is an app-level control: whoever can read the database file or server can still read the data. The shared demo administrator only sees simulated teams.
- **Sharing:** the creator of a team (or an admin) clicks *Share*, enters a colleague's work email and picks *Can edit* or *View only* (enforced on the server). An account is created for an email that has not signed in yet. Sharing is audited and works for private teams too.
- A **team** is a project with its own people, scenarios and holiday calendar, optionally filed under a business unit. Admins assign extra access in **Users**.

## What it does
- **Calculator:** pick a person, move Rate / Experience / Genus Cost; margin updates live. Genus changes are marked *override*; brackets can be set by hand (*manual*). Search, sort and filter the team; warnings flag unknown roles, rate below cost and mismatched imports. Each slider shows a baseline mark and its change; a **Target margin** slider sets the rate from a margin you choose; quick buttons (-5%, +5%, break-even, reach Good); a plain-words reading of what would move a person's margin; a *vs baseline* column, edited-person dots and a total row for exactly the people shown; **Bulk adjust** (a % change for everyone shown, with Undo); arrow-key navigation.
- **Months:** monthly revenue = rate x hours per day x working days x allocation. Working days = Mon-Fri minus the team calendar's holidays, limited to each person's Starts / Ends dates. One rate and one cost per person, so margin % does not change month to month unless inputs do.
- **Scenarios:** save, **Compare** any two of baseline / current / a scenario (people deleted or added since are listed and can be restored), **Load** with automatic backup and Undo.
- **Insights (managers and admins):** margin distribution, revenue-to-margin waterfall, scenario comparison, team mix by level / role / bracket with an add-remove-swap what-if, sensitivity of margin to rates and costs, and a **target solver** (rates, targeted rates capped by `solver_max_uplift_pct`, or allocation). API: `/api/insights`, `/api/solve`, `/api/mix`.
- **Genus tables:** versioned upload -> pending -> a different admin approves -> active (`ALLOW_SELF_APPROVAL=1` lets a single administrator approve their own upload, for pilots only); diff against the active table (changes over 25% flagged); rollback; re-price teams.
- **Countries and currencies:** every country has its own Genus table in its own currency (the sheet's `Country` and `Currency` columns). One upload may hold several countries and becomes one pending table per country; approving a table replaces only that country's active table, and a country keeps its currency from one version to the next. A team belongs to a country (chosen when it is created, editable later) and is priced from that country's table, so all its figures are in that currency. Totals across teams are never added across currencies: the Teams page shows one total per currency. A sheet without `Country` / `Currency` columns is read as the default country and currency (`country` and `currency` in `config.json`: India / INR).
- **Guided Demo (tab):** a step-by-step tour that runs on the real screens, with two options. *Log in with your own account*: create a team, upload an Excel file (a sample sheet is downloadable from the tour) and experiment with every parameter. *Log in with a demo account*: pick a demo role and explore the ready-made sample projects. Also reachable from the sign-in page ("New here? Take the guided demo"). Progress is kept in the browser and can be paused and resumed. The steps are plain data in the `STEPS` list in `frontend/js/demo.js`. Demo accounts are shared (see below), so the tour offers a *Put everything back* button. API: `GET /api/demo/sample-sheet`.
- **Import / export** Excel; **audit log** of logins, edits (old and new values), imports, scenarios and approvals; **Guide** page (text lives in the `GUIDE` list in `frontend/js/guide.js`).

## Front-end layout
The page is plain HTML, CSS and JavaScript: no build step, and no external fonts or CDNs, so it works on locked-down networks.

```
frontend/
  index.html          page shell: one stylesheet, eight scripts
  css/app.css         all styling, in layers: tokens, base, header/footer, panels and tables, controls, screens, responsive, print
  js/core.js          helpers, icons, dialogs and toasts, shared state, business-rule helpers, edit queue
  js/calculator.js    Calculator: people table, person panel, Role per MSA search, scenarios, compare
  js/teams.js         Teams overview, welcome screen for new accounts, team dialogs, sharing, Assistant (coming soon) page
  js/insights.js      Insights: charts, team mix, sensitivity, target solver
  js/guide.js         the in-app Guide
  js/demo.js          the Guided Demo tab and tour engine
  js/admin.js         Genus tables, Holidays, Users, Audit log
  js/app.js           sign-in, start-up, header, navigation and footer (loaded last)
  img/                logo (transparent PNG, light on dark) and favicon
```
Every screen is built the same way: page header, then a context bar for the controls that decide what you see (team, month), then panels. **Hide cost** is one switch in the top bar and is remembered in the browser. Colours and sizes are the tokens at the top of `css/app.css`: navy for the header and primary buttons, mint for highlights, status shown only as small dots. To change the logo, replace `img/nagarro-logo.png`. The server compresses responses and asks browsers to re-check static files, so a new release shows up on the next page load.

## Overview presentation and feedback
- **Slides instead of the app:** `frontend/docs/Margin_Calculator_Overview.pptx` is served at `/static/docs/Margin_Calculator_Overview.pptx`. It is linked from the sign-in page, the Guide, the footer and the account menu. To update it, replace that file.
- **Send feedback:** the footer, the account menu and the Guide have a *Send feedback* button. Each message is saved in `data/feedback.jsonl`, noted in the audit log, and emailed to `FEEDBACK_TO` (default `abhishek.srivastava04@nagarro.com`) when `SMTP_HOST` and the related settings in `.env.example` are set. With no mail server, the page offers to open the person's own mail program with the text filled in.

## Genus table format
Each country's Genus sheet has the columns `ServiceRegion, Country, ServiceLocation, Genus, Currency, Genus Cost`. One sheet can hold several countries (each becomes its own pending table); a Genus can appear once per country; any manager can upload and the table goes live at once (set `"genus_approval": true` in `config.json` to bring back admin approval by a different admin); `ServiceLocation` is stored and shown with the version but does not change pricing. Sheets without `ServiceLocation` (or without `Country` / `Currency`, the older formats) are still accepted.

## Data and privacy
- Everything is stored in `data/app.db` (SQLite) or your PostgreSQL database. It contains cost data: do not commit or share it (`.gitignore` already excludes it).
- `data/Revenue_Sheet.xlsx` and `data/Genus_Cost.xlsx` only seed a fresh database. Names in the bundled sheet are anonymised and the Genus costs are **simulated**: replace them with approved data before real use.
- On first start (email and dev modes) 6 **simulated practice projects** and the demo accounts are created. Set `DEMO_DATA=0` to skip them. Delete `data/app.db` to start fresh.
- Input limits are enforced on the server (`config.json`: `max_rate`, `max_genus`, `max_exp`, `max_alloc`, `hours_per_day`, colour thresholds `margin_warn_below` / `margin_good_from`).

## Deploying
Run behind HTTPS (for example nginx in front of `uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1 --proxy-headers`), set `HTTPS_ONLY=1`, and back up `data/app.db` (or the PostgreSQL database) before upgrades. Existing databases upgrade automatically on start.

## Roadmap
- **Chatbot assistant (coming soon):** ask questions about a team in plain English, for example "Which people are below 20% margin?".
- **History of every client and employee:** the full record of rates agreed, revisions and renewals for clients, and of cost, role and allocation changes for employees, kept over time. It supports rate negotiation and helps protect and grow the margin.
- **Models that help maximise the margin:** rate recommendation, team mix, forecasting and early warning for people and clients whose margin is slipping.

Today there is a placeholder *Assistant* tab that describes all three, and a line on the sign-in page. Nothing is wired up yet.

## Known limits
Currencies are not converted: there are no exchange rates, so teams in different countries are compared by margin %, never by adding amounts, and people cannot be copied between teams of different countries. The `max_rate` and `max_genus` limits in `config.json` apply to every currency (raise them for high-denomination currencies such as JPY or IDR). Margin is before overheads, bench time and benefits. There is one rate and one cost per person (no future rate changes, leave or promotions). Concurrent edits to the same person are last-write-wins. Hide-cost is a display setting, not a security control.
