from backend.models.base import Base, BaseMixin
from backend.models.discussion import Discussion
from backend.models.discussion_agent import DiscussionAgent
from backend.models.skill import Skill
from backend.models.user import User

# 让Alembic 能扫到这些表

__all__ = [
    "Base",
    "BaseMixin",
    "User",
    "Skill",
    "Discussion",
    "DiscussionAgent",
]