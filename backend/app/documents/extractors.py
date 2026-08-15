"""Domain-specific data extractors for financial documents.

Each extractor receives the raw *content* (text or dict) produced by
:class:`DocumentProcessor` and returns structured records ready for
normalization and validation.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


# ---------------------------------------------------------------------------
# Extracted-record data-classes
# ---------------------------------------------------------------------------

@dataclass
class ExtractedTransaction:
    """A single financial transaction (generic)."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    txn_date: date | None = None
    description: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "TZS"
    counterparty: str = ""
    reference: str = ""
    category_hint: str = ""
    confidence: float = 0.0


@dataclass
class InvoiceLineItem:
    description: str = ""
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")


@dataclass
class ExtractedInvoice:
    """An invoice extracted from a document."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    invoice_number: str = ""
    issue_date: date | None = None
    due_date: date | None = None
    vendor_name: str = ""
    customer_name: str = ""
    line_items: list[InvoiceLineItem] = field(default_factory=list)
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    currency: str = "TZS"
    confidence: float = 0.0


@dataclass
class ExtractedExpense:
    """A single expense line from an expense report or receipt."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    expense_date: date | None = None
    category: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "TZS"
    vendor: str = ""
    receipt_ref: str = ""
    confidence: float = 0.0


@dataclass
class ExtractedProduct:
    """A product/service line item."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    sku: str = ""
    name: str = ""
    description: str = ""
    unit_price: Decimal = Decimal("0")
    currency: str = "TZS"
    category: str = ""


@dataclass
class ExtractedBankTransaction:
    """A single row from a bank statement."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    value_date: date | None = None
    description: str = ""
    reference: str = ""
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")
    currency: str = "TZS"
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",   # 2024-01-15 or 2024/01/15
    r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",   # 15-01-2024 or 15/01/2024
    r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",  # 15 Jan 2024
]

_AMOUNT_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def _parse_date(raw: str) -> date | None:
    """Try to parse a date string into a :class:`date`."""
    raw = raw.strip()
    for fmt in (
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y",
    ):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(raw: str) -> Decimal:
    """Parse a numeric string, stripping commas."""
    cleaned = raw.replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _find_date(text: str) -> date | None:
    for pat in _DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            parsed = _parse_date(m.group(1))
            if parsed:
                return parsed
    return None


def _find_amount(text: str) -> Decimal:
    m = _AMOUNT_RE.search(text)
    return _parse_decimal(m.group()) if m else Decimal("0")


# ---------------------------------------------------------------------------
# Public extractor functions
# ---------------------------------------------------------------------------

def extract_transactions(content: dict[str, Any]) -> list[ExtractedTransaction]:
    """Extract generic transactions from processed content.

    Parameters
    ----------
    content : dict
        Must contain ``"text"`` (str) and optionally ``"tables"``.

    Returns
    -------
    list[ExtractedTransaction]
    """
    text: str = content.get("text", "")
    tables: list[dict] = content.get("tables", [])
    results: list[ExtractedTransaction] = []

    # Strategy 1: parse from tables
    for table in tables:
        headers = [h.lower() for h in table.get("headers", [])]
        for row in table.get("rows", []):
            if len(row) < 2:
                continue
            record: dict[str, Any] = dict(zip(headers, row))
            results.append(
                ExtractedTransaction(
                    txn_date=_find_date(str(record.get("date", ""))),
                    description=str(record.get("description", row[0])),
                    amount=_find_amount(str(record.get("amount", row[-1]))),
                    currency=str(record.get("currency", "TZS")),
                    counterparty=str(record.get("counterparty", "")),
                    reference=str(record.get("reference", "")),
                    confidence=0.8,
                )
            )

    # Strategy 2: line-by-line heuristic fallback
    if not results and text:
        for line in text.splitlines():
            amt = _find_amount(line)
            if amt != 0:
                results.append(
                    ExtractedTransaction(
                        txn_date=_find_date(line),
                        description=line.strip(),
                        amount=amt,
                        confidence=0.5,
                    )
                )

    return results


