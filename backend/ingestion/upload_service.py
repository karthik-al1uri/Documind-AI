"""DocuMind AI — File upload service.

Handles file receipt, type detection, storage to the local filesystem,
and creation of the initial document record in the database.
"""

import os
import uuid
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from utils.database import Document

load_dotenv()

logger = logging.getLogger(__name__)

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")

SUPPORTED_PDF_TYPES = {"application/pdf"}
SUPPORTED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/bmp",
}
SUPPORTED_EXTENSIONS_PDF = {".pdf"}
SUPPORTED_EXTENSIONS_IMAGE = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


def detect_file_type(filename: str, content_type: str | None) -> str:
    """Detect whether the uploaded file is a PDF or an image.

    Uses both the MIME content-type and the file extension as fallback.

    Args:
        filename: Original filename from the upload.
        content_type: MIME type reported by the client.

    Returns:
        str: Either 'pdf' or 'image'.

    Raises:
        ValueError: If the file type is not supported.
    """
    ext = Path(filename).suffix.lower()

    if content_type in SUPPORTED_PDF_TYPES or ext in SUPPORTED_EXTENSIONS_PDF:
        return "pdf"
    if content_type in SUPPORTED_IMAGE_TYPES or ext in SUPPORTED_EXTENSIONS_IMAGE:
        return "image"

    raise ValueError(f"Unsupported file type: {content_type} / extension {ext}")


async def save_upload(file: UploadFile) -> tuple[str, str]:
    """Save an uploaded file to local storage.

    Creates a unique subdirectory under STORAGE_PATH to avoid collisions.

    Args:
        file: The FastAPI UploadFile object.

    Returns:
        tuple[str, str]: (absolute storage path, detected file_type).

    Raises:
        ValueError: If the file type is not supported.
    """
    file_type = detect_file_type(file.filename or "unknown", file.content_type)

    file_id = str(uuid.uuid4())
    ext = Path(file.filename or "file").suffix
    dest_dir = os.path.join(STORAGE_PATH, file_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, f"original{ext}")

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    logger.info("Saved %s (%s) to %s", file.filename, file_type, dest_path)
    return dest_path, file_type


async def create_document_record(
    session: AsyncSession,
    filename: str,
    file_type: str,
    storage_path: str,
) -> Document:
    """Insert a new document record into the database.

    Args:
        session: Async database session.
        filename: Original filename.
        file_type: Detected type ('pdf' or 'image').
        storage_path: Path where the file is stored.

    Returns:
        Document: The newly created Document ORM object.
    """
    doc = Document(
        filename=filename,
        file_type=file_type,
        storage_path=storage_path,
        status="processing",
    )
    session.add(doc)
    await session.flush()
    logger.info("Created document record: id=%s, filename=%s", doc.id, filename)
    return doc
