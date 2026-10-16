import io, openpyxl
from .test_api import client

def mk_team(c, name, **kw):
    r = c.post("/api/teams", json={"name": name, **kw}); assert r.status_code == 200, r.text; return r.json()["id"]

def test_teams_are_isolated():
    m = client("manager@local"); main = m.get("/api/teams").json()[0]["id"]; n_main = len(m.get(f"/api/team?team_id={main}").json())
    t2 = mk_team(m, "Pune delivery"); assert m.get(f"/api/team?team_id={t2}").json() == []
    p = m.post(f"/api/team?team_id={t2}").json(); assert p["team_id"] == t2
    assert len(m.get(f"/api/team?team_id={main}").json()) == n_main and len(m.get(f"/api/team?team_id={t2}").json()) == 1
    assert m.post("/api/teams", json={"name": "pune DELIVERY"}).status_code == 400            # unique, case-insensitive
    assert m.post("/api/teams", json={"name": "  "}).status_code == 400

def test_import_replaces_only_that_team():
    m = client("manager@local"); main = m.get("/api/teams").json()[0]["id"]; before = len(m.get(f"/api/team?team_id={main}").json())
    t2 = mk_team(m, "Import target", copy_from=main); assert len(m.get(f"/api/team?team_id={t2}").json()) == before     # copy people
    wb = openpyxl.Workbook(); ws = wb.active; ws.append(["Team Member", "Role per MSA", "Rate Card", "Current Experience"]); ws.append(["Only One", "3.1-JAVA", 2500, 4])
    b = io.BytesIO(); wb.save(b)
    r = m.post(f"/api/team/import?team_id={t2}", files={"file": ("t.xlsx", b.getvalue())}); assert r.status_code == 200 and len(r.json()) == 1
    assert len(m.get(f"/api/team?team_id={main}").json()) == before                                       # other team untouched

def test_start_end_dates_drive_working_days():
    m = client("manager@local"); t = mk_team(m, "Dated team"); p = m.post(f"/api/team?team_id={t}").json()
    assert m.patch(f"/api/team/{p['id']}", json={"start_date": "2026-10-15"}).json()["start_date"] == "2026-10-15"
    per = m.get(f"/api/period?month=2026-10&team_id={t}").json(); assert per["days"][p["id"]] == 12 and per["business_days"] == 21
    assert m.patch(f"/api/team/{p['id']}", json={"end_date": "2026-10-01"}).status_code == 400         # end before start
    assert m.get(f"/api/period?month=2026-09&team_id={t}").json()["days"][p["id"]] == 0

def test_regional_calendars():
    a = client("admin@local"); cal = a.post("/api/calendars", json={"name": "Test region"}).json()["id"]
    a.post("/api/holidays", json={"calendar_id": cal, "day": "2026-10-05", "name": "Local festival"})
    t = mk_team(a, "Calendar team", calendar_id=cal)
    assert a.get(f"/api/period?month=2026-10&team_id={t}").json()["business_days"] == 22 - 1               # no Oct-2 holiday here, but Oct-5 is
    assert a.delete(f"/api/calendars/{cal}").status_code == 400                                           # in use by a team
    assert a.post("/api/holidays", json={"calendar_id": cal, "day": "not-a-date"}).status_code == 400

def test_only_admin_deletes_team_and_never_the_last():
    m, a = client("manager@local"), client("admin@local"); t = mk_team(m, "Throwaway")
    assert m.delete(f"/api/teams/{t}").status_code == 403 and a.delete(f"/api/teams/{t}").status_code == 200
    for x in a.get("/api/teams").json()[1:]: a.delete(f"/api/teams/{x['id']}")
    assert a.delete(f"/api/teams/{a.get('/api/teams').json()[0]['id']}").status_code == 400

def test_validation_rejects_bad_input():
    m = client("manager@local"); p = m.get("/api/team").json()[0]; u = f"/api/team/{p['id']}"
    for body in ({"rate": -5}, {"rate": 0}, {"rate": "abc"}, {"rate": 10**7}, {"exp": -1}, {"exp": 99}, {"alloc": 3}, {"alloc": -0.1}, {"bracket": "1-2"}, {"name": "  "}, {"name": "x" * 101}, {"start_date": "31/12/2026"}, {"genus": -1}, {"rate": True}):
        assert m.patch(u, json=body).status_code == 400, body
    assert m.patch(u, json={"rate": 2600, "alloc": 0.5, "exp": 7.5}).status_code == 200
    a = client("admin@local"); assert a.post("/api/users", json={"email": "not-an-email", "role": "manager"}).status_code == 400
    assert m.post("/api/team/import", files={"file": ("x.xlsx", b"not an excel file")}).status_code == 400
    assert m.post("/api/genus/upload", files={"file": ("x.xlsx", b"junk")}).status_code == 400

def test_old_bad_values_do_not_block_unrelated_edits():
    m = client("manager@local"); t = mk_team(m, "Legacy"); p = m.post(f"/api/team?team_id={t}").json()
    assert m.patch(f"/api/team/{p['id']}", json={"name": "Renamed", "rate": 2500, "genus": 1800, "alloc": 1}).status_code == 200

