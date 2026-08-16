# 请求/响应

from pydantic import BaseModel, Field


class CharacterCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=1024)
    tags: list[str] = Field(default_factory=list)
    is_public: bool = False

class CharacterGenerateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=1024)


class CharacterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=1024)
    tags: list[str] | None = None
    is_public: bool | None = None


class FileContentRequest(BaseModel):
    path: str = Field(default="SKILL.md")
    content: str | None = None


class CharacterResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    tags: list[str]
    is_public: bool
    status: str
    created_at: str
    updated_at: str
    # 从 SKILL.md 提取的 > 引用语，最多 5 条；description 优先用第一条
    quotes: list[str] = []


class CharacterListResponse(BaseModel):
    items: list[CharacterResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class RecommendationsResponse(BaseModel):
    items: list[str]
    source: str