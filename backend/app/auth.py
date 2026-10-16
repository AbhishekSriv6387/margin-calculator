import os, re, time, hmac
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from .db import get_db, User, TeamAccess, log

# email = work-email sign-in for internal demos (no password, see README) | oidc = company SSO | dev = local test picker
MODE = os.getenv("AUTH_MODE", "email")
router = APIRouter(prefix="/auth")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
DEMO_RE = re.compile(r"^demo(\d*)(admin|projectmanager|delmanager)@demo\.example$")
_fails = {}  # ip -> times of failed administrator sign-ins

def is_demo(email): return bool(DEMO_RE.match(email or ""))
def demo_on(): return MODE == "email" and os.getenv("DEMO_DATA", "1") != "0"
def _demo_label(email):
    n, kind = DEMO_RE.match(email).groups()
    return {"admin": "Administrator", "projectmanager": f"Project manager {n}", "delmanager": f"Delivery manager {n}"}[kind].strip()

def _ip(request): return request.client.host if request.client else "?"
def _throttle(request, limit=5, window=600):
    recent = [t for t in _fails.get(_ip(request), []) if time.time() - t < window]; _fails[_ip(request)] = recent
    if len(recent) >= limit: raise HTTPException(429, "Too many attempts. Try again in a few minutes.")

def current_user(request: Request, db=Depends(get_db)):
    email = request.session.get("email")
    u = db.query(User).filter_by(email=email, active=True).first() if email else None
    if not u: raise HTTPException(401, "Not signed in")
    return u

def require(*roles):
    def dep(u: User = Depends(current_user)):
        if u.role not in roles: raise HTTPException(403, "Not allowed for your role")
        return u
    return dep

def _start(request, db, u, how):
    request.session.clear(); request.session["email"] = u.email; log(db, u, "login", "user", u.email, {"mode": how}); return {"ok": True}

def demo_list(db):
    rank = {"admin": 0, "projectmanager": 1, "delmanager": 2}; out = []
    for u in db.query(User).filter_by(active=True):
        if not is_demo(u.email): continue
        n = db.query(TeamAccess).filter_by(user_id=u.id).count()
        out.append({"email": u.email, "label": _demo_label(u.email), "role": u.role, "note": "Sees every team, approves tables, manages users" if u.role == "admin" else f"{n} sample project{'s' if n != 1 else ''}"})
    return sorted(out, key=lambda d: (rank[DEMO_RE.match(d["email"]).group(2)], d["email"]))

@router.get("/config")
def cfg(db=Depends(get_db)):
    return {"mode": MODE, "domain": os.getenv("ALLOWED_EMAIL_DOMAIN", ""), "admin_login": bool(os.getenv("ADMIN_PASSWORD")),
            "users": [{"email": u.email, "role": u.role} for u in db.query(User).filter_by(active=True)] if MODE == "dev" else [],
            "demo": demo_list(db) if demo_on() else []}

@router.get("/me")
def me(u: User = Depends(current_user)): return {"email": u.email, "name": u.name, "role": u.role, "demo": is_demo(u.email)}

@router.post("/logout")
def logout(request: Request): request.session.clear(); return {"ok": True}

@router.post("/email-login")
def email_login(body: dict, request: Request, db=Depends(get_db)):
    """Internal-demo sign-in: type your work email and go. The first time, a manager account is created for you.
    The email is NOT verified, so administrator accounts can never sign in this way."""
    if MODE != "email": raise HTTPException(404)
    email = str(body.get("email", "")).strip().lower()
    if not EMAIL_RE.match(email): raise HTTPException(400, "Enter a valid work email address.")
    dom = os.getenv("ALLOWED_EMAIL_DOMAIN", "").lower().lstrip("@")
    if dom and not email.endswith("@" + dom): raise HTTPException(403, f"Use your @{dom} email address.")
    if email.endswith("@demo.example"): raise HTTPException(403, "Use the demo account buttons on the sign-in page.")
    u = db.query(User).filter_by(email=email).first()
    if u and u.role == "admin": raise HTTPException(403, "Administrator accounts use the administrator sign-in below.")
    if u and not u.active: raise HTTPException(403, "This account has been disabled. Please contact an administrator.")
    if not u:
        u = User(email=email, name=email.split("@")[0], role="manager"); db.add(u); db.commit(); log(db, u, "user_self_register", "user", email)
    return _start(request, db, u, "email")

@router.post("/demo-login")
def demo_login(body: dict, request: Request, db=Depends(get_db)):
    """One click into a ready-made demo account (sample data only). Switched off with DEMO_DATA=0."""
    if not demo_on(): raise HTTPException(404)
    email = str(body.get("email", "")).strip().lower()
    u = db.query(User).filter_by(email=email, active=True).first() if is_demo(email) else None
    if not u: raise HTTPException(404, "Unknown demo account")
    return _start(request, db, u, "demo")

@router.post("/admin-login")
def admin_login(body: dict, request: Request, db=Depends(get_db)):
    if MODE != "email": raise HTTPException(404)
    pw = os.getenv("ADMIN_PASSWORD")
    if not pw: raise HTTPException(403, "Administrator sign-in is not set up on this server.")
    _throttle(request)
    u = db.query(User).filter_by(email=str(body.get("email", "")).strip().lower(), role="admin", active=True).first()
    if not (u and hmac.compare_digest(str(body.get("password", "")).encode(), pw.encode())):
        _fails.setdefault(_ip(request), []).append(time.time()); time.sleep(0.4); raise HTTPException(401, "Wrong email or password.")
    return _start(request, db, u, "admin-password")

@router.post("/dev-login")  # LOCAL TESTING ONLY: AUTH_MODE=dev
def dev_login(body: dict, request: Request, db=Depends(get_db)):
    if MODE != "dev": raise HTTPException(404)
    u = db.query(User).filter_by(email=body.get("email"), active=True).first()
    if not u: raise HTTPException(404, "Unknown user")
    return _start(request, db, u, "dev")

if MODE == "oidc":
    from authlib.integrations.starlette_client import OAuth
    oauth = OAuth()
    oauth.register("sso", server_metadata_url=os.environ["OIDC_METADATA_URL"], client_id=os.environ["OIDC_CLIENT_ID"],
                   client_secret=os.environ["OIDC_CLIENT_SECRET"], client_kwargs={"scope": "openid email profile"})
    @router.get("/login")
    async def login(request: Request):
        return await oauth.sso.authorize_redirect(request, str(request.url_for("callback")))
    @router.get("/callback")
    async def callback(request: Request, db=Depends(get_db)):
        tok = await oauth.sso.authorize_access_token(request)
        info = tok.get("userinfo") or {}; email = (info.get("email") or info.get("preferred_username") or "").lower()
        dom = os.getenv("ALLOWED_EMAIL_DOMAIN")
        if not email or (dom and not email.endswith("@" + dom)): raise HTTPException(403, "Account not allowed")
        u = db.query(User).filter_by(email=email).first()
        if not u:  # first sign-in: sees no teams until they create or are given some
            u = User(email=email, name=info.get("name", email), role=os.getenv("DEFAULT_ROLE", "manager")); db.add(u); db.commit()
        if not u.active: raise HTTPException(403, "Account disabled")
        _start(request, db, u, "sso"); return RedirectResponse("/")