def extract_invoices(content: dict[str, Any]) -> list[ExtractedInvoice]:
    """Extract invoice records from processed content."""
    text: str = content.get("text", "")
    tables: list[dict] = content.get("tables", [])
    results: list[ExtractedInvoice] = []

    # Naive: one invoice per document for now
    inv = ExtractedInvoice(confidence=0.6)

    # Invoice number
    m = re.search(r"(?:invoice\s*(?:#|no\.?|number)?)\s*[:\-]?\s*(\S+)", text, re.I)
    if m:
        inv.invoice_number = m.group(1)

    inv.issue_date = _find_date(text)
    # Due date — second date occurrence
    dates_found = []
    for pat in _DATE_PATTERNS:
        for dm in re.finditer(pat, text):
            d = _parse_date(dm.group(1))
            if d:
                dates_found.append(d)
    if len(dates_found) >= 2:
        inv.due_date = dates_found[1]

    # Vendor / customer
    vendor_m = re.search(r"(?:from|vendor|supplier)\s*[:\-]?\s*(.+)", text, re.I)
    if vendor_m:
        inv.vendor_name = vendor_m.group(1).strip()
    cust_m = re.search(r"(?:bill\s*to|customer|client)\s*[:\-]?\s*(.+)", text, re.I)
    if cust_m:
        inv.customer_name = cust_m.group(1).strip()

    # Totals
    total_m = re.search(r"(?:total|amount\s*due)\s*[:\-]?\s*([+-]?\d[\d,]*\.?\d*)", text, re.I)
    if total_m:
        inv.total = _parse_decimal(total_m.group(1))
    subtotal_m = re.search(r"subtotal\s*[:\-]?\s*([+-]?\d[\d,]*\.?\d*)", text, re.I)
    if subtotal_m:
        inv.subtotal = _parse_decimal(subtotal_m.group(1))
    tax_m = re.search(r"(?:tax|vat)\s*[:\-]?\s*([+-]?\d[\d,]*\.?\d*)", text, re.I)
    if tax_m:
        inv.tax = _parse_decimal(tax_m.group(1))

    # Line items from tables
    for table in tables:
        headers = [h.lower() for h in table.get("headers", [])]
        for row in table.get("rows", []):
            record = dict(zip(headers, row))
            inv.line_items.append(
                InvoiceLineItem(
                    description=str(record.get("description", row[0] if row else "")),
                    quantity=_parse_decimal(str(record.get("qty", record.get("quantity", "1")))),
                    unit_price=_parse_decimal(str(record.get("unit_price", record.get("price", "0")))),
                    amount=_parse_decimal(str(record.get("amount", record.get("total", "0")))),
                )
            )

    results.append(inv)
    return results


def extract_expenses(content: dict[str, Any]) -> list[ExtractedExpense]:
    """Extract expense lines from processed content."""
    text: str = content.get("text", "")
    tables: list[dict] = content.get("tables", [])
    results: list[ExtractedExpense] = []

    for table in tables:
        headers = [h.lower() for h in table.get("headers", [])]
        for row in table.get("rows", []):
            if len(row) < 2:
                continue
            record = dict(zip(headers, row))
            results.append(
                ExtractedExpense(
                    expense_date=_find_date(str(record.get("date", ""))),
                    category=str(record.get("category", "")),
                    description=str(record.get("description", row[0])),
                    amount=_find_amount(str(record.get("amount", row[-1]))),
                    currency=str(record.get("currency", "TZS")),
                    vendor=str(record.get("vendor", "")),
                    receipt_ref=str(record.get("receipt_ref", record.get("ref", ""))),
                    confidence=0.75,
                )
            )

    # Fallback: keyword-based extraction from text
    if not results:
        for line in text.splitlines():
            low = line.lower()
            if any(kw in low for kw in ("expense", "reimbursement", "mileage")):
                results.append(
                    ExtractedExpense(
                        description=line.strip(),
                        amount=_find_amount(line),
                        confidence=0.4,
                    )
                )

    return results


def extract_products(content: dict[str, Any]) -> list[ExtractedProduct]:
    """Extract product/service line items."""
    tables: list[dict] = content.get("tables", [])
    results: list[ExtractedProduct] = []

    for table in tables:
        headers = [h.lower() for h in table.get("headers", [])]
        for row in table.get("rows", []):
            if len(row) < 2:
                continue
            record = dict(zip(headers, row))
            results.append(
                ExtractedProduct(
                    sku=str(record.get("sku", "")),
                    name=str(record.get("name", record.get("product", row[0]))),
                    description=str(record.get("description", "")),
                    unit_price=_parse_decimal(str(record.get("unit_price", record.get("price", "0")))),
                    currency=str(record.get("currency", "TZS")),
                    category=str(record.get("category", "")),
                )
            )

    return results


def extract_bank_transactions(content: dict[str, Any]) -> list[ExtractedBankTransaction]:
    """Extract rows from a bank statement."""
    text: str = content.get("text", "")
    tables: list[dict] = content.get("tables", [])
    results: list[ExtractedBankTransaction] = []

    for table in tables:
        headers = [h.lower() for h in table.get("headers", [])]
        for row in table.get("rows", []):
            if len(row) < 3:
                continue
            record = dict(zip(headers, row))
            results.append(
                ExtractedBankTransaction(
                    value_date=_find_date(str(record.get("date", record.get("value_date", "")))),
                    description=str(record.get("description", record.get("narrative", row[1] if len(row) > 1 else ""))),
                    reference=str(record.get("reference", record.get("ref", ""))),
                    debit=_parse_decimal(str(record.get("debit", record.get("withdrawal", "0")))),
                    credit=_parse_decimal(str(record.get("credit", record.get("deposit", "0")))),
                    balance=_parse_decimal(str(record.get("balance", "0"))),
                    currency=str(record.get("currency", "TZS")),
                    confidence=0.85,
                )
            )

    # Text-based fallback for single-column formats
    if not results:
        for line in text.splitlines():
            if _find_amount(line) != 0:
                results.append(
                    ExtractedBankTransaction(
                        value_date=_find_date(line),
                        description=line.strip(),
                        debit=_find_amount(line) if "dr" in line.lower() else Decimal("0"),
                        credit=_find_amount(line) if "cr" in line.lower() else Decimal("0"),
                        confidence=0.4,
                    )
                )

    return results
