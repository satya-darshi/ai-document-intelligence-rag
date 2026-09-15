import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document

settings = get_settings()
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


def validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError("Only PDF, TXT, and Markdown files are supported.")


def save_upload(file: UploadFile, document_id: UUID) -> tuple[Path, str]:
    suffix = ALLOWED_TYPES.get(file.content_type or "", Path(file.filename or "").suffix.lower())
    safe_name = f"{document_id}{suffix}"
    destination = settings.upload_path / safe_name
    data = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValueError(f"File exceeds the {settings.max_upload_mb} MB upload limit.")
    destination.write_bytes(data)
    checksum = hashlib.sha256(data).hexdigest()
    return destination, checksum


def create_document(db: Session, file: UploadFile) -> Document:
    validate_upload(file)
    document = Document(
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        path="",
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    path, _checksum = save_upload(file, document.id)
    document.path = str(path)
    db.commit()
    db.refresh(document)
    return document
