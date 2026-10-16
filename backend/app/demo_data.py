"""Simulated teams (projects) for demos and testing. Everything here is FAKE and flagged as simulated.

How it is modelled on the real Revenue_Sheet.xlsx / Genus_Cost.xlsx:
  * Role per MSA is "<level>-<technology>", exactly as in the sheet, and Genus cost comes from the active Genus table.
  * Rate cards follow level and experience (as in the sheet); margin then falls out of rate vs Genus cost,
    so some people end up Good, some Medium, some Low and a few Loss, just like the real data.
  * Output is deterministic (fixed random seed): the same data every time. Switch it off with DEMO_DATA=0.
"""
import datetime as dt, random, uuid
from . import calc
from .db import (Team, TeamLine, TeamAccess, Calendar, CalendarDay, Scenario, User, Setting)

SEED = 20261012
FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karan", "Siddharth", "Nikhil", "Rahul", "Amit", "Varun", "Manish", "Harsh", "Deepak", "Kunal", "Anil",
         "Ananya", "Diya", "Isha", "Kavya", "Meera", "Neha", "Pooja", "Priyanka", "Riya", "Sneha", "Tanvi", "Shreya", "Divya", "Aditi", "Swati", "Nisha",
         "Lukas", "Jonas", "Felix", "Anna", "Marta", "Elena", "Tobias", "Sofia"]
LAST = ["Sharma", "Verma", "Iyer", "Nair", "Reddy", "Menon", "Kapoor", "Joshi", "Patil", "Kulkarni", "Desai", "Mehta", "Bose", "Das", "Rao", "Gupta",
        "Singh", "Chopra", "Malhotra", "Bhat", "Pillai", "Hegde", "Shetty", "Naidu", "Banerjee", "Chatterjee", "Agarwal", "Saxena", "Mishra", "Pandey",
        "Weber", "Becker", "Fischer", "Keller", "Novak", "Rossi"]
# Rate card per level (the real sheet: 2.3 ~ 2300, 3.1 ~ 2370-2700, 3.2 ~ 2660-2850, 3.3 ~ 2850-2960); lower and higher levels extrapolated.
LEVEL_RATE = {"2.1": 1650, "2.2": 1950, "2.3": 2300, "3.1": 2450, "3.2": 2720, "3.3": 2900, "4.1": 3700, "4.2": 4150}
LEVEL_EXP = {"2.1": (0.5, 2), "2.2": (2, 3.5), "2.3": (3, 5), "3.1": (4, 7), "3.2": (6, 9.5), "3.3": (8.5, 12), "4.1": (11, 15), "4.2": (13, 18)}

