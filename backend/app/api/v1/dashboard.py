"""Dashboard routes — health score and summary."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.accounting import Transaction, JournalEntry, JournalLine, ChartOfAccounts
from app.models.document import Document
from app.models.contacts import Invoice, Bill
from app.models.ai import Alert
from app.models.business import User
from app.schemas.dashboard import HealthScoreResponse, DashboardSummaryResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /dashboard/health-score
# ---------------------------------------------------------------------------

@router.get("/health-score", response_model=HealthScoreResponse)
async def get_health_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compute a financial health score (0-100) based on multiple factors."""
    bid = current_user.business_id

    # 1. Transaction categorization rate
    txn_total = (await db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.business_id == bid)
    )).scalar() or 0
    txn_categorized = (await db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.business_id == bid, Transaction.status == "categorized")
    )).scalar() or 0
    cat_rate = round((txn_categorized / txn_total * 100) if txn_total > 0 else 0)

    # 2. Invoice collection rate
    inv_total = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.business_id == bid)
    )).scalar() or 0
    inv_paid = (await db.execute(
        select(func.count())
        .select_from(Invoice)
        .where(Invoice.business_id == bid, Invoice.status == "paid")
    )).scalar() or 0
    collection_rate = round((inv_paid / inv_total * 100) if inv_total > 0 else 100)

    # 3. Unacknowledged alerts
    open_alerts = (await db.execute(
        select(func.count())
        .select_from(Alert)
        .where(Alert.business_id == bid, Alert.acknowledged == False)
    )).scalar() or 0

    # 4. Document processing rate
    doc_total = (await db.execute(
        select(func.count()).select_from(Document).where(Document.business_id == bid)
    )).scalar() or 0
    doc_parsed = (await db.execute(
        select(func.count())
        .select_from(Document)
        .where(Document.business_id == bid, Document.parse_status == "parsed")
    )).scalar() or 0
    parse_rate = round((doc_parsed / doc_total * 100) if doc_total > 0 else 100)

    # 5. Accounts setup
    account_count = (await db.execute(
        select(func.count()).select_from(ChartOfAccounts).where(ChartOfAccounts.business_id == bid)
    )).scalar() or 0
    accounts_score = min(100, account_count * 5)

    # Weighted overall score
    overall = max(0, min(100, round(
        cat_rate * 0.25
        + collection_rate * 0.25
        + max(0, 100 - open_alerts * 15) * 0.20
        + parse_rate * 0.15
        + accounts_score * 0.15
    )))

    if overall >= 80:
        rec = "Your finances are well-organized. Keep it up!"
    elif overall >= 60:
        rec = "Good progress. Focus on categorizing pending transactions and processing documents."
    elif overall >= 40:
        rec = "Needs attention. Prioritize pending items and review open alerts."
    else:
        rec = "Action required. Categorize transactions, process documents, and address alerts urgently."

    return HealthScoreResponse(
        overall_score=overall,
        cash_health=min(100, parse_rate + 20),
        revenue_trend=collection_rate,
        expense_control=cat_rate,
        receivables=collection_rate,
        recommendation=rec,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick financial summary for the dashboard."""
    bid = current_user.business_id

    total_txn = (await db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.business_id == bid)
    )).scalar() or 0

    pending_txn = (await db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.business_id == bid, Transaction.status == "pending")
    )).scalar() or 0

    # Revenue — sum credits on revenue accounts from approved journal lines
    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), Decimal("0")))
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(
            ChartOfAccounts.business_id == bid,
            ChartOfAccounts.account_type == "revenue",
            JournalEntry.is_draft.is_(False),
        )
    )).scalar() or Decimal("0")

    # Expenses — sum debits on expense accounts from approved journal lines
    total_expenses = (await db.execute(
        select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), Decimal("0")))
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(
            ChartOfAccounts.business_id == bid,
            ChartOfAccounts.account_type == "expense",
            JournalEntry.is_draft.is_(False),
        )
    )).scalar() or Decimal("0")

    # Invoices
    pending_invoices = (await db.execute(
        select(func.count())
        .select_from(Invoice)
        .where(Invoice.business_id == bid, Invoice.status == "unpaid")
    )).scalar() or 0

    overdue_invoices = (await db.execute(
        select(func.count())
        .select_from(Invoice)
        .where(Invoice.business_id == bid, Invoice.status == "overdue")
    )).scalar() or 0

    # Accounts
    accounts_receivable = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0))
        .select_from(Invoice)
        .where(Invoice.business_id == bid, Invoice.status.in_(["unpaid", "overdue"]))
    )).scalar() or 0

    accounts_payable = (await db.execute(
        select(func.coalesce(func.sum(Bill.amount), 0))
        .select_from(Bill)
        .where(Bill.business_id == bid, Bill.status.in_(["unpaid", "overdue"]))
    )).scalar() or 0

    # Alerts
    active_alerts = (await db.execute(
        select(func.count())
        .select_from(Alert)
        .where(Alert.business_id == bid, Alert.acknowledged == False)
    )).scalar() or 0

    # Ensure Decimal types for monetary fields
    total_revenue = Decimal(str(total_revenue)) if not isinstance(total_revenue, Decimal) else total_revenue
    total_expenses = Decimal(str(total_expenses)) if not isinstance(total_expenses, Decimal) else total_expenses
    accounts_receivable = Decimal(str(accounts_receivable)) if not isinstance(accounts_receivable, Decimal) else accounts_receivable
    accounts_payable = Decimal(str(accounts_payable)) if not isinstance(accounts_payable, Decimal) else accounts_payable

    return DashboardSummaryResponse(
        currency="TZS",
        period_label=date.today().strftime("%B %Y"),
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_income=total_revenue - total_expenses,
        cash_balance=total_revenue - total_expenses,
        accounts_receivable=accounts_receivable,
        accounts_payable=accounts_payable,
        transaction_count=total_txn,
        pending_invoices=pending_invoices,
        overdue_invoices=overdue_invoices,
        active_alerts=active_alerts,
    )
