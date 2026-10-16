import os, datetime as dt
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Date, JSON, ForeignKey, UniqueConstraint, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

Path("data").mkdir(exist_ok=True)
URL = os.getenv("DATABASE_URL", "sqlite:///data/app.db")
engine = create_engine(URL, connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(engine); Base = declarative_base()
now = lambda: dt.datetime.utcnow()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True); email = Column(String, unique=True, index=True); name = Column(String)
    role = Column(String, default="manager")  # admin | manager
    active = Column(Boolean, default=True)
class GenusVersion(Base):
    __tablename__ = "genus_versions"
    id = Column(Integer, primary_key=True); label = Column(String); status = Column(String, default="pending")  # pending|active|archived|rejected
    created_by = Column(String); created_at = Column(DateTime, default=now); decided_by = Column(String); decided_at = Column(DateTime)
    source_status = Column(String, default="unverified"); report = Column(JSON)
class GenusRate(Base):
    __tablename__ = "genus_rates"
    id = Column(Integer, primary_key=True); version_id = Column(Integer, ForeignKey("genus_versions.id"), index=True)
    key = Column(String, index=True); label = Column(String); cost = Column(Float)
class Calendar(Base):
    __tablename__ = "calendars"
    id = Column(Integer, primary_key=True); name = Column(String, unique=True)
class CalendarDay(Base):
    __tablename__ = "calendar_days"
    id = Column(Integer, primary_key=True); calendar_id = Column(Integer, ForeignKey("calendars.id"), index=True); day = Column(Date); name = Column(String)
    __table_args__ = (UniqueConstraint("calendar_id", "day"),)
class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True); name = Column(String); calendar_id = Column(Integer, ForeignKey("calendars.id"))
    created_by = Column(String); created_at = Column(DateTime, default=now)
    unit = Column(String)                       # business unit, e.g. "Data & AI" (free text, optional)
    simulated = Column(Boolean, default=False)  # demo data, shown with a "Simulated" tag
    removed = Column(JSON)                      # people deleted from this team (numbers kept so Compare can still show them); cleared when the team sheet is re-imported
    private = Column(Boolean, default=False)    # True = administrators cannot see this team unless given access
class TeamAccess(Base):  # who may see which team (admins see every non-private team and need no rows)
    __tablename__ = "team_access"
    edit = Column(Boolean, default=True)  # False = shared as view only
    id = Column(Integer, primary_key=True); user_id = Column(Integer, ForeignKey("users.id"), index=True); team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    __table_args__ = (UniqueConstraint("user_id", "team_id"),)
class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True); value = Column(String)
class TeamLine(Base):
    __tablename__ = "team_lines"
    id = Column(String, primary_key=True); pos = Column(Integer, default=0); name = Column(String); role = Column(String)
    exp = Column(Float); rate = Column(Float); bracket = Column(String); bracket_override = Column(Boolean, default=False)
    genus = Column(Float); genus_override = Column(Boolean, default=False); alloc = Column(Float, default=1)
    base = Column(JSON); warnings = Column(JSON)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True); start_date = Column(Date); end_date = Column(Date)
class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(Integer, primary_key=True); name = Column(String); created_by = Column(String); created_at = Column(DateTime, default=now); data = Column(JSON)
    team_id = Column(Integer, index=True); auto = Column(Boolean, default=False)  # auto = safety backup taken before loading a scenario
class Holiday(Base):  # legacy single global calendar; copied into calendars on first start, no longer used
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True); day = Column(Date, unique=True); name = Column(String)
class Audit(Base):
    __tablename__ = "audit"
    id = Column(Integer, primary_key=True); ts = Column(DateTime, default=now, index=True); user = Column(String)
    action = Column(String, index=True); entity = Column(String); entity_id = Column(String); details = Column(JSON)
    hidden = Column(Boolean, default=False)  # logged against a private team: details are not shown to administrators

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def log(db, user, action, entity="", eid="", details=None, team=None):
    db.add(Audit(user=getattr(user, "email", user), action=action, entity=entity, entity_id=str(eid), details=details or {}, hidden=bool(team is not None and team.private))); db.commit()

def ensure_schema():
    """Creates new tables and adds newer columns to an existing database (no migration tool needed).
    Returns True when this is an upgrade from a version without team access control, so existing users can keep what they could see."""
    insp0 = inspect(engine); names = set(insp0.get_table_names())
    legacy_grant = "team_access" not in names and "users" in names
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    adds = {"team_lines": [("team_id", "INTEGER"), ("start_date", "DATE"), ("end_date", "DATE")], "scenarios": [("team_id", "INTEGER"), ("auto", "BOOLEAN")],
            "teams": [("unit", "VARCHAR"), ("simulated", "BOOLEAN"), ("removed", "JSON"), ("private", "BOOLEAN")], "audit": [("hidden", "BOOLEAN")], "team_access": [("edit", "BOOLEAN")]}
    with engine.begin() as c:
        for t, cols in adds.items():
            have = {x["name"] for x in insp.get_columns(t)}
            for n, ty in cols:
                if n not in have: c.execute(text(f"ALTER TABLE {t} ADD COLUMN {n} {ty}"))
    return legacy_grant
