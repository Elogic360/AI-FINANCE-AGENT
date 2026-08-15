"""
FinPilot AI — Financial Engine
──────────────────────────────
Core deterministic financial calculations.  Every method queries the
database via SQLAlchemy and computes results with Python ``Decimal`` math.

**No LLM calls** — all outputs are fully deterministic and reproducible.

Sign convention (double-entry):
    asset / expense                → debit-positive  (balance = debits − credits)
    liability / equity / revenue   → credit-positive (balance = credits − debits)
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import ChartOfAccounts, JournalEntry, JournalLine, Transaction
from app.models.contacts import Bill, Customer, Invoice, Vendor

from app.financial.metrics import (
    BalanceSheet,
    BreakEvenAnalysis,
    CashFlowStatement,
    CashMetrics,
    ExpenseMetrics,
    FinancialRatios,
    PayablesReport,
    PLStatement,
    ReceivablesMetrics,
    ReceivablesReport,
    RevenueMetrics,
    WorkingCapitalMetrics,
)


# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

_CREDIT_NORMAL = frozenset({"liability", "equity", "revenue"})
_ZERO = Decimal("0")


def _d(value: Any) -> Decimal:
    """Safely coerce *value* to ``Decimal``."""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return _ZERO
    return Decimal(str(value))


def _display_balance(debit: Decimal, credit: Decimal, account_type: str) -> Decimal:
    """
    Return the normal-balance display value.

    * debit-normal (asset, expense): debit − credit
    * credit-normal (liability, equity, revenue): credit − debit
    """
    if account_type in _CREDIT_NORMAL:
        return credit - debit
    return debit - credit


def _pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Return numerator / denominator as a Decimal percentage, or 0."""
    if denominator == _ZERO:
        return _ZERO
    return (numerator / denominator * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Return numerator / denominator as a Decimal, or 0."""
    if denominator == _ZERO:
        return _ZERO
    return (numerator / denominator).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )


# ──────────────────────────────────────────────────────────────────────
# Shared query helpers
# ──────────────────────────────────────────────────────────────────────

async def _account_balances_by_type(
    db: AsyncSession,
    org_id: uuid.UUID,
    account_type: str,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return per-account balances for a given type within an optional date range."""
    filters = [
        ChartOfAccounts.business_id == org_id,
        ChartOfAccounts.account_type == account_type,
        JournalEntry.is_draft.is_(False),
    ]
    if start_date is not None:
        filters.append(JournalEntry.entry_date >= start_date)
    if end_date is not None:
        filters.append(JournalEntry.entry_date <= end_date)

    stmt = (
        select(
            ChartOfAccounts.id.label("account_id"),
            ChartOfAccounts.code.label("code"),
            ChartOfAccounts.name.label("name"),
            ChartOfAccounts.account_type.label("account_type"),
            ChartOfAccounts.parent_id.label("parent_id"),
            func.coalesce(func.sum(JournalLine.debit), _ZERO).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), _ZERO).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(and_(*filters))
        .group_by(
            ChartOfAccounts.id, ChartOfAccounts.code,
            ChartOfAccounts.name, ChartOfAccounts.account_type,
            ChartOfAccounts.parent_id,
        )
        .order_by(ChartOfAccounts.code)
    )
    rows = (await db.execute(stmt)).all()

    items: list[dict[str, Any]] = []
    for r in rows:
        bal = _display_balance(r.total_debit, r.total_credit, r.account_type)
        items.append({
            "account_id": r.account_id,
            "code": r.code,
            "name": r.name,
            "account_type": r.account_type,
            "parent_id": r.parent_id,
            "total_debit": r.total_debit,
            "total_credit": r.total_credit,
            "balance": bal,
        })
    return items


