"""Validation for extracted and normalized document data.

Checks required fields, date validity, amount sanity, and
flags potential duplicates.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    """A single validation finding."""
    field: str
    message: str
    severity: str = "error"  # "error" | "warning"
    record_id: str | None = None


@dataclass
class ValidationResult:
    """Aggregated validation output."""
    is_valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    duplicate_groups: list[list[int]] = field(default_factory=list)
    record_count: int = 0
    valid_count: int = 0
    error_count: int = 0
    warning_count: int = 0

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        if issue.severity == "error":
            self.error_count += 1
        else:
            self.warning_count += 1

    def finalize(self) -> None:
        """Recompute summary flags."""
        self.record_count = self.record_count or 0
        self.error_count = sum(1 for i in self.issues if i.severity == "error")
        self.warning_count = sum(1 for i in self.issues if i.severity == "warning")
        self.is_valid = self.error_count == 0


# ---------------------------------------------------------------------------
# Required-field spec per record type
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: dict[str, list[str]] = {
    "transaction": ["txn_date", "amount", "currency"],
    "invoice": ["invoice_number", "total", "currency"],
    "expense": ["expense_date", "amount", "currency"],
    "product": ["name", "unit_price"],
    "bank_transaction": ["value_date"],
}

# Date-like field names
_DATE_FIELDS = {"txn_date", "expense_date", "issue_date", "due_date", "value_date", "date"}

# Amount-like field names
_AMOUNT_FIELDS = {
    "amount", "total", "subtotal", "tax", "debit", "credit",
    "balance", "unit_price", "fee",
}


# ---------------------------------------------------------------------------
# DataValidator
# ---------------------------------------------------------------------------

class DataValidator:
    """Validate extracted records against business rules."""

    def validate(
        self,
        records: list[dict[str, Any]],
        record_type: str = "transaction",
    ) -> ValidationResult:
        """Run all validation checks.

        Parameters
        ----------
        records : list[dict]
            Normalized records (strings, ISO dates, Decimal strings).
        record_type : str
            One of ``transaction``, ``invoice``, ``expense``,
            ``product``, ``bank_transaction``.

        Returns
        -------
        ValidationResult
        """
        result = ValidationResult(record_count=len(records))

        for idx, record in enumerate(records):
            rid = str(record.get("id", idx))

            # 1. Required fields
            self._check_required(record, record_type, idx, rid, result)

            # 2. Date validity
            self._check_dates(record, idx, rid, result)

            # 3. Amount validity
            self._check_amounts(record, idx, rid, result)

        # 4. Duplicate detection
        self._check_duplicates(records, record_type, result)

        result.valid_count = result.record_count - result.error_count
        result.finalize()
        return result

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_required(
        self,
        record: dict[str, Any],
        record_type: str,
        idx: int,
        rid: str,
        result: ValidationResult,
    ) -> None:
        required = REQUIRED_FIELDS.get(record_type, [])
        for field_name in required:
            value = record.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Required field '{field_name}' is missing or empty.",
                    severity="error",
                    record_id=rid,
                ))

    def _check_dates(
        self,
        record: dict[str, Any],
        idx: int,
        rid: str,
        result: ValidationResult,
    ) -> None:
        for field_name in _DATE_FIELDS:
            value = record.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            if isinstance(value, str):
                try:
                    parsed = date.fromisoformat(value)
                except (ValueError, TypeError):
                    result.add_issue(ValidationIssue(
                        field=field_name,
                        message=f"Invalid date format for '{field_name}': {value!r}",
                        severity="error",
                        record_id=rid,
                    ))
                    continue
            elif isinstance(value, (date, datetime)):
                parsed = value if isinstance(value, date) else value.date()
            else:
                continue

            # Future date sanity check
            if parsed > date.today():
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Date '{field_name}' is in the future: {parsed}",
                    severity="warning",
                    record_id=rid,
                ))

    def _check_amounts(
        self,
        record: dict[str, Any],
        idx: int,
        rid: str,
        result: ValidationResult,
    ) -> None:
        for field_name in _AMOUNT_FIELDS:
            value = record.get(field_name)
            if value is None:
                continue
            try:
                amount = Decimal(str(value))
            except (InvalidOperation, ValueError):
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Invalid amount for '{field_name}': {value!r}",
                    severity="error",
                    record_id=rid,
                ))
                continue

            # Negative amount warning (allowed but flagged)
            if amount < 0 and field_name not in ("debit", "credit", "balance"):
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Negative amount in '{field_name}': {amount}",
                    severity="warning",
                    record_id=rid,
                ))

            # Absurdly large amount
            if abs(amount) > Decimal("999999999999"):
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Suspiciously large amount in '{field_name}': {amount}",
                    severity="warning",
                    record_id=rid,
                ))

    def _check_duplicates(
        self,
        records: list[dict[str, Any]],
        record_type: str,
        result: ValidationResult,
    ) -> None:
        """Group records that look like duplicates.

        Duplicate heuristic: same date + same amount + same description
        (or same reference number).
        """
        seen: dict[str, list[int]] = {}
        for idx, record in enumerate(records):
            date_val = str(record.get("txn_date", record.get("value_date", record.get("expense_date", ""))))
            amount_val = str(record.get("amount", record.get("total", record.get("debit", ""))))
            desc_val = str(record.get("description", record.get("reference", "")))[:80]
            key = f"{date_val}|{amount_val}|{desc_val.lower().strip()}"
            seen.setdefault(key, []).append(idx)

        for group_indices in seen.values():
            if len(group_indices) > 1:
                result.duplicate_groups.append(group_indices)
                for idx in group_indices:
                    result.add_issue(ValidationIssue(
                        field="_duplicate",
                        message=f"Possible duplicate of record(s) {[i for i in group_indices if i != idx]}",
                        severity="warning",
                        record_id=str(idx),
                    ))
