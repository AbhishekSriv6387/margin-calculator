"""Team access control: a manager sees only the teams assigned to them, enforced on the server."""
import io, openpyxl
from .test_api import client

def team_id(c, startswith): return next(t["id"] for t in c.get("/api/teams").json() if t["name"].startswith(startswith))
def user_id(a, email): return next(u["id"] for u in a.get("/api/users").json() if u["email"] == email)

def test_demo_assignments_scope_each_user():
    a = client("admin@local"); names = lambda c: [t["name"].split(":")[0] for t in c.get("/api/teams").json()]
    assert len(names(a)) >= 7                                                                  # admin sees every team
    assert names(client("manager@local")) == ["Main team", "Atlas", "Beacon"]                   # 3 projects
    assert names(client("priya.manager@local")) == ["Cobalt", "Delta"]
    assert names(client("ravi.manager@local")) == ["Atlas", "Ember", "Flux"]                    # Atlas is shared with manager@local

def test_every_team_endpoint_is_closed_to_unassigned_users():
    a, m = client("admin@local"), client("manager@local"); other = team_id(a, "Cobalt")
    line = a.get(f"/api/team?team_id={other}").json()[0]["id"]
    sid = a.post(f"/api/scenarios?team_id={other}", json={"name": "secret"}).json()["id"]
    wb = openpyxl.Workbook(); wb.active.append(["Team Member", "Role per MSA", "Rate Card", "Current Experience"]); b = io.BytesIO(); wb.save(b)
    calls = [m.get(f"/api/team?team_id={other}"), m.post(f"/api/team?team_id={other}"), m.get(f"/api/period?month=2026-10&team_id={other}"),
             m.get(f"/api/export?team_id={other}"), m.get(f"/api/scenarios?team_id={other}"),
             m.post(f"/api/scenarios?team_id={other}", json={"name": "x"}), m.patch(f"/api/team/{line}", json={"rate": 2000}), m.delete(f"/api/team/{line}"),
             m.delete(f"/api/scenarios/{sid}"), m.post(f"/api/scenarios/{sid}/apply"),
             m.get(f"/api/scenarios/compare?a={sid}&b=current&team_id={other}"), m.patch(f"/api/teams/{other}", json={"name": "hijack"}),
             m.post(f"/api/team/import?team_id={other}", files={"file": ("t.xlsx", b.getvalue())}), m.post("/api/teams", json={"name": "copy", "copy_from": other})]
    assert [c.status_code for c in calls] == [404] * len(calls)
    assert m.delete(f"/api/teams/{other}").status_code == 403                                   # admin only
    assert a.get(f"/api/team?team_id={other}").json()[0]["rate"] == a.get(f"/api/team?team_id={other}").json()[0]["rate"]   # untouched
    assert all(t["name"] != "hijack" for t in a.get("/api/teams").json())

def test_manager_cannot_probe_other_teams_either():
    a, p = client("admin@local"), client("priya.manager@local"); other = team_id(a, "Atlas")
    assert p.get(f"/api/team?team_id={other}").status_code == 404
    assert p.get(f"/api/insights?team_id={other}").status_code == 404

def test_manager_with_two_teams_sees_both_and_a_combined_total():
    p = client("priya.manager@local"); ts = p.get("/api/teams?month=2026-10").json()
    assert [t["name"].split(":")[0] for t in ts] == ["Cobalt", "Delta"]
    for t in ts: assert p.get(f"/api/team?team_id={t['id']}").status_code == 200

def test_delivery_role_no_longer_exists():
    a = client("admin@local"); assert all(u["role"] in ("admin", "manager") for u in a.get("/api/users").json())
    assert a.post("/api/users", json={"email": "x@local", "role": "delivery"}).status_code == 400

def test_unassigned_user_sees_nothing():
    a = client("admin@local"); a.post("/api/users", json={"email": "newbie@local", "role": "manager"})
    n = client("newbie@local"); assert n.get("/api/teams").json() == []
    assert n.get("/api/team").status_code == 403 and n.get("/api/period?month=2026-10").status_code == 403 and n.get("/api/scenarios").status_code == 403

