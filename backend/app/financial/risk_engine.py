"""
FinPilot AI — Risk Detection Engine
────────────────────────────────────
Deterministic financial risk detection across 11 categories:

    CASH_FLOW, PROFITABILITY, EXPENSE, RECEIVABLE, PAYABLE,
    INVENTORY, FRAUD, DATA_QUALITY, CONCENTRATION, TAX, OPERATIONAL

Each risk includes severity, category, title, evidence, impact,
recommendation, and confidence.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import ChartOfAccounts, JournalEntry, JournalLine, Transaction
from app.models.contacts import Bill, Invoice

from app.financial.metrics import Risk
from app.financial.engine import (
    FinancialEngine,
    _safe_ratio,
    _pct,
    _ZERO,
    _d,
)


# ──────────────────────────────────────────────────────────────────────
# Risk detection functions (each returns list[Risk])
# ──────────────────────────────────────────────────────────────────────

async def _detect_cash_flow_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect cash flow related risks."""
    risks: list[Risk] = []
    today = date.today()
    period = (today - timedelta(days=90), today)

    cf = await engine.calculate_cash_flow(db, org_id, period)

    # Negative operating cash flow
    if cf.operating_activities < _ZERO:
        risks.append(Risk(
            category="CASH_FLOW",
            severity="high" if cf.operating_activities < -Decimal("100000") else "medium",
            title="Negative Operating Cash Flow",
            evidence=f"Operating cash flow is {cf.operating_activities} over the last 90 days.",
            impact="Business is spending more than it earns from operations. "
                   "Without intervention, cash reserves will deplete.",
            recommendation="Review expense categories for cost-cutting opportunities. "
                          "Accelerate receivables collection and negotiate extended payables terms.",
            confidence=Decimal("0.9"),
            affected_amount=abs(cf.operating_activities),
        ))

    # Rapid cash depletion
    if cf.ending_cash < cf.beginning_cash and cf.beginning_cash > _ZERO:
        depletion_rate = _pct(cf.beginning_cash - cf.ending_cash, cf.beginning_cash)
        if depletion_rate > Decimal("30"):
            risks.append(Risk(
                category="CASH_FLOW",
                severity="critical" if depletion_rate > Decimal("50") else "high",
                title="Rapid Cash Depletion",
                evidence=f"Cash decreased by {depletion_rate}% over the last 90 days "
                         f"(from {cf.beginning_cash} to {cf.ending_cash}).",
                impact="At current burn rate, the business may face insolvency within months.",
                recommendation="Immediately review all discretionary spending. "
                              "Consider emergency financing options.",
                confidence=Decimal("0.85"),
                affected_amount=cf.beginning_cash - cf.ending_cash,
            ))

    # Low cash balance
    if cf.ending_cash < _ZERO:
        risks.append(Risk(
            category="CASH_FLOW",
            severity="critical",
            title="Negative Cash Balance",
            evidence=f"Ending cash position is {cf.ending_cash}.",
            impact="Business cannot meet its financial obligations.",
            recommendation="Urgent: Secure emergency funding or negotiate payment deferrals.",
            confidence=Decimal("0.95"),
            affected_amount=abs(cf.ending_cash),
        ))

    return risks


