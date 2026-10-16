"""Pure calculation + parsing helpers (the single place for business logic)."""
import re

def parse_exp(v):
    if v is None or v == "": return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).lower().strip()
    y = re.search(r"(\d+(?:\.\d+)?)\s*y", s)
    m = re.search(r"(\d+)\s*m", s)
    if y: return float(y.group(1)) + (int(m.group(1)) / 12 if m else 0)
    try: return float(s)
    except ValueError: return None

def bracket(years):
    if years is None: return None
    return "3-6" if years < 6 else "6-9" if years < 9 else "9-12" if years < 12 else "12-15"

def norm_bracket(v):
    m = re.search(r"(\d+)\s*-\s*(\d+)", str(v or ""))
    return f"{m.group(1)}-{m.group(2)}" if m else None

def norm_role(v): return re.sub(r"\s+", "", str(v or "")).upper()

def margin(rate, genus):
    """Returns (absolute, pct). pct is None when rate is 0 (undefined)."""
    a = rate - genus
    return a, (a / rate * 100 if rate else None)

def rate_for_target(genus, target_pct): return genus / (1 - target_pct / 100) if target_pct < 100 else None

def rollup(rows):
    """Weighted roll-up: never average the percentages."""
    rev = sum(r["rate"] * r.get("alloc", 1) for r in rows)
    cost = sum(r["genus"] * r.get("alloc", 1) for r in rows)
    a, p = margin(rev, cost)
    return {"revenue": rev, "cost": cost, "margin": a, "margin_pct": p}

import calendar, datetime as _dt
def business_days(year, month, holidays=()):
    """Mon-Fri days in the month minus listed holidays that fall on a weekday."""
    hs = set(holidays); n = 0; hl = []
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        day = _dt.date(year, month, d)
        if day.weekday() >= 5: continue
        if day in hs: hl.append(day.isoformat()); continue
        n += 1
    return n, hl

def monthly(rate, genus, hours_per_day, days, alloc=1):
    h = hours_per_day * days * alloc
    return {"revenue": rate * h, "cost": genus * h, "margin": (rate - genus) * h}

def band(pct, warn, good):
    return "red" if pct is None else "loss" if pct < 0 else "red" if pct < warn else "amber" if pct < good else "green"

def person_days(year, month, holidays=(), start=None, end=None):
    """Working days one person is on the team in a month: Mon-Fri minus holidays, limited to their start/end dates (None = open-ended)."""
    last = _dt.date(year, month, calendar.monthrange(year, month)[1])
    s = max(_dt.date(year, month, 1), start) if start else _dt.date(year, month, 1)
    e = min(last, end) if end else last
    hs, n, d = set(holidays), 0, s
    while d <= e:
        if d.weekday() < 5 and d not in hs: n += 1
        d += _dt.timedelta(days=1)
    return n

def month_rollup(rows, hours_per_day):
    """rows: dicts with rate, genus, alloc, days. Returns monthly revenue / cost / margin for the group (weighted, never averaged %)."""
    rev = sum(r["rate"] * r["alloc"] * hours_per_day * r["days"] for r in rows)
    cost = sum(r["genus"] * r["alloc"] * hours_per_day * r["days"] for r in rows)
    a, p = margin(rev, cost)
    return {"revenue": rev, "cost": cost, "margin": a, "margin_pct": p, "headcount": sum(1 for r in rows if r["days"] > 0)}

