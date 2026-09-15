from pathlib import Path
from uuid import UUID

from langchain_core.documents import Document as LCDocument
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document
from app.services.embeddings import get_embeddings

settings = get_settings()


def extract_pages(path: Path, content_type: str) -> list[LCDocument]:
    if content_type == "application/pdf":
        import fitz

        pdf = fitz.open(path)
        pages: list[LCDocument] = []
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(LCDocument(page_content=text, metadata={"page": page_number}))
        pdf.close()
        return pages

    text = path.read_text(encoding="utf-8", errors="ignore")
    return [LCDocument(page_content=text, metadata={"page": 1})]


def get_vector_store() -> QdrantVectorStore:
    client = QdrantClient(url=settings.qdrant_url)
    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=get_embeddings(),
    )


def ensure_collection() -> None:
    client = QdrantClient(url=settings.qdrant_url)
    collections = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )


def ingest_document(db: Session, document_id: UUID) -> None:
    document = db.get(Document, document_id)
    if not document:
        return

    try:
        ensure_collection()
        pages = extract_pages(Path(document.path), document.content_type)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        chunks = splitter.split_documents(pages)
        for index, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "document_id": str(document.id),
                    "filename": document.filename,
                    "chunk_id": f"{document.id}:{index}",
                }
            )

        if chunks:
            get_vector_store().add_documents(chunks)

        document.chunk_count = len(chunks)
        document.status = "ready"
        document.error_message = None
        db.commit()
    except Exception as exc:  # noqa: BLE001
        document.status = "failed"
        document.error_message = str(exc)[:2000]
        db.commit()


def delete_document_vectors(document_id: UUID) -> None:
    client = QdrantClient(url=settings.qdrant_url)
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    try:
        client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=Filter(
                must=[FieldCondition(key="metadata.document_id", match=MatchValue(value=str(document_id)))]
            ),
        )
    except Exception:
        pass
