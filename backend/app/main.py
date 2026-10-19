import secrets, io, json, os, re, uuid, datetime as dt
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
import openpyxl
from . import calc, auth, feedback
from .db import *
import math
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent          # the backend folder
FRONTEND = Path(os.getenv("FRONTEND_DIR") or ROOT.parent / "frontend")   # the page, CSS and scripts (served at /static)
DEFAULTS = {"country": "India", "currency": "INR", "unit_label": "per hour", "margin_warn_below": 20, "margin_good_from": 30, "hours_per_day": 8, "genus_change_flag_pct": 25, "genus_approval": False,
            "max_rate": 100000, "max_genus": 100000, "max_exp": 60, "max_alloc": 1}
CONFIG = {**DEFAULTS, **json.loads((ROOT / "config.json").read_text())}  # config.json may omit new keys
DEFAULT_COUNTRY = CONFIG["country"]  # teams and Genus tables without a country belong here (its currency is CONFIG["currency"])
SELF_APPROVE = os.getenv("ALLOW_SELF_APPROVAL") == "1"
NEEDS_APPROVAL = bool(CONFIG["genus_approval"])  # False (default): an uploaded Genus table becomes active at once; True: it waits for a different admin (maker-checker)
LEVELS = {"1.1", "2.1", "2.2", "2.3", "3.1", "3.2", "3.3", "4.1", "4.2", "4.3", "5.1", "5.2", "5.3"}
def session_secret():
    """SESSION_SECRET if set, otherwise a random secret created once and kept in data/ (never a published default)."""
    if os.getenv("SESSION_SECRET"): return os.environ["SESSION_SECRET"]
    p = ROOT / "data" / ".session_secret"; p.parent.mkdir(exist_ok=True)
    if not p.exists(): p.write_text(secrets.token_hex(32)); os.chmod(p, 0o600)
    return p.read_text().strip()
app = FastAPI(title="Margin What-If Calculator")
app.add_middleware(GZipMiddleware, minimum_size=1024)  # the page, scripts and large API answers are sent compressed
app.add_middleware(SessionMiddleware, secret_key=session_secret(), https_only=os.getenv("HTTPS_ONLY") == "1", same_site="lax")
app.include_router(auth.router)
app.include_router(feedback.router)
ANY, MGR, ADM = Depends(auth.current_user), Depends(auth.require("admin", "manager")), Depends(auth.require("admin"))

# ---------- helpers ----------
def read_rows(src):
    try: rows = list(openpyxl.load_workbook(src, data_only=True).active.iter_rows(values_only=True))
    except Exception: raise HTTPException(400, "Could not read the file. Please upload a valid .xlsx workbook.")
    if not rows: raise HTTPException(400, "The file is empty.")
    if len(rows) > 2001: raise HTTPException(400, "The file has more than 2000 rows.")
    hdr = [str(h or "").strip().lower() for h in rows[0]]
    return [dict(zip(hdr, r)) for r in rows[1:] if any(c is not None for c in r)]

CUR = re.compile(r"^[A-Z]{3}$")
def clean_country(v): return " ".join(str(v or "").split())[:60]
def same_country(a, b): return clean_country(a).casefold() == clean_country(b).casefold()

def parse_genus(src):
    """Reads a Genus sheet: ServiceRegion, Country, ServiceLocation, Genus, Currency, Genus Cost.
    Returns ({country: {"country", "currency", "rates": {key: (label, cost)}, "locations": {key: service location}}}, [(country, message), ...]).
    One sheet may hold several countries. A sheet without Country / Currency columns (the older format) is the default country in the default currency."""
    groups, bad = {}, []
    for i, r in enumerate(read_rows(src), start=2):
        label = str(r.get("genus") or "").strip(); country = clean_country(r.get("country")) or DEFAULT_COUNTRY
        loc = " ".join(str(r.get("servicelocation") or r.get("service location") or "").split())[:80]
        g = groups.setdefault(country.casefold(), {"country": country, "rows": []})
        cur = str(r.get("currency") or "").strip().upper()
        if not cur and same_country(country, DEFAULT_COUNTRY): cur = CONFIG["currency"]
        try: cost = float(r.get("genus cost"))
        except (TypeError, ValueError): bad.append((g["country"], f"Row {i} ({label}): cost not a number")); continue
        m = re.match(r"^(\d\.\d)-(.+)$", label)
        if not m or m.group(1) not in LEVELS: bad.append((g["country"], f"Row {i} ({label}): bad Genus format or level")); continue
        if not (cost > 0): bad.append((g["country"], f"Row {i} ({label}): cost must be > 0")); continue
        if not cur: bad.append((g["country"], f"Row {i} ({label}): currency missing for {g['country']}")); continue
        if not CUR.match(cur): bad.append((g["country"], f"Row {i} ({label}): currency must be a 3-letter code such as INR or EUR")); continue
        g["rows"].append((i, label, cost, cur, loc))
    out = {}
    for k, g in groups.items():
        if not g["rows"]: continue  # every row of this country was rejected: the reasons are in `bad`
        cur = Counter(r[3] for r in g["rows"]).most_common(1)[0][0]; rt, lc = {}, {}
        for i, label, cost, c, loc in g["rows"]:
            if c != cur: bad.append((g["country"], f"Row {i} ({label}): currency {c} differs from {cur}, used by the other {g['country']} rows")); continue
            key = calc.norm_role(label)
            if key in rt: bad.append((g["country"], f"Row {i} ({label}): duplicate Genus for {g['country']}" + (f" (service location {loc})" if loc else "") + ", each Genus can appear once per country")); continue
            rt[key] = (label, cost); lc[key] = loc
        out[k] = {"country": g["country"], "currency": cur, "rates": rt, "locations": lc}
    bad.sort(key=lambda x: int(re.match(r"Row (\d+)", x[1]).group(1)))
    return out, bad

def rates(db, vid): return {r.key: (r.label, r.cost) for r in db.query(GenusRate).filter_by(version_id=vid)}
def tcountry(t): return (t.country if t is not None and t.country else None) or DEFAULT_COUNTRY
def canon_country(db, name):
    """The spelling already in use for this country (any capitals), otherwise the cleaned name."""
    name = clean_country(name) or DEFAULT_COUNTRY
    for (c,) in db.query(GenusVersion.country).distinct():
        if c and c.casefold() == name.casefold(): return c
    return name
def active_version(db, country=None): return db.query(GenusVersion).filter_by(status="active", country=canon_country(db, country or DEFAULT_COUNTRY)).first()
def genus_dict(db, country=None):
    """The active Genus table of one country (the default country when none is given)."""
    v = active_version(db, country)
    return {k: {"genus": l, "cost": c} for k, (l, c) in rates(db, v.id).items()} if v else {}
def country_currency(db, country):
    v = active_version(db, country)
    return v.currency if v and v.currency else (CONFIG["currency"] if same_country(country, DEFAULT_COUNTRY) else None)
def active_countries(db):
    res = []
    for v in db.query(GenusVersion).filter_by(status="active"):
        res.append({"country": v.country or DEFAULT_COUNTRY, "currency": v.currency or CONFIG["currency"], "rows": db.query(GenusRate).filter_by(version_id=v.id).count(), "version_id": v.id})
    return sorted(res, key=lambda c: (not same_country(c["country"], DEFAULT_COUNTRY), c["country"].casefold()))
def need_country(db, name):
    """A team's country must have an approved Genus table, because that table prices the team."""
    c = canon_country(db, name) if name else DEFAULT_COUNTRY
    if not active_version(db, c): raise HTTPException(400, f"There is no approved Genus table for {c} yet. An administrator must approve one first.")
    return c
def ranges_for(db, country):
    """Slider ranges for a team. The default currency keeps the classic ranges (None); any other currency is scaled from that country's own table."""
    v = active_version(db, country); cur = country_currency(db, country)
    if not v or cur in (None, CONFIG["currency"]): return None
    cs = sorted(c for _, c in rates(db, v.id).values())
    if not cs: return None
    step = 10 ** (math.floor(math.log10(cs[-1])) - 2); up = lambda x: round(math.ceil(x / step - 1e-9) * step, 6); dn = lambda x: round(math.floor(x / step) * step, 6)
    glo, ghi = dn(cs[0] * 0.5), up(cs[-1] * 1.3)
    return {"genus": [glo, ghi, round(step, 6)], "rate": [glo, up(ghi * 1.5), round(step, 6)]}