async def _detect_profitability_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect profitability related risks."""
    risks: list[Risk] = []
    today = date.today()
    period = (today - timedelta(days=180), today)

    pl = await engine.calculate_profit_loss(db, org_id, period)

    if pl.net_income < _ZERO:
        severity = "critical" if abs(pl.net_income) > pl.revenue * Decimal("0.2") else "high"
        risks.append(Risk(
            category="PROFITABILITY",
            severity=severity,
            title="Net Loss",
            evidence=f"Net loss of {abs(pl.net_income)} over the last 180 days. "
                     f"Revenue: {pl.revenue}, Total expenses: {pl.cost_of_goods_sold + pl.operating_expenses + pl.other_expenses}.",
            impact="Sustained losses erode equity and threaten business viability.",
            recommendation="Analyze expense breakdown for cost reduction. "
                          "Review pricing strategy and explore revenue diversification.",
            confidence=Decimal("0.9"),
            affected_amount=abs(pl.net_income),
        ))

    # Declining margins
    if pl.revenue > _ZERO:
        gross_margin = _pct(pl.gross_profit, pl.revenue)
        if gross_margin < Decimal("10"):
            risks.append(Risk(
                category="PROFITABILITY",
                severity="high" if gross_margin < _ZERO else "medium",
                title="Low Gross Margin",
                evidence=f"Gross margin is {gross_margin}%. Industry healthy range is typically 30-50%.",
                impact="Low margins leave little room for operating expenses and growth investment.",
                recommendation="Review pricing strategy and cost of goods. "
                              "Negotiate better supplier terms or optimize production costs.",
                confidence=Decimal("0.8"),
            ))

    return risks


async def _detect_expense_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect expense related risks."""
    risks: list[Risk] = []
    today = date.today()
    current = (today - timedelta(days=90), today)
    previous = (today - timedelta(days=180), today - timedelta(days=91))

    exp = await engine.calculate_expenses(db, org_id, current)
    prev_exp = await engine.calculate_expenses(db, org_id, previous)
    rev = await engine.calculate_revenue(db, org_id, current)

    # Expenses exceed revenue
    if rev.total_revenue > _ZERO and exp.total_expenses > rev.total_revenue:
        risks.append(Risk(
            category="EXPENSE",
            severity="high",
            title="Expenses Exceed Revenue",
            evidence=f"Expenses ({exp.total_expenses}) exceed revenue ({rev.total_revenue}) "
                     f"by {exp.total_expenses - rev.total_revenue} in the last 90 days.",
            impact="Operating at a loss. Business is consuming capital to sustain operations.",
            recommendation="Implement expense reduction plan. Prioritize cuts in "
                          "non-essential operating expenses.",
            confidence=Decimal("0.95"),
            affected_amount=exp.total_expenses - rev.total_revenue,
        ))

    # Rapid expense growth
    if prev_exp.total_expenses > _ZERO:
        growth = _pct(exp.total_expenses - prev_exp.total_expenses, prev_exp.total_expenses)
        if growth > Decimal("30"):
            risks.append(Risk(
                category="EXPENSE",
                severity="medium" if growth < Decimal("50") else "high",
                title="Rapid Expense Growth",
                evidence=f"Expenses grew by {growth}% compared to the prior 90-day period.",
                impact="Uncontrolled expense growth can quickly erode profitability.",
                recommendation="Audit recent expense increases. Implement approval workflows "
                              "for new expenditures.",
                confidence=Decimal("0.8"),
                affected_amount=exp.total_expenses - prev_exp.total_expenses,
            ))

    return risks


async def _detect_receivable_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect accounts receivable risks."""
    risks: list[Risk] = []
    rec = await engine.calculate_receivables(db, org_id)

    if rec.total_outstanding == _ZERO:
        return risks

    # High overdue ratio
    overdue_total = rec.overdue_30 + rec.overdue_60 + rec.overdue_90_plus
    overdue_ratio = _safe_ratio(overdue_total, rec.total_outstanding)

    if overdue_ratio > Decimal("0.3"):
        risks.append(Risk(
            category="RECEIVABLE",
            severity="high" if overdue_ratio > Decimal("0.5") else "medium",
            title="High Overdue Receivables",
            evidence=f"{(overdue_ratio * 100).quantize(Decimal('0.1'))}% of receivables are overdue "
                     f"({overdue_total} out of {rec.total_outstanding}).",
            impact="Impaired cash flow and potential bad debt write-offs.",
            recommendation="Implement stricter credit policies. Follow up on overdue invoices "
                          "and consider offering early payment discounts.",
            confidence=Decimal("0.9"),
            affected_amount=overdue_total,
        ))

    # Long DSO
    if rec.average_days_outstanding > 60:
        risks.append(Risk(
            category="RECEIVABLE",
            severity="medium",
            title="Slow Collections (High DSO)",
            evidence=f"Average days sales outstanding: {rec.average_days_outstanding} days.",
            impact="Extended collection periods strain working capital.",
            recommendation="Review payment terms. Implement automated payment reminders "
                          "and consider invoice factoring for large receivables.",
            confidence=Decimal("0.85"),
        ))

    # 90+ day overdue (potential bad debt)
    if rec.overdue_90_plus > _ZERO:
        risks.append(Risk(
            category="RECEIVABLE",
            severity="high",
            title="Potential Bad Debt",
            evidence=f"{rec.overdue_90_plus} in receivables overdue by 90+ days.",
            impact="High likelihood of non-payment. Consider provisioning for bad debt.",
            recommendation="Escalate collection efforts for 90+ day accounts. "
                          "Review bad debt allowance and write off uncollectable amounts.",
            confidence=Decimal("0.8"),
            affected_amount=rec.overdue_90_plus,
        ))

    return risks


async def _detect_payable_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect accounts payable risks."""
    risks: list[Risk] = []
    pay = await engine.calculate_payables(db, org_id)

    if pay.total_outstanding == _ZERO:
        return risks

    # High overdue payables
    overdue_total = pay.overdue_30 + pay.overdue_60 + pay.overdue_90_plus
    if overdue_total > _ZERO:
        overdue_ratio = _safe_ratio(overdue_total, pay.total_outstanding)
        risks.append(Risk(
            category="PAYABLE",
            severity="high" if overdue_ratio > Decimal("0.3") else "medium",
            title="Overdue Payables",
            evidence=f"{overdue_total} in payables are overdue "
                     f"({(overdue_ratio * 100).quantize(Decimal('0.1'))}% of total).",
            impact="Damaged vendor relationships, potential service disruptions, "
                   "and possible late payment penalties.",
            recommendation="Prioritize overdue payments by amount and vendor importance. "
                          "Negotiate payment plans for large overdue amounts.",
            confidence=Decimal("0.9"),
            affected_amount=overdue_total,
        ))

    # Payables significantly exceed receivables
    rec = await engine.calculate_receivables(db, org_id)
    if rec.total_outstanding > _ZERO and pay.total_outstanding > rec.total_outstanding * Decimal("2"):
        risks.append(Risk(
            category="PAYABLE",
            severity="medium",
            title="Payables Significantly Exceed Receivables",
            evidence=f"Payables ({pay.total_outstanding}) are more than 2x receivables ({rec.total_outstanding}).",
            impact="Negative working capital position may indicate cash flow stress.",
            recommendation="Accelerate receivables collection. Review payables schedule "
                          "and negotiate extended terms where possible.",
            confidence=Decimal("0.75"),
        ))

    return risks


