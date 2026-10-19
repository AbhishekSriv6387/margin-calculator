import io, datetime as dt, openpyxl
from fastapi.testclient import TestClient
from app.main import app
from app.calc import business_days

def client(email):
    c = TestClient(app); c.__enter__(); assert c.post("/auth/dev-login", json={"email": email}).status_code == 200; return c

def test_business_days():
    assert business_days(2026, 10)[0] == 22
    n, hl = business_days(2026, 10, [dt.date(2026, 10, 2)]); assert n == 21 and hl == ["2026-10-02"]
    assert business_days(2026, 2)[0] == 20

def test_requires_login():
    assert TestClient(app).get("/api/team").status_code == 401

def test_manager_gets_cost_but_not_admin_endpoints():
    c = client("manager@local"); t = c.get("/api/team").json(); assert t
    for m in t: assert m["genus"] > 0 and "warnings" in m and m["band"] in ("loss", "red", "amber", "green")
    assert c.get("/api/genus").status_code == 200 and c.get("/api/audit").status_code == 403 and c.get("/api/users").status_code == 403

def test_manager_edit_is_audited_and_maker_checker():
    m = client("manager@local"); t = m.get("/api/team").json(); pid = t[0]["id"]
    assert "genus" in t[0]; assert m.patch(f"/api/team/{pid}", json={"rate": 3000}).json()["rate"] == 3000
    wb = openpyxl.Workbook(); ws = wb.active; ws.append(["ServiceRegion", "Country", "ServiceLocation", "Genus", "Currency", "Genus Cost"])
    ws.append(["R", "India", "Pune", "3.1-JAVA", "INR", 1900]); ws.append(["R", "India", "Pune", "3.1-JAVA", "INR", 1]); ws.append(["R", "India", "Pune", "9.9-X", "INR", 5])
    b = io.BytesIO(); wb.save(b)
    r = m.post("/api/genus/upload", files={"file": ("g.xlsx", b.getvalue())}).json(); assert r["accepted"] == 1 and r["rejected_count"] == 2
    assert m.post(f"/api/genus/versions/{r['id']}/approve").status_code == 403  # manager cannot approve
    a = client("admin@local"); assert a.post(f"/api/genus/versions/{r['id']}/approve").status_code == 200
    assert any(x["action"] == "person_edit" and x["details"]["changes"]["rate"] == [t[0]["rate"], 3000] for x in a.get("/api/audit").json())
    assert any(x["action"] == "genus_approve" for x in a.get("/api/audit").json())
    vs = a.get("/api/genus/versions").json(); old = [v for v in vs if v["status"] == "archived"][0]
    assert a.post(f"/api/genus/versions/{old['id']}/approve").status_code == 200  # rollback
    assert a.get("/api/genus").json()["3.1-JAVA".replace("-", "-")]["cost"] == 1800

def test_admin_cannot_approve_own_upload():
    a = client("admin@local"); wb = openpyxl.Workbook(); ws = wb.active; ws.append(["Genus", "Genus Cost"]); ws.append(["3.1-JAVA", 2000]); b = io.BytesIO(); wb.save(b)
    vid = a.post("/api/genus/upload", files={"file": ("g.xlsx", b.getvalue())}).json()["id"]
    assert a.post(f"/api/genus/versions/{vid}/approve").status_code == 403
    assert client("admin2@local").post(f"/api/genus/versions/{vid}/reject").status_code == 200

def test_period():
    assert client("manager@local").get("/api/period?month=2026-10").json()["business_days"] == 21
