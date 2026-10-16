from app import analysis as A
from .test_api import client

def row(i, rate, genus, alloc=1, role="3.1-Java"): return {"id": i, "name": i, "role": role, "bracket": "6-9", "rate": rate, "genus": genus, "alloc": alloc, "days": 20}
ROWS = [row("a", 3000, 2000), row("b", 2400, 2200, role="3.2-Devops"), row("c", 2000, 2100, role="2.3-Custom")]
H = 8

def test_groups_are_weighted_not_averaged():
    g = {x["key"]: x for x in A.groups(ROWS, H, lambda r: A.level(r["role"]))}
    assert set(g) == {"3.1", "3.2", "2.3"} and round(g["3.1"]["margin_pct"], 2) == 33.33

def test_distribution_counts_everyone_once():
    d = A.distribution(ROWS, H); assert sum(b["people"] for b in d) == 3 and d[0]["people"] == 1  # one loss-making person

def test_waterfall_adds_up():
    w = A.waterfall(ROWS, H); assert round(w[0]["value"] + sum(x["value"] for x in w[1:-1]) - w[-1]["value"], 6) == 0

def test_sensitivity_rate_up_improves_margin():
    s = A.sensitivity(ROWS, H); lv = {l["label"]: l for l in s["levers"]}
    assert lv["Rate +5%"]["d_margin"] > 0 > lv["Rate -5%"]["d_margin"] and lv["Genus cost +5%"]["d_margin"] < 0
    assert s["grid"][2][2] == s["base"]["margin_pct"]  # centre cell = today

def test_solver_levers_hit_target_and_respect_caps():
    base = A.tot(ROWS, H)["margin_pct"]; r = A.solver(ROWS, H, 20, 15, 100000)
    assert not r["met"] and base < 20
    for l in r["levers"]:
        if l["feasible"]: assert l["after"]["margin_pct"] >= 20 - 1e-6
    t = next(l for l in r["levers"] if l["id"] == "targeted")
    assert all(c["pct"] <= 15.0001 for c in t["changes"])
    assert A.solver(ROWS, H, 1, 15, 100000)["met"]

def test_solver_allocation_only_touches_below_team_margin():
    r = A.solver(ROWS, H, 15, 15, 100000); a = next(l for l in r["levers"] if l["id"] == "allocation")
    assert a["feasible"] and [c["name"] for c in a["changes"]][0] == "c"

def test_mix_add_remove_swap():
    new = row("new", 2800, 1800); assert A.mix(ROWS, H, "add", None, new)["delta"]["revenue"] > 0
    assert A.mix(ROWS, H, "remove", "c")["delta"]["margin_pct"] > 0  # removing the loss-maker lifts %
    assert A.mix(ROWS, H, "swap", "c", row("c", 2600, 2100))["delta"]["margin"] > 0

def test_api_manager_only_and_scoped():
    m = client("manager@local"); tid = m.get("/api/teams").json()[0]["id"]
    r = m.get(f"/api/insights?team_id={tid}").json(); assert r["by_level"] and r["distribution"] and r["scenarios"][0]["name"] == "Baseline"
    s = m.post("/api/solve", json={"team_id": tid, "target": 60}).json(); assert s["levers"] and s["target"] == 60
    assert m.post("/api/solve", json={"team_id": tid, "target": 150}).status_code == 400
    assert m.post("/api/mix", json={"team_id": tid, "action": "add", "role": "3.1-Java", "rate": 2800}).json()["delta"]["revenue"] > 0
    assert m.post("/api/mix", json={"team_id": tid, "action": "add", "role": "9.9-Nope", "rate": 2800}).status_code == 400
    assert client("admin@local").get(f"/api/insights?team_id={tid}").status_code == 200
    other = next(t["id"] for t in client("admin@local").get("/api/teams").json() if t["id"] not in {x["id"] for x in m.get("/api/teams").json()})
    assert m.get(f"/api/insights?team_id={other}").status_code == 404  # a team you cannot see does not exist