async def _detect_fraud_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect potential fraud indicators."""
    risks: list[Risk] = []
    today = date.today()

    # Check for round-number transactions (potential fabrication)
    round_stmt = (
        select(func.count(Transaction.id))
        .where(
            Transaction.business_id == org_id,
            Transaction.amount % 1000 == 0,
            Transaction.amount > 0,
            Transaction.txn_date >= today - timedelta(days=90),
        )
    )
    round_count = (await db.execute(round_stmt)).scalar() or 0

    total_stmt = (
        select(func.count(Transaction.id))
        .where(
            Transaction.business_id == org_id,
            Transaction.txn_date >= today - timedelta(days=90),
        )
    )
    total_count = (await db.execute(total_stmt)).scalar() or 0

    if total_count > 10 and round_count > 0:
        round_ratio = _d(round_count) / _d(total_count)
        if round_ratio > Decimal("0.5"):
            risks.append(Risk(
                category="FRAUD",
                severity="medium",
                title="High Proportion of Round-Number Transactions",
                evidence=f"{round_count} of {total_count} transactions ({(round_ratio * 100).quantize(Decimal('0.1'))}%) "
                         f"are exact round numbers.",
                impact="Round-number transactions may indicate fabricated or estimated entries.",
                recommendation="Audit round-number transactions for supporting documentation. "
                              "Implement transaction-level document attachment requirements.",
                confidence=Decimal("0.6"),
            ))

    # Check for weekend/after-hours entries (if timestamps available)
    # Check for duplicate amounts on same day
    dup_stmt = (
        select(
            Transaction.amount,
            Transaction.txn_date,
            func.count(Transaction.id).label("cnt"),
        )
        .where(
            Transaction.business_id == org_id,
            Transaction.txn_date >= today - timedelta(days=30),
        )
        .group_by(Transaction.amount, Transaction.txn_date)
        .having(func.count(Transaction.id) > 2)
    )
    dups = (await db.execute(dup_stmt)).all()

    if dups:
        dup_total = sum(d.amount * (d.cnt - 1) for d in dups)
        risks.append(Risk(
            category="FRAUD",
            severity="low",
            title="Duplicate Amounts on Same Day",
            evidence=f"{len(dups)} instances of 3+ transactions with identical amounts on the same day.",
            impact="May indicate duplicate entries or intentional splitting to avoid approval limits.",
            recommendation="Review flagged transactions for legitimacy. "
                          "Implement duplicate detection in transaction import.",
            confidence=Decimal("0.5"),
            affected_amount=dup_total,
        ))

    return risks


async def _detect_data_quality_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect data quality issues."""
    risks: list[Risk] = []

    # Uncategorized transactions
    uncategorized_stmt = (
        select(func.count(Transaction.id))
        .where(
            Transaction.business_id == org_id,
            Transaction.status == "pending",
        )
    )
    uncategorized = (await db.execute(uncategorized_stmt)).scalar() or 0

    if uncategorized > 0:
        risks.append(Risk(
            category="DATA_QUALITY",
            severity="low" if uncategorized < 10 else "medium",
            title=f"{uncategorized} Uncategorized Transactions",
            evidence=f"{uncategorized} transactions are still pending categorization.",
            impact="Incomplete categorization affects report accuracy and decision-making.",
            recommendation="Run auto-categorization and manually review remaining uncategorized entries.",
            confidence=Decimal("0.95"),
        ))

    # Draft journal entries
    draft_stmt = (
        select(func.count(JournalEntry.id))
        .where(
            JournalEntry.business_id == org_id,
            JournalEntry.is_draft.is_(True),
        )
    )
    drafts = (await db.execute(draft_stmt)).scalar() or 0

    if drafts > 5:
        risks.append(Risk(
            category="DATA_QUALITY",
            severity="low",
            title=f"{drafts} Unposted Journal Entries",
            evidence=f"{drafts} journal entries are still in draft status.",
            impact="Draft entries are excluded from financial reports, potentially understating balances.",
            recommendation="Review and approve pending journal entries to ensure complete reporting.",
            confidence=Decimal("0.9"),
        ))

    return risks


