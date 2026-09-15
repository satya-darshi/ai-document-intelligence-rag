from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        conversation, answer, citations, cached = chat(
            db,
            question=request.message,
            document_ids=request.document_ids,
            conversation_id=request.conversation_id,
            mode=request.mode,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc
    return ChatResponse(
        conversation_id=conversation.id,
        answer=answer,
        citations=citations,
        cached=cached,
    )