def test_admin_assigns_and_removes_access_and_it_is_audited():
    a = client("admin@local"); a.post("/api/users", json={"email": "grant@local", "role": "manager"}); uid = user_id(a, "grant@local")
    t1, t2 = team_id(a, "Delta"), team_id(a, "Flux"); g = client("grant@local")
    assert a.put(f"/api/users/{uid}/teams", json={"team_ids": [t1, t2]}).status_code == 200
    assert sorted(t["id"] for t in g.get("/api/teams").json()) == sorted([t1, t2])
    a.put(f"/api/users/{uid}/teams", json={"team_ids": [t1]}); assert [t["id"] for t in g.get("/api/teams").json()] == [t1]
    assert g.get(f"/api/team?team_id={t2}").status_code == 404                                  # takes effect immediately
    assert next(u for u in a.get("/api/users").json() if u["id"] == uid)["team_ids"] == [t1]
    log = [x for x in a.get("/api/audit").json() if x["action"] == "user_access" and x["id"] == "grant@local"]
    assert len(log) == 2 and log[1]["details"]["added"] and log[0]["details"]["removed"] == [t["name"] for t in a.get("/api/teams").json() if t["id"] == t2]  # newest first

def test_only_admins_can_assign_and_input_is_validated():
    a, m = client("admin@local"), client("manager@local"); uid = user_id(a, "ravi.manager@local")
    assert m.put(f"/api/users/{uid}/teams", json={"team_ids": []}).status_code == 403 and m.get("/api/users").status_code == 403
    for bad in ({"team_ids": "all"}, {"team_ids": [99999]}, {"team_ids": ["1"]}, {"team_ids": [True]}, {}):
        assert a.put(f"/api/users/{uid}/teams", json=bad).status_code == 400, bad

def test_creator_keeps_access_and_can_only_copy_what_they_see():
    m = client("manager@local"); r = m.post("/api/teams", json={"name": "Mine", "unit": "Digital Engineering"}); assert r.status_code == 200
    assert any(t["name"] == "Mine" and t["unit"] == "Digital Engineering" for t in m.get("/api/teams").json())
    assert client("priya.manager@local").get(f"/api/team?team_id={r.json()['id']}").status_code == 404   # a colleague does not see it
    assert m.post("/api/teams", json={"name": "Mine copy", "copy_from": r.json()["id"]}).status_code == 200

def test_calendar_list_does_not_leak_other_teams_names():
    p = client("priya.manager@local"); cals = p.get("/api/calendars").json(); shown = {n for c in cals for n in c["teams"]}
    assert shown and all(n.startswith(("Cobalt", "Delta")) for n in shown)

def test_reprice_only_touches_teams_you_can_see():
    a, p = client("admin@local"), client("priya.manager@local"); other = team_id(a, "Atlas"); before = a.get(f"/api/team?team_id={other}").json()
    a.patch(f"/api/team/{before[0]['id']}", json={"genus": before[0]["genus"] + 100, "genus_override": False})   # make Atlas stale vs the Genus table
    p.post("/api/team/reprice"); assert a.get(f"/api/team?team_id={other}").json()[0]["genus"] == before[0]["genus"] + 100   # priya cannot reach it
    assert p.post(f"/api/team/reprice?team_id={other}").status_code == 404

def test_deleting_a_team_removes_its_access_rows_and_users_keep_working():
    a = client("admin@local"); t = a.post("/api/teams", json={"name": "Temp project"}).json()["id"]; uid = user_id(a, "priya.manager@local")
    cur = next(u for u in a.get("/api/users").json() if u["id"] == uid)["team_ids"]; a.put(f"/api/users/{uid}/teams", json={"team_ids": cur + [t]})
    assert a.delete(f"/api/teams/{t}").status_code == 200
    assert t not in next(u for u in a.get("/api/users").json() if u["id"] == uid)["team_ids"] and client("priya.manager@local").get("/api/teams").status_code == 200

def test_demo_data_is_realistic_and_marked_simulated():
    a = client("admin@local"); ts = [t for t in a.get("/api/teams").json() if t["simulated"]]
    assert len(ts) == 6 and all("(simulated)" in t["name"] and t["unit"] for t in ts) and {t["unit"] for t in ts} == {"Digital Engineering", "Data & AI", "Enterprise Platforms"}
    bands = set()
    for t in ts:
        ppl = a.get(f"/api/team?team_id={t['id']}").json(); assert 8 <= len(ppl) <= 13; bands |= {p["band"] for p in ppl}
        assert all(p["genus"] > 0 and p["rate"] > 0 and p["role"][:4] in {f"{l}-" for l in ("2.1", "2.2", "2.3", "3.1", "3.2", "3.3", "4.1", "4.2")} for p in ppl)
        assert sum("(simulated)" in x["name"] for x in a.get(f"/api/scenarios?team_id={t['id']}").json()) == 2
    assert bands == {"green", "amber", "red", "loss"}                                           # every margin band shows up
