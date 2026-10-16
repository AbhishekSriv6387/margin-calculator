"""Sharing a team with other people: view-only vs can-edit, owner-only, and private teams stay hidden from admins."""
from .test_api import client

def names(c): return [t["name"] for t in c.get("/api/teams").json()]

def test_share_view_only_then_edit_then_remove():
    client("admin@local").post("/api/users", json={"email": "pat@company.com", "role": "manager"})
    o, p = client("manager@local"), client("pat@company.com")
    tid = o.post("/api/teams", json={"name": "Shared one", "calendar_id": 1}).json()["id"]; pid = o.post(f"/api/team?team_id={tid}").json()["id"]
    assert "Shared one" not in names(p)
    assert o.put(f"/api/teams/{tid}/shares", json={"email": "pat@company.com", "edit": False}).status_code == 200
    t = next(x for x in p.get("/api/teams").json() if x["name"] == "Shared one"); assert t["can_edit"] is False and t["owner"] == "manager@local"
    assert p.get(f"/api/team?team_id={tid}").status_code == 200
    for r in (p.patch(f"/api/team/{pid}", json={"rate": 2000}), p.post(f"/api/team?team_id={tid}"), p.delete(f"/api/team/{pid}"), p.post(f"/api/scenarios?team_id={tid}", json={"name": "x"}),
              p.patch(f"/api/teams/{tid}", json={"name": "hijack"})): assert r.status_code == 403
    assert p.get(f"/api/teams/{tid}/shares").status_code == 403                                    # only the owner manages sharing
    assert o.put(f"/api/teams/{tid}/shares", json={"email": "pat@company.com", "edit": True}).status_code == 200
    assert p.patch(f"/api/team/{pid}", json={"rate": 2000}).status_code == 200
    assert [x["email"] for x in o.get(f"/api/teams/{tid}/shares").json()] == ["manager@local", "pat@company.com"]
    assert o.delete(f"/api/teams/{tid}/shares?email=pat@company.com").status_code == 200 and p.get(f"/api/team?team_id={tid}").status_code == 404
    assert o.delete(f"/api/teams/{tid}").status_code == 403                                         # managers still cannot delete public teams
    client("admin@local").delete(f"/api/teams/{tid}")

def test_share_rules_and_new_accounts():
    o = client("manager@local"); tid = o.post("/api/teams", json={"name": "Shared two", "calendar_id": 1, "private": True}).json()["id"]
    put = lambda e: o.put(f"/api/teams/{tid}/shares", json={"email": e}).status_code
    assert put("manager@local") == 400 and put("demo1projectmanager@demo.example") == 400 and put("not-an-email") == 400
    assert put("new.person@company.com") == 200                                                      # an account is created for someone who has not signed in yet
    a = client("admin@local"); assert "Shared two" not in names(a) and a.get(f"/api/teams/{tid}/shares").status_code == 404
    assert "Shared two" in names(client("new.person@company.com"))
    o.delete(f"/api/teams/{tid}")