async def _identify_cash_accounts(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> set[uuid.UUID]:
    """Return the set of cash/bank account IDs."""
    stmt = (
        select(ChartOfAccounts.id, ChartOfAccounts.name)
        .where(
            ChartOfAccounts.business_id == org_id,
            ChartOfAccounts.account_type == "asset",
        )
    )
    rows = (await db.execute(stmt)).all()
    return {r.id for r in rows if "cash" in r.name.lower() or "bank" in r.name.lower()}


# ──────────────────────────────────────────────────────────────────────
# FinancialEngine
# ──────────────────────────────────────────────────────────────────────

class FinancialEngine:
    """
    Stateless, deterministic financial calculation engine.

    All methods are ``async`` and accept an ``AsyncSession`` plus the
    ``org_id`` (business UUID) and a date / period parameter.
    """

    # ── 1. Revenue ────────────────────────────────────────────────────

    async def calculate_revenue(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        period: tuple[date, date],
    ) -> RevenueMetrics:
        """
        Calculate revenue metrics for a period.

        Parameters
        ----------
        period : tuple[date, date]
            (start_date, end_date)
        """
        start_date, end_date = period
        items = await _account_balances_by_type(
            db, org_id, "revenue", start_date=start_date, end_date=end_date,
        )

        total = _ZERO
        for item in items:
            total += abs(item["balance"])

        # Count revenue transactions in the period
        txn_count_stmt = (
            select(func.count(Transaction.id))
            .where(
                Transaction.business_id == org_id,
                Transaction.txn_date >= start_date,
                Transaction.txn_date <= end_date,
                Transaction.ai_category.ilike("%revenue%"),
            )
        )
        txn_count = (await db.execute(txn_count_stmt)).scalar() or 0

        avg_txn = (total / txn_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if txn_count else _ZERO

        # Month-over-month growth (compare to previous period of same length)
        period_length = (end_date - start_date).days + 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_length - 1)
        prev_items = await _account_balances_by_type(
            db, org_id, "revenue", start_date=prev_start, end_date=prev_end,
        )
        prev_total = sum(abs(i["balance"]) for i in prev_items)
        mom_growth = _pct(total - prev_total, prev_total) if prev_total else None

        return RevenueMetrics(
            org_id=org_id,
            period_start=start_date,
            period_end=end_date,
            total_revenue=total,
            recurring_revenue=_ZERO,  # Requires subscription model data
            one_time_revenue=total,
            revenue_by_account=items,
            transaction_count=txn_count,
            average_transaction_value=avg_txn,
            month_over_month_growth=mom_growth,
        )

    # ── 2. Expenses ───────────────────────────────────────────────────

    async def calculate_expenses(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        period: tuple[date, date],
    ) -> ExpenseMetrics:
        """Calculate expense metrics for a period."""
        start_date, end_date = period
        items = await _account_balances_by_type(
            db, org_id, "expense", start_date=start_date, end_date=end_date,
        )

        cogs = _ZERO
        operating = _ZERO
        financial = _ZERO
        other = _ZERO

        for item in items:
            amt = abs(item["balance"])
            name_lower = item["name"].lower()
            if "cost of goods" in name_lower or "cogs" in name_lower or item["parent_id"] is not None:
                cogs += amt
            elif any(kw in name_lower for kw in ("bank", "interest", "finance", "loan")):
                financial += amt
            elif any(kw in name_lower for kw in ("rent", "salary", "wage", "utility", "insurance", "office", "marketing")):
                operating += amt
            else:
                other += amt

        total = cogs + operating + financial + other

        # Top 5 expense accounts
        top5 = sorted(items, key=lambda x: abs(x["balance"]), reverse=True)[:5]

        return ExpenseMetrics(
            org_id=org_id,
            period_start=start_date,
            period_end=end_date,
            total_expenses=total,
            cost_of_goods_sold=cogs,
            operating_expenses=operating,
            financial_expenses=financial,
            other_expenses=other,
            expense_by_account=items,
            expense_by_category={
                "cost_of_goods_sold": cogs,
                "operating_expenses": operating,
                "financial_expenses": financial,
                "other_expenses": other,
            },
            top_expense_accounts=top5,
        )

    # ── 3. Profit & Loss ──────────────────────────────────────────────

    async def calculate_profit_loss(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        period: tuple[date, date],
    ) -> PLStatement:
        """Calculate a full Profit & Loss statement."""
        start_date, end_date = period

        rev_items = await _account_balances_by_type(
            db, org_id, "revenue", start_date=start_date, end_date=end_date,
        )
        exp_items = await _account_balances_by_type(
            db, org_id, "expense", start_date=start_date, end_date=end_date,
        )

        total_revenue = sum(abs(i["balance"]) for i in rev_items)

        cogs = _ZERO
        operating = _ZERO
        other_exp = _ZERO
        for item in exp_items:
            amt = abs(item["balance"])
            name_lower = item["name"].lower()
            if "cost of goods" in name_lower or "cogs" in name_lower or item["parent_id"] is not None:
                cogs += amt
            elif any(kw in name_lower for kw in ("bank", "interest", "finance")):
                other_exp += amt
            else:
                operating += amt

        # Other income (gain accounts)
        gain_stmt = (
            select(
                func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), _ZERO).label("amount"),
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
            .where(
                ChartOfAccounts.business_id == org_id,
                ChartOfAccounts.account_type == "revenue",
                ChartOfAccounts.name.ilike("%gain%"),
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date >= start_date,
                JournalEntry.entry_date <= end_date,
            )
        )
        gain_row = (await db.execute(gain_stmt)).one()
        other_income = abs(gain_row.amount) if gain_row else _ZERO

        gross_profit = total_revenue - cogs
        operating_income = gross_profit - operating
        net_income = operating_income + other_income - other_exp

        return PLStatement(
            org_id=org_id,
            period_start=start_date,
            period_end=end_date,
            revenue=total_revenue,
            cost_of_goods_sold=cogs,
            gross_profit=gross_profit,
            operating_expenses=operating,
            operating_income=operating_income,
            other_income=other_income,
            other_expenses=other_exp,
            net_income=net_income,
            revenue_items=[
                {"account_id": i["account_id"], "code": i["code"], "name": i["name"], "amount": abs(i["balance"])}
                for i in rev_items
            ],
            expense_items=[
                {"account_id": i["account_id"], "code": i["code"], "name": i["name"], "amount": abs(i["balance"])}
                for i in exp_items
            ],
        )

    # ── 4. Balance Sheet ──────────────────────────────────────────────

    async def calculate_balance_sheet(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        as_of_date: date,
    ) -> BalanceSheet:
        """Calculate a Balance Sheet as of a given date."""
        assets = await _account_balances_by_type(
            db, org_id, "asset", end_date=as_of_date,
        )
        liabilities = await _account_balances_by_type(
            db, org_id, "liability", end_date=as_of_date,
        )
        equity = await _account_balances_by_type(
            db, org_id, "equity", end_date=as_of_date,
        )

        total_assets = sum(a["balance"] for a in assets)
        total_liabilities = sum(l["balance"] for l in liabilities)
        total_equity = sum(e["balance"] for e in equity)

        # Current vs non-current classification (heuristic by account name)
        current_asset_keywords = ("cash", "bank", "receivable", "inventory", "stock", "prepaid", "petty")
        current_liability_keywords = ("payable", "short-term", "current", "tax payable", "accrued")

        current_assets = sum(
            a["balance"] for a in assets
            if any(kw in a["name"].lower() for kw in current_asset_keywords)
        )
        non_current_assets = total_assets - current_assets

        current_liabilities = sum(
            l["balance"] for l in liabilities
            if any(kw in l["name"].lower() for kw in current_liability_keywords)
        )
        non_current_liabilities = total_liabilities - current_liabilities

        is_balanced = total_assets == (total_liabilities + total_equity)

        return BalanceSheet(
            org_id=org_id,
            as_of_date=as_of_date,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            current_assets=current_assets,
            non_current_assets=non_current_assets,
            current_liabilities=current_liabilities,
            non_current_liabilities=non_current_liabilities,
            assets=[
                {"account_id": a["account_id"], "code": a["code"], "name": a["name"], "balance": a["balance"]}
                for a in assets
            ],
            liabilities=[
                {"account_id": l["account_id"], "code": l["code"], "name": l["name"], "balance": l["balance"]}
                for l in liabilities
            ],
            equity=[
                {"account_id": e["account_id"], "code": e["code"], "name": e["name"], "balance": e["balance"]}
                for e in equity
            ],
            is_balanced=is_balanced,
        )

    # ── 5. Cash Flow ──────────────────────────────────────────────────

    async def calculate_cash_flow(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        period: tuple[date, date],
    ) -> CashFlowStatement:
        """Calculate a Cash Flow Statement (indirect method)."""
        start_date, end_date = period

        cash_account_ids = await _identify_cash_accounts(db, org_id)

        # All asset account IDs
        all_assets_stmt = (
            select(ChartOfAccounts.id)
            .where(
                ChartOfAccounts.business_id == org_id,
                ChartOfAccounts.account_type == "asset",
            )
        )
        all_asset_ids = {r.id for r in (await db.execute(all_assets_stmt)).all()}
        non_cash_ids = all_asset_ids - cash_account_ids

        # Operating: revenue inflows − expense outflows
        rev_stmt = (
            select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
            .where(
                ChartOfAccounts.business_id == org_id,
                ChartOfAccounts.account_type == "revenue",
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date >= start_date,
                JournalEntry.entry_date <= end_date,
            )
        )
        operating_inflows = (await db.execute(rev_stmt)).scalar() or _ZERO

        exp_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
            .where(
                ChartOfAccounts.business_id == org_id,
                ChartOfAccounts.account_type == "expense",
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date >= start_date,
                JournalEntry.entry_date <= end_date,
            )
        )
        operating_outflows = (await db.execute(exp_stmt)).scalar() or _ZERO
        net_operating = operating_inflows - operating_outflows

        # Investing: non-cash asset changes
        inv_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                JournalLine.account_id.in_(non_cash_ids) if non_cash_ids else False,
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date >= start_date,
                JournalEntry.entry_date <= end_date,
            )
        )
        inv_raw = (await db.execute(inv_stmt)).scalar() or _ZERO
        net_investing = -inv_raw  # Debit increase on non-cash asset = cash outflow

        # Financing: liability + equity changes
        fin_stmt = (
            select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
            .where(
                ChartOfAccounts.account_type.in_(["liability", "equity"]),
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date >= start_date,
                JournalEntry.entry_date <= end_date,
            )
        )
        net_financing = (await db.execute(fin_stmt)).scalar() or _ZERO

        # Cash balances
        beg_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                JournalLine.account_id.in_(cash_account_ids) if cash_account_ids else False,
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date < start_date,
            )
        )
        end_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                JournalLine.account_id.in_(cash_account_ids) if cash_account_ids else False,
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date <= end_date,
            )
        )
        beginning_cash = (await db.execute(beg_stmt)).scalar() or _ZERO
        net_cash_flow = net_operating + net_investing + net_financing
        ending_cash = beginning_cash + net_cash_flow

        return CashFlowStatement(
            org_id=org_id,
            period_start=start_date,
            period_end=end_date,
            operating_activities=net_operating,
            investing_activities=net_investing,
            financing_activities=net_financing,
            net_cash_flow=net_cash_flow,
            beginning_cash=beginning_cash,
            ending_cash=ending_cash,
            details={
                "operating": [
                    {"type": "revenue_inflows", "amount": operating_inflows},
                    {"type": "expense_outflows", "amount": -operating_outflows},
                ],
            },
        )

    # ── 6. Receivables ────────────────────────────────────────────────

    async def calculate_receivables(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
    ) -> ReceivablesReport:
        """Calculate accounts receivable report from invoices."""
        today = date.today()

        stmt = (
            select(Invoice)
            .where(
                Invoice.business_id == org_id,
                Invoice.status.in_(["unpaid", "overdue"]),
            )
            .order_by(Invoice.due_date)
        )
        invoices = (await db.execute(stmt)).scalars().all()

        total = _ZERO
        current = _ZERO
        overdue_30 = _ZERO
        overdue_60 = _ZERO
        overdue_90_plus = _ZERO
        total_days = _ZERO
        count_with_due = 0
        inv_list: list[dict[str, Any]] = []
        by_customer: dict[str, Decimal] = {}

        for inv in invoices:
            amt = inv.total or _ZERO
            total += amt
            days_overdue = (today - inv.due_date).days if inv.due_date else 0

            if days_overdue <= 0:
                current += amt
            elif days_overdue <= 30:
                overdue_30 += amt
            elif days_overdue <= 60:
                overdue_60 += amt
            else:
                overdue_90_plus += amt

            if inv.issue_date and inv.due_date:
                total_days += _d((inv.due_date - inv.issue_date).days)
                count_with_due += 1

            inv_list.append({
                "invoice_id": str(inv.id),
                "customer_id": str(inv.customer_id) if inv.customer_id else None,
                "invoice_number": inv.invoice_number,
                "total": amt,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "days_overdue": max(days_overdue, 0),
                "status": inv.status,
            })

            cust_id = str(inv.customer_id) if inv.customer_id else "unknown"
            by_customer[cust_id] = by_customer.get(cust_id, _ZERO) + amt

        avg_dso = (total_days / count_with_due).quantize(Decimal("1"), rounding=ROUND_HALF_UP) if count_with_due else _ZERO

        return ReceivablesReport(
            org_id=org_id,
            total_outstanding=total,
            current=current,
            overdue_30=overdue_30,
            overdue_60=overdue_60,
            overdue_90_plus=overdue_90_plus,
            average_days_outstanding=avg_dso,
            invoices=inv_list,
            by_customer=[
                {"customer_id": cid, "total_outstanding": amt}
                for cid, amt in sorted(by_customer.items(), key=lambda x: x[1], reverse=True)
            ],
        )

    # ── 7. Payables ───────────────────────────────────────────────────

    async def calculate_payables(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
    ) -> PayablesReport:
        """Calculate accounts payable report from bills."""
        today = date.today()

        stmt = (
            select(Bill)
            .where(
                Bill.business_id == org_id,
                Bill.status.in_(["unpaid", "overdue"]),
            )
            .order_by(Bill.due_date)
        )
        bills = (await db.execute(stmt)).scalars().all()

        total = _ZERO
        current = _ZERO
        overdue_30 = _ZERO
        overdue_60 = _ZERO
        overdue_90_plus = _ZERO
        total_days = _ZERO
        count_with_due = 0
        bill_list: list[dict[str, Any]] = []
        by_vendor: dict[str, Decimal] = {}

        for bill in bills:
            amt = bill.amount or _ZERO
            total += amt
            days_overdue = (today - bill.due_date).days if bill.due_date else 0

            if days_overdue <= 0:
                current += amt
            elif days_overdue <= 30:
                overdue_30 += amt
            elif days_overdue <= 60:
                overdue_60 += amt
            else:
                overdue_90_plus += amt

            if bill.due_date:
                total_days += _d(days_overdue)
                count_with_due += 1

            bill_list.append({
                "bill_id": str(bill.id),
                "vendor_id": str(bill.vendor_id) if bill.vendor_id else None,
                "amount": amt,
                "due_date": bill.due_date.isoformat() if bill.due_date else None,
                "days_overdue": max(days_overdue, 0),
                "status": bill.status,
            })

            vend_id = str(bill.vendor_id) if bill.vendor_id else "unknown"
            by_vendor[vend_id] = by_vendor.get(vend_id, _ZERO) + amt

        avg_dpo = (total_days / count_with_due).quantize(Decimal("1"), rounding=ROUND_HALF_UP) if count_with_due else _ZERO

        return PayablesReport(
            org_id=org_id,
            total_outstanding=total,
            current=current,
            overdue_30=overdue_30,
            overdue_60=overdue_60,
            overdue_90_plus=overdue_90_plus,
            average_days_outstanding=avg_dpo,
            bills=bill_list,
            by_vendor=[
                {"vendor_id": vid, "total_outstanding": amt}
                for vid, amt in sorted(by_vendor.items(), key=lambda x: x[1], reverse=True)
            ],
        )

    # ── 8. Working Capital ────────────────────────────────────────────

    async def calculate_working_capital(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
    ) -> Decimal:
        """Return net working capital (current assets − current liabilities)."""
        bs = await self.calculate_balance_sheet(db, org_id, date.today())
        return bs.current_assets - bs.current_liabilities

    # ── 9. Financial Ratios ───────────────────────────────────────────

    async def calculate_ratios(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
    ) -> FinancialRatios:
        """Calculate comprehensive financial ratios."""
        today = date.today()
        # Use trailing 12 months for income-statement ratios
        period_start = today - timedelta(days=365)

        bs = await self.calculate_balance_sheet(db, org_id, today)
        pl = await self.calculate_profit_loss(db, org_id, (period_start, today))

        # Cash accounts
        cash_ids = await _identify_cash_accounts(db, org_id)
        cash_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                JournalLine.account_id.in_(cash_ids) if cash_ids else False,
                JournalEntry.is_draft.is_(False),
            )
        )
        cash_balance = (await db.execute(cash_stmt)).scalar() or _ZERO

        # Inventory (asset accounts with "inventory" or "stock")
        inv_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
            .where(
                ChartOfAccounts.business_id == org_id,
                ChartOfAccounts.account_type == "asset",
                ChartOfAccounts.name.ilike("%inventory%"),
                JournalEntry.is_draft.is_(False),
            )
        )
        inventory = (await db.execute(inv_stmt)).scalar() or _ZERO

        quick_assets = bs.current_assets - inventory

        # ── Liquidity ──
        current_ratio = _safe_ratio(bs.current_assets, bs.current_liabilities)
        quick_ratio = _safe_ratio(quick_assets, bs.current_liabilities)
        cash_ratio = _safe_ratio(cash_balance, bs.current_liabilities)

        # ── Profitability ──
        gross_margin = _pct(pl.gross_profit, pl.revenue)
        operating_margin = _pct(pl.operating_income, pl.revenue)
        net_margin = _pct(pl.net_income, pl.revenue)
        roe = _pct(pl.net_income, bs.total_equity)
        roa = _pct(pl.net_income, bs.total_assets)

        # ── Efficiency ──
        # Receivables turnover = revenue / average receivables
        rec = await self.calculate_receivables(db, org_id)
        receivables_turnover = _safe_ratio(pl.revenue, rec.total_outstanding)

        # Payables turnover = COGS / average payables
        pay = await self.calculate_payables(db, org_id)
        payables_turnover = _safe_ratio(pl.cost_of_goods_sold, pay.total_outstanding)

        asset_turnover = _safe_ratio(pl.revenue, bs.total_assets)

        # ── Leverage ──
        debt_to_equity = _safe_ratio(bs.total_liabilities, bs.total_equity)
        debt_to_assets = _safe_ratio(bs.total_liabilities, bs.total_assets)

        # Interest coverage = operating income / financial expenses
        interest_coverage = _safe_ratio(pl.operating_income, pl.other_expenses)

        return FinancialRatios(
            org_id=org_id,
            as_of_date=today,
            current_ratio=current_ratio,
            quick_ratio=quick_ratio,
            cash_ratio=cash_ratio,
            gross_margin=gross_margin,
            operating_margin=operating_margin,
            net_margin=net_margin,
            roe=roe,
            roa=roa,
            receivables_turnover=receivables_turnover,
            payables_turnover=payables_turnover,
            asset_turnover=asset_turnover,
            debt_to_equity=debt_to_equity,
            debt_to_assets=debt_to_assets,
            interest_coverage=interest_coverage,
        )

    # ── 10. Break-Even Analysis ───────────────────────────────────────

    async def calculate_break_even(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
    ) -> BreakEvenAnalysis:
        """
        Estimate break-even point.

        Heuristic: expenses containing rent/salary/insurance/depreciation
        are classified as fixed; others as variable.
        """
        today = date.today()
        period_start = today - timedelta(days=365)

        exp_items = await _account_balances_by_type(
            db, org_id, "expense", start_date=period_start, end_date=today,
        )
        rev_items = await _account_balances_by_type(
            db, org_id, "revenue", start_date=period_start, end_date=today,
        )

        fixed_keywords = ("rent", "salary", "wage", "insurance", "depreciation", "amortization", "lease", "mortgage")
        fixed = _ZERO
        variable = _ZERO

        for item in exp_items:
            amt = abs(item["balance"])
            name_lower = item["name"].lower()
            if any(kw in name_lower for kw in fixed_keywords):
                fixed += amt
            else:
                variable += amt

        total_revenue = sum(abs(i["balance"]) for i in rev_items)
        total_expenses = fixed + variable
        contribution_margin = total_revenue - variable
        cm_ratio = _safe_ratio(contribution_margin, total_revenue)
        be_revenue = _safe_ratio(fixed, cm_ratio)
        margin_of_safety = total_revenue - be_revenue
        mos_ratio = _pct(margin_of_safety, total_revenue)

        return BreakEvenAnalysis(
            org_id=org_id,
            period_start=period_start,
            period_end=today,
            fixed_costs=fixed,
            variable_costs=variable,
            total_revenue=total_revenue,
            contribution_margin=contribution_margin,
            contribution_margin_ratio=cm_ratio,
            break_even_revenue=be_revenue,
            break_even_units=_ZERO,  # Requires unit pricing data
            margin_of_safety=margin_of_safety,
            margin_of_safety_ratio=mos_ratio,
            is_above_breakeven=total_revenue > be_revenue,
        )