# (name, business unit, calendar, size, level mix, technology mix)
PROJECTS = [
    ("Atlas: Retail Banking Portal (simulated)", "Digital Engineering", "India - Pune (simulated)", 12,
     {"2.3": 2, "3.1": 4, "3.2": 4, "3.3": 2, "4.1": 1}, {"JAVA": 5, "JAVA-FULLSTACK": 3, "DEVOPS": 2, "CLOUD-INFRASTRUCTURE": 1}),
    ("Beacon: Mobile Commerce App (simulated)", "Digital Engineering", "India - Pune (simulated)", 10,
     {"2.3": 3, "3.1": 3, "3.2": 3, "3.3": 2, "4.1": 1}, {"JAVA-FULLSTACK": 4, "DOTNET-FULLSTACK": 2, "PYTHON": 2, "DEVOPS": 1}),
    ("Cobalt: Data Lakehouse (simulated)", "Data & AI", "India - Bangalore (simulated)", 13,
     {"2.3": 2, "3.1": 3, "3.2": 4, "3.3": 3, "4.1": 1}, {"BIG-DATA-ENGINEER": 6, "DATA-ANALYST": 3, "PYTHON": 2, "CLOUD-INFRASTRUCTURE": 2}),
    ("Delta: MLOps Platform (simulated)", "Data & AI", "India - Bangalore (simulated)", 9,
     {"3.1": 2, "3.2": 3, "3.3": 4, "4.1": 2}, {"DATA-SCIENCE": 4, "GENERATIVE-AI": 2, "PYTHON": 3, "DEVOPS": 2}),
    ("Ember: CRM Rollout (simulated)", "Enterprise Platforms", "Germany (simulated)", 11,
     {"2.3": 3, "3.1": 4, "3.2": 3, "3.3": 1}, {"CRM-SALESFORCE": 7, "CRM-MULESOFT": 3, "CUSTOM": 1}),
    ("Flux: Integration Hub (simulated)", "Enterprise Platforms", "India (national)", 8,
     {"3.1": 2, "3.2": 3, "3.3": 3, "4.1": 1}, {"CRM-MULESOFT": 5, "JAVA": 2, "DEVOPS": 1}),
]
CALENDARS = {  # fixed-date holidays only; regional extras are invented placeholders and labelled as such
    "India - Pune (simulated)": [("01-26", "Republic Day"), ("05-01", "Maharashtra Day"), ("08-15", "Independence Day"), ("10-02", "Gandhi Jayanti"), ("12-25", "Christmas"), ("10-20", "Regional festival (simulated)")],
    "India - Bangalore (simulated)": [("01-26", "Republic Day"), ("08-15", "Independence Day"), ("10-02", "Gandhi Jayanti"), ("11-01", "Karnataka Rajyotsava"), ("12-25", "Christmas")],
    "Germany (simulated)": [("01-01", "New Year's Day"), ("05-01", "Labour Day"), ("10-03", "German Unity Day"), ("12-25", "Christmas Day"), ("12-26", "Second Day of Christmas")],
}
# demo sign-ins and the teams each may see (a project manager typically has 3-4 projects; some projects are shared)
USERS = [("priya.manager@local", "manager"), ("ravi.manager@local", "manager")]
ACCESS = {
    "manager@local": ["Main team", "Atlas", "Beacon"],
    "priya.manager@local": ["Cobalt", "Delta"],
    "ravi.manager@local": ["Ember", "Flux", "Atlas"],
}

def _pick(rng, weights): return rng.choices(list(weights), weights=list(weights.values()))[0]

def _people(rng, size, levels, techs, genus, used):
    out = []
    for _ in range(size):
        lv, tech = _pick(rng, levels), _pick(rng, techs)
        g = genus.get(calc.norm_role(f"{lv}-{tech}"))
        if not g: continue
        lo, hi = LEVEL_EXP[lv]; exp = round(rng.uniform(lo, hi), 2)
        rate = round(LEVEL_RATE[lv] * rng.uniform(0.96, 1.05))
        while True:
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            if name not in used: used.add(name); break
        b = calc.bracket(exp)
        out.append(dict(id=uuid.uuid4().hex[:8], name=name, role=g["genus"], rate=rate, exp=exp, bracket=b, bracket_override=False, genus=g["cost"], genus_override=False,
                        alloc=rng.choices([1, 0.5, 0.75], weights=[85, 10, 5])[0], warnings=[], base=dict(rate=rate, exp=exp, genus=g["cost"], bracket=b)))
    return out

