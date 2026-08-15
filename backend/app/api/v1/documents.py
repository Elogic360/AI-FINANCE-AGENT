"""Document upload, retrieval, listing, deletion, and analysis routes."""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.document import Document, ExtractedRecord
from app.models.business import User
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentAnalysisResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse

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
# GET /documents — List documents
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    file_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents for the current business with pagination."""
    base = select(Document).where(Document.business_id == current_user.business_id)

    if status_filter:
        base = base.where(Document.parse_status == status_filter)
    if file_type:
        base = base.where(Document.file_type == file_type)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(Document.uploaded_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
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


# ---------------------------------------------------------------------------
# DELETE /documents/{id}
# ---------------------------------------------------------------------------

@router.delete("/{doc_id}", response_model=MessageResponse)
async def delete_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its extracted records."""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.business_id == current_user.business_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Delete associated extracted records first
    await db.execute(
        delete(ExtractedRecord).where(ExtractedRecord.document_id == doc_id)
    )

    await db.delete(doc)
    return MessageResponse(message="Document deleted successfully")


# ---------------------------------------------------------------------------
# POST /documents/{id}/analyze — Trigger AI analysis
# ---------------------------------------------------------------------------

@router.post("/{doc_id}/analyze", response_model=DocumentAnalysisResponse)
async def trigger_analysis(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI analysis on an uploaded document.

    In production this queues an async job. For demo, returns immediately.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.business_id == current_user.business_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Simulate analysis
    doc.parse_status = "parsed"
    doc.parsed_by = "ai_v1"
    await db.flush()
    await db.refresh(doc)

    return DocumentAnalysisResponse(
        document_id=doc.id,
        parse_status=doc.parse_status,
        parsed_by=doc.parsed_by,
        summary=f"Document '{doc.original_filename}' analyzed successfully. "
                f"This appears to be a {doc.file_type.upper()} file with financial data.",
        extracted_records_count=0,
    )


# ---------------------------------------------------------------------------
# GET /documents/{id}/analysis — Get analysis results
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/analysis")
async def get_analysis_results(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI analysis results for a document."""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.business_id == current_user.business_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Fetch extracted records
    records_result = await db.execute(
        select(ExtractedRecord).where(ExtractedRecord.document_id == doc_id)
    )
    records = records_result.scalars().all()

    return {
        "document_id": doc.id,
        "filename": doc.original_filename,
        "parse_status": doc.parse_status,
        "parsed_by": doc.parsed_by,
        "extracted_records": [
            {
                "id": r.id,
                "record_type": r.record_type,
                "payload": r.payload,
                "confidence": float(r.confidence) if r.confidence else None,
                "validation_status": r.validation_status,
            }
            for r in records
        ],
        "total_records": len(records),
    }