def test_scenarios_store_allocation_compare_and_undo():
    m = client("manager@local"); t = mk_team(m, "Scenario lab"); p = m.post(f"/api/team?team_id={t}").json(); pid = p["id"]
    m.patch(f"/api/team/{pid}", json={"alloc": 0.5}); sid = m.post(f"/api/scenarios?team_id={t}", json={"name": "Half time"}).json()["id"]
    m.patch(f"/api/team/{pid}", json={"alloc": 1, "rate": 4000})
    cmp = m.get(f"/api/scenarios/compare?a={sid}&b=current&team_id={t}&month=2026-10").json()
    assert cmp["rows"][0]["changed"] and cmp["rows"][0]["a"]["alloc"] == 0.5 and cmp["rows"][0]["b"]["rate"] == 4000 and cmp["b"]["revenue"] > cmp["a"]["revenue"]
    assert m.get(f"/api/scenarios/compare?a=baseline&b=current&team_id={t}").json()["rows"][0]["changed"]
    r = m.post(f"/api/scenarios/{sid}/apply").json(); cur = m.get(f"/api/team?team_id={t}").json()[0]
    assert cur["alloc"] == 0.5 and cur["rate"] == 2500 and r["undo_id"]                                   # allocation restored (was missed before)
    m.post(f"/api/scenarios/{r['undo_id']}/apply"); cur = m.get(f"/api/team?team_id={t}").json()[0]
    assert cur["alloc"] == 1 and cur["rate"] == 4000                                                      # Undo brings back what was there
    assert any(s["auto"] for s in m.get(f"/api/scenarios?team_id={t}").json())
    assert m.get(f"/api/scenarios/compare?a={sid}&b=current&team_id={mk_team(m, 'Other')}").status_code == 404   # scenario belongs to another team

def test_compare_shows_a_removed_person():
    m = client("manager@local"); t = mk_team(m, "Removal lab")
    m.post(f"/api/team?team_id={t}")
    b = m.post(f"/api/team?team_id={t}").json()
    before = m.post(f"/api/scenarios?team_id={t}", json={"name": "Both"}).json()["id"]
    assert m.delete(f"/api/team/{b['id']}").status_code == 200
    after = m.post(f"/api/scenarios?team_id={t}", json={"name": "One left"}).json()["id"]
    c = lambda x, y: m.get(f"/api/scenarios/compare?a={x}&b={y}&team_id={t}&month=2026-10").json()
    r = c("baseline", "current"); gone = [x for x in r["rows"] if x["status"] == "removed"]          # baseline still includes the removed person
    assert len(gone) == 1 and gone[0]["id"] == b["id"] and gone[0]["b"] is None and gone[0]["changed"]
    assert r["a"]["revenue"] > r["b"]["revenue"] and r["a"]["cost"] > r["b"]["cost"]                  # and the totals reflect it
    assert [x["status"] for x in c("baseline", after)["rows"]].count("removed") == 1                   # the case from the bug report
    assert [x["status"] for x in c(before, "current")["rows"]].count("removed") == 1                   # saved before the removal
    assert [x["status"] for x in c("current", before)["rows"]].count("added") == 1                     # direction flipped
    assert all(x["status"] is None for x in c(after, "current")["rows"])

def test_reimport_starts_a_new_baseline():
    m = client("manager@local"); t = mk_team(m, "Reimport lab"); p = m.post(f"/api/team?team_id={t}").json(); m.delete(f"/api/team/{p['id']}")
    from app.main import replace_team; from app.db import SessionLocal
    with SessionLocal() as db: replace_team(db, [], t)
    assert m.get(f"/api/scenarios/compare?a=baseline&b=current&team_id={t}").json()["rows"] == []

def test_restore_a_removed_person():
    m = client("manager@local"); t = mk_team(m, "Restore lab"); p = m.post(f"/api/team?team_id={t}").json()
    m.patch(f"/api/team/{p['id']}", json={"name": "Bayani", "rate": 3100, "alloc": 0.5})
    sid = m.post(f"/api/scenarios?team_id={t}", json={"name": "Before"}).json()["id"]; m.delete(f"/api/team/{p['id']}")
    assert m.get(f"/api/team?team_id={t}").json() == []
    row = m.get(f"/api/scenarios/compare?a=baseline&b=current&team_id={t}").json()["rows"][0]; assert row["restorable"] and row["status"] == "removed"
    r = m.post(f"/api/team/restore/{p['id']}?team_id={t}"); assert r.status_code == 200
    back = m.get(f"/api/team?team_id={t}").json(); assert len(back) == 1 and back[0]["id"] == p["id"] and back[0]["name"] == "Bayani" and back[0]["rate"] == 3100 and back[0]["alloc"] == 0.5
    assert back[0]["base"] == p["base"]                                                                       # original baseline comes back too
    cmp = m.get(f"/api/scenarios/compare?a={sid}&b=current&team_id={t}").json(); assert cmp["rows"][0]["status"] is None and not cmp["rows"][0]["changed"]
    assert m.post(f"/api/team/restore/{p['id']}?team_id={t}").status_code == 404                              # nothing left to restore
    assert client("ravi.manager@local").post(f"/api/team/restore/{p['id']}?team_id={t}").status_code in (403, 404)