def seed_demo(db, genus, today=None):
    """Creates the simulated teams once (tracked in settings) and the demo access rules. Safe to call on every start."""
    if db.get(Setting, "demo_seeded"): return False
    today = today or dt.date.today(); rng = random.Random(SEED); used = set()
    first_of_month = today.replace(day=1)
    cals = {}
    for name, days in CALENDARS.items():
        c = db.query(Calendar).filter_by(name=name).first() or Calendar(name=name)
        if not c.id:
            db.add(c); db.commit()
            for y in range(today.year, today.year + 2):
                for md, label in days: db.add(CalendarDay(calendar_id=c.id, day=dt.date.fromisoformat(f"{y}-{md}"), name=label))
            db.commit()
        cals[name] = c
    default_cal = db.query(Calendar).order_by(Calendar.id).first()
    top = db.query(TeamLine).count()
    for name, unit, cal, size, levels, techs in PROJECTS:
        if db.query(Team).filter_by(name=name).first(): continue
        t = Team(name=name, unit=unit, simulated=True, created_by="simulated data", calendar_id=(cals.get(cal) or default_cal).id); db.add(t); db.commit()
        for i, p in enumerate(_people(rng, size, levels, techs, genus, used)):
            if rng.random() < 0.12:  # joins in the next 1-3 months
                p["start_date"] = (first_of_month + dt.timedelta(days=31 * rng.randint(1, 3))).replace(day=rng.choice([1, 8, 15]))
            elif rng.random() < 0.10:  # rolls off in the next 2-6 months
                p["end_date"] = (first_of_month + dt.timedelta(days=31 * rng.randint(2, 6))).replace(day=rng.choice([15, 28]))
            db.add(TeamLine(pos=top, team_id=t.id, **p)); top += 1
        db.commit()
        _scenarios(db, t)
    for email, role in USERS:
        if not db.query(User).filter_by(email=email).first(): db.add(User(email=email, name=email, role=role))
    db.commit()
    teams = db.query(Team).all()
    for email, wanted in ACCESS.items():
        u = db.query(User).filter_by(email=email).first()
        if not u: continue
        for t in teams:
            if any(t.name == w or t.name.startswith(w + ":") for w in wanted) and not db.query(TeamAccess).filter_by(user_id=u.id, team_id=t.id).first():
                db.add(TeamAccess(user_id=u.id, team_id=t.id))
    db.add(Setting(key="demo_seeded", value=today.isoformat())); db.commit()
    return True

def _scenarios(db, t):
    ls = db.query(TeamLine).filter_by(team_id=t.id).order_by(TeamLine.pos).all()
    def make(name, rate_f, genus_f):
        vals = [dict(id=l.id, name=l.name, rate=round(l.rate * rate_f), exp=l.exp, genus=round(l.genus * genus_f, 2), bracket=l.bracket, alloc=l.alloc) for l in ls]
        d = {"vals": vals, "people": len(ls), **calc.rollup([{"rate": v["rate"], "genus": v["genus"], "alloc": v["alloc"]} for v in vals])}
        db.add(Scenario(name=name, created_by="simulated data", data=d, team_id=t.id, auto=False))
    make("Rate card +5% (simulated)", 1.05, 1.0)
    make("Cost optimisation, Genus -3% (simulated)", 1.0, 0.97)
    db.commit()


# One-click demo accounts for showcases (shown on the sign-in page). Fixed roles, fixed teams; delivery managers are managers too.
DEMO_DOMAIN = "demo.example"
DEMO_ACCOUNTS = [  # (email, role, teams they see)
    (f"demoadmin@{DEMO_DOMAIN}", "admin", []),
    (f"demo1projectmanager@{DEMO_DOMAIN}", "manager", ["Main team", "Atlas", "Beacon"]),
    (f"demo2projectmanager@{DEMO_DOMAIN}", "manager", ["Cobalt", "Delta"]),
    (f"demo1delmanager@{DEMO_DOMAIN}", "manager", ["Ember", "Flux", "Atlas"]),
    (f"demo2delmanager@{DEMO_DOMAIN}", "manager", ["Beacon", "Cobalt", "Flux"]),
]

def ensure_demo_accounts(db):
    """Creates any missing demo account and its team access. Safe to call on every start."""
    teams = db.query(Team).all()
    for email, role, wanted in DEMO_ACCOUNTS:
        u = db.query(User).filter_by(email=email).first()
        if not u: u = User(email=email, name=email.split("@")[0], role=role, active=True); db.add(u); db.commit()
        u.role, u.active = role, True
        for t in teams:
            if any(t.name == w or t.name.startswith(w + ":") for w in wanted) and not db.query(TeamAccess).filter_by(user_id=u.id, team_id=t.id).first():
                db.add(TeamAccess(user_id=u.id, team_id=t.id))
    db.commit()
