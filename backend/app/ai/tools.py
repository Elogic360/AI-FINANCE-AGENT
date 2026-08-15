"""
FinPilot AI Agent Tools — the ONLY interface between runtime agents and the ledger.
All tools are read-only or draft-only. No execute_* tools exist by design.
"""

from decimal import Decimal
from typing import Any
import uuid


# ── READ tools ──────────────────────────────────────────────────────────────

async def get_business_profile(business_id: uuid.UUID) -> dict:
    """Return business name, currency, country, creation date."""
    ...

async def get_chart_of_accounts(business_id: uuid.UUID) -> list[dict]:
    """Return full chart of accounts for the business."""
    ...

async def get_transactions(
    business_id: uuid.UUID,
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Search and filter transactions."""
    ...

async def search_transactions(business_id: uuid.UUID, query: str, limit: int = 50) -> list[dict]:
    """Full-text search across transaction descriptions and counterparties."""
    ...

async def get_revenue(business_id: uuid.UUID, period: str = "month") -> dict:
    """Aggregate revenue by period with trend."""
    ...

async def get_expenses(business_id: uuid.UUID, period: str = "month") -> dict:
    """Aggregate expenses by period with trend."""
    ...

async def get_profit_loss(business_id: uuid.UUID, period: str = "month") -> dict:
    """Full P&L statement for the period."""
    ...

async def get_balance_sheet(business_id: uuid.UUID) -> dict:
    """Balance sheet at current date."""
    ...

async def get_cash_flow(business_id: uuid.UUID, period: str = "month") -> dict:
    """Cash flow statement by period."""
    ...

async def get_customers(business_id: uuid.UUID) -> list[dict]:
    """List all customers with balances."""
    ...

async def get_customer_balance(business_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
    """Outstanding balance for a specific customer."""
    ...

async def get_invoices(business_id: uuid.UUID, status: str | None = None) -> list[dict]:
    """List invoices optionally filtered by status."""
    ...

async def get_overdue_invoices(business_id: uuid.UUID) -> list[dict]:
    """All unpaid invoices past their due date."""
    ...

async def get_vendors(business_id: uuid.UUID) -> list[dict]:
    """List all vendors with balances."""
    ...

async def get_payables(business_id: uuid.UUID) -> list[dict]:
    """Outstanding bills to pay."""
    ...

async def get_bank_transactions(business_id: uuid.UUID) -> list[dict]:
    """Raw imported bank transactions (pre-ledger)."""
    ...

async def get_reconciliation_status(business_id: uuid.UUID) -> dict:
    """Reconciliation report: matched, unmatched, discrepancies."""
    ...

async def analyze_document(business_id: uuid.UUID, document_id: uuid.UUID) -> dict:
    """Parse status + extracted records for a document."""
    ...

async def search_documents(business_id: uuid.UUID, query: str) -> list[dict]:
    """Search documents by filename or content."""
    ...

async def calculate_financial_ratio(business_id: uuid.UUID, ratio_name: str) -> dict:
    """Compute a specific financial ratio (current_ratio, debt_ratio, etc.)."""
    ...

async def run_business_health_check(business_id: uuid.UUID) -> dict:
    """Comprehensive health score with breakdown."""
    ...


# ── DRAFT tools (propose, never auto-execute) ──────────────────────────────

async def create_draft_journal_entry(
    business_id: uuid.UUID,
    transaction_id: uuid.UUID | None,
    entry_date: str,
    lines: list[dict],  # [{account_id, debit, credit}]
    memo: str | None = None,
) -> dict:
    """Propose a draft journal entry. Returns with is_draft=True. Human must approve."""
    ...

async def create_draft_invoice(
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    items: list[dict],
    due_date: str | None = None,
) -> dict:
    """Propose a draft invoice. Human must approve before sending."""
    ...

async def generate_forecast(
    business_id: uuid.UUID,
    forecast_type: str,
    horizon_days: int,
    assumptions: dict | None = None,
) -> dict:
    """Generate a forecast with explicit assumptions and confidence level."""
    ...


# ── Tool registry for agent tool-calling ────────────────────────────────────

TOOL_REGISTRY = {
    "get_business_profile": get_business_profile,
    "get_chart_of_accounts": get_chart_of_accounts,
    "get_transactions": get_transactions,
    "search_transactions": search_transactions,
    "get_revenue": get_revenue,
    "get_expenses": get_expenses,
    "get_profit_loss": get_profit_loss,
    "get_balance_sheet": get_balance_sheet,
    "get_cash_flow": get_cash_flow,
    "get_customers": get_customers,
    "get_customer_balance": get_customer_balance,
    "get_invoices": get_invoices,
    "get_overdue_invoices": get_overdue_invoices,
    "get_vendors": get_vendors,
    "get_payables": get_payables,
    "get_bank_transactions": get_bank_transactions,
    "get_reconciliation_status": get_reconciliation_status,
    "analyze_document": analyze_document,
    "search_documents": search_documents,
    "calculate_financial_ratio": calculate_financial_ratio,
    "run_business_health_check": run_business_health_check,
    "create_draft_journal_entry": create_draft_journal_entry,
    "create_draft_invoice": create_draft_invoice,
    "generate_forecast": generate_forecast,
}
