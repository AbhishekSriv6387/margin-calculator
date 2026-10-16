"""Margin analysis (pure functions, no database): grouping, chart data, sensitivity, target solver, team-mix what-if.
Rows are monthly person rows: {id, name, role, bracket, rate, genus, alloc, days}. Percentages are always weighted, never averaged."""
import re
from . import calc

def level(role): m = re.match(r"^(\d\.\d)", role or ""); return m.group(1) if m else "?"
def family(role): m = re.match(r"^\d\.\d-(.+)$", role or ""); return m.group(1).upper() if m else (role or "?").upper()
def live(rows): return [r for r in rows if r["days"] > 0 and r["alloc"] > 0]
def pct(r): return calc.margin(r["rate"], r["genus"])[1]
def tot(rows, h): return calc.month_rollup(rows, h)
def brief(t): return {k: t[k] for k in ("revenue", "cost", "margin", "margin_pct", "headcount")}

def groups(rows, h, keyf):
    g = {}
    for r in live(rows): g.setdefault(keyf(r), []).append(r)
    return [{"key": k, **brief(tot(v, h))} for k, v in sorted(g.items())]

BINS = [("Loss", None, 0), ("0-10%", 0, 10), ("10-20%", 10, 20), ("20-30%", 20, 30), ("30-40%", 30, 40), ("40%+", 40, None)]
def distribution(rows, h):
    out = [{"label": l, "lo": lo, "hi": hi, "people": 0, "revenue": 0.0} for l, lo, hi in BINS]
    for r in live(rows):
        p = pct(r); p = -1 if p is None else p
        for b in out:
            if (b["lo"] is None or p >= b["lo"]) and (b["hi"] is None or p < b["hi"]):
                b["people"] += 1; b["revenue"] += r["rate"] * r["alloc"] * h * r["days"]; break
    return out

def waterfall(rows, h):
    t = tot(rows, h); steps = [{"label": "Revenue", "value": t["revenue"], "kind": "total"}]
    for g in groups(rows, h, lambda r: level(r["role"])): steps.append({"label": "Cost " + g["key"], "value": -g["cost"], "kind": "cost"})
    steps.append({"label": "Margin", "value": t["margin"], "kind": "total"}); return steps

def _scaled(rows, rate=1.0, genus=1.0, alloc=1.0, cap=None):
    return [{**r, "rate": r["rate"] * rate, "genus": r["genus"] * genus, "alloc": min(r["alloc"] * alloc, cap) if (cap and alloc > 1) else r["alloc"] * alloc} for r in rows]

def sensitivity(rows, h, max_alloc=1.0):
    b = tot(rows, h); lv = []
    for label, kw in (("Rate +5%", dict(rate=1.05)), ("Rate -5%", dict(rate=.95)), ("Genus cost +5%", dict(genus=1.05)), ("Genus cost -5%", dict(genus=.95))):
        a = tot(_scaled(rows, **kw), h)
        lv.append({"label": label, "margin": a["margin"], "d_margin": a["margin"] - b["margin"], "margin_pct": a["margin_pct"],
                   "d_pts": None if a["margin_pct"] is None or b["margin_pct"] is None else a["margin_pct"] - b["margin_pct"]})
    steps = [-10, -5, 0, 5, 10]
    grid = [[tot(_scaled(rows, rate=1 + dr / 100, genus=1 + dc / 100), h)["margin_pct"] for dc in steps] for dr in steps]
    people = []
    for r in live(rows):
        w = r["alloc"] * h * r["days"]; after = tot([{**x, "rate": x["rate"] * 1.05} if x["id"] == r["id"] else x for x in rows], h)
        people.append({"name": r["name"], "role": r["role"], "margin_pct": pct(r), "d_margin": r["rate"] * .05 * w,
                       "d_pts": None if after["margin_pct"] is None or b["margin_pct"] is None else after["margin_pct"] - b["margin_pct"]})
    people.sort(key=lambda p: -p["d_margin"])
    return {"base": brief(b), "levers": lv, "steps": steps, "grid": grid, "people": people[:10]}

