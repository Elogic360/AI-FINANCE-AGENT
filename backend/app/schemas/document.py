"""Document schemas for FinPilot AI."""

import uuid
from datetime import datetime
from decimal import Decimal
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