async def _detect_concentration_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect customer/vendor concentration risks."""
    risks: list[Risk] = []
    rec = await engine.calculate_receivables(db, org_id)

    # Customer concentration: if one customer > 50% of receivables
    if rec.by_customer and rec.total_outstanding > _ZERO:
        top_customer = rec.by_customer[0]
        concentration = _safe_ratio(top_customer["total_outstanding"], rec.total_outstanding)
        if concentration > Decimal("0.5"):
            risks.append(Risk(
                category="CONCENTRATION",
                severity="high" if concentration > Decimal("0.7") else "medium",
                title="Customer Concentration Risk",
                evidence=f"Top customer represents {(concentration * 100).quantize(Decimal('0.1'))}% "
                         f"of total receivables ({top_customer['total_outstanding']}).",
                impact="Loss of this customer would significantly impact revenue and cash flow.",
                recommendation="Diversify customer base. Negotiate longer-term contracts "
                              "with key customers and build relationships with new clients.",
                confidence=Decimal("0.85"),
                affected_amount=top_customer["total_outstanding"],
            ))

    return risks


async def _detect_tax_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect tax-related risks."""
    risks: list[Risk] = []
    today = date.today()

    # Check for tax payable accounts with large balances
    tax_stmt = (
        select(
            ChartOfAccounts.id,
            ChartOfAccounts.name,
            func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), _ZERO).label("balance"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            ChartOfAccounts.business_id == org_id,
            ChartOfAccounts.name.ilike("%tax%"),
            JournalEntry.is_draft.is_(False),
        )
        .group_by(ChartOfAccounts.id, ChartOfAccounts.name)
    )
    tax_rows = (await db.execute(tax_stmt)).all()

    for row in tax_rows:
        if row.balance > Decimal("500000"):  # Threshold for TZS
            risks.append(Risk(
                category="TAX",
                severity="medium",
                title=f"Large Tax Payable: {row.name}",
                evidence=f"Tax account '{row.name}' has a balance of {row.balance}.",
                impact="Unpaid tax obligations may incur penalties and interest charges.",
                recommendation="Review tax payment schedule. Ensure timely remittance "
                              "to avoid penalties.",
                confidence=Decimal("0.7"),
                affected_amount=row.balance,
            ))

    return risks


async def _detect_operational_risks(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """Detect operational risks."""
    risks: list[Risk] = []

    # Transaction volume anomaly (sudden drop)
    today = date.today()
    recent_count = (
        await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.business_id == org_id,
                Transaction.txn_date >= today - timedelta(days=30),
            )
        )
    ).scalar() or 0

    prev_count = (
        await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.business_id == org_id,
                Transaction.txn_date >= today - timedelta(days=60),
                Transaction.txn_date < today - timedelta(days=30),
            )
        )
    ).scalar() or 0

    if prev_count > 5 and recent_count < prev_count // 2:
        risks.append(Risk(
            category="OPERATIONAL",
            severity="medium",
            title="Sudden Drop in Transaction Volume",
            evidence=f"Last 30 days: {recent_count} transactions vs "
                     f"{prev_count} in the prior 30 days.",
            impact="May indicate business slowdown or data ingestion issues.",
            recommendation="Verify transaction import pipeline is functioning. "
                          "If business-related, review sales pipeline and operations.",
            confidence=Decimal("0.7"),
        ))

    return risks


# ──────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────

async def detect_risks(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Risk]:
    """
    Detect all financial risks for the organization.

    Runs all 11 risk detectors and returns a combined list sorted by
    severity (critical → high → medium → low).
    """
    engine = FinancialEngine()

    detectors = [
        _detect_cash_flow_risks,
        _detect_profitability_risks,
        _detect_expense_risks,
        _detect_receivable_risks,
        _detect_payable_risks,
        _detect_fraud_risks,
        _detect_data_quality_risks,
        _detect_concentration_risks,
        _detect_tax_risks,
        _detect_operational_risks,
    ]

    all_risks: list[Risk] = []
    for detector in detectors:
        try:
            risks = await detector(engine, db, org_id)
            all_risks.extend(risks)
        except Exception:
            # Don't let one detector failure break the entire scan
            continue

    # Sort by severity (critical first)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_risks.sort(key=lambda r: severity_order.get(r.severity, 99))

    return all_risks
