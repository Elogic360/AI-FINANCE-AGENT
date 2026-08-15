"""Journal entry schemas for FinPilot AI."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class JournalLineCreate(BaseModel):
    """Single journal line (debit or credit)."""
    account_id: uuid.UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


class JournalEntryCreate(BaseModel):
    """Create a balanced journal entry with lines."""
    transaction_id: uuid.UUID | None = None
    entry_date: date
    lines: list[JournalLineCreate]
    memo: str | None = None
    created_by: str = "system"


class JournalLineResponse(BaseModel):
    """Journal line response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    journal_entry_id: uuid.UUID
    account_id: uuid.UUID
    debit: Decimal
    credit: Decimal


class JournalEntryResponse(BaseModel):
    """Journal entry response with lines."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    transaction_id: uuid.UUID | None
    entry_date: date
    memo: str | None
    created_by: str
    is_draft: bool
    created_at: datetime
    lines: list[JournalLineResponse]
