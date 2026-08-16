# 审计后台本地库：管理员 + 设置（SQLite，不占用主库）
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from passlib.context import CryptContext

from audit_backend.config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def db_path() -> Path:
    path = Path(settings.audit_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit_admin_users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        cur = conn.execute("SELECT COUNT(*) AS c FROM audit_admin_users")
        if cur.fetchone()["c"] == 0:
            conn.execute(
                "INSERT INTO audit_admin_users (id, username, password_hash, created_at) VALUES (?,?,?,?)",
                (
                    str(uuid.uuid4()),
                    settings.audit_admin_username,
                    pwd.hash(settings.audit_admin_password),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        conn.execute(
            "INSERT OR IGNORE INTO audit_settings (key, value) VALUES (?, ?)",
            ("retention_days", "90"),
        )
        conn.commit()
    finally:
        conn.close()


def find_admin(username: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, created_at FROM audit_admin_users WHERE username=?",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def verify_admin(username: str, password: str) -> dict | None:
    row = find_admin(username)
    if row and pwd.verify(password, row["password_hash"]):
        return {"id": row["id"], "username": row["username"]}
    if (
        username == settings.audit_admin_username
        and password == settings.audit_admin_password
    ):
        return {"id": "env", "username": username}
    return None


def list_admins() -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, username, created_at FROM audit_admin_users ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_admin(username: str, password: str) -> dict:
    conn = connect()
    try:
        aid = str(uuid.uuid4())
        created = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO audit_admin_users (id, username, password_hash, created_at) VALUES (?,?,?,?)",
            (aid, username, pwd.hash(password), created),
        )
        conn.commit()
        return {"id": aid, "username": username, "created_at": created}
    finally:
        conn.close()


def update_admin(admin_id: str, *, username: str | None, password: str | None) -> dict | None:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT id, username, created_at FROM audit_admin_users WHERE id=?",
            (admin_id,),
        ).fetchone()
        if not row:
            return None
        if username:
            conn.execute(
                "UPDATE audit_admin_users SET username=? WHERE id=?",
                (username, admin_id),
            )
        if password:
            conn.execute(
                "UPDATE audit_admin_users SET password_hash=? WHERE id=?",
                (pwd.hash(password), admin_id),
            )
        conn.commit()
        row = conn.execute(
            "SELECT id, username, created_at FROM audit_admin_users WHERE id=?",
            (admin_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_admin(admin_id: str) -> bool:
    conn = connect()
    try:
        count = conn.execute("SELECT COUNT(*) AS c FROM audit_admin_users").fetchone()["c"]
        if count <= 1:
            return False
        cur = conn.execute("DELETE FROM audit_admin_users WHERE id=?", (admin_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_settings() -> dict:
    conn = connect()
    try:
        days = conn.execute(
            "SELECT value FROM audit_settings WHERE key='retention_days'"
        ).fetchone()
        return {"retention_days": int(days["value"]) if days else 90}
    finally:
        conn.close()


def set_retention_days(days: int) -> dict:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO audit_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ("retention_days", str(days)),
        )
        conn.commit()
    finally:
        conn.close()
    return get_settings()
