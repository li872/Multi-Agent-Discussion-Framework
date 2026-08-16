import datetime
import os
import subprocess

repo = r"D:\Multi-Agent-Discussion-Framework\Multi-Agent-Discussion-Framework"
os.chdir(repo)

subprocess.run(["git", "add", "-A"], check=True)

tree = subprocess.run(
    ["git", "write-tree"], check=True, capture_output=True, text=True, encoding="utf-8"
).stdout.strip()

msg = (
    "feat(audit): add audit_events table, repository, and admin query endpoint\n\n"
    "- add AuditEvent model + alembic migration (user_id/discussion_id FK, JSONB payload, P0-P2 level)\n"
    "- add AuditRepository with record/list/count methods; shares DB session with business logic\n"
    "- wire user.register/login/login_failed, username/phone/password changes into audit_events\n"
    "- wire character create/generate/copy/update/delete/file_write into audit_events\n"
    "- wire discussion create/start/resume/intervene/delete into audit_events\n"
    "- add GET /api/v1/admin/audit/events with X-Admin-Token guard for audit backstage proxy\n"
    "- add ADMIN_TOKEN to .env/config; backend image rebuilt and verified in Docker"
)

env = os.environ.copy()
env["GIT_AUTHOR_NAME"] = "li872"
env["GIT_AUTHOR_EMAIL"] = "3496841962@qq.com"
env["GIT_AUTHOR_DATE"] = datetime.datetime.now().astimezone().strftime(
    "%Y-%m-%dT%H:%M:%S%z"
)

sha = subprocess.run(
    ["git", "commit-tree", tree, "-p", "HEAD"],
    input=msg,
    capture_output=True,
    text=True,
    encoding="utf-8",
    env=env,
).stdout.strip()

subprocess.run(["git", "update-ref", "HEAD", sha], check=True)
print("commit", sha)
