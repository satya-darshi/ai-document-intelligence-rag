from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Conversation, Message
from app.schemas.chat import Citation
from app.services.agent import AgentRunner
from app.services.cache import get_cached, make_key, set_cached
from app.services.llm import grounded_answer
from app.services.retrieval import build_context, retrieve


def _history(conversation: Conversation) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in conversation.messages]


def get_or_create_conversation(db: Session, conversation_id: UUID | None) -> Conversation:
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation:
            return conversation
    conversation = Conversation()
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def chat(
    db: Session,
    question: str,
    document_ids: list[UUID],
    conversation_id: UUID | None,
    mode: str,
) -> tuple[Conversation, str, list[Citation], bool]:
    conversation = get_or_create_conversation(db, conversation_id)
    history = _history(conversation)
    cache_key = make_key(question, [str(x) for x in document_ids]) if mode == "rag" else ""
    cached = get_cached(cache_key) if cache_key else None

    if cached:
        answer = cached["answer"]
        citations = [Citation(**citation) for citation in cached["citations"]]
        was_cached = True
    else:
        if mode == "agent":
            answer, chunks = AgentRunner(db, document_ids).run(question, history)
        else:
            chunks = retrieve(question, document_ids, db)
            context = build_context(chunks)
            answer = grounded_answer(question, context, history)

        citations = [
            Citation(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page=chunk.page,
                chunk_id=chunk.chunk_id,
                score=chunk.score,
                excerpt=chunk.text[:500],
            )
            for chunk in chunks
        ]
        was_cached = False
        if cache_key:
            set_cached(cache_key, {"answer": answer, "citations": [c.model_dump(mode="json") for c in citations]})

    db.add(Message(conversation_id=conversation.id, role="user", content=question))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()
    return conversation, answer, citations, was_cached
