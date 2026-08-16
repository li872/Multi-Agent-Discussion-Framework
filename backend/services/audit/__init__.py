# audit 模块：横切关注点，提供 AuditRepository 给 user/character/discussion 等服务注入。
from backend.services.audit.repository import AuditRepository

__all__ = ["AuditRepository"]
