"""Feedback and improvement ideas from any signed-in user.
Every submission is saved to data/feedback.jsonl and noted in the audit log. It is also emailed to FEEDBACK_TO
(default: the tool owner) when a mail server is set in .env (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM).
Without a mail server the answer says so and the page offers a ready-made email instead, so nothing is lost."""
import os, json, smtplib, datetime as dt
from email.message import EmailMessage
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from . import auth
from .db import get_db, log

router = APIRouter()
DEFAULT_TO = "abhishek.srivastava04@nagarro.com"
KINDS = {"idea": "Improvement idea", "bug": "Something is not working", "other": "Other feedback"}
FILE = Path(__file__).resolve().parent.parent / "data" / "feedback.jsonl"

def recipient(): return os.getenv("FEEDBACK_TO") or DEFAULT_TO

def send_mail(subject, body, reply_to):
    """Returns True when the email was handed to the mail server, False when no mail server is set up or it failed."""
    host = os.getenv("SMTP_HOST")
    if not host: return False
    try:
        m = EmailMessage(); m["To"] = recipient(); m["Subject"] = subject
        m["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "margin-calculator@localhost"
        if reply_to: m["Reply-To"] = reply_to
        m.set_content(body)
        port = int(os.getenv("SMTP_PORT") or 587)
        with (smtplib.SMTP_SSL(host, port, timeout=15) if port == 465 else smtplib.SMTP(host, port, timeout=15)) as s:
            if port != 465 and os.getenv("SMTP_STARTTLS", "1") != "0": s.starttls()
            if os.getenv("SMTP_USER"): s.login(os.environ["SMTP_USER"], os.getenv("SMTP_PASSWORD", ""))
            s.send_message(m)
        return True
    except Exception: return False

@router.get("/api/feedback/info")
def feedback_info(u=Depends(auth.current_user)): return {"to": recipient()}

@router.post("/api/feedback")
def feedback(b: dict, u=Depends(auth.current_user), db=Depends(get_db)):
    msg = str(b.get("message") or "").strip(); kind = b.get("kind") if b.get("kind") in KINDS else "idea"
    if len(msg) < 5: raise HTTPException(400, "Please write a few words about your feedback.")
    if len(msg) > 4000: raise HTTPException(400, "Please keep feedback under 4000 characters.")
    page = str(b.get("page") or "")[:60]
    rec = {"ts": dt.datetime.utcnow().isoformat(timespec="seconds"), "user": u.email, "kind": kind, "page": page, "message": msg}
    try:
        FILE.parent.mkdir(exist_ok=True)
        with FILE.open("a", encoding="utf-8") as fh: fh.write(json.dumps(rec) + "\n")
    except OSError: pass
    sent = send_mail(f"[Margin Calculator] {KINDS[kind]} from {u.email}", f"From: {u.email}\nType: {KINDS[kind]}\nScreen: {page or '-'}\nTime (UTC): {rec['ts']}\n\n{msg}\n", u.email)
    log(db, u, "feedback", "feedback", "", {"type": kind, "emailed": sent, "characters": len(msg)})
    return {"ok": True, "emailed": sent, "to": recipient()}
