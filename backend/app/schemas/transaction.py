"""Transaction schemas for FinPilot AI."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class TransactionCreate(BaseModel):
    """Create a new transaction."""
    txn_date: date
    description: str | None = None
    amount: Decimal
    currency: str = "TZS"
    counterparty: str | None = None
    source: str = "manual"
    ai_category: str | None = None


class TransactionResponse(BaseModel):
    """Transaction detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    source: str
    document_id: uuid.UUID | None
    txn_date: date
    description: str | None
    amount: Decimal
    currency: str
    counterparty: str | None
    ai_category: str | None
    ai_confidence: Decimal | None
    status: str
    created_at: datetime


class TransactionImportResponse(BaseModel):
    """Response after importing transactions from a document."""
    total_found: int
    imported: int
    skipped: int
    transaction_ids: list[uuid.UUID]
