"""Entity resolution — match extracted records to existing entities.

Fuzzy-matches customer/vendor/transaction names against the
organization's existing database to avoid creating duplicates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any


# ---------------------------------------------------------------------------
# Match result data-classes
# ---------------------------------------------------------------------------

@dataclass
class EntityMatch:
    """A single match candidate."""
    existing_id: str
    existing_name: str
    score: float  # 0.0 – 1.0
    match_method: str = "fuzzy"  # "exact" | "fuzzy" | "partial"


@dataclass
class ResolutionResult:
    """Result of resolving one extracted entity."""
    extracted_name: str
    matched: bool = False
    best_match: EntityMatch | None = None
    candidates: list[EntityMatch] = field(default_factory=list)
    action: str = "create_new"  # "link_existing" | "create_new" | "merge"


# ---------------------------------------------------------------------------
# Matching utilities
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _fuzzy_score(a: str, b: str) -> float:
    """Return a 0-1 similarity score between two names."""
    na, nb = _normalize_name(a), _normalize_name(b)
    if na == nb:
        return 1.0
    return round(SequenceMatcher(None, na, nb).ratio(), 4)


def _partial_match(extracted: str, existing: str) -> bool:
    """Check if one name is a substring of the other."""
    ne = _normalize_name(extracted)
    nx = _normalize_name(existing)
    return ne in nx or nx in ne


# Thresholds
EXACT_THRESHOLD = 1.0
FUZZY_THRESHOLD = 0.80
PARTIAL_THRESHOLD = 0.60


# ---------------------------------------------------------------------------
# EntityResolver
# ---------------------------------------------------------------------------

class EntityResolver:
    """Match extracted entities against existing records."""

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def resolve_customers(
        self,
        extracted: list[dict[str, Any]],
        existing: list[dict[str, Any]],
    ) -> list[ResolutionResult]:
        """Match extracted customer names to existing customers.

        Parameters
        ----------
        extracted : list[dict]
            Records with at least a ``"customer_name"`` or ``"name"`` field.
        existing : list[dict]
            Existing customers with ``"id"`` and ``"name"``.

        Returns
        -------
        list[ResolutionResult]
        """
        return self._resolve_entities(
            extracted=extracted,
            existing=existing,
            name_field="customer_name",
        )

    # ------------------------------------------------------------------
    # Vendors
    # ------------------------------------------------------------------

    def resolve_vendors(
        self,
        extracted: list[dict[str, Any]],
        existing: list[dict[str, Any]],
    ) -> list[ResolutionResult]:
        """Match extracted vendor/supplier names to existing vendors."""
        return self._resolve_entities(
            extracted=extracted,
            existing=existing,
            name_field="vendor_name",
        )

    # ------------------------------------------------------------------
    # Transactions (de-duplication against existing)
    # ------------------------------------------------------------------

    def resolve_transactions(
        self,
        extracted: list[dict[str, Any]],
        existing: list[dict[str, Any]],
    ) -> list[ResolutionResult]:
        """Match extracted transactions to existing ones.

        Uses a composite key: date + amount + counterparty/description.
        """
        results: list[ResolutionResult] = []

        for ext_rec in extracted:
            ext_key = self._transaction_key(ext_rec)
            resolution = ResolutionResult(
                extracted_name=str(ext_rec.get("description", "")),
            )

            best: EntityMatch | None = None
            candidates: list[EntityMatch] = []

            for ex_rec in existing:
                ex_key = self._transaction_key(ex_rec)
                score = _fuzzy_score(ext_key, ex_key)
                if score >= EXACT_THRESHOLD:
                    candidates.append(EntityMatch(
                        existing_id=str(ex_rec.get("id", "")),
                        existing_name=str(ex_rec.get("description", "")),
                        score=score,
                        match_method="exact",
                    ))
                    best = candidates[-1]
                elif score >= FUZZY_THRESHOLD:
                    candidates.append(EntityMatch(
                        existing_id=str(ex_rec.get("id", "")),
                        existing_name=str(ex_rec.get("description", "")),
                        score=score,
                        match_method="fuzzy",
                    ))
                    if best is None or score > best.score:
                        best = candidates[-1]

            resolution.candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
            if best:
                resolution.matched = True
                resolution.best_match = best
                resolution.action = "link_existing"
            else:
                resolution.action = "create_new"

            results.append(resolution)

        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_entities(
        self,
        extracted: list[dict[str, Any]],
        existing: list[dict[str, Any]],
        name_field: str,
    ) -> list[ResolutionResult]:
        """Generic entity resolution by name matching."""
        results: list[ResolutionResult] = []

        for ext_rec in extracted:
            ext_name = str(ext_rec.get(name_field, ext_rec.get("name", "")))
            resolution = ResolutionResult(extracted_name=ext_name)

            best: EntityMatch | None = None
            candidates: list[EntityMatch] = []

            for ex_rec in existing:
                ex_name = str(ex_rec.get("name", ""))
                ex_id = str(ex_rec.get("id", ""))

                # Exact
                if _normalize_name(ext_name) == _normalize_name(ex_name):
                    match = EntityMatch(
                        existing_id=ex_id,
                        existing_name=ex_name,
                        score=1.0,
                        match_method="exact",
                    )
                    candidates.append(match)
                    best = match
                    break

                # Fuzzy
                score = _fuzzy_score(ext_name, ex_name)
                if score >= FUZZY_THRESHOLD:
                    match = EntityMatch(
                        existing_id=ex_id,
                        existing_name=ex_name,
                        score=score,
                        match_method="fuzzy",
                    )
                    candidates.append(match)
                    if best is None or score > best.score:
                        best = match
                elif _partial_match(ext_name, ex_name):
                    match = EntityMatch(
                        existing_id=ex_id,
                        existing_name=ex_name,
                        score=PARTIAL_THRESHOLD,
                        match_method="partial",
                    )
                    candidates.append(match)
                    if best is None:
                        best = match

            resolution.candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
            if best:
                resolution.matched = True
                resolution.best_match = best
                resolution.action = "link_existing"
            else:
                resolution.action = "create_new"

            results.append(resolution)

        return results

    @staticmethod
    def _transaction_key(rec: dict[str, Any]) -> str:
        """Build a composite key for transaction dedup."""
        date_str = str(rec.get("txn_date", rec.get("value_date", "")))
        amount_str = str(rec.get("amount", rec.get("total", rec.get("debit", ""))))
        desc_str = str(rec.get("description", rec.get("counterparty", "")))[:60]
        return f"{date_str}|{amount_str}|{_normalize_name(desc_str)}"
