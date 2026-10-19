import io, openpyxl
from .test_api import client
from .test_teams import mk_team

HDR = ("ServiceRegion", "Country", "ServiceLocation", "Genus", "Currency", "Genus Cost")
OLD = ("ServiceRegion", "Country", "Genus", "Currency", "Genus Cost")   # the format before ServiceLocation was added: still accepted

def sheet(rows, header=HDR):
    wb = openpyxl.Workbook(); ws = wb.active; ws.append(list(header))
    for r in rows: ws.append(list(r))
    b = io.BytesIO(); wb.save(b); return b.getvalue()

def upload(c, rows, header=HDR, name="g.xlsx"):
    return c.post("/api/genus/upload", files={"file": (name, sheet(rows, header))})

def versions(c, country=None):
    return [v for v in c.get("/api/genus/versions").json() if country is None or v["country"] == country]

def active(c, country):
    return [v for v in versions(c, country) if v["status"] == "active"]

DE = [("EU", "Germany", "Berlin", "3.1-JAVA", "EUR", 60), ("EU", "Germany", "Berlin", "3.2-JAVA", "EUR", 75), ("EU", "Germany", "Berlin", "3.1-DEVOPS", "EUR", 66), ("EU", "Germany", "Berlin", "9.9-BAD", "EUR", 5)]
JP = [("AP", "Japan", "Tokyo", "3.1-JAVA", "JPY", 5200), ("AP", "Japan", "Tokyo", "3.2-JAVA", "JPY", 6400)]

def test_one_sheet_can_hold_several_countries():
    m = client("manager@local"); r = upload(m, DE + JP).json()
    assert {v["country"] for v in r["versions"]} == {"Germany", "Japan"} and r["accepted"] == 5 and r["rejected_count"] == 1
    de = versions(m, "Germany")[0]
    assert de["status"] == "pending" and de["currency"] == "EUR" and de["rows"] == 3 and de["report"]["rejected_count"] == 1
    assert versions(m, "Japan")[0]["currency"] == "JPY" and versions(m, "Japan")[0]["report"]["rejected_count"] == 0
    assert "Germany" not in [c["country"] for c in m.get("/api/genus/countries").json()]    # pending tables do not price anything yet

def test_currency_rules():
    m = client("manager@local")
    r = upload(m, [("S", "Chile", "Santiago", "3.1-JAVA", "CLP", 21000), ("S", "Chile", "Santiago", "3.2-JAVA", "CLP", 26000), ("S", "Chile", "Santiago", "3.3-JAVA", "usd", 30)]).json()
    assert r["accepted"] == 2 and r["rejected_count"] == 1 and "differs from CLP" in r["rejected"][0]
    assert upload(m, [("S", "Peru", "Lima", "3.1-JAVA", "SOLES", 90)]).status_code == 400                  # not a 3-letter code
    assert upload(m, [("S", "Spain", "Madrid", "3.1-JAVA", "", 90)]).status_code == 400                      # currency is required outside the default country
    old = upload(m, [("3.1-JAVA", 1700)], header=("Genus", "Genus Cost")).json()                   # the older two-column format still works
    v = [x for x in versions(m) if x["id"] == old["id"]][0]; assert v["country"] == "India" and v["currency"] == "INR"
    assert client("admin@local").post(f"/api/genus/versions/{old['id']}/reject").status_code == 200  # keep the default country untouched
    blank = upload(m, [("S", "", "Pune", "3.1-JAVA", "", 1650)]).json()                                     # blank country and currency = the defaults
    assert blank["versions"][0]["country"] == "India" and blank["versions"][0]["currency"] == "INR"
    assert client("admin@local").post(f"/api/genus/versions/{blank['id']}/reject").status_code == 200

