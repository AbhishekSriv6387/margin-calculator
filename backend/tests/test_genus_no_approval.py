from app import main
from .test_api import client
from .test_countries import upload, versions, active

def test_manager_upload_is_live_without_approval(monkeypatch):
    monkeypatch.setattr(main, "NEEDS_APPROVAL", False)
    m = client("manager@local")
    r = upload(m, [("EU", "Poland", "Warsaw", "3.1-JAVA", "PLN", 120), ("EU", "Poland", "Warsaw", "3.2-JAVA", "PLN", 150)]).json()
    assert r["approval_required"] is False and r["versions"][0]["status"] == "active" and [v["status"] for v in versions(m, "Poland")] == ["active"]
    assert "Poland" in [c["country"] for c in m.get("/api/genus/countries").json()]            # it prices teams already
    r2 = upload(m, [("EU", "Poland", "Warsaw", "3.1-JAVA", "PLN", 130)]).json()                  # a second upload replaces only Poland's table
    assert [v["status"] for v in versions(m, "Poland")] == ["active", "archived"] and active(m, "India")
    old = versions(m, "Poland")[1]["id"]
    assert m.post(f"/api/genus/versions/{old}/approve").status_code == 200                       # a manager can roll back too
    assert versions(m, "Poland")[1]["status"] == "active" or versions(m, "Poland")[0]["status"] == "archived"

def test_approval_can_be_switched_back_on():
    m = client("manager@local"); r = upload(m, [("EU", "Sweden", "Stockholm", "3.1-JAVA", "SEK", 700)]).json()
    assert r["approval_required"] is True and versions(m, "Sweden")[0]["status"] == "pending"
    assert m.post(f"/api/genus/versions/{r['id']}/approve").status_code == 403
