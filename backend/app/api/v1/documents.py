"""Document upload and retrieval routes."""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.document import Document
from app.models.business import User
from app.schemas.document import DocumentUploadResponse, DocumentResponse

router = APIRouter()

# Allowed file types
_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".csv", ".xlsx"}
_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a financial document (PDF, image, CSV, XLSX)."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {_MAX_FILE_SIZE // (1024 * 1024)} MB limit",
        )

    # --- Local storage fallback (replace with Cloudflare R2 in production) ---
    upload_dir = os.path.join("/tmp", "finpilot_uploads", str(current_user.business_id))
    os.makedirs(upload_dir, exist_ok=True)
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    storage_url = f"local://{file_path}"
    file_type = ext.lstrip(".")

    doc = Document(
        business_id=current_user.business_id,
        file_type=file_type,
        storage_url=storage_url,
        original_filename=file.filename,
        parse_status="pending",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.original_filename,
        file_type=doc.file_type,
        storage_url=doc.storage_url,
        parse_status=doc.parse_status,
        message="Document uploaded successfully",
    )


# ---------------------------------------------------------------------------
# GET /documents/{id}
# ---------------------------------------------------------------------------

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a document by ID."""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.business_id == current_user.business_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DocumentResponse.model_validate(doc)
