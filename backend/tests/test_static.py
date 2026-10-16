"""The front-end is served as separate files that browsers re-check on every visit, and large responses are compressed."""
import re
from fastapi.testclient import TestClient
from app.main import app

def page(): return TestClient(app).get("/")

def test_page_references_files_that_exist():
    c = TestClient(app); r = c.get("/")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
    refs = re.findall(r'(?:src|href)="(/static/[^"]+)"', r.text)
    assert "/static/css/app.css" in refs and "/static/js/app.js" in refs and "/static/img/favicon.png" in refs and len(refs) == 10
    for ref in refs + ["/static/img/nagarro-logo.png"]:     # the logo is used by the header, footer and sign-in page
        got = c.get(ref); assert got.status_code == 200, ref
        assert got.headers["cache-control"] == "no-cache", ref

def test_scripts_load_in_dependency_order():
    refs = re.findall(r'src="/static/js/([a-z]+)\.js"', page().text)
    assert refs[0] == "core" and refs[-1] == "app"          # shared helpers first, start-up last

def test_large_responses_are_compressed():
    r = TestClient(app).get("/static/css/app.css", headers={"accept-encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"

def test_no_external_requests_in_the_page():
    html = page().text
    assert "fonts.googleapis" not in html and "http://" not in html and "https://" not in html
