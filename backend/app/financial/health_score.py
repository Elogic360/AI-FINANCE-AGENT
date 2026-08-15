"""
FinPilot AI — Financial Health Score
─────────────────────────────────────
Deterministic composite health score with weighted components:

    profitability  25 %
    liquidity      25 %
    cash_flow      20 %
    receivables    10 %
    expense_control 10 %
    growth         10 %

Each component is scored 0–100.  The overall score is the weighted average.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import ChartOfAccounts, JournalEntry, JournalLine
from app.models.contacts import Invoice

from app.financial.metrics import HealthScore, HealthScoreComponent
from app.financial.engine import FinancialEngine, _safe_ratio, _pct, _ZERO, _d


# ──────────────────────────────────────────────────────────────────────
# Component weight configuration
# ──────────────────────────────────────────────────────────────────────

_COMPONENT_WEIGHTS: list[tuple[str, Decimal, str]] = [
    ("profitability", Decimal("0.25"), "Net margin, gross margin, and operating margin"),
    ("liquidity", Decimal("0.25"), "Current ratio, quick ratio, and cash position"),
    ("cash_flow", Decimal("0.20"), "Operating cash flow relative to expenses"),
    ("receivables", Decimal("0.10"), "Collection speed and overdue aging"),
    ("expense_control", Decimal("0.10"), "Expense growth relative to revenue growth"),
    ("growth", Decimal("0.10"), "Revenue growth trajectory"),
]


def _clamp_score(score: Decimal) -> int:
    """Clamp score to 0–100 integer."""
    return max(0, min(100, int(score.quantize(Decimal("1"), rounding=ROUND_HALF_UP))))


def _grade(score: int) -> str:
    """Map numeric score to letter grade."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


# ──────────────────────────────────────────────────────────────────────
# Component scorers (each returns 0–100 Decimal)
# ──────────────────────────────────────────────────────────────────────

