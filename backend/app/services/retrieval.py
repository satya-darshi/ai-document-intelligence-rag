import re
from dataclasses import dataclass
from uuid import UUID

from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document
from app.services.ingestion import get_vector_store

settings = get_settings()
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


@dataclass
class RetrievedChunk:
    document_id: UUID
    filename: str
    page: int | None
    chunk_id: str
    score: float | None
    text: str


def _allowed_filter(document_ids: list[UUID]) -> Filter | None:
    if not document_ids:
        return None
    return Filter(
        should=[
            FieldCondition(key="metadata.document_id", match=MatchValue(value=str(doc_id)))
            for doc_id in document_ids
        ]
    )


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if len(token) > 2}


def _lexical_overlap(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    text_tokens = _tokens(text)
    return len(query_tokens & text_tokens) / len(query_tokens)


def retrieve(
    query: str,
    document_ids: list[UUID],
    db: Session,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    """Retrieve vector candidates, then rerank them with lexical overlap.

    Qdrant supplies the semantic similarity score. A lightweight lexical score
    is combined with it so chunks containing important query terms move upward
    when semantic scores are close.
    """
    final_limit = limit or settings.rerank_top_k
    candidate_limit = max(settings.top_k, final_limit) * 2
    store = get_vector_store()
    results = store.similarity_search_with_score(
        query,
        k=candidate_limit,
        filter=_allowed_filter(document_ids),
    )

    allowed_ids = {
        str(item.id)
        for item in db.query(Document).filter(Document.id.in_(document_ids)).all()
    }
    candidates: list[tuple[RetrievedChunk, float]] = []
    requested_ids = {str(x) for x in document_ids}

    for doc, vector_score in results:
        metadata = doc.metadata
        doc_id = str(metadata.get("document_id", ""))
        if not doc_id or (document_ids and doc_id not in requested_ids):
            continue
        if document_ids and doc_id not in allowed_ids:
            continue

        chunk = RetrievedChunk(
            document_id=UUID(doc_id),
            filename=metadata.get("filename", "unknown"),
            page=metadata.get("page"),
            chunk_id=metadata.get("chunk_id", "unknown"),
            score=float(vector_score) if vector_score is not None else None,
            text=doc.page_content,
        )
        vector = max(0.0, min(1.0, float(vector_score)))
        lexical = _lexical_overlap(query, chunk.text)
        rerank_score = (0.75 * vector) + (0.25 * lexical)
        candidates.append((chunk, rerank_score))

    candidates.sort(key=lambda item: item[1], reverse=True)
    return [chunk for chunk, _score in candidates[:final_limit]]


def build_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        page = f"page {chunk.page}" if chunk.page else "unknown page"
        parts.append(f"[SOURCE {index}] {chunk.filename} ({page})\n{chunk.text}")
    return "\n\n".join(parts)