def new_person_defaults(db, t):
    """Starting rate and Genus cost for 'Add person'. Unchanged for the default currency; otherwise the middle of the country's own table at a 28% margin."""
    v = active_version(db, tcountry(t))
    if not v or country_currency(db, tcountry(t)) in (None, CONFIG["currency"]): return 2500, 1800
    cs = sorted(c for _, c in rates(db, v.id).values()); g = cs[len(cs) // 2]
    return round(g / 0.72, 2), g

BRACKETS = ("3-6", "6-9", "9-12", "12-15")
def iso(d): return d.isoformat() if d else None

def out(m):
    d = {c: getattr(m, c) for c in ["id", "name", "role", "exp", "rate", "bracket", "bracket_override", "genus", "genus_override", "alloc", "base", "warnings", "team_id"]}
    d["start_date"], d["end_date"] = iso(m.start_date), iso(m.end_date)
    w, g = CONFIG["margin_warn_below"], CONFIG["margin_good_from"]
    d["band"] = calc.band(calc.margin(m.rate, m.genus)[1], w, g)
    return d

# ---------- validation (server side, so every client is protected) ----------
def num(v, label, lo=None, hi=None, gt=None):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise HTTPException(400, f"{label} must be a number")
    if gt is not None and v <= gt: raise HTTPException(400, f"{label} must be greater than {gt}")
    if lo is not None and v < lo: raise HTTPException(400, f"{label} cannot be less than {lo:g}")
    if hi is not None and v > hi: raise HTTPException(400, f"{label} cannot be more than {hi:g}")
    return float(v)
def text_field(v, label, mx=100, required=False):
    if not isinstance(v, str): raise HTTPException(400, f"{label} must be text")
    v = v.strip()
    if required and not v: raise HTTPException(400, f"{label} is required")
    if len(v) > mx: raise HTTPException(400, f"{label} must be {mx} characters or fewer")
    return v
def date_field(v, label):
    if v in (None, ""): return None
    if isinstance(v, dt.datetime): return v.date()
    if isinstance(v, dt.date): return v
    try: return dt.date.fromisoformat(str(v))
    except ValueError: raise HTTPException(400, f"{label} must be a date (YYYY-MM-DD)")
def month_field(month):
    try: y, m = map(int, str(month).split("-")); assert 1 <= m <= 12 and 2000 <= y <= 2100
    except Exception: raise HTTPException(400, "month must be YYYY-MM")
    return y, m

def clean_person_patch(m, b):
    """Validates only the fields that actually change (so an old bad value never blocks an unrelated edit)."""
    new = {}
    for k in FIELDS:
        if k not in b: continue
        v = b[k]
        if k in ("start_date", "end_date"):
            v = date_field(v, "Start date" if k == "start_date" else "End date")
            if v == getattr(m, k): continue
        else:
            if v == getattr(m, k): continue
            if k == "name": v = text_field(v, "Name", 100, True)
            elif k == "role": v = text_field(v, "Role", 100)
            elif k == "rate": v = num(v, "Rate card", gt=0, hi=CONFIG["max_rate"])
            elif k == "genus": v = num(v, "Genus cost", lo=0, hi=CONFIG["max_genus"])
            elif k == "exp": v = num(v, "Experience", lo=0, hi=CONFIG["max_exp"])
            elif k == "alloc": v = num(v, "Allocation", lo=0, hi=CONFIG["max_alloc"])
            elif k == "bracket":
                if v not in BRACKETS: raise HTTPException(400, "Bracket must be one of " + ", ".join(BRACKETS))
            elif k in ("bracket_override", "genus_override"):
                if not isinstance(v, bool): raise HTTPException(400, f"{k} must be true or false")
        new[k] = v
    s, e = new.get("start_date", m.start_date), new.get("end_date", m.end_date)
    if s and e and e < s: raise HTTPException(400, "End date cannot be before the start date")
    return new

def import_team(src, genus, team_id=None):
    members, seen, done = [], {}, set()
    rows = read_rows(src)
    for r in rows:
        k = str(r.get("team member") or "").strip().lower(); seen[k] = seen.get(k, 0) + 1
    for i, r in enumerate(rows, start=2):
        k = str(r.get("team member") or "").strip().lower()
        if k and k in done: continue
        done.add(k); w = []
        if k and seen[k] > 1: w.append(f"{seen[k]-1} duplicate row(s) for this person ignored (first row kept)")
        role = str(r.get("role per msa") or "").strip()
        try: rate = float(r.get("rate card") or 0)
        except (TypeError, ValueError): raise HTTPException(400, f"Row {i}: Rate Card is not a number")
        exp = calc.parse_exp(r.get("current experience")); g = genus.get(calc.norm_role(role))
        try: gsrc = float(r["genus cost"]) if r.get("genus cost") not in (None, "") else None
        except (TypeError, ValueError): raise HTTPException(400, f"Row {i}: Genus Cost is not a number")
        if rate < 0 or rate > CONFIG["max_rate"]: raise HTTPException(400, f"Row {i}: Rate Card must be between 0 and {CONFIG['max_rate']:g}")
        if rate == 0: w.append("Rate card missing or zero")
        if g: cost = g["cost"]
        else: cost = gsrc or 0; w.append("Role not in Genus table - using sheet value, edit manually")
        if g and gsrc is not None and abs(gsrc - g["cost"]) > 0.5: w.append(f"Sheet genus {gsrc} differs from table {g['cost']}")
        if rate < cost: w.append("Rate below Genus cost (negative margin)")
        if exp is None: w.append("Experience unreadable")
        elif exp > CONFIG["max_exp"]: raise HTTPException(400, f"Row {i}: Experience cannot be more than {CONFIG['max_exp']:g} years")
        bs, bd = calc.norm_bracket(r.get("experience bracket")), calc.bracket(exp)
        if bs and bd and bs != bd: w.append(f"Bracket {bs} differs from derived {bd}")
        sm = r.get("margin")
        if isinstance(sm, (int, float)) and rate and abs(calc.margin(rate, cost)[1] - sm * 100) > 0.5: w.append(f"Sheet margin {sm*100:.2f}% does not match calculation")
        sd, ed = date_field(r.get("start date"), f"Row {i}: Start date"), date_field(r.get("end date"), f"Row {i}: End date")
        if sd and ed and ed < sd: raise HTTPException(400, f"Row {i}: End date is before the start date")
        e = round(exp or 0, 2)
        members.append(dict(id=uuid.uuid4().hex[:8], name=str(r.get("team member") or f"Row {i}")[:100], role=role[:100], rate=rate, exp=e, bracket=bs or bd,
            bracket_override=bool(bs and bs != bd), genus=cost, genus_override=g is None, alloc=1, warnings=w, start_date=sd, end_date=ed,
            base=dict(rate=rate, exp=e, genus=cost, bracket=bs or bd)))
    return members

def replace_team(db, members, team_id):
    """Replaces only this team's people (other teams are untouched)."""
    db.query(TeamLine).filter_by(team_id=team_id).delete()
    t = db.get(Team, team_id)
    if t is not None: t.removed = []  # a fresh import starts a new baseline
    top = db.query(TeamLine).count()
    for i, m in enumerate(members): db.add(TeamLine(pos=top + i, team_id=team_id, **m))
    db.commit()

# ---------- teams + calendars (lookup helpers) ----------
def team_or_404(db, tid):
    t = db.get(Team, tid) if tid else db.query(Team).order_by(Team.id).first()  # no id -> first team (keeps old clients working)
    if not t: raise HTTPException(404, "Team not found")
    return t
# ---------- team access: admins see every team; everyone else only the teams assigned to them ----------
def access_ids(db, u):
    """The set of team ids this user may see. Admins see every team EXCEPT private ones they were not given access to.
    The shared demo administrator only ever sees the built-in simulated teams, never ones people create."""
    own = {r.team_id for r in db.query(TeamAccess).filter_by(user_id=u.id)}
    if u.role != "admin": return own
    q = db.query(Team.id).filter(Team.private.isnot(True))
    if auth.is_demo(u.email): q = q.filter(Team.created_by.in_(["system", "simulated data"]))
    return {r[0] for r in q} | own
def can_see(db, u, team_id):
    ids = access_ids(db, u); return ids is None or team_id in ids
def can_write(db, u, team_id):
    r = db.query(TeamAccess).filter_by(user_id=u.id, team_id=team_id).first()
    return not (r and r.edit is False)  # a team shared with you as "view only" cannot be changed
def team_for(db, u, tid, write=False):
    t = _team_for(db, u, tid)
    if write and not can_write(db, u, t.id): raise HTTPException(403, "This team was shared with you as view only.")
    return t
def _team_for(db, u, tid):
    """The team a request refers to, if this user may see it. An inaccessible team looks exactly like a missing one (404), so its existence is not revealed."""
    ids = access_ids(db, u)
    if tid:
        t = db.get(Team, tid)
        if not t or (ids is not None and tid not in ids): raise HTTPException(404, "Team not found")
        return t
    q = db.query(Team).order_by(Team.id)
    if ids is not None: q = q.filter(Team.id.in_(ids or {-1}))
    t = q.first()
    if not t: raise HTTPException(403, "No teams are assigned to you yet. Ask an admin for access.")
    return t
def visible_teams(db, u):
    ids = access_ids(db, u); q = db.query(Team).order_by(Team.id)
    return q.all() if ids is None else (q.filter(Team.id.in_(ids)).all() if ids else [])
def line_for(db, u, pid, write=False):
    m = db.get(TeamLine, pid)
    if not m or not can_see(db, u, m.team_id): raise HTTPException(404, "Not found")
    if write and not can_write(db, u, m.team_id): raise HTTPException(403, "This team was shared with you as view only.")
    return m
def scen_for(db, u, sid, write=False):
    s = db.get(Scenario, sid)
    if not s or not can_see(db, u, s.team_id): raise HTTPException(404, "Scenario not found")
    if write and not can_write(db, u, s.team_id): raise HTTPException(403, "This team was shared with you as view only.")
    return s

def cal_or_404(db, cid):
    c = db.get(Calendar, cid) if cid else db.query(Calendar).order_by(Calendar.id).first()
    if not c: raise HTTPException(404, "Holiday calendar not found")
    return c
def holiday_set(db, cal_id): return {d.day for d in db.query(CalendarDay).filter_by(calendar_id=cal_id)}
def lines(db, t): return db.query(TeamLine).filter_by(team_id=t.id).order_by(TeamLine.pos).all()
def cur_month(): return dt.datetime.utcnow().strftime("%Y-%m")
def line_rows(ls, hs, y, m):
    return [{"rate": l.rate, "genus": l.genus, "alloc": l.alloc, "days": calc.person_days(y, m, hs, l.start_date, l.end_date)} for l in ls]
def band_of(p): return calc.band(p, CONFIG["margin_warn_below"], CONFIG["margin_good_from"])

# ---------- config / period ----------
@app.get("/api/config")
def config(u=ANY): return CONFIG
@app.get("/api/period")
def period(month: str, team_id: int | None = None, u=ANY, db=Depends(get_db)):
    y, m = month_field(month); t = team_for(db, u, team_id); hs = holiday_set(db, t.calendar_id)
    n, hl = calc.business_days(y, m, hs)
    days = {l.id: calc.person_days(y, m, hs, l.start_date, l.end_date) for l in lines(db, t)}  # per person: honours start / end dates
    c = tcountry(t); return {"month": month, "team_id": t.id, "business_days": n, "holidays": hl, "hours_per_day": CONFIG["hours_per_day"], "days": days,
                             "country": c, "currency": country_currency(db, c) or CONFIG["currency"], "ranges": ranges_for(db, c)}

# ---------- holiday calendars (regional) ----------
@app.get("/api/calendars")
def calendars(u=ANY, db=Depends(get_db)):
    teams_by = {}
    for t in visible_teams(db, u): teams_by.setdefault(t.calendar_id, []).append(t.name)  # only names of teams this user may see
    return [{"id": c.id, "name": c.name, "days": db.query(CalendarDay).filter_by(calendar_id=c.id).count(), "teams": teams_by.get(c.id, [])} for c in db.query(Calendar).order_by(Calendar.id)]
@app.post("/api/calendars")
def calendar_add(b: dict, u=ADM, db=Depends(get_db)):
    name = text_field(b.get("name", ""), "Calendar name", 60, True)
    if db.query(Calendar).filter(Calendar.name.ilike(name)).first(): raise HTTPException(400, "A calendar with this name already exists")
    c = Calendar(name=name); db.add(c); db.commit()
    if b.get("copy_from"):
        for d in db.query(CalendarDay).filter_by(calendar_id=cal_or_404(db, b["copy_from"]).id): db.add(CalendarDay(calendar_id=c.id, day=d.day, name=d.name))
        db.commit()
    log(db, u, "calendar_add", "calendar", c.id, {"name": name}); return {"id": c.id}
@app.delete("/api/calendars/{cid}")
def calendar_del(cid: int, u=ADM, db=Depends(get_db)):
    c = cal_or_404(db, cid)
    if db.query(Team).filter_by(calendar_id=cid).count(): raise HTTPException(400, "This calendar is used by a team. Move the team to another calendar first.")
    if db.query(Calendar).count() <= 1: raise HTTPException(400, "At least one calendar is required")
    db.query(CalendarDay).filter_by(calendar_id=cid).delete(); log(db, u, "calendar_delete", "calendar", cid, {"name": c.name}); db.delete(c); db.commit(); return {"ok": True}
@app.get("/api/holidays")
def holidays(calendar_id: int | None = None, u=ANY, db=Depends(get_db)):
    c = cal_or_404(db, calendar_id)
    return [{"id": h.id, "day": h.day.isoformat(), "name": h.name, "calendar_id": c.id} for h in db.query(CalendarDay).filter_by(calendar_id=c.id).order_by(CalendarDay.day)]
@app.post("/api/holidays")
def holiday_add(b: dict, u=ADM, db=Depends(get_db)):
    c = cal_or_404(db, b.get("calendar_id")); d = date_field(b.get("day"), "Date")
    if not d: raise HTTPException(400, "Date is required")
    if db.query(CalendarDay).filter_by(calendar_id=c.id, day=d).first(): raise HTTPException(400, "This date is already in the calendar")
    name = text_field(b.get("name", ""), "Holiday name", 100)
    db.add(CalendarDay(calendar_id=c.id, day=d, name=name)); db.commit(); log(db, u, "holiday_add", "holiday", d.isoformat(), {"calendar": c.name, "name": name}); return {"ok": True}
@app.delete("/api/holidays/{hid}")
def holiday_del(hid: int, u=ADM, db=Depends(get_db)):
    h = db.get(CalendarDay, hid); log(db, u, "holiday_delete", "holiday", hid, {"day": str(h.day) if h else None})
    if h: db.delete(h); db.commit()
    return {"ok": True}

# ---------- teams ----------
@app.get("/api/teams")
def teams(month: str | None = None, u=ANY, db=Depends(get_db)):
    """Overview of every team you can see, for one month."""
    y, m = month_field(month or cur_month()); res = []
    for t in visible_teams(db, u):
        ls = lines(db, t); r = calc.month_rollup(line_rows(ls, holiday_set(db, t.calendar_id), y, m), CONFIG["hours_per_day"])
        cal = db.get(Calendar, t.calendar_id); d = {"id": t.id, "name": t.name, "unit": t.unit or "", "country": tcountry(t), "currency": country_currency(db, tcountry(t)) or CONFIG["currency"], "simulated": bool(t.simulated), "private": bool(t.private), "mine": t.created_by == u.email, "can_edit": can_write(db, u, t.id), "owner": t.created_by if "@" in (t.created_by or "") else "", "calendar_id": t.calendar_id, "calendar": cal.name if cal else "", "people": len(ls), "headcount": r["headcount"], "revenue": r["revenue"], "cost": r["cost"], "margin": r["margin"], "margin_pct": r["margin_pct"], "band": band_of(r["margin_pct"])}
        res.append(d)
    return res
@app.post("/api/teams")
def team_create(b: dict, u=MGR, db=Depends(get_db)):
    name = text_field(b.get("name", ""), "Team name", 80, True)
    if any(x.name.lower() == name.lower() for x in visible_teams(db, u)): raise HTTPException(400, "You already have a team with this name")
    cal = cal_or_404(db, b.get("calendar_id")); unit = text_field(b.get("unit") or "", "Business unit", 60); private = b.get("private") is True
    src = team_for(db, u, b["copy_from"]) if b.get("copy_from") else None  # you can only copy from a team you can see
    country = need_country(db, b.get("country"))
    if src and not same_country(tcountry(src), country): raise HTTPException(400, f"You can only copy people from a team in {country}: rates and costs in another country use another currency.")
    t = Team(name=name, calendar_id=cal.id, unit=unit or None, created_by=u.email, private=private, country=country); db.add(t); db.commit()
    if u.role != "admin" or private: db.add(TeamAccess(user_id=u.id, team_id=t.id)); db.commit()  # the creator keeps access to what they create
    copied = 0
    if src:  # start from another team's people
        top = db.query(TeamLine).count()
        for i, l in enumerate(lines(db, src)):
            db.add(TeamLine(id=uuid.uuid4().hex[:8], pos=top + i, team_id=t.id, **{k: getattr(l, k) for k in ["name", "role", "exp", "rate", "bracket", "bracket_override", "genus", "genus_override", "alloc", "base", "warnings", "start_date", "end_date"]})); copied += 1
        db.commit()
    log(db, u, "team_add", "team", t.id, {"name": name, "calendar": cal.name, "country": country, "copied_people": copied, "private": private}, team=t); return {"id": t.id}
SAMPLE_PEOPLE = [("3.1-Java", 5.5, 2450), ("3.2-Java", 8, 2720), ("3.3-Java", 10.5, 2900), ("3.1-Devops", 6, 2450), ("2.3-Custom", 4.5, 2300), ("3.2-CRM-SALESFORCE", 7.5, 2700), ("3.1-Python", 5, 2400), ("3.2-Data-Science", 8.5, 2760)]
@app.post("/api/teams/sample")
def team_sample(u=MGR, db=Depends(get_db)):
    """A ready-made practice team (invented people, real Genus costs) so a first-time user can explore straight away."""
    mine = {x.name.lower() for x in visible_teams(db, u)}; name, n = "Sample team", 1
    while name.lower() in mine: n += 1; name = f"Sample team {n}"
    cal = db.query(Calendar).order_by(Calendar.id).first()
    if not cal: raise HTTPException(400, "No holiday calendar exists yet. Ask an administrator.")
    t = Team(name=name, calendar_id=cal.id, created_by=u.email, simulated=True, country=DEFAULT_COUNTRY); db.add(t); db.commit()
    if u.role != "admin": db.add(TeamAccess(user_id=u.id, team_id=t.id)); db.commit()
    g, top = genus_dict(db), db.query(TeamLine).count()
    for i, (role, exp, rate) in enumerate(SAMPLE_PEOPLE):
        x = g.get(calc.norm_role(role)); cost = x["cost"] if x else round(rate * 0.7, 2); b = calc.bracket(exp)
        db.add(TeamLine(id=uuid.uuid4().hex[:8], pos=top + i, team_id=t.id, name=f"Sample person {i+1}", role=role, exp=exp, rate=rate, bracket=b, bracket_override=False,
                        genus=cost, genus_override=x is None, alloc=1, base=dict(rate=rate, exp=exp, genus=cost, bracket=b), warnings=[]))
    db.commit(); log(db, u, "team_sample", "team", t.id, {"name": name}); return {"id": t.id}
@app.get("/api/demo/sample-sheet")
def demo_sample_sheet(u=ANY, db=Depends(get_db)):
    """A small Excel team sheet (invented people, real roles) in exactly the format Import reads. Used by the Guided Demo so a first-time user has a file to upload."""
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Team"
    ws.append(["Team Member", "Current Experience", "Experience Bracket", "Role per MSA", "Rate Card", "Genus Cost", "Margin"])
    g = genus_dict(db)
    for i, (role, exp, rate) in enumerate(SAMPLE_PEOPLE):
        x = g.get(calc.norm_role(role)); cost = x["cost"] if x else round(rate * 0.7, 2)
        ws.append([f"Demo person {i+1}", exp, calc.bracket(exp), role, rate, cost, round(calc.margin(rate, cost)[1] / 100, 4)])
    b = io.BytesIO(); wb.save(b); b.seek(0)
    return StreamingResponse(b, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=sample_team_sheet.xlsx"})
@app.patch("/api/teams/{tid}")
def team_edit(tid: int, b: dict, u=MGR, db=Depends(get_db)):
    t = team_for(db, u, tid, True); ch = {}
    if "unit" in b and (b["unit"] or None) != t.unit:
        unit = text_field(b["unit"] or "", "Business unit", 60); ch["unit"] = [t.unit, unit or None]; t.unit = unit or None
    if "name" in b and b["name"] != t.name:
        name = text_field(b["name"], "Team name", 80, True)
        if any(x.name.lower() == name.lower() and x.id != t.id for x in visible_teams(db, u)): raise HTTPException(400, "You already have a team with this name")
        ch["name"] = [t.name, name]; t.name = name
    if "private" in b and (b["private"] is True) != bool(t.private):
        if t.created_by != u.email: raise HTTPException(403, "Only the person who created a team can change its privacy.")
        t.private = b["private"] is True; ch["private"] = [not t.private, t.private]
        if t.private and not db.query(TeamAccess).filter_by(user_id=u.id, team_id=t.id).first(): db.add(TeamAccess(user_id=u.id, team_id=t.id))
    if "country" in b and b["country"] and not same_country(b["country"], tcountry(t)):
        c = need_country(db, b["country"]); ch["country"] = [tcountry(t), c]; t.country = c  # rates and costs already in the team are NOT converted
    if "calendar_id" in b and b["calendar_id"] != t.calendar_id:
        cal = cal_or_404(db, b["calendar_id"]); ch["calendar"] = [t.calendar_id, cal.id]; t.calendar_id = cal.id
    if ch: db.commit(); log(db, u, "team_edit", "team", t.id, ch, team=t)
    return {"ok": True}
@app.delete("/api/teams/{tid}")
def team_delete(tid: int, u=MGR, db=Depends(get_db)):
    t = db.get(Team, tid)
    if u.role != "admin" and not (t and t.private and t.created_by == u.email): raise HTTPException(403, "Only an administrator can delete a team.")
    t = team_for(db, u, tid)  # a private team is invisible (404) to admins who were not given access
    if db.query(Team).count() <= 1: raise HTTPException(400, "You cannot delete the last team")
    n = db.query(TeamLine).filter_by(team_id=t.id).delete(); db.query(Scenario).filter_by(team_id=t.id).delete(); db.query(TeamAccess).filter_by(team_id=t.id).delete()
    log(db, u, "team_delete", "team", t.id, {"name": t.name, "people_removed": n}, team=t); db.delete(t); db.commit(); return {"ok": True}

# ---------- sharing a team with other people in the app ----------
def owner_team(db, u, tid):
    t = team_for(db, u, tid)
    if u.role != "admin" and t.created_by != u.email: raise HTTPException(403, "Only the person who created this team (or an administrator) can share it.")
    return t
@app.get("/api/teams/{tid}/shares")
def shares(tid: int, u=MGR, db=Depends(get_db)):
    t = owner_team(db, u, tid)
    rows = db.query(TeamAccess, User).join(User, User.id == TeamAccess.user_id).filter(TeamAccess.team_id == t.id).all()
    return [{"email": x.email, "name": x.name, "edit": a.edit is not False, "owner": x.email == t.created_by} for a, x in rows if not auth.is_demo(x.email)]
@app.put("/api/teams/{tid}/shares")
def share_set(tid: int, b: dict, u=MGR, db=Depends(get_db)):
    t = owner_team(db, u, tid); email = text_field(b.get("email", ""), "Email", 200, True).lower(); edit = b.get("edit") is not False
    if not auth.EMAIL_RE.match(email) or auth.is_demo(email): raise HTTPException(400, "Enter a valid work email address.")
    dom = os.getenv("ALLOWED_EMAIL_DOMAIN", "").lower().lstrip("@")
    if dom and not email.endswith("@" + dom): raise HTTPException(400, f"Use an @{dom} email address.")
    if email == u.email or email == t.created_by: raise HTTPException(400, "The team owner already has full access.")
    x = db.query(User).filter_by(email=email).first()
    if x and not x.active: raise HTTPException(400, "That account has been disabled.")
    if not x: x = User(email=email, name=email.split("@")[0], role="manager"); db.add(x); db.commit(); log(db, u, "user_add", "user", email, {"role": "manager", "via": "share"})
    a = db.query(TeamAccess).filter_by(user_id=x.id, team_id=t.id).first()
    if a: a.edit = edit
    else: db.add(TeamAccess(user_id=x.id, team_id=t.id, edit=edit))
    db.commit(); log(db, u, "team_share", "team", t.id, {"team": t.name, "with": email, "edit": edit}, team=t); return {"ok": True}
@app.delete("/api/teams/{tid}/shares")
def share_remove(tid: int, email: str, u=MGR, db=Depends(get_db)):
    t = owner_team(db, u, tid); email = email.strip().lower()
    if email == t.created_by: raise HTTPException(400, "You cannot remove the team owner.")
    x = db.query(User).filter_by(email=email).first()
    if x: db.query(TeamAccess).filter_by(user_id=x.id, team_id=t.id).delete(); db.commit(); log(db, u, "team_unshare", "team", t.id, {"team": t.name, "with": email}, team=t)
    return {"ok": True}

# ---------- people in a team ----------
@app.get("/api/team")
def team(team_id: int | None = None, u=ANY, db=Depends(get_db)): return [out(m) for m in lines(db, team_for(db, u, team_id))]
FIELDS = ["name", "role", "exp", "rate", "bracket", "bracket_override", "genus", "genus_override", "alloc", "start_date", "end_date"]
@app.post("/api/team")
def team_add(team_id: int | None = None, u=MGR, db=Depends(get_db)):
    t = team_for(db, u, team_id, True); n = (db.query(TeamLine).count()); rate0, genus0 = new_person_defaults(db, t); b = dict(rate=rate0, exp=5, genus=genus0, bracket="3-6")
    m = TeamLine(id=uuid.uuid4().hex[:8], pos=n, team_id=t.id, name="New person", role="", rate=rate0, exp=5, bracket="3-6", genus=genus0, genus_override=True, alloc=1, base=b, warnings=[])
    db.add(m); db.commit(); log(db, u, "person_add", "team", m.id, {"team": t.name}, team=t); return out(m)
@app.patch("/api/team/{pid}")
def team_patch(pid: str, b: dict, u=MGR, db=Depends(get_db)):
    m = line_for(db, u, pid, True)
    new = clean_person_patch(m, b); ch = {}
    for k, v in new.items():
        old = getattr(m, k); ch[k] = [iso(old) if isinstance(old, dt.date) else old, iso(v) if isinstance(v, dt.date) else v]; setattr(m, k, v)
    if ch: db.commit(); log(db, u, "person_edit", "team", pid, {"name": m.name, "changes": ch}, team=db.get(Team, m.team_id))
    return out(m)
@app.delete("/api/team/{pid}")
def team_del(pid: str, u=MGR, db=Depends(get_db)):
    m = line_for(db, u, pid, True)
    if m:
        t = db.get(Team, m.team_id); log(db, u, "person_delete", "team", pid, {"name": m.name}, team=t)
        if t is not None:  # keep the numbers so Compare can still show who was removed and what that did to the margin
            gone = {k: getattr(m, k) for k in ("id", "name", "role", "exp", "rate", "genus", "bracket", "bracket_override", "genus_override", "alloc", "base", "warnings")}
            t.removed = [*(t.removed or []), {**gone, "start_date": iso(m.start_date), "end_date": iso(m.end_date)}][-200:]
        db.delete(m); db.commit()
    return {"ok": True}
@app.post("/api/team/restore/{pid}")
def team_restore(pid: str, team_id: int | None = None, u=MGR, db=Depends(get_db)):
    """Brings a removed person back with their original numbers, dates and baseline (same id, so saved scenarios line up again)."""
    t = team_for(db, u, team_id, True); gone = list(t.removed or []); r = next((x for x in gone if x["id"] == pid), None)
    if not r or db.get(TeamLine, pid): raise HTTPException(404, "That person was not removed from this team")
    g = genus_dict(db, tcountry(t)).get(calc.norm_role(r.get("role") or ""))
    m = TeamLine(id=pid, pos=db.query(TeamLine).count(), team_id=t.id, name=r["name"], role=r.get("role") or "", exp=r["exp"], rate=r["rate"], bracket=r["bracket"],
                 bracket_override=r.get("bracket_override", r["bracket"] != calc.bracket(r["exp"])), genus=r["genus"],
                 genus_override=r.get("genus_override", not (g and abs(g["cost"] - r["genus"]) < 0.005)), alloc=r.get("alloc", 1), base=r["base"], warnings=r.get("warnings") or [],
                 start_date=dt.date.fromisoformat(r["start_date"]) if r.get("start_date") else None, end_date=dt.date.fromisoformat(r["end_date"]) if r.get("end_date") else None)
    t.removed = [x for x in gone if x["id"] != pid]; db.add(m); db.commit(); log(db, u, "person_restore", "team", pid, {"name": m.name, "team": t.name}, team=t); return out(m)
@app.post("/api/team/import")
async def team_import(file: UploadFile = File(...), team_id: int | None = None, u=MGR, db=Depends(get_db)):
    t = team_for(db, u, team_id, True)
    ms = import_team(io.BytesIO(await file.read()), genus_dict(db, tcountry(t))); replace_team(db, ms, t.id)
    log(db, u, "team_import", "team", t.id, {"team": t.name, "rows": len(ms), "file": file.filename}, team=t); return team(t.id, u, db)
@app.post("/api/team/reprice")
def reprice(team_id: int | None = None, u=MGR, db=Depends(get_db)):
    """Re-prices every team you can see, or just team_id. Each team is priced from the active Genus table of its own country."""
    n, cache = 0, {}
    ids = [team_for(db, u, team_id, True).id] if team_id else [t.id for t in visible_teams(db, u) if can_write(db, u, t.id)]
    owner = {t.id: tcountry(t) for t in db.query(Team).filter(Team.id.in_(ids or [-1]))}
    for m in db.query(TeamLine).filter(TeamLine.team_id.in_(ids or [-1])):
        c = owner.get(m.team_id, DEFAULT_COUNTRY); g = cache.get(c) or cache.setdefault(c, genus_dict(db, c))
        x = g.get(calc.norm_role(m.role))
        if x and not m.genus_override and abs(x["cost"] - m.genus) > 0.005:
            m.genus = x["cost"]; m.base = {**m.base, "genus": x["cost"]}; n += 1
    db.commit(); log(db, u, "team_reprice", "team", team_id or "", {"changed": n}); return {"changed": n}
@app.get("/api/export")
def export(team_id: int | None = None, u=MGR, db=Depends(get_db)):
    t = team_for(db, u, team_id); wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Margin"
    ws.append(["Team Member", "Experience (yrs)", "Bracket", "Role per MSA", "Rate Card", "Genus Cost", "Margin", "Margin %", "Genus overridden", "Allocation (FTE)", "Start date", "End date"])
    for m in lines(db, t):
        a, p = calc.margin(m.rate, m.genus)
        ws.append([m.name, m.exp, m.bracket, m.role, m.rate, m.genus, round(a, 2), None if p is None else round(p, 2), "Yes" if m.genus_override else "No", m.alloc, iso(m.start_date), iso(m.end_date)])
    b = io.BytesIO(); wb.save(b); b.seek(0); log(db, u, "export", "team", t.id, {"team": t.name}, team=t)
    fn = re.sub(r"[^A-Za-z0-9_-]+", "_", t.name).strip("_") or "team"
    return StreamingResponse(b, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=margin_export_{fn}.xlsx"})

# ---------- multi-month forecast ----------
# ---------- scenarios (managers) ----------
def snapshot_vals(ms): return [{k: getattr(m, k) for k in ("id", "name", "rate", "exp", "genus", "bracket", "alloc")} for m in ms]
def make_scenario(db, t, u, name, auto=False):
    ms = lines(db, t)
    d = {"vals": snapshot_vals(ms), "people": len(ms), **calc.rollup([{"rate": m.rate, "genus": m.genus, "alloc": m.alloc} for m in ms])}
    s = Scenario(name=name, created_by=u.email, data=d, team_id=t.id, auto=auto); db.add(s); db.commit()
    if auto:  # keep only the 5 newest safety backups per team
        olds = db.query(Scenario).filter_by(team_id=t.id, auto=True).order_by(Scenario.id.desc()).offset(5).all()
        for o in olds: db.delete(o)
        db.commit()
    return s
@app.get("/api/scenarios")
def scen(team_id: int | None = None, u=MGR, db=Depends(get_db)):
    t = team_for(db, u, team_id)
    return [{"id": s.id, "name": s.name, "by": s.created_by, "at": s.created_at.isoformat(timespec="minutes"), "auto": bool(s.auto), **{k: v for k, v in s.data.items() if k != "vals"}}
            for s in db.query(Scenario).filter_by(team_id=t.id).order_by(Scenario.id)]
@app.post("/api/scenarios")
def scen_add(b: dict, team_id: int | None = None, u=MGR, db=Depends(get_db)):
    t = team_for(db, u, team_id, True); name = text_field(b.get("name") or "Scenario", "Scenario name", 100) or "Scenario"
    s = make_scenario(db, t, u, name); log(db, u, "scenario_save", "scenario", s.id, {"name": name, "team": t.name}, team=t); return {"id": s.id}
@app.delete("/api/scenarios/{sid}")
def scen_del(sid: int, u=MGR, db=Depends(get_db)):
    s = scen_for(db, u, sid, True)
    if s: log(db, u, "scenario_delete", "scenario", sid, {"name": s.name}, team=db.get(Team, s.team_id)); db.delete(s); db.commit()
    return {"ok": True}
@app.post("/api/scenarios/{sid}/apply")
def scen_apply(sid: int, backup: bool = True, u=MGR, db=Depends(get_db)):
    s = scen_for(db, u, sid, True); t = team_for(db, u, s.team_id); g = genus_dict(db, tcountry(t))
    bk = make_scenario(db, t, u, f"Before loading “{s.name}”", auto=True) if backup else None  # safety net: Undo = load this backup
    for v in s.data["vals"]:
        m = db.get(TeamLine, v["id"])
        if m and m.team_id == t.id:
            m.rate, m.exp, m.genus, m.bracket = v["rate"], v["exp"], v["genus"], v["bracket"]
            if v.get("alloc") is not None: m.alloc = v["alloc"]  # older scenarios did not store allocation
            x = g.get(calc.norm_role(m.role)); m.genus_override = not (x and abs(x["cost"] - v["genus"]) < 0.005)
    db.commit(); log(db, u, "scenario_apply", "scenario", sid, {"name": s.name, "backup_id": bk.id if bk else None}, team=t); return {"team": team(t.id, u, db), "undo_id": bk.id if bk else None, "team_id": t.id}
@app.get("/api/scenarios/compare")
def scen_compare(a: str, b: str, team_id: int | None = None, month: str | None = None, u=MGR, db=Depends(get_db)):
    """Per-person and total comparison of any two states: a scenario id, 'current' (live numbers) or 'baseline'.
    A person who exists on only one side (removed or added since) is listed as such and counts in that side's totals."""
    t = team_for(db, u, team_id); ls = lines(db, t); y, mo = month_field(month or cur_month()); hs = holiday_set(db, t.calendar_id)
    live = {m.id: m for m in ls}; gone = {r["id"]: r for r in (t.removed or [])}
    meta = {m.id: (m.name, m.role, m.start_date, m.end_date) for m in ls}  # id -> name, role, start, end
    for i, r in gone.items(): meta[i] = (r["name"], r.get("role", ""), dt.date.fromisoformat(r["start_date"]) if r.get("start_date") else None, dt.date.fromisoformat(r["end_date"]) if r.get("end_date") else None)
    def state(spec):
        if spec == "current": return "Current numbers", {m.id: dict(rate=m.rate, genus=m.genus, alloc=m.alloc) for m in ls}
        if spec == "baseline":  # allocation is not part of a baseline; people removed since then are part of it
            d = {m.id: dict(rate=m.base["rate"], genus=m.base["genus"], alloc=m.alloc) for m in ls}
            d.update({i: dict(rate=r["base"]["rate"], genus=r["base"]["genus"], alloc=r.get("alloc", 1)) for i, r in gone.items()})
            return "Baseline", d
        try: s = db.get(Scenario, int(spec))
        except ValueError: s = None
        if not s or s.team_id != t.id: raise HTTPException(404, "Scenario not found in this team")
        for v in s.data["vals"]: meta.setdefault(v["id"], (v.get("name") or "Removed person", "", None, None))
        return s.name, {v["id"]: dict(rate=v["rate"], genus=v["genus"], alloc=v["alloc"] if v.get("alloc") is not None else (live[v["id"]].alloc if v["id"] in live else gone.get(v["id"], {}).get("alloc", 1))) for v in s.data["vals"]}
    (na, sa), (nb, sb) = state(a), state(b); rows, ta, tb, seen = [], [], [], set()
    side = lambda p: None if p is None else {**p, "margin_pct": calc.margin(p["rate"], p["genus"])[1]}
    for i in [m.id for m in ls] + list(sa) + list(sb):
        if i in seen or (i not in sa and i not in sb): continue
        seen.add(i); name, role, sd, ed = meta[i]; d = calc.person_days(y, mo, hs, sd, ed); pa, pb = sa.get(i), sb.get(i)
        rows.append({"id": i, "name": name, "role": role, "a": side(pa), "b": side(pb), "changed": pa != pb, "status": "removed" if pb is None else "added" if pa is None else None, "restorable": i in gone and i not in live})
        if pa: ta.append({**pa, "days": d})
        if pb: tb.append({**pb, "days": d})
    ra, rb = calc.month_rollup(ta, CONFIG["hours_per_day"]), calc.month_rollup(tb, CONFIG["hours_per_day"])
    return {"a": {"name": na, **ra}, "b": {"name": nb, **rb}, "rows": rows, "month": f"{y}-{mo:02d}"}

# ---------- Genus versions: upload -> pending -> admin approves (maker-checker) -> active; rollback = re-activate.
# Every country has its own table in its own currency: approving a version replaces only that country's active table. ----------
@app.get("/api/genus")
def genus(team_id: int | None = None, country: str | None = None, u=MGR, db=Depends(get_db)):
    """The active table used by a team (team_id), or by a country, or by the default country."""
    c = tcountry(team_for(db, u, team_id)) if team_id else (canon_country(db, country) if country else DEFAULT_COUNTRY)
    return genus_dict(db, c)
@app.get("/api/genus/countries")
def genus_countries(u=ANY, db=Depends(get_db)): return active_countries(db)
@app.get("/api/genus/versions")
def versions(u=MGR, db=Depends(get_db)):
    return [{"id": v.id, "label": v.label, "status": v.status, "by": v.created_by, "at": v.created_at.isoformat(), "decided_by": v.decided_by, "rows": db.query(GenusRate).filter_by(version_id=v.id).count(), "report": v.report,
             "country": v.country or DEFAULT_COUNTRY, "currency": v.currency or CONFIG["currency"], "locations": (v.report or {}).get("locations", [])}
            for v in db.query(GenusVersion).order_by(GenusVersion.id.desc())]
def activate(db, v, u, was):
    """Makes version v the active table of its country (the current one is archived) and counts team lines whose table cost changed."""
    country = v.country or DEFAULT_COUNTRY; act = active_version(db, country)
    if act and act.id != v.id: act.status = "archived"  # only this country's table is replaced
    v.status, v.decided_by, v.decided_at = "active", u.email, now(); db.commit()
    g = genus_dict(db, country); tids = [t.id for t in db.query(Team) if same_country(tcountry(t), country)]
    stale = sum(1 for m in db.query(TeamLine).filter(TeamLine.team_id.in_(tids or [-1])) if (x := g.get(calc.norm_role(m.role))) and not m.genus_override and abs(x["cost"] - m.genus) > 0.005)
    log(db, u, "genus_rollback" if was == "archived" else "genus_approve", "genus_version", v.id, {"label": v.label, "country": country, "team_lines_with_new_cost": stale, "auto": was == "pending"}); return stale
@app.post("/api/genus/upload")
async def genus_upload(file: UploadFile = File(...), u=MGR, db=Depends(get_db)):
    groups, bad = parse_genus(io.BytesIO(await file.read())); made = []
    for g in groups.values():
        country = canon_country(db, g["country"]); last = db.query(GenusVersion).filter(GenusVersion.country == country, GenusVersion.currency.isnot(None)).order_by(GenusVersion.id.desc()).first()
        if last and last.currency != g["currency"]:  # a country keeps its currency: a different one would silently corrupt every team priced from it
            bad += [(g["country"], f"{lbl}: {country} is priced in {last.currency}, but this sheet says {g['currency']}") for lbl, _ in g["rates"].values()]; continue
        mine = [m for c, m in bad if c.casefold() == g["country"].casefold()]
        report = {"accepted": len(g["rates"]), "rejected": mine[:50], "rejected_count": len(mine), "country": country, "currency": g["currency"], "locations": sorted({x for x in g["locations"].values() if x})}
        v = GenusVersion(label=file.filename, status="pending", country=country, currency=g["currency"], created_by=u.email, report=report)
        db.add(v); db.commit()
        for k, (l, c) in g["rates"].items(): db.add(GenusRate(version_id=v.id, key=k, label=l, cost=c, location=g["locations"].get(k) or None))
        db.commit(); log(db, u, "genus_upload", "genus_version", v.id, report)
        stale = None if NEEDS_APPROVAL else activate(db, v, u, "pending")  # no approval step: the upload is live straight away
        made.append({"id": v.id, "country": country, "currency": g["currency"], "accepted": len(g["rates"]), "rejected_count": len(mine), "status": v.status, "stale_lines": stale})
    allbad = [m for _, m in bad]
    if not made: raise HTTPException(400, "No valid rows. " + "; ".join(allbad[:5]))
    return {"id": made[0]["id"], "accepted": sum(m["accepted"] for m in made), "rejected": allbad[:50], "rejected_count": len(allbad), "versions": made, "approval_required": NEEDS_APPROVAL,
            "stale_lines": sum(m["stale_lines"] or 0 for m in made)}
@app.get("/api/genus/versions/{vid}/diff")
def diff(vid: int, u=MGR, db=Depends(get_db)):
    v = db.get(GenusVersion, vid)
    if not v: raise HTTPException(404, "Version not found")
    new, act = rates(db, vid), active_version(db, v.country); old = rates(db, act.id) if act else {}; th = CONFIG["genus_change_flag_pct"]
    ch = [{"key": new[k][0], "old": old[k][1], "new": new[k][1], "pct": round((new[k][1] - old[k][1]) / old[k][1] * 100, 1)} for k in new if k in old and abs(new[k][1] - old[k][1]) > 0.005]
    for c in ch: c["flag"] = abs(c["pct"]) > th
    return {"country": v.country or DEFAULT_COUNTRY, "currency": v.currency or CONFIG["currency"], "added": [new[k][0] for k in new if k not in old], "removed": [old[k][0] for k in old if k not in new], "changed": sorted(ch, key=lambda c: -abs(c["pct"]))}
@app.post("/api/genus/versions/{vid}/approve")
def approve(vid: int, u=MGR, db=Depends(get_db)):
    v = db.get(GenusVersion, vid)
    if not v or v.status not in ("pending", "archived"): raise HTTPException(400, "Version cannot be activated")
    if NEEDS_APPROVAL and u.role != "admin": raise HTTPException(403, "Only an administrator can approve a Genus table")
    if NEEDS_APPROVAL and v.status == "pending" and v.created_by == u.email and not SELF_APPROVE: raise HTTPException(403, "A different admin must approve your upload")
    country = v.country or DEFAULT_COUNTRY; stale = activate(db, v, u, v.status)
    return {"ok": True, "stale_lines": stale, "country": country}
@app.post("/api/genus/versions/{vid}/reject")
def reject(vid: int, u=MGR, db=Depends(get_db)):
    if NEEDS_APPROVAL and u.role != "admin": raise HTTPException(403, "Only an administrator can reject a Genus table")
    v = db.get(GenusVersion, vid)
    if not v or v.status != "pending": raise HTTPException(400)
    v.status, v.decided_by, v.decided_at = "rejected", u.email, now(); db.commit(); log(db, u, "genus_reject", "genus_version", vid); return {"ok": True}

# ---------- admin ----------
@app.get("/api/audit")
def audit(u=ADM, db=Depends(get_db)):
    return [{"ts": a.ts.isoformat(timespec="seconds"), "user": a.user, "action": a.action, "entity": "private team" if a.hidden else a.entity, "id": "" if a.hidden else a.entity_id,
             "details": {"hidden": "Private team: details are not shown to administrators"} if a.hidden else a.details} for a in db.query(Audit).order_by(Audit.id.desc()).limit(300)]
@app.get("/api/users")
def users(u=ADM, db=Depends(get_db)):
    acc, vis = {}, access_ids(db, u)
    for r in db.query(TeamAccess):
        if r.team_id in vis: acc.setdefault(r.user_id, []).append(r.team_id)
    return [{"id": x.id, "email": x.email, "name": x.name, "role": x.role, "active": x.active, "team_ids": sorted(acc.get(x.id, []))} for x in db.query(User).order_by(User.id)]
def set_access(db, actor, user, team_ids):
    """Replaces the teams a user may see (admins always see all, so nothing is stored for them)."""
    ids = {int(i) for i in team_ids if isinstance(i, int) and not isinstance(i, bool)}
    if len(ids) != len(team_ids): raise HTTPException(400, "team_ids must be a list of team ids")
    vis = access_ids(db, actor)  # you can only grant or take away access to teams you can see yourself
    valid = {t.id: t.name for t in db.query(Team).filter(Team.id.in_(ids or {-1}))}
    if set(valid) != ids or not ids <= vis: raise HTTPException(400, "One or more teams do not exist")
    cur = {r.team_id for r in db.query(TeamAccess).filter_by(user_id=user.id)} & vis  # private teams this admin cannot see are left untouched
    names = {t.id: t.name for t in db.query(Team)}
    for tid in ids - cur: db.add(TeamAccess(user_id=user.id, team_id=tid))
    for tid in cur - ids: db.query(TeamAccess).filter_by(user_id=user.id, team_id=tid).delete()
    db.commit()
    if ids != cur: log(db, actor, "user_access", "user", user.email, {"added": [names[i] for i in sorted(ids - cur)], "removed": [names.get(i, str(i)) for i in sorted(cur - ids)]})
@app.put("/api/users/{uid}/teams")
def user_teams(uid: int, b: dict, u=ADM, db=Depends(get_db)):
    x = db.get(User, uid)
    if not x: raise HTTPException(404, "User not found")
    if auth.is_demo(x.email): raise HTTPException(400, "Demo accounts cannot be changed.")
    if not isinstance(b.get("team_ids"), list): raise HTTPException(400, "team_ids must be a list")
    set_access(db, u, x, b["team_ids"]); return {"ok": True}
@app.post("/api/users")
def user_add(b: dict, u=ADM, db=Depends(get_db)):
    if b.get("role") not in ("admin", "manager"): raise HTTPException(400, "bad role")
    e = text_field(b.get("email", ""), "Email", 200, True).lower()
    if not re.match(r"^[^@\s]+@[^@\s]+$", e): raise HTTPException(400, "Enter a valid email address")
    dom = os.getenv("ALLOWED_EMAIL_DOMAIN")
    if dom and not e.endswith("@" + dom): raise HTTPException(400, f"Email must be a @{dom} address")
    if db.query(User).filter_by(email=e).first(): raise HTTPException(400, "Exists")
    nu = User(email=e, name=text_field(b.get("name", e), "Name", 100) or e, role=b["role"]); db.add(nu); db.commit(); log(db, u, "user_add", "user", e, {"role": b["role"]})
    if isinstance(b.get("team_ids"), list): set_access(db, u, nu, b["team_ids"])
    return {"ok": True, "id": nu.id}
@app.patch("/api/users/{uid}")
def user_patch(uid: int, b: dict, u=ADM, db=Depends(get_db)):
    x = db.get(User, uid)
    if not x: raise HTTPException(404)
    if x.id == u.id: raise HTTPException(400, "You cannot change your own role or access")
    if auth.is_demo(x.email): raise HTTPException(400, "Demo accounts cannot be changed.")
    ch = {}
    if b.get("role") in ("admin", "manager") and b["role"] != x.role: ch["role"] = [x.role, b["role"]]; x.role = b["role"]
    if "active" in b and bool(b["active"]) != x.active: ch["active"] = [x.active, bool(b["active"])]; x.active = bool(b["active"])
    db.commit(); log(db, u, "user_edit", "user", x.email, ch); return {"ok": True}

# ---------- seed + static ----------
# ---------- insights: charts, mix, sensitivity, target solver (managers and admins only: they contain cost) ----------
from . import analysis
def insight_rows(db, u, team_id, month):
    t = team_for(db, u, team_id); y, mo = month_field(month or cur_month()); hs = holiday_set(db, t.calendar_id); ls = lines(db, t)
    return t, y, mo, hs, ls, [{"id": l.id, "name": l.name, "role": l.role, "bracket": l.bracket, "rate": l.rate, "genus": l.genus, "alloc": l.alloc,
                               "days": calc.person_days(y, mo, hs, l.start_date, l.end_date)} for l in ls]
@app.get("/api/insights")
def insights(team_id: int | None = None, month: str | None = None, u=MGR, db=Depends(get_db)):
    t, y, mo, hs, ls, rows = insight_rows(db, u, team_id, month); h = CONFIG["hours_per_day"]; tt = analysis.tot(rows, h)
    hourly = lambda f: calc.rollup([{"rate": f(l)[0], "genus": f(l)[1], "alloc": l.alloc} for l in ls])
    sc = [("Baseline", hourly(lambda l: (l.base["rate"], l.base["genus"]))), ("Current", hourly(lambda l: (l.rate, l.genus)))]
    sc += [(s.name, s.data) for s in db.query(Scenario).filter_by(team_id=t.id, auto=False).order_by(Scenario.id)]
    return {"team_id": t.id, "team": t.name, "month": f"{y}-{mo:02d}", "total": analysis.brief(tt), "band": band_of(tt["margin_pct"]),
            "by_level": analysis.groups(rows, h, lambda r: analysis.level(r["role"])), "by_role": analysis.groups(rows, h, lambda r: analysis.family(r["role"])),
            "by_bracket": analysis.groups(rows, h, lambda r: r["bracket"] or "?"), "distribution": analysis.distribution(rows, h), "waterfall": analysis.waterfall(rows, h),
            "sensitivity": analysis.sensitivity(rows, h, CONFIG.get("max_alloc", 1)),
            "scenarios": [{"name": n, "margin_pct": d.get("margin_pct"), "revenue": d.get("revenue"), "cost": d.get("cost")} for n, d in sc]}
@app.post("/api/solve")
def solve(b: dict, u=MGR, db=Depends(get_db)):
    target = num(b.get("target"), "Target margin", lo=0, hi=95)
    t, y, mo, hs, ls, rows = insight_rows(db, u, b.get("team_id"), b.get("month"))
    return {"team": t.name, "month": f"{y}-{mo:02d}", **analysis.solver(rows, CONFIG["hours_per_day"], target, CONFIG.get("solver_max_uplift_pct", 15), CONFIG["max_rate"])}
@app.post("/api/mix")
def mix(b: dict, u=MGR, db=Depends(get_db)):
    t, y, mo, hs, ls, rows = insight_rows(db, u, b.get("team_id"), b.get("month")); act = b.get("action")
    if act not in ("add", "remove", "swap"): raise HTTPException(400, "action must be add, remove or swap")
    pid = b.get("person_id"); old = next((r for r in rows if r["id"] == pid), None)
    if act != "add" and not old: raise HTTPException(404, "Person not found in this team")
    new = None
    if act != "remove":
        role = text_field(b.get("role"), "Role", required=True); g = genus_dict(db, tcountry(t)).get(calc.norm_role(role))
        cost = num(b["genus_override"], "Genus cost", gt=0, hi=CONFIG["max_genus"]) if b.get("genus_override") not in (None, "") else (g["cost"] if g else None)
        if cost is None: raise HTTPException(400, f"Role '{role}' is not in the Genus table. Enter a Genus cost.")
        alloc = num(b.get("alloc", old["alloc"] if old else 1), "Allocation", gt=0, hi=CONFIG["max_alloc"])
        new = {"id": pid or "new", "name": "New person", "role": role, "bracket": None, "rate": num(b.get("rate"), "Rate", gt=0, hi=CONFIG["max_rate"]), "genus": cost, "alloc": alloc,
               "days": old["days"] if old else calc.person_days(y, mo, hs)}
    return {"action": act, "team": t.name, "month": f"{y}-{mo:02d}", **analysis.mix(rows, CONFIG["hours_per_day"], act, pid, new)}

@app.on_event("startup")
def seed():
    legacy = ensure_schema(); db = SessionLocal()
    db.query(GenusVersion).filter(GenusVersion.country.is_(None)).update({"country": DEFAULT_COUNTRY, "currency": CONFIG["currency"]})  # tables and teams from before countries existed
    db.query(Team).filter(Team.country.is_(None)).update({"country": DEFAULT_COUNTRY}); db.commit()
    if auth.MODE == "dev" and not db.query(User).count():
        for e, r in (("admin@local", "admin"), ("admin2@local", "admin"), ("manager@local", "manager")): db.add(User(email=e, name=e, role=r))
    for e in re.split(r"[,\s;]+", (os.getenv("ADMIN_EMAILS", "") + "," + os.getenv("FIRST_ADMIN_EMAIL", "")).lower()):  # administrators are named here, never self-registered
        if not e: continue
        x = db.query(User).filter_by(email=e).first()
        if x: x.role, x.active = "admin", True
        else: db.add(User(email=e, name=e.split("@")[0], role="admin"))
    if not db.query(GenusVersion).count():
        groups, _ = parse_genus(ROOT / "data/Genus_Cost.xlsx")
        for g in groups.values():
            v = GenusVersion(label="Initial table (SIMULATED, unverified)", status="active", country=g["country"], currency=g["currency"], created_by="system", decided_by="system", decided_at=now(), report={"accepted": len(g["rates"])})
            db.add(v); db.commit()
            for k, (l, c) in g["rates"].items(): db.add(GenusRate(version_id=v.id, key=k, label=l, cost=c, location=g["locations"].get(k) or None))
    if not db.query(Calendar).count():  # first start, or upgrade from the single global calendar
        cal = Calendar(name="India (national)"); db.add(cal); db.commit()
        legacy = db.query(Holiday).all()
        if legacy:
            for h in legacy: db.add(CalendarDay(calendar_id=cal.id, day=h.day, name=h.name))
        else:  # fixed-date national holidays only; admin must add company/regional holidays
            for y in (2026, 2027):
                for md, n in (("01-26", "Republic Day"), ("08-15", "Independence Day"), ("10-02", "Gandhi Jayanti"), ("12-25", "Christmas")): db.add(CalendarDay(calendar_id=cal.id, day=dt.date.fromisoformat(f"{y}-{md}"), name=n))
    db.commit()
    if not db.query(Team).count():
        t = Team(name="Main team", calendar_id=db.query(Calendar).order_by(Calendar.id).first().id, created_by="system", country=DEFAULT_COUNTRY); db.add(t); db.commit()
    for x in db.query(User).filter_by(role="delivery"):  # the delivery role was removed: keep the account, but with no team access until an admin assigns teams again
        x.role = "manager"; db.query(TeamAccess).filter_by(user_id=x.id).delete()
    db.commit()
    first = db.query(Team).order_by(Team.id).first()
    db.query(TeamLine).filter(TeamLine.team_id.is_(None)).update({"team_id": first.id}); db.query(Scenario).filter(Scenario.team_id.is_(None)).update({"team_id": first.id}); db.commit()
    if not db.query(TeamLine).count(): replace_team(db, import_team(ROOT / "data/Revenue_Sheet.xlsx", genus_dict(db)), first.id)
    if legacy:  # upgrading from a version without team access: existing managers keep seeing the existing teams (admins can then narrow it down)
        for x in db.query(User).filter(User.role != "admin"):
            for t in db.query(Team):
                if not db.query(TeamAccess).filter_by(user_id=x.id, team_id=t.id).first(): db.add(TeamAccess(user_id=x.id, team_id=t.id))
        db.commit()
    if auth.MODE in ("dev", "email") and os.getenv("DEMO_DATA", "1") != "0":  # simulated teams: local testing only, never in SSO / production mode
        from .demo_data import seed_demo, ensure_demo_accounts
        seed_demo(db, genus_dict(db)); ensure_demo_accounts(db)
        db.query(Team).filter(Team.country.is_(None)).update({"country": DEFAULT_COUNTRY}); db.commit()
    db.close()

class Static(StaticFiles):
    """Static files that the browser re-checks on every visit (a cheap 304 when nothing changed), so a new release shows up straight away."""
    async def get_response(self, path, scope):
        r = await super().get_response(path, scope); r.headers["Cache-Control"] = "no-cache"; return r

@app.get("/")
def index(): return FileResponse(FRONTEND / "index.html", headers={"Cache-Control": "no-cache"})
app.mount("/static", Static(directory=FRONTEND), name="static")
