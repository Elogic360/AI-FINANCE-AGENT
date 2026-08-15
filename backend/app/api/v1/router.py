"""Aggregated v1 API router."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.journal import router as journal_router
from app.api.v1.reports import router as reports_router
from app.api.v1.documents import router as documents_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.contacts import router as contacts_router
from app.api.v1.alerts import router as alerts_router

api_router = APIRouter()

# auth_router already has prefix="/auth"
api_router.include_router(auth_router)
api_router.include_router(transactions_router, prefix="/transactions", tags=["transactions"])
api_router.include_router(journal_router, prefix="/journal-entries", tags=["journal"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(contacts_router, prefix="/contacts", tags=["contacts"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
