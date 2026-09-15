from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    document_ids: list[UUID] = Field(default_factory=list)
    conversation_id: UUID | None = None
    mode: str = Field(default="rag", pattern="^(rag|agent)$")


class Citation(BaseModel):
    document_id: UUID
    filename: str
    page: int | None = None
    chunk_id: str
    score: float | None = None
    excerpt: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    citations: list[Citation]
    cached: bool = False
