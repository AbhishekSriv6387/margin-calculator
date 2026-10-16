"""Feedback: saved, audited, emailed to the owner when a mail server is set, and never lost when it is not."""
import json
from fastapi.testclient import TestClient
from app.main import app
from app import feedback
from .test_api import client

def test_feedback_is_saved_and_falls_back_without_mail_server(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "FILE", tmp_path / "feedback.jsonl"); monkeypatch.delenv("SMTP_HOST", raising=False)
    c = client("manager@local")
    r = c.post("/api/feedback", json={"kind": "idea", "message": "Please add a CSV export", "page": "calc"})
    assert r.status_code == 200 and r.json()["emailed"] is False and r.json()["to"] == "abhishek.srivastava04@nagarro.com"
    rec = json.loads((tmp_path / "feedback.jsonl").read_text().splitlines()[0])
    assert rec["user"] == "manager@local" and rec["message"] == "Please add a CSV export" and rec["kind"] == "idea"
    assert any(a["action"] == "feedback" for a in client("admin@local").get("/api/audit").json())

def test_feedback_is_emailed_when_a_mail_server_is_set(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "FILE", tmp_path / "feedback.jsonl"); sent = []
    monkeypatch.setattr(feedback, "send_mail", lambda subject, body, reply_to: sent.append((subject, body, reply_to)) or True)
    r = client("manager@local").post("/api/feedback", json={"kind": "bug", "message": "The chart is empty"})
    assert r.json()["emailed"] is True and "The chart is empty" in sent[0][1] and sent[0][2] == "manager@local"

def test_feedback_needs_sign_in_and_a_message(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "FILE", tmp_path / "feedback.jsonl")
    assert TestClient(app).post("/api/feedback", json={"message": "hello there"}).status_code == 401
    c = client("manager@local")
    assert c.post("/api/feedback", json={"message": "  "}).status_code == 400
    assert c.post("/api/feedback", json={"message": "x" * 4001}).status_code == 400

def test_overview_presentation_is_served():
    r = TestClient(app).get("/static/docs/Margin_Calculator_Overview.pptx")
    assert r.status_code == 200 and r.content[:2] == b"PK"
