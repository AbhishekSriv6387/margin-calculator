from fastapi.testclient import TestClient
from app import auth
from app.main import app

D = "@demo.example"
def fresh():
    c = TestClient(app); c.__enter__(); return c
def names(c): return sorted(t["name"].split(":")[0] for t in c.get("/api/teams").json())

def test_sign_in_page_lists_the_demo_accounts(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); c = fresh(); d = c.get("/auth/config").json()["demo"]
    assert [x["label"] for x in d] == ["Administrator", "Project manager 1", "Project manager 2", "Delivery manager 1", "Delivery manager 2"]
    assert [x["email"] for x in d][:2] == ["demoadmin" + D, "demo1projectmanager" + D]
    monkeypatch.setenv("DEMO_DATA", "0"); assert fresh().get("/auth/config").json()["demo"] == []
    assert fresh().post("/auth/demo-login", json={"email": "demoadmin" + D}).status_code == 404

def test_each_demo_account_sees_its_own_projects(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); seen = {}
    for e in ("demo1projectmanager", "demo2projectmanager", "demo1delmanager", "demo2delmanager", "demoadmin"):
        c = fresh(); assert c.post("/auth/demo-login", json={"email": e + D}).status_code == 200; seen[e] = names(c)
    assert seen["demo1projectmanager"] == ["Atlas", "Beacon", "Main team"] and seen["demo2projectmanager"] == ["Cobalt", "Delta"]
    assert seen["demo1delmanager"] == ["Atlas", "Ember", "Flux"] and seen["demo2delmanager"] == ["Beacon", "Cobalt", "Flux"]
    assert len(seen["demoadmin"]) >= 7                                              # administrator sees every team

def test_demo_roles_are_real_roles(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); a, m = fresh(), fresh()
    a.post("/auth/demo-login", json={"email": "demoadmin" + D}); m.post("/auth/demo-login", json={"email": "demo1delmanager" + D})
    assert a.get("/auth/me").json() == {"email": "demoadmin" + D, "name": "demoadmin", "role": "admin", "demo": True}
    assert m.get("/auth/me").json()["role"] == "manager" and m.get("/api/users").status_code == 403 and a.get("/api/users").status_code == 200

def test_demo_accounts_cannot_be_broken_or_typed_in(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); a = fresh(); a.post("/auth/demo-login", json={"email": "demoadmin" + D})
    uid = next(u["id"] for u in a.get("/api/users").json() if u["email"] == "demo1projectmanager" + D)
    assert a.patch(f"/api/users/{uid}", json={"active": False}).status_code == 400
    assert a.patch(f"/api/users/{uid}", json={"role": "admin"}).status_code == 400
    assert a.put(f"/api/users/{uid}/teams", json={"team_ids": []}).status_code == 400
    assert fresh().post("/auth/email-login", json={"email": "demoadmin" + D}).status_code == 403
    assert fresh().post("/auth/email-login", json={"email": "demo1projectmanager" + D}).status_code == 403
    assert fresh().post("/auth/demo-login", json={"email": "someone@company.com"}).status_code == 404
    assert fresh().post("/auth/demo-login", json={"email": "demo9projectmanager" + D}).status_code == 404

def test_demo_login_closed_outside_email_mode(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "oidc"); assert fresh().post("/auth/demo-login", json={"email": "demoadmin" + D}).status_code == 404
