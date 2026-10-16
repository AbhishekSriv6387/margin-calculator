import os, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mkdtemp() + "/t.db"
os.environ["AUTH_MODE"] = "dev"
