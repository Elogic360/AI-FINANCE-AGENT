"""Document schemas for FinPilot AI."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    id: uuid.UUID
    filename: str
    file_type: str
    storage_url: str
    parse_status: str
    message: str


class DocumentResponse(BaseModel):
    """Document detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    file_type: str
    storage_url: str
    original_filename: str
    parsed_by: str | None
    parse_status: str
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated document list."""
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentAnalysisResponse(BaseModel):
    """Response after triggering document analysis."""
    document_id: uuid.UUID
    parse_status: str
    parsed_by: str | None
    summary: str
    extracted_records_count: int
