from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    status: str
    error_message: str | None = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime
