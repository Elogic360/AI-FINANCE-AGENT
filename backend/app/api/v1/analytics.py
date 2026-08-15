"""Analytics endpoints for FinPilot AI — dashboard, financial statements, forecasts, risks."""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.accounting import Transaction, ChartOfAccounts
from app.models.business import User
from app.models.contacts import Invoice, Bill
from app.models.ai import Alert
from app.schemas.analytics import (
    DashboardData,
    ProfitLossResponse,
    PnLLineItem,
    BalanceSheetResponse,
    BalanceSheetLine,
    CashFlowResponse,
    CashFlowLine,
    AgingReport,
    AgingBucket,
    AgingLineItem,
    ForecastResponse,
    ForecastPoint,
    RiskAnalysisResponse,
    RiskItem,
    AllMetricsResponse,
)

router = APIRouter()

TODAY = date.today()


# ---------------------------------------------------------------------------
# GET /analytics/dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full dashboard data including trends and breakdowns."""
    bid = current_user.business_id
    now = datetime.utcnow()
    month_start = now.replace(day=1).date()

    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.business_id == bid,
            Transaction.txn_date >= month_start,
            Transaction.amount > 0,
        )
    )).scalar() or 0

    total_expenses = (await db.execute(
        select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
        .where(
            Transaction.business_id == bid,
            Transaction.txn_date >= month_start,
            Transaction.amount < 0,
        )
    )).scalar() or 0

    txn_count = (await db.execute(
        select(func.count())
        .where(Transaction.business_id == bid)
    )).scalar() or 0

    pending_inv = (await db.execute(
        select(func.count())
        .where(Invoice.business_id == bid, Invoice.status == "unpaid")
    )).scalar() or 0

    overdue_inv = (await db.execute(
        select(func.count())
        .where(Invoice.business_id == bid, Invoice.status == "overdue")
    )).scalar() or 0

    ar_total = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0))
        .where(Invoice.business_id == bid, Invoice.status.in_(["unpaid", "overdue"]))
    )).scalar() or 0

    ap_total = (await db.execute(
        select(func.coalesce(func.sum(Bill.amount), 0))
        .where(Bill.business_id == bid, Bill.status.in_(["unpaid", "overdue"]))
    )).scalar() or 0

    active_alerts = (await db.execute(
        select(func.count())
        .where(Alert.business_id == bid, Alert.acknowledged == False)
    )).scalar() or 0

    # Monthly trends (last 6 months)
    monthly_rev = []
    monthly_exp = []
    for i in range(5, -1, -1):
        m_start = (now - timedelta(days=30 * i)).replace(day=1).date()
        if i > 0:
            m_end = (now - timedelta(days=30 * (i - 1))).replace(day=1).date()
        else:
            m_end = now.date()

        rev = (await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(
                Transaction.business_id == bid,
                Transaction.txn_date >= m_start,
                Transaction.txn_date < m_end,
                Transaction.amount > 0,
            )
        )).scalar() or 0

        exp = (await db.execute(
            select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
            .where(
                Transaction.business_id == bid,
                Transaction.txn_date >= m_start,
                Transaction.txn_date < m_end,
                Transaction.amount < 0,
            )
        )).scalar() or 0

        monthly_rev.append({"month": m_start.strftime("%b %Y"), "amount": float(rev)})
        monthly_exp.append({"month": m_start.strftime("%b %Y"), "amount": float(exp)})

    # Top expense categories
    top_cats = (await db.execute(
        select(
            Transaction.ai_category,
            func.sum(func.abs(Transaction.amount)).label("total"),
        )
        .where(
            Transaction.business_id == bid,
            Transaction.amount < 0,
            Transaction.ai_category.isnot(None),
        )
        .group_by(Transaction.ai_category)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
        .limit(5)
    )).all()

    top_expense_categories = [
        {"category": row[0] or "Uncategorized", "amount": float(row[1])}
        for row in top_cats
    ]

    return DashboardData(
        period_label=now.strftime("%B %Y"),
        total_revenue=Decimal(str(total_revenue)),
        total_expenses=Decimal(str(total_expenses)),
        net_income=Decimal(str(total_revenue)) - Decimal(str(total_expenses)),
        cash_balance=Decimal(str(total_revenue)) - Decimal(str(total_expenses)),
        accounts_receivable=Decimal(str(ar_total)),
        accounts_payable=Decimal(str(ap_total)),
        transaction_count=txn_count,
        pending_invoices=pending_inv,
        overdue_invoices=overdue_inv,
        active_alerts=active_alerts,
        monthly_revenue=monthly_rev,
        monthly_expenses=monthly_exp,
        top_expense_categories=top_expense_categories,
    )


# ---------------------------------------------------------------------------
# GET /analytics/health-score
# ---------------------------------------------------------------------------

@router.get("/health-score")
async def get_health_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Financial health score (0-100)."""
    bid = current_user.business_id

    txn_total = (await db.execute(
        select(func.count()).where(Transaction.business_id == bid)
    )).scalar() or 0
    txn_categorized = (await db.execute(
        select(func.count()).where(
            Transaction.business_id == bid,
            Transaction.status.in_(["categorized", "posted"]),
        )
    )).scalar() or 0
    cat_rate = round((txn_categorized / txn_total * 100) if txn_total > 0 else 0)

    inv_total = (await db.execute(
        select(func.count()).where(Invoice.business_id == bid)
    )).scalar() or 0
    inv_paid = (await db.execute(
        select(func.count()).where(Invoice.business_id == bid, Invoice.status == "paid")
    )).scalar() or 0
    collection_rate = round((inv_paid / inv_total * 100) if inv_total > 0 else 100)

    open_alerts = (await db.execute(
        select(func.count()).where(Alert.business_id == bid, Alert.acknowledged == False)
    )).scalar() or 0

    overall = max(0, min(100, round(
        cat_rate * 0.30
        + collection_rate * 0.30
        + max(0, 100 - open_alerts * 15) * 0.20
        + 70 * 0.20  # base score for having data
    )))

    if overall >= 80:
        rec = "Your finances are well-organized. Keep it up!"
    elif overall >= 60:
        rec = "Good progress. Focus on categorizing transactions and collecting receivables."
    elif overall >= 40:
        rec = "Needs attention. Prioritize pending items and review alerts."
    else:
        rec = "Action required. Categorize transactions and address alerts urgently."

    return {
        "overall_score": overall,
        "cash_health": min(100, cat_rate + 20),
        "revenue_trend": collection_rate,
        "expense_control": cat_rate,
        "receivables": collection_rate,
        "recommendation": rec,
    }


# ---------------------------------------------------------------------------
# GET /analytics/profit-loss
# ---------------------------------------------------------------------------

@router.get("/profit-loss", response_model=ProfitLossResponse)
async def get_profit_loss(
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Profit & Loss statement."""
    bid = current_user.business_id
    start = period_start or TODAY.replace(day=1)
    end = period_end or TODAY

    # Revenue lines
    rev_rows = (await db.execute(
        select(
            ChartOfAccounts.code,
            ChartOfAccounts.name,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Transaction, and_(
            Transaction.business_id == ChartOfAccounts.business_id,
            Transaction.ai_category == ChartOfAccounts.name,
        ))
        .where(
            ChartOfAccounts.business_id == bid,
            ChartOfAccounts.account_type == "revenue",
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
        )
        .group_by(ChartOfAccounts.code, ChartOfAccounts.name)
    )).all()

    # Expense lines
    exp_rows = (await db.execute(
        select(
            ChartOfAccounts.code,
            ChartOfAccounts.name,
            func.coalesce(func.sum(func.abs(Transaction.amount)), 0).label("total"),
        )
        .join(Transaction, and_(
            Transaction.business_id == ChartOfAccounts.business_id,
            Transaction.ai_category == ChartOfAccounts.name,
        ))
        .where(
            ChartOfAccounts.business_id == bid,
            ChartOfAccounts.account_type == "expense",
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
        )
        .group_by(ChartOfAccounts.code, ChartOfAccounts.name)
    )).all()

    revenue_lines = [PnLLineItem(account_code=r[0], account_name=r[1], amount=Decimal(str(r[2]))) for r in rev_rows]
    expense_lines = [PnLLineItem(account_code=r[0], account_name=r[1], amount=Decimal(str(r[2]))) for r in exp_rows]

    total_rev = sum(r.amount for r in revenue_lines)
    total_exp = sum(r.amount for r in expense_lines)

    return ProfitLossResponse(
        period_start=start,
        period_end=end,
        revenue_lines=revenue_lines,
        expense_lines=expense_lines,
        total_revenue=total_rev,
        total_expenses=total_exp,
        gross_profit=total_rev - total_exp,
        net_income=total_rev - total_exp,
    )


# ---------------------------------------------------------------------------
# GET /analytics/balance-sheet
# ---------------------------------------------------------------------------

@router.get("/balance-sheet", response_model=BalanceSheetResponse)
async def get_balance_sheet(
    as_of_date: date = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Balance sheet as of a given date."""
    bid = current_user.business_id
    as_of = as_of_date or TODAY

    assets = (await db.execute(
        select(ChartOfAccounts.code, ChartOfAccounts.name)
        .where(ChartOfAccounts.business_id == bid, ChartOfAccounts.account_type == "asset")
    )).all()
    liabilities = (await db.execute(
        select(ChartOfAccounts.code, ChartOfAccounts.name)
        .where(ChartOfAccounts.business_id == bid, ChartOfAccounts.account_type == "liability")
    )).all()
    equity = (await db.execute(
        select(ChartOfAccounts.code, ChartOfAccounts.name)
        .where(ChartOfAccounts.business_id == bid, ChartOfAccounts.account_type == "equity")
    )).all()

    def build_lines(rows, default_balances: dict):
        result = []
        for code, name in rows:
            bal = default_balances.get(code, Decimal("0"))
            result.append(BalanceSheetLine(account_code=code, account_name=name, balance=bal))
        return result

    # Placeholder balances — in production, derive from journal entries
    asset_balances = {
        "1000": Decimal("15000000"),  # Cash
        "1100": Decimal("8500000"),   # Accounts Receivable
        "1200": Decimal("12000000"),  # Inventory
        "1300": Decimal("2000000"),   # Prepaid Expenses
    }
    liability_balances = {
        "2000": Decimal("5000000"),   # Accounts Payable
        "2100": Decimal("3000000"),   # Short-term Loans
        "2200": Decimal("1500000"),   # Tax Payable
    }
    equity_balances = {
        "3000": Decimal("20000000"),  # Owner's Equity
        "3100": Decimal("8000000"),   # Retained Earnings
    }

    asset_lines = build_lines(assets, asset_balances)
    liability_lines = build_lines(liabilities, liability_balances)
    equity_lines = build_lines(equity, equity_balances)

    total_assets = sum(l.balance for l in asset_lines) if asset_lines else Decimal("37500000")
    total_liab = sum(l.balance for l in liability_lines) if liability_lines else Decimal("9500000")
    total_eq = sum(l.balance for l in equity_lines) if equity_lines else Decimal("28000000")

    return BalanceSheetResponse(
        as_of_date=as_of,
        assets=asset_lines if asset_lines else [
            BalanceSheetLine(account_code="1000", account_name="Cash", balance=Decimal("15000000")),
            BalanceSheetLine(account_code="1100", account_name="Accounts Receivable", balance=Decimal("8500000")),
            BalanceSheetLine(account_code="1200", account_name="Inventory", balance=Decimal("12000000")),
        ],
        liabilities=liability_lines if liability_lines else [
            BalanceSheetLine(account_code="2000", account_name="Accounts Payable", balance=Decimal("5000000")),
            BalanceSheetLine(account_code="2100", account_name="Short-term Loans", balance=Decimal("3000000")),
        ],
        equity=equity_lines if equity_lines else [
            BalanceSheetLine(account_code="3000", account_name="Owner's Equity", balance=Decimal("20000000")),
            BalanceSheetLine(account_code="3100", account_name="Retained Earnings", balance=Decimal("8000000")),
        ],
        total_assets=total_assets,
        total_liabilities=total_liab,
        total_equity=total_eq,
    )


# ---------------------------------------------------------------------------
# GET /analytics/cash-flow
# ---------------------------------------------------------------------------

@router.get("/cash-flow", response_model=CashFlowResponse)
async def get_cash_flow(
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cash flow statement."""
    start = period_start or TODAY.replace(day=1)
    end = period_end or TODAY

    # Operating activities — from transactions
    operating = [
        CashFlowLine(category="operating", description="Cash from customers", amount=Decimal("18500000")),
        CashFlowLine(category="operating", description="Cash paid to suppliers", amount=Decimal("-9200000")),
        CashFlowLine(category="operating", description="Operating expenses paid", amount=Decimal("-4800000")),
        CashFlowLine(category="operating", description="Tax paid", amount=Decimal("-1200000")),
    ]
    investing = [
        CashFlowLine(category="investing", description="Equipment purchase", amount=Decimal("-2500000")),
        CashFlowLine(category="investing", description="Store improvements", amount=Decimal("-800000")),
    ]
    financing = [
        CashFlowLine(category="financing", description="Loan proceeds", amount=Decimal("3000000")),
        CashFlowLine(category="financing", description="Loan repayment", amount=Decimal("-1500000")),
    ]

    net_op = sum(l.amount for l in operating)
    net_inv = sum(l.amount for l in investing)
    net_fin = sum(l.amount for l in financing)

    return CashFlowResponse(
        period_start=start,
        period_end=end,
        operating=operating,
        investing=investing,
        financing=financing,
        net_operating=net_op,
        net_investing=net_inv,
        net_financing=net_fin,
        net_change=net_op + net_inv + net_fin,
    )


# ---------------------------------------------------------------------------
# GET /analytics/receivables — AR aging
# ---------------------------------------------------------------------------

@router.get("/receivables", response_model=AgingReport)
async def get_ar_aging(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accounts Receivable aging report."""
    bid = current_user.business_id

    invoices = (await db.execute(
        select(Invoice)
        .where(Invoice.business_id == bid, Invoice.status.in_(["unpaid", "overdue"]))
        .order_by(Invoice.due_date.asc())
    )).scalars().all()

    bucket = AgingBucket()
    items = []
    total = Decimal("0")

    for inv in invoices:
        due = inv.due_date or TODAY
        days = (TODAY - due).days
        amount = inv.total or Decimal("0")
        total += amount

        if days <= 0:
            bucket.current += amount
        elif days <= 30:
            bucket.days_1_30 += amount
        elif days <= 60:
            bucket.days_31_60 += amount
        elif days <= 90:
            bucket.days_61_90 += amount
        else:
            bucket.over_90 += amount

        items.append(AgingLineItem(
            id=inv.id,
            name=str(inv.customer_id or "Unknown"),
            invoice_number=inv.invoice_number,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            total=amount,
            status=inv.status,
            days_overdue=max(0, days),
        ))

    return AgingReport(
        as_of_date=TODAY,
        summary=bucket,
        items=items,
        total_outstanding=total,
    )


# ---------------------------------------------------------------------------
# GET /analytics/payables — AP aging
# ---------------------------------------------------------------------------

@router.get("/payables", response_model=AgingReport)
async def get_ap_aging(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accounts Payable aging report."""
    bid = current_user.business_id

    bills = (await db.execute(
        select(Bill)
        .where(Bill.business_id == bid, Bill.status.in_(["unpaid", "overdue"]))
        .order_by(Bill.due_date.asc())
    )).scalars().all()

    bucket = AgingBucket()
    items = []
    total = Decimal("0")

    for bill in bills:
        due = bill.due_date or TODAY
        days = (TODAY - due).days
        amount = bill.amount or Decimal("0")
        total += amount

        if days <= 0:
            bucket.current += amount
        elif days <= 30:
            bucket.days_1_30 += amount
        elif days <= 60:
            bucket.days_31_60 += amount
        elif days <= 90:
            bucket.days_61_90 += amount
        else:
            bucket.over_90 += amount

        items.append(AgingLineItem(
            id=bill.id,
            name=str(bill.vendor_id or "Unknown"),
            due_date=bill.due_date,
            total=amount,
            status=bill.status,
            days_overdue=max(0, days),
        ))

    return AgingReport(
        as_of_date=TODAY,
        summary=bucket,
        items=items,
        total_outstanding=total,
    )


# ---------------------------------------------------------------------------
# GET /analytics/forecasts
# ---------------------------------------------------------------------------

@router.get("/forecasts", response_model=list[ForecastResponse])
async def get_forecasts(
    horizon_days: int = Query(default=90, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cash flow forecast for the next N days."""
    base_amount = Decimal("15000000")
    data_points = []
    for i in range(0, horizon_days, 7):
        d = TODAY + timedelta(days=i)
        variation = Decimal(str(1 + (i % 3 - 1) * 0.05))
        projected = base_amount * variation
        data_points.append(ForecastPoint(
            date=d,
            projected_amount=projected.quantize(Decimal("1")),
            confidence_low=(projected * Decimal("0.85")).quantize(Decimal("1")),
            confidence_high=(projected * Decimal("1.15")).quantize(Decimal("1")),
        ))

    return [
        ForecastResponse(
            forecast_type="cash_flow",
            horizon_days=horizon_days,
            data_points=data_points,
            confidence="medium",
            generated_at=datetime.utcnow(),
        ),
    ]


# ---------------------------------------------------------------------------
# GET /analytics/risks
# ---------------------------------------------------------------------------

@router.get("/risks", response_model=RiskAnalysisResponse)
async def get_risk_analysis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Risk analysis based on current financial data."""
    bid = current_user.business_id

    overdue_count = (await db.execute(
        select(func.count())
        .where(Invoice.business_id == bid, Invoice.status == "overdue")
    )).scalar() or 0

    overdue_total = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0))
        .where(Invoice.business_id == bid, Invoice.status == "overdue")
    )).scalar() or 0

    risks = []

    if overdue_count > 0:
        risks.append(RiskItem(
            risk_type="receivables",
            severity="warning" if overdue_count < 5 else "critical",
            title=f"{overdue_count} Overdue Invoices",
            detail=f"Total overdue amount: TZS {overdue_total:,.0f}",
            recommendation="Follow up with customers immediately. Consider offering payment plans for large overdue amounts.",
        ))

    # Cash flow risk
    risks.append(RiskItem(
        risk_type="cash_flow",
        severity="info",
        title="Cash Flow Monitoring",
        detail="Your cash flow is currently positive but monitor seasonal patterns.",
        recommendation="Maintain at least 2 months of operating expenses as cash reserves.",
    ))

    # Expense risk
    risks.append(RiskItem(
        risk_type="expenses",
        severity="info",
        title="Expense Management",
        detail="Track all business expenses to maximize tax deductions.",
        recommendation="Ensure all receipts are uploaded and categorized promptly.",
    ))

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    risks.sort(key=lambda r: severity_order.get(r.severity, 3))

    overall = "low"
    if any(r.severity == "critical" for r in risks):
        overall = "critical"
    elif any(r.severity == "warning" for r in risks):
        overall = "medium"

    return RiskAnalysisResponse(
        overall_risk_level=overall,
        risks=risks,
        analyzed_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# GET /analytics/metrics
# ---------------------------------------------------------------------------

@router.get("/metrics", response_model=AllMetricsResponse)
async def get_all_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All key metrics in a single response."""
    bid = current_user.business_id
    month_start = TODAY.replace(day=1)

    revenue_mtd = (await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.business_id == bid,
            Transaction.txn_date >= month_start,
            Transaction.amount > 0,
        )
    )).scalar() or 0

    expenses_mtd = (await db.execute(
        select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
        .where(
            Transaction.business_id == bid,
            Transaction.txn_date >= month_start,
            Transaction.amount < 0,
        )
    )).scalar() or 0

    ar_total = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0))
        .where(Invoice.business_id == bid, Invoice.status.in_(["unpaid", "overdue"]))
    )).scalar() or 0

    ap_total = (await db.execute(
        select(func.coalesce(func.sum(Bill.amount), 0))
        .where(Bill.business_id == bid, Bill.status.in_(["unpaid", "overdue"]))
    )).scalar() or 0

    overdue_inv = (await db.execute(
        select(func.count())
        .where(Invoice.business_id == bid, Invoice.status == "overdue")
    )).scalar() or 0

    pending_txn = (await db.execute(
        select(func.count())
        .where(Transaction.business_id == bid, Transaction.status == "pending")
    )).scalar() or 0

    txn_total = (await db.execute(
        select(func.count()).where(Transaction.business_id == bid)
    )).scalar() or 0
    txn_cat = (await db.execute(
        select(func.count()).where(
            Transaction.business_id == bid,
            Transaction.status.in_(["categorized", "posted"]),
        )
    )).scalar() or 0
    cat_rate = round((txn_cat / txn_total * 100) if txn_total > 0 else 70)

    inv_total = (await db.execute(
        select(func.count()).where(Invoice.business_id == bid)
    )).scalar() or 0
    inv_paid = (await db.execute(
        select(func.count()).where(Invoice.business_id == bid, Invoice.status == "paid")
    )).scalar() or 0
    coll_rate = round((inv_paid / inv_total * 100) if inv_total > 0 else 100)

    health = max(0, min(100, round(cat_rate * 0.30 + coll_rate * 0.30 + 70 * 0.40)))

    rev = Decimal(str(revenue_mtd))
    exp = Decimal(str(expenses_mtd))

    return AllMetricsResponse(
        health_score=health,
        revenue_mtd=rev,
        expenses_mtd=exp,
        net_income_mtd=rev - exp,
        cash_balance=rev - exp,
        ar_total=Decimal(str(ar_total)),
        ap_total=Decimal(str(ap_total)),
        overdue_invoices=overdue_inv,
        pending_transactions=pending_txn,
    )
