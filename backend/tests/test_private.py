"""Private teams: hidden from administrators too, and the audit log does not leak their details."""
from .test_api import client

def mine(c): return {t["name"]: t for t in c.get("/api/teams").json()}

def test_private_team_is_hidden_from_admins_but_not_from_its_owner():
    m, a = client("manager@local"), client("admin@local")
    tid = m.post("/api/teams", json={"name": "Hush project", "calendar_id": 1, "private": True}).json()["id"]
    assert "Hush project" in mine(m) and mine(m)["Hush project"]["private"] is True
    assert "Hush project" not in mine(a)
    for url in (f"/api/team?team_id={tid}", f"/api/scenarios?team_id={tid}", f"/api/insights?team_id={tid}", f"/api/export?team_id={tid}"):
        assert a.get(url).status_code == 404, url
    assert a.patch(f"/api/teams/{tid}", json={"name": "x"}).status_code == 404 and a.delete(f"/api/teams/{tid}").status_code == 404
    assert client("priya.manager@local").get(f"/api/team?team_id={tid}").status_code == 404
    assert m.delete(f"/api/teams/{tid}").status_code == 200                                         # tidy up: the owner can delete it

def test_admin_cannot_grant_access_to_a_private_team_or_see_its_audit_details():
    m, a = client("manager@local"), client("admin@local")
    tid = m.post("/api/teams", json={"name": "Hush audit", "calendar_id": 1, "private": True}).json()["id"]
    pid = m.post(f"/api/team?team_id={tid}").json()["id"]; m.patch(f"/api/team/{pid}", json={"name": "Secret Person"})
    uid = next(u["id"] for u in a.get("/api/users").json() if u["email"] == "manager@local")
    assert a.put(f"/api/users/{uid}/teams", json={"team_ids": [tid]}).status_code == 400
    assert tid not in next(u for u in a.get("/api/users").json() if u["email"] == "manager@local")["team_ids"]
    log = a.get("/api/audit").json(); text = str(log)
    assert "Secret Person" not in text and "Hush audit" not in text
    assert any(r["action"] == "person_edit" and r["entity"] == "private team" for r in log)
    m.delete(f"/api/teams/{tid}")

def test_admin_reassigning_access_does_not_wipe_a_managers_private_team():
    m, a = client("manager@local"), client("admin@local")
    tid = m.post("/api/teams", json={"name": "Hush keep", "calendar_id": 1, "private": True}).json()["id"]
    uid = next(u["id"] for u in a.get("/api/users").json() if u["email"] == "manager@local")
    main = mine(a)["Main team"]["id"]; assert a.put(f"/api/users/{uid}/teams", json={"team_ids": [main]}).status_code == 200
    assert "Hush keep" in mine(m); m.delete(f"/api/teams/{tid}")

def test_only_the_creator_changes_privacy_and_can_delete_a_private_team():
    m, a = client("manager@local"), client("admin@local")
    pub = m.post("/api/teams", json={"name": "Open one", "calendar_id": 1}).json()["id"]
    assert "Open one" in mine(a) and mine(m)["Open one"]["mine"] is True
    assert a.patch(f"/api/teams/{pub}", json={"private": True}).status_code == 403                 # an admin cannot hide someone else's team
    assert m.patch(f"/api/teams/{pub}", json={"private": True}).status_code == 200 and "Open one" not in mine(a)
    assert client("priya.manager@local").delete(f"/api/teams/{pub}").status_code == 403
    assert m.delete(f"/api/teams/{pub}").status_code == 200 and "Open one" not in mine(m)

def test_admin_created_private_team_stays_visible_to_that_admin():
    a = client("admin2@local"); a.post("/api/teams", json={"name": "Admin hush", "calendar_id": 1, "private": True})
    assert "Admin hush" in mine(a) and "Admin hush" not in mine(client("admin@local"))
    a.delete(f"/api/teams/{mine(a)['Admin hush']['id']}")
