from fastapi.testclient import TestClient
from app import auth
from app.main import app

def fresh():
    c = TestClient(app); c.__enter__(); return c

def test_new_manager_signs_in_with_email_only_and_builds_a_team(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); c = fresh()
    assert c.get("/api/teams").status_code == 401
    assert c.post("/auth/email-login", json={"email": "New.PM@Company.com "}).status_code == 200
    me = c.get("/auth/me").json(); assert me["email"] == "new.pm@company.com" and me["role"] == "manager"
    assert c.get("/api/teams").json() == []                                           # starts empty: sees nothing of anyone else's
    tid = c.post("/api/teams/sample").json()["id"]
    assert [t["name"] for t in c.get("/api/teams").json()] == ["Sample team"]
    assert len(c.get(f"/api/team?team_id={tid}").json()) == 8
    assert c.post("/api/teams", json={"name": "Mine", "calendar_id": c.get("/api/calendars").json()[0]["id"]}).status_code == 200
    assert c.get("/api/users").status_code == 403 and c.get("/api/audit").status_code == 403   # no admin rights

def test_two_managers_can_use_the_same_team_name_and_cannot_see_each_other(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); a, b = fresh(), fresh()
    a.post("/auth/email-login", json={"email": "a1@company.com"}); b.post("/auth/email-login", json={"email": "b1@company.com"})
    ta = a.post("/api/teams/sample").json()["id"]; tb = b.post("/api/teams/sample").json()["id"]
    assert [t["name"] for t in a.get("/api/teams").json()] == ["Sample team"] == [t["name"] for t in b.get("/api/teams").json()]
    assert b.get(f"/api/team?team_id={ta}").status_code == 404 and a.get(f"/api/team?team_id={tb}").status_code == 404
    assert a.post("/api/teams/sample").json()["id"] and sorted(t["name"] for t in a.get("/api/teams").json()) == ["Sample team", "Sample team 2"]

def test_email_signin_rules(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); c = fresh()
    assert c.post("/auth/email-login", json={"email": "not-an-email"}).status_code == 400
    assert c.post("/auth/email-login", json={"email": "admin@local"}).status_code == 400
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAIN", "company.com")
    assert c.post("/auth/email-login", json={"email": "x@other.com"}).status_code == 403
    assert c.post("/auth/email-login", json={"email": "x@company.com"}).status_code == 200

def test_admin_cannot_sign_in_by_email_and_needs_the_password(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); monkeypatch.setattr(auth.time, "sleep", lambda s: None); c = fresh()
    d = fresh(); d.post("/auth/email-login", json={"email": "boss@company.com"})
    from app.db import SessionLocal, User
    with SessionLocal() as db: u = db.query(User).filter_by(email="boss@company.com").first(); u.role = "admin"; db.commit()
    assert c.post("/auth/email-login", json={"email": "boss@company.com"}).status_code == 403
    assert c.post("/auth/admin-login", json={"email": "boss@company.com", "password": "x"}).status_code == 403   # not set up
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret"); auth._fails.clear()
    assert c.post("/auth/admin-login", json={"email": "boss@company.com", "password": "wrong"}).status_code == 401
    assert c.post("/auth/admin-login", json={"email": "manager@local", "password": "s3cret"}).status_code == 401  # not an admin
    assert c.post("/auth/admin-login", json={"email": "boss@company.com", "password": "s3cret"}).status_code == 200
    assert c.get("/auth/me").json()["role"] == "admin"

def test_admin_password_attempts_are_limited(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "email"); monkeypatch.setattr(auth.time, "sleep", lambda s: None); monkeypatch.setenv("ADMIN_PASSWORD", "s3cret"); auth._fails.clear(); c = fresh()
    codes = [c.post("/auth/admin-login", json={"email": "boss@company.com", "password": "no"}).status_code for _ in range(7)]
    assert codes[:5] == [401] * 5 and codes[5:] == [429, 429]; auth._fails.clear()

def test_dev_and_email_logins_are_closed_in_the_wrong_mode(monkeypatch):
    monkeypatch.setattr(auth, "MODE", "oidc"); c = fresh()
    assert c.post("/auth/email-login", json={"email": "a@company.com"}).status_code == 404
    assert c.post("/auth/dev-login", json={"email": "admin@local"}).status_code == 404

def test_session_secret_is_never_a_known_default(monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    from app.main import session_secret; s = session_secret(); assert len(s) >= 32 and s != "dev-only-change-me" and session_secret() == s
