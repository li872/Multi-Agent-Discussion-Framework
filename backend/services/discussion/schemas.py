# 接口请求/响应的数据格式

from pydantic import BaseModel, Field


class DiscussionCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=256)
    character_ids: list[str] = Field(min_length=1, max_length=10)
    duration: int = Field(ge=60, le=3600, default=600)


class AgentInfo(BaseModel):
    skill_id: str
    name: str


class DiscussionResponse(BaseModel):
    id: str
    owner_id: str
    topic: str
    duration: int
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    created_at: str
    updated_at: str
    agents: list[AgentInfo] = []

class MessageResponse(BaseModel):
    id: str
    discussion_id: str
    round_number: int
    agent_id: str | None = None
    agent_name: str | None = None
    message_type: str
    content: str
    confidence: float | None = None
    created_at: str


class InterveneRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class TopicGenerateResponse(BaseModel):
    # AI 生成讨论主题：topic 约 30 字；source 标明 llm 或 fallback
    topic: str
    source: str