def test_approving_one_country_leaves_the_others_alone():
    a, a2, m = client("admin@local"), client("admin2@local"), client("manager@local")
    india = active(a, "India")[0]["id"]
    de, jp = versions(m, "Germany")[0]["id"], versions(m, "Japan")[0]["id"]
    assert a.post(f"/api/genus/versions/{de}/approve").json()["country"] == "Germany"
    assert a.post(f"/api/genus/versions/{jp}/approve").status_code == 200
    cs = {c["country"]: c["currency"] for c in m.get("/api/genus/countries").json()}
    assert cs["India"] == "INR" and cs["Germany"] == "EUR" and cs["Japan"] == "JPY" and list(cs)[0] == "India"
    assert active(a, "India")[0]["id"] == india                                                      # India's table was not touched
    r2 = upload(m, [("EU", "germany", "Berlin", "3.1-JAVA", "EUR", 63), ("EU", "Germany", "Berlin", "3.2-JAVA", "EUR", 75), ("EU", "Germany", "Berlin", "3.1-DEVOPS", "EUR", 66)]).json()
    assert r2["versions"][0]["country"] == "Germany"                                                 # same country in other capitals is the same country
    a.post(f"/api/genus/versions/{r2['id']}/approve")
    assert [v["id"] for v in active(a, "Germany")] == [r2["id"]] and versions(a, "Germany")[1]["status"] == "archived"
    assert active(a, "India")[0]["id"] == india and len(active(a, "Japan")) == 1
    assert a.get(f"/api/genus/versions/{r2['id']}/diff").json()["country"] == "Germany"

def test_maker_checker_still_applies_in_every_country():
    a = client("admin@local"); r = upload(a, [("AP", "Japan", "Tokyo", "3.1-JAVA", "JPY", 5400)]).json()
    assert a.post(f"/api/genus/versions/{r['id']}/approve").status_code == 403
    assert client("admin2@local").post(f"/api/genus/versions/{r['id']}/reject").status_code == 200

def test_a_country_keeps_its_currency():
    m = client("manager@local"); n = len(versions(m, "Germany"))
    r = upload(m, [("EU", "Germany", "Berlin", "3.1-JAVA", "USD", 65)]); assert r.status_code == 400 and "priced in EUR" in r.json()["detail"]
    assert len(versions(m, "Germany")) == n

def test_a_team_is_priced_in_its_countrys_currency():
    m = client("manager@local"); de = mk_team(m, "Berlin delivery", country="Germany"); main = m.get("/api/teams").json()[0]["id"]
    t = {x["id"]: x for x in m.get("/api/teams").json()}
    assert t[de]["country"] == "Germany" and t[de]["currency"] == "EUR" and t[main]["country"] == "India" and t[main]["currency"] == "INR"
    p = m.get(f"/api/period?month=2026-10&team_id={de}").json()
    assert p["currency"] == "EUR" and p["country"] == "Germany" and p["ranges"]["genus"][0] < 60 < p["ranges"]["genus"][1] and p["ranges"]["genus"][2] <= 1
    pi = m.get(f"/api/period?month=2026-10&team_id={main}").json(); assert pi["currency"] == "INR" and pi["ranges"] is None   # India keeps the classic ranges
    g = m.get(f"/api/genus?team_id={de}").json(); assert g["3.1-JAVA"]["cost"] == 63 and m.get("/api/genus").json()["3.1-JAVA"]["cost"] != 63
    wb = openpyxl.Workbook(); ws = wb.active; ws.append(["Team Member", "Role per MSA", "Rate Card", "Current Experience"]); ws.append(["Anna", "3.1-JAVA", 95, 4]); b = io.BytesIO(); wb.save(b)
    assert m.post(f"/api/team/import?team_id={de}", files={"file": ("t.xlsx", b.getvalue())}).status_code == 200
    line = m.get(f"/api/team?team_id={de}").json()[0]; assert line["genus"] == 63 and line["genus_override"] is False
    new = m.post(f"/api/team?team_id={de}").json(); assert new["genus"] == 66 and 90 < new["rate"] < 95    # the middle of Germany's table, not 1800 / 2500
    assert m.post(f"/api/team?team_id={main}").json()["rate"] == 2500