async def _score_profitability(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> tuple[int, str]:
    """
    Score profitability based on net margin.

    90+  → net margin ≥ 20%
    70+  → net margin ≥ 10%
    50+  → net margin ≥ 0%
    30+  → net margin ≥ -10%
    else → 0–30
    """
    today = date.today()
    period = (today - timedelta(days=365), today)
    pl = await engine.calculate_profit_loss(db, org_id, period)

    net_margin = _pct(pl.net_income, pl.revenue) if pl.revenue else _ZERO
    gross_margin = _pct(pl.gross_profit, pl.revenue) if pl.revenue else _ZERO

    # Blend: 60% net margin, 40% gross margin
    if pl.revenue == _ZERO:
        score = Decimal("50")  # No data = neutral
        desc = "No revenue data available"
    else:
        # Map margin percentages to 0-100
        # net margin: -50% → 0, 0% → 50, 30% → 100
        net_score = max(_ZERO, min(Decimal("100"), (net_margin + Decimal("50")) * Decimal("2")))
        # gross margin: 0% → 30, 50% → 100
        gross_score = max(_ZERO, min(Decimal("100"), gross_margin * Decimal("2") + Decimal("30")))
        score = net_score * Decimal("0.6") + gross_score * Decimal("0.4")
        desc = f"Net margin: {net_margin}%, Gross margin: {gross_margin}%"

    return _clamp_score(score), desc


async def _score_liquidity(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> tuple[int, str]:
    """
    Score liquidity based on current ratio and quick ratio.

    current ratio ≥ 2.0 → 90+
    current ratio ≥ 1.5 → 70+
    current ratio ≥ 1.0 → 50+
    current ratio < 1.0  → 20–40
    """
    bs = await engine.calculate_balance_sheet(db, org_id, date.today())

    if bs.current_liabilities == _ZERO:
        # No liabilities = healthy, but also could mean no data
        if bs.current_assets > _ZERO:
            return 90, "Strong cash position with no current liabilities"
        return 50, "Insufficient data for liquidity assessment"

    current_ratio = _safe_ratio(bs.current_assets, bs.current_liabilities)

    # Map ratio to score: 0 → 0, 1.0 → 50, 2.0 → 80, 3.0+ → 100
    score = min(Decimal("100"), current_ratio * Decimal("40"))

    desc = f"Current ratio: {current_ratio}, Current assets: {bs.current_assets}, Current liabilities: {bs.current_liabilities}"
    return _clamp_score(score), desc


async def _score_cash_flow(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> tuple[int, str]:
    """
    Score cash flow based on operating cash flow relative to expenses.

    Positive and growing → 80+
    Positive but flat → 60–79
    Slightly negative → 30–59
    Strongly negative → 0–29
    """
    today = date.today()
    current_period = (today - timedelta(days=90), today)
    prev_period = (today - timedelta(days=180), today - timedelta(days=91))

    cf = await engine.calculate_cash_flow(db, org_id, current_period)
    prev_cf = await engine.calculate_cash_flow(db, org_id, prev_period)

    operating = cf.operating_activities

    if operating > _ZERO:
        score = Decimal("70")
        if cf.ending_cash > cf.beginning_cash:
            score += Decimal("15")  # Growing cash
        if prev_cf.operating_activities > _ZERO and operating > prev_cf.operating_activities:
            score += Decimal("10")  # Improving trend
        desc = f"Positive operating cash flow: {operating}"
    elif operating == _ZERO:
        score = Decimal("50")
        desc = "No operating cash flow data"
    else:
        # Negative cash flow
        score = Decimal("30")
        if operating > prev_cf.operating_activities:
            score += Decimal("15")  # Improving (less negative)
        desc = f"Negative operating cash flow: {operating}"

    return _clamp_score(min(Decimal("100"), score)), desc


async def _score_receivables(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> tuple[int, str]:
    """
    Score receivables health based on DSO and overdue ratio.

    DSO ≤ 30 and low overdue → 90+
    DSO ≤ 45 → 70+
    DSO ≤ 60 → 50+
    DSO > 60 → 20–49
    """
    rec = await engine.calculate_receivables(db, org_id)

    if rec.total_outstanding == _ZERO:
        return 70, "No outstanding receivables"

    overdue_ratio = _safe_ratio(
        rec.overdue_30 + rec.overdue_60 + rec.overdue_90_plus,
        rec.total_outstanding,
    )

    dso = rec.average_days_outstanding

    # DSO score: 0 days → 100, 30 → 80, 60 → 50, 90+ → 20
    dso_score = max(_ZERO, Decimal("100") - dso * Decimal("1"))
    # Overdue penalty
    overdue_penalty = overdue_ratio * Decimal("100") * Decimal("0.5")

    score = max(_ZERO, dso_score - overdue_penalty)

    desc = f"DSO: {dso} days, Overdue ratio: {(overdue_ratio * 100).quantize(Decimal('0.1'))}%"
    return _clamp_score(score), desc


async def _score_expense_control(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> tuple[int, str]:
    """
    Score expense control: expenses growing slower than (or shrinking relative to) revenue.

    Expense/revenue ratio improving → 80+
    Stable ratio → 60–79
    Worsening ratio → 30–59
    Expenses exceed revenue → 0–29
    """
    today = date.today()
    current = (today - timedelta(days=180), today)
    previous = (today - timedelta(days=365), today - timedelta(days=181))

    rev = await engine.calculate_revenue(db, org_id, current)
    exp = await engine.calculate_expenses(db, org_id, current)
    prev_rev = await engine.calculate_revenue(db, org_id, previous)
    prev_exp = await engine.calculate_expenses(db, org_id, previous)

    current_ratio = _safe_ratio(exp.total_expenses, rev.total_revenue) if rev.total_revenue else _ZERO
    prev_ratio = _safe_ratio(prev_exp.total_expenses, prev_rev.total_revenue) if prev_rev.total_revenue else _ZERO

    if rev.total_revenue == _ZERO:
        return 50, "Insufficient data for expense control assessment"

    if current_ratio < Decimal("0.5"):
        score = Decimal("90")
    elif current_ratio < Decimal("0.8"):
        score = Decimal("75")
    elif current_ratio < Decimal("1.0"):
        score = Decimal("60")
    else:
        score = Decimal("30")

    # Bonus for improving trend
    if prev_ratio > _ZERO and current_ratio < prev_ratio:
        score = min(Decimal("100"), score + Decimal("10"))

    desc = f"Expense/Revenue ratio: {(current_ratio * 100).quantize(Decimal('0.1'))}%"
    return _clamp_score(score), desc


async def _score_growth(
    engine: FinancialEngine,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> tuple[int, str]:
    """
    Score growth based on recent vs prior period revenue.

    Growth > 20% → 90+
    Growth > 10% → 70+
    Growth > 0%  → 55+
    Flat         → 45
    Declining    → 20–40
    """
    today = date.today()
    current = (today - timedelta(days=90), today)
    previous = (today - timedelta(days=180), today - timedelta(days=91))

    rev = await engine.calculate_revenue(db, org_id, current)
    prev_rev = await engine.calculate_revenue(db, org_id, previous)

    if prev_rev.total_revenue == _ZERO:
        if rev.total_revenue > _ZERO:
            return 70, "New revenue detected (no prior period for comparison)"
        return 50, "No revenue data for growth assessment"

    growth_pct = _pct(rev.total_revenue - prev_rev.total_revenue, prev_rev.total_revenue)

    # Map growth % to score: -50% → 10, 0% → 50, 30% → 100
    score = Decimal("50") + growth_pct * Decimal("2")
    score = max(_ZERO, min(Decimal("100"), score))

    desc = f"Revenue growth: {growth_pct}% (90-day periods)"
    return _clamp_score(score), desc


# ──────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────

async def calculate_health_score(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> HealthScore:
    """
    Calculate the composite financial health score.

    Components and weights:
        profitability    25%
        liquidity        25%
        cash_flow        20%
        receivables      10%
        expense_control  10%
        growth           10%

    Each component is scored 0–100.
    Returns overall score (weighted average) + component breakdown.
    """
    engine = FinancialEngine()

    scorers = [
        ("profitability", _score_profitability),
        ("liquidity", _score_liquidity),
        ("cash_flow", _score_cash_flow),
        ("receivables", _score_receivables),
        ("expense_control", _score_expense_control),
        ("growth", _score_growth),
    ]

    components: list[HealthScoreComponent] = []
    weighted_sum = _ZERO
    total_weight = _ZERO

    for (name, weight, _default_desc), (score_name, scorer_fn) in zip(_COMPONENT_WEIGHTS, scorers):
        score, description = await scorer_fn(engine, db, org_id)
        weighted_sum += Decimal(score) * weight
        total_weight += weight
        components.append(HealthScoreComponent(
            name=name,
            score=score,
            weight=weight,
            description=description,
        ))

    overall = _clamp_score(weighted_sum) if total_weight else 0

    # Build recommendation
    weakest = min(components, key=lambda c: c.score)
    strongest = max(components, key=lambda c: c.score)

    recommendations: list[str] = []
    if weakest.score < 50:
        recommendations.append(
            f"Priority: Improve {weakest.name} ({weakest.score}/100). "
            f"{weakest.description}"
        )
    if overall < 60:
        recommendations.append(
            "Overall financial health needs attention. Focus on cash flow management "
            "and expense control."
        )
    elif overall < 80:
        recommendations.append(
            "Financial health is fair. Consider strengthening receivables collection "
            "and building cash reserves."
        )
    else:
        recommendations.append(
            "Financial health is strong. Maintain current practices and consider "
            "growth investments."
        )

    return HealthScore(
        org_id=org_id,
        overall_score=overall,
        components=components,
        recommendation=" | ".join(recommendations),
        grade=_grade(overall),
    )
