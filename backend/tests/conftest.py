import os, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mkdtemp() + "/t.db"
os.environ["AUTH_MODE"] = "dev"

import pytest
@pytest.fixture(autouse=True)
def approval_on(monkeypatch):
    """The older tests cover the maker-checker flow, which is now switched off by default (config "genus_approval"): switch it on for them."""
    from app import main
    monkeypatch.setattr(main, "NEEDS_APPROVAL", True)
