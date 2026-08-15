"""Data normalization for extracted financial records.

Standardizes dates, amounts, currencies, and account names
so downstream validation and entity resolution work on
uniform data.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


# ---------------------------------------------------------------------------
# Currency mapping — common abbreviations → ISO 4217
# ---------------------------------------------------------------------------

_CURRENCY_ALIASES: dict[str, str] = {
    "tsh": "TZS", "tanzania shilling": "TZS", "tzsh": "TZS",
    "ksh": "KES", "kenya shilling": "KES",
    "ugx": "UGX", "uganda shilling": "UGX",
    "usd": "USD", "$": "USD", "us dollar": "USD", "dollars": "USD",
    "eur": "EUR", "€": "EUR", "euro": "EUR", "euros": "EUR",
    "gbp": "GBP", "£": "GBP", "pound": "GBP", "pounds": "GBP",
    "ngn": "NGN", "naira": "NGN", "₦": "NGN",
    "zar": "ZAR", "rand": "ZAR",
    "kes": "KES",
    "rwf": "RWF", "franc": "RWF",
    "bif": "BIF",
}

# Amount cleaning: remove currency symbols, thousand separators
# Covers TZS, USD, EUR, GBP, KES, NGN, UGX prefixes/symbols
_AMOUNT_NOISE = re.compile(r"[A-Z$€£₦\s]")


# ---------------------------------------------------------------------------
# DataNormalizer
# ---------------------------------------------------------------------------

class DataNormalizer:
    """Normalize extracted records into canonical forms."""

    DEFAULT_CURRENCY: str = "TZS"
    DEFAULT_DATE_FMT: str = "%Y-%m-%d"

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------

    def normalize_dates(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert all ``*_date`` / ``date`` fields to ISO strings.

        Parameters
        ----------
        data : list[dict]
            Records with date fields that may be strings, ``date``,
            ``datetime``, or ``None``.

        Returns
        -------
        list[dict]
            Same records with date fields normalized to ``YYYY-MM-DD`` strings.
        """
        normalized: list[dict[str, Any]] = []
        for record in data:
            out: dict[str, Any] = {}
            for key, value in record.items():
                if "date" in key.lower():
                    out[key] = self._normalize_single_date(value)
                else:
                    out[key] = value
            normalized.append(out)
        return normalized

    def _normalize_single_date(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, str):
            parsed = self._parse_date_str(value.strip())
            return parsed.isoformat() if parsed else value
        return str(value)

    @staticmethod
    def _parse_date_str(raw: str) -> date | None:
        for fmt in (
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
            "%Y/%m/%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y",
            "%B %d, %Y",
        ):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------------
    # Amounts
    # ------------------------------------------------------------------

    def normalize_amounts(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert all ``*_amount`` / ``amount`` / ``total`` etc. fields
        to ``Decimal`` strings with two decimal places.
        """
        amount_keywords = {"amount", "total", "subtotal", "tax", "debit", "credit", "balance", "price", "fee"}
        normalized: list[dict[str, Any]] = []
        for record in data:
            out: dict[str, Any] = {}
            for key, value in record.items():
                if any(kw in key.lower() for kw in amount_keywords):
                    out[key] = self._normalize_single_amount(value)
                else:
                    out[key] = value
            normalized.append(out)
        return normalized

    def _normalize_single_amount(self, value: Any) -> str:
        if value is None:
            return "0.00"
        if isinstance(value, Decimal):
            return f"{value:.2f}"
        if isinstance(value, (int, float)):
            return f"{Decimal(str(value)):.2f}"
        if isinstance(value, str):
            cleaned = _AMOUNT_NOISE.sub("", value).strip()
            # Remove thousand separators (commas)
            cleaned = cleaned.replace(",", "")
            # Handle parentheses for negative: (1234.56) → -1234.56
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = "-" + cleaned[1:-1]
            try:
                return f"{Decimal(cleaned):.2f}"
            except (InvalidOperation, ValueError):
                return "0.00"
        return "0.00"

    # ------------------------------------------------------------------
    # Currencies
    # ------------------------------------------------------------------

    def normalize_currencies(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Map currency fields to ISO 4217 uppercase codes."""
        currency_keywords = {"currency", "curr", "ccy"}
        normalized: list[dict[str, Any]] = []
        for record in data:
            out: dict[str, Any] = {}
            for key, value in record.items():
                if any(kw in key.lower() for kw in currency_keywords):
                    out[key] = self._normalize_single_currency(value)
                else:
                    out[key] = value
            normalized.append(out)
        return normalized

    def _normalize_single_currency(self, value: Any) -> str:
        if value is None:
            return self.DEFAULT_CURRENCY
        s = str(value).strip().lower()
        return _CURRENCY_ALIASES.get(s, s.upper())

    # ------------------------------------------------------------------
    # Account names
    # ------------------------------------------------------------------

    def normalize_account_names(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Title-case and strip account / counterparty name fields."""
        name_keywords = {"account", "counterparty", "vendor", "customer", "name", "payee", "beneficiary"}
        normalized: list[dict[str, Any]] = []
        for record in data:
            out: dict[str, Any] = {}
            for key, value in record.items():
                if any(kw in key.lower() for kw in name_keywords) and isinstance(value, str):
                    out[key] = self._normalize_name(value)
                else:
                    out[key] = value
            normalized.append(out)
        return normalized

    @staticmethod
    def _normalize_name(raw: str) -> str:
        """Collapse whitespace, strip, title-case."""
        cleaned = re.sub(r"\s+", " ", raw).strip()
        return cleaned.title()

    # ------------------------------------------------------------------
    # Convenience: run all normalizations in sequence
    # ------------------------------------------------------------------

    def normalize_all(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply date → amount → currency → name normalization."""
        result = self.normalize_dates(data)
        result = self.normalize_amounts(result)
        result = self.normalize_currencies(result)
        result = self.normalize_account_names(result)
        return result
