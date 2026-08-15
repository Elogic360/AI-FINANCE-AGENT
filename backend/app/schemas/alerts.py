"""Alert schemas for FinPilot AI."""

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    """Alert detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    severity: str
    title: str
    detail: str
    source_refs: dict[str, Any] | None
    created_at: datetime
    acknowledged: bool
