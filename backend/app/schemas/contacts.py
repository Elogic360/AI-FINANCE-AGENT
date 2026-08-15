"""Contact schemas for FinPilot AI."""

import uuid
from pydantic import BaseModel, ConfigDict


class CustomerCreate(BaseModel):
    """Create a customer."""
    name: str


class CustomerResponse(BaseModel):
    """Customer detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str


class VendorCreate(BaseModel):
    """Create a vendor."""
    name: str


class VendorResponse(BaseModel):
    """Vendor detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