def test_reprice_uses_each_teams_own_country():
    a, m = client("admin@local"), client("manager@local"); de = next(x["id"] for x in m.get("/api/teams").json() if x["name"] == "Berlin delivery"); main = m.get("/api/teams").json()[0]["id"]
    india_before = [x["genus"] for x in m.get(f"/api/team?team_id={main}").json()]
    r = upload(m, [("EU", "Germany", "Berlin", "3.1-JAVA", "EUR", 70)]).json(); a.post(f"/api/genus/versions/{r['id']}/approve")
    assert m.post(f"/api/team/reprice?team_id={de}").json()["changed"] == 1
    assert m.get(f"/api/team?team_id={de}").json()[0]["genus"] == 70
    m.post("/api/team/reprice"); assert [x["genus"] for x in m.get(f"/api/team?team_id={main}").json()] == india_before   # the German change never reaches Indian teams

def test_team_country_rules():
    m = client("manager@local"); de = next(x["id"] for x in m.get("/api/teams").json() if x["name"] == "Berlin delivery"); main = m.get("/api/teams").json()[0]["id"]
    assert m.post("/api/teams", json={"name": "Atlantis team", "country": "Atlantis"}).status_code == 400        # no approved table for it
    assert m.post("/api/teams", json={"name": "Mixed copy", "country": "Germany", "copy_from": main}).status_code == 400   # people cannot move between currencies
    assert m.post("/api/teams", json={"name": "Tokyo copy", "country": "japan"}).status_code == 200              # any capitals
    t = mk_team(m, "Moves later"); assert m.patch(f"/api/teams/{t}", json={"country": "Japan"}).status_code == 200
    assert next(x for x in m.get("/api/teams").json() if x["id"] == t)["currency"] == "JPY"
    assert m.patch(f"/api/teams/{t}", json={"country": "Atlantis"}).status_code == 400
    assert any(x["action"] == "team_edit" and x["details"].get("country") == ["India", "Japan"] for x in client("admin@local").get("/api/audit").json())

def test_old_database_gets_the_new_columns(tmp_path, monkeypatch):
    import sqlalchemy as sa
    from app import db as dbm
    eng = sa.create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with eng.begin() as c:
        c.execute(sa.text("CREATE TABLE genus_versions (id INTEGER PRIMARY KEY, label VARCHAR, status VARCHAR, created_by VARCHAR, created_at DATETIME, decided_by VARCHAR, decided_at DATETIME, source_status VARCHAR, report JSON)"))
        c.execute(sa.text("CREATE TABLE teams (id INTEGER PRIMARY KEY, name VARCHAR, calendar_id INTEGER, created_by VARCHAR, created_at DATETIME, unit VARCHAR, simulated BOOLEAN, removed JSON, private BOOLEAN)"))
        c.execute(sa.text("INSERT INTO genus_versions (id, label, status) VALUES (1, 'Initial', 'active')"))
    monkeypatch.setattr(dbm, "engine", eng); dbm.ensure_schema()
    cols = lambda t: {x["name"] for x in sa.inspect(eng).get_columns(t)}
    assert {"country", "currency"} <= cols("genus_versions") and "country" in cols("teams")
    with eng.begin() as c: assert c.execute(sa.text("SELECT label FROM genus_versions")).scalar() == "Initial"   # nothing was lost


def test_service_location_is_read_and_kept():
    m = client("manager@local")
    r = upload(m, [("EU", "France", "Paris", "3.1-JAVA", "EUR", 61), ("EU", "France", "Lyon", "3.2-JAVA", "EUR", 74), ("EU", "France", "", "3.3-JAVA", "EUR", 80)]).json()
    v = versions(m, "France")[0]
    assert r["accepted"] == 3 and r["rejected_count"] == 0 and v["rows"] == 3 and v["locations"] == ["Lyon", "Paris"]   # a blank location is allowed

def test_a_genus_can_appear_only_once_per_country():
    m = client("manager@local")
    r = upload(m, [("EU", "Italy", "Rome", "3.1-JAVA", "EUR", 58), ("EU", "Italy", "Milan", "3.1-JAVA", "EUR", 62)]).json()
    assert r["accepted"] == 1 and r["rejected_count"] == 1 and "once per country" in r["rejected"][0] and "Milan" in r["rejected"][0]

def test_sheet_without_service_location_still_works():
    m = client("manager@local"); r = upload(m, [("EU", "Austria", "3.1-JAVA", "EUR", 59)], header=OLD).json()
    assert r["accepted"] == 1 and versions(m, "Austria")[0]["locations"] == []
