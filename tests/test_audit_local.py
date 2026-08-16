from pathlib import Path

from audit_backend import local_db
from audit_backend.config import settings


def test_should_seed_admin_and_update_retention(tmp_path, monkeypatch):
    db = tmp_path / "audit.db"
    monkeypatch.setattr(settings, "audit_db_path", str(db))
    monkeypatch.setattr(settings, "audit_admin_username", "admin")
    monkeypatch.setattr(settings, "audit_admin_password", "audit123")
    local_db.init_db()
    assert local_db.verify_admin("admin", "audit123")
    created = local_db.create_admin("ops", "secret1")
    assert created["username"] == "ops"
    assert len(local_db.list_admins()) == 2
    assert local_db.delete_admin(created["id"]) is True
    settings_data = local_db.set_retention_days(30)
    assert settings_data["retention_days"] == 30
    leftover = local_db.list_admins()[0]
    assert local_db.delete_admin(leftover["id"]) is False
    assert Path(db).exists()
