# 业务审计事件表：记录关键操作、异常和 Agent/搜索资源消耗。
#
# 技术说明：
# - 所有业务模块（user / character / discussion）通过 AuditRepository 写入，
#   与业务操作共享同一个 DB session，保证事务一致性。
# - payload 使用 PostgreSQL JSONB，支持灵活的键值查询和索引扩展。
# - level 字段为 P0/P1/P2，按 CLAUDE.md 审计事件分级。
# - 表本身不软删除（业务审计不可删），但仍继承 BaseMixin 以统一 created_at/updated_at。

import uuid

from sqlalchemy import (
    UUID,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin


class AuditEvent(BaseMixin, Base):
    __tablename__ = "audit_events"

    # 谁触发的事件；用户删除后保留事件记录，但 user_id 置 NULL
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 关联的讨论；讨论删除后保留事件记录，discussion_id 置 NULL
    discussion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discussions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 事件类型，如 user.register / skill.generate / discussion.create
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # 审计级别：P0 必须审计、P1 应该审计、P2 可以审计
    level: Mapped[str] = mapped_column(
        String(4), nullable=False, default="P2"
    )

    # 任意结构化事件负载，JSONB 方便后续按 discussion_id / payload 键值查询
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    __table_args__ = (
        CheckConstraint(
            "level IN ('P0', 'P1', 'P2')",
            name="ck_audit_events_level",
        ),
        Index(
            "idx_ae_user_created",
            "user_id",
            "created_at",
        ),
        Index(
            "idx_ae_discussion_created",
            "discussion_id",
            "created_at",
        ),
        Index(
            "idx_ae_event_type_created",
            "event_type",
            "created_at",
        ),
    )