def solver(rows, h, target, max_uplift_pct, max_rate):
    """What gets the team to `target` margin %? Three independent levers, each reported with its trade-offs."""
    base = tot(rows, h); T = target / 100; R, C = base["revenue"], base["cost"]; res = {"target": target, "baseline": brief(base), "met": (base["margin_pct"] or -1) >= target, "levers": []}
    if res["met"] or R <= 0: return res
    lv = [r for r in live(rows) if r["rate"] > 0]
    k = C / (R * (1 - T)); up = (k - 1) * 100; ok = up <= max_uplift_pct and all(r["rate"] * k <= max_rate for r in lv)
    res["levers"].append({"id": "uniform", "title": "Raise every rate by the same %", "feasible": ok, "needed_pct": up,
        "note": f"Needs +{up:.1f}% on all rates." + ("" if ok else f" That is above the {max_uplift_pct:g}% limit per person, so use the targeted option or combine levers."), "changes": []})
    cur = [dict(r) for r in rows]; ch = []
    for r in sorted(lv, key=lambda r: pct(r) if pct(r) is not None else -1e9):
        if (tot(cur, h)["margin_pct"] or -1) >= target: break
        want = min(max(r["rate"], r["genus"] / (1 - T)), r["rate"] * (1 + max_uplift_pct / 100), max_rate)
        if want > r["rate"] + 0.005:
            next(x for x in cur if x["id"] == r["id"])["rate"] = want; ch.append({"name": r["name"], "role": r["role"], "from": r["rate"], "to": round(want, 2), "pct": (want / r["rate"] - 1) * 100})
    a = tot(cur, h); res["levers"].append({"id": "targeted", "title": "Raise only the low-margin people's rates", "feasible": (a["margin_pct"] or -1) >= target - 1e-9,
        "after": brief(a), "changes": ch, "note": f"Capped at +{max_uplift_pct:g}% per person (and never above the max rate)."})
    cur = [dict(r) for r in rows]; ch = []
    for r in sorted(live(rows), key=lambda r: pct(r) if pct(r) is not None else -1e9):
        t0 = tot(cur, h)
        if (t0["margin_pct"] or -1) >= target: break
        x = next(x for x in cur if x["id"] == r["id"]); p = pct(r)
        if p is not None and t0["margin_pct"] is not None and p >= t0["margin_pct"]: continue
        old = x["alloc"]; x["alloc"] = 0
        if (tot(cur, h)["margin_pct"] or -1) < target: pass
        else:
            lo, hi = 0.0, old
            for _ in range(40):
                mid = (lo + hi) / 2; x["alloc"] = mid
                if (tot(cur, h)["margin_pct"] or -1) >= target: lo = mid
                else: hi = mid
            x["alloc"] = lo
        ch.append({"name": r["name"], "role": r["role"], "from": old, "to": round(x["alloc"], 2)})
    a = tot(cur, h); res["levers"].append({"id": "allocation", "title": "Move allocation away from the lowest-margin people", "feasible": (a["margin_pct"] or -1) >= target - 1e-9,
        "after": brief(a), "changes": ch, "note": "Raises the percentage by shrinking low-margin work. Check the total margin in rupees: it can fall even when the % rises."})
    for l in res["levers"]:
        if l["id"] == "uniform":
            a = tot(_scaled(rows, rate=k), h); l["after"] = brief(a)
    return res

def mix(rows, h, action, person_id=None, new=None):
    """Team effect of adding a person, removing one, or swapping one for a different role / rate."""
    before = tot(rows, h)
    if action == "add": rs = rows + [new]
    elif action == "remove": rs = [r for r in rows if r["id"] != person_id]
    else: rs = [new if r["id"] == person_id else r for r in rows]
    after = tot(rs, h); d = lambda k: None if after[k] is None or before[k] is None else after[k] - before[k]
    return {"before": brief(before), "after": brief(after), "delta": {"margin": d("margin"), "margin_pct": d("margin_pct"), "revenue": d("revenue"), "cost": d("cost")}}
