import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin


class TokenUsage(BaseMixin, Base):
    __tablename__ = "token_usages"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    discussion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discussions.id", ondelete="SET NULL"),
        nullable=True,
    )
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="llm")

    __table_args__ = (
        Index("idx_tu_user_created", "user_id", "created_at"),
        Index("idx_tu_discussion_created", "discussion_id", "created_at"),
    )
