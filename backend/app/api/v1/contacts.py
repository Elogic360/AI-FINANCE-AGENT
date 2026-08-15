"""Contact routes — Customers and Vendors CRUD."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.contacts import Customer, Vendor
from app.models.business import User
from app.schemas.contacts import CustomerCreate, CustomerResponse, VendorCreate, VendorResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _list_contacts(
    db: AsyncSession,
    model,
    business_id: uuid.UUID,
    page: int,
    page_size: int,
    search: Optional[str] = None,
):
    base = select(model).where(model.business_id == business_id)
    if search:
        base = base.where(model.name.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(model.name).offset(offset).limit(page_size)
    )
    items = result.scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)

    return total, items, pages


# =========================================================================
# CUSTOMERS
# =========================================================================

@router.get("/customers", response_model=PaginatedResponse[CustomerResponse])
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List customers with pagination and search."""
    total, items, pages = await _list_contacts(
        db, Customer, current_user.business_id, page, page_size, search
    )
    return PaginatedResponse(
        items=[CustomerResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new customer."""
    customer = Customer(
        business_id=current_user.business_id,
        name=body.name,
    )
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)


# =========================================================================
# VENDORS
# =========================================================================

@router.get("/vendors", response_model=PaginatedResponse[VendorResponse])
async def list_vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List vendors with pagination and search."""
    total, items, pages = await _list_contacts(
        db, Vendor, current_user.business_id, page, page_size, search
    )
    return PaginatedResponse(
        items=[VendorResponse.model_validate(v) for v in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new vendor."""
    vendor = Vendor(
        business_id=current_user.business_id,
        name=body.name,
    )
    db.add(vendor)
    await db.flush()
    await db.refresh(vendor)
    return VendorResponse.model_validate(vendor)
