"""DocumentProcessor — central orchestrator for document ingestion.

Supports: PDF, DOCX, XLSX, CSV, PNG, JPG.
Extracts text, tables, and metadata, then classifies the document type.
"""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Domain enums & data-classes
# ---------------------------------------------------------------------------

class DocumentType(str, Enum):
    BANK_STATEMENT = "bank_statement"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    FINANCIAL_STATEMENT = "financial_statement"
    TAX_DOCUMENT = "tax_document"
    EXPENSE_REPORT = "expense_report"
    UNKNOWN = "unknown"


class MimeType(str, Enum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    CSV = "text/csv"
    PNG = "image/png"
    JPG = "image/jpeg"


@dataclass
class ExtractedTable:
    """A table pulled from the document."""
    headers: list[str]
    rows: list[list[str]]


@dataclass
class ProcessedDocument:
    """Result of processing a single document."""
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    file_path: str = ""
    mime_type: str = ""
    document_type: DocumentType = DocumentType.UNKNOWN
    text_content: str = ""
    tables: list[ExtractedTable] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    page_count: int = 0
    processed_at: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DocumentProcessor
# ---------------------------------------------------------------------------

class DocumentProcessor:
    """Ingest a file, extract content, classify document type."""

    SUPPORTED_MIME_TYPES: set[str] = {m.value for m in MimeType}

    # Keyword heuristics for document-type classification
    _TYPE_KEYWORDS: dict[DocumentType, list[str]] = {
        DocumentType.BANK_STATEMENT: [
            "bank statement", "account statement", "opening balance",
            "closing balance", "transaction history", "debit", "credit",
        ],
        DocumentType.INVOICE: [
            "invoice", "bill to", "invoice number", "due date",
            "subtotal", "amount due", "payment terms",
        ],
        DocumentType.RECEIPT: [
            "receipt", "total due", "paid", "change", "cash",
            "card payment", "transaction id",
        ],
        DocumentType.FINANCIAL_STATEMENT: [
            "balance sheet", "income statement", "cash flow",
            "profit and loss", "equity", "assets", "liabilities",
        ],
        DocumentType.TAX_DOCUMENT: [
            "tax return", "vat", "tax invoice", "tin", "tax authority",
            "withholding", "tax period",
        ],
        DocumentType.EXPENSE_REPORT: [
            "expense report", "reimbursement", "mileage",
            "per diem", "travel expense", "business expense",
        ],
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_document(
        self,
        file_path: str,
        mime_type: str,
    ) -> ProcessedDocument:
        """Process a document and return structured data.

        Parameters
        ----------
        file_path : str
            Absolute or relative path to the file on disk.
        mime_type : str
            MIME type of the file (e.g. ``application/pdf``).

        Returns
        -------
        ProcessedDocument
            Extracted text, tables, metadata, and classified document type.
        """
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            return ProcessedDocument(
                file_path=file_path,
                mime_type=mime_type,
                errors=[f"Unsupported MIME type: {mime_type}"],
            )

        path = Path(file_path)
        if not path.exists():
            return ProcessedDocument(
                file_path=file_path,
                mime_type=mime_type,
                errors=[f"File not found: {file_path}"],
            )

        result = ProcessedDocument(
            file_path=file_path,
            mime_type=mime_type,
            metadata={"filename": path.name, "size_bytes": path.stat().st_size},
        )

        try:
            if mime_type == MimeType.PDF.value:
                self._process_pdf(path, result)
            elif mime_type == MimeType.DOCX.value:
                self._process_docx(path, result)
            elif mime_type == MimeType.XLSX.value:
                self._process_xlsx(path, result)
            elif mime_type == MimeType.CSV.value:
                self._process_csv(path, result)
            elif mime_type in (MimeType.PNG.value, MimeType.JPG.value):
                self._process_image(path, result)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"Processing error: {exc}")

        # Classify
        if not result.errors:
            result.document_type = self._classify(result.text_content)
            result.confidence = self._compute_confidence(result)

        return result

    # ------------------------------------------------------------------
    # Format-specific extractors (stubs — replace with real libs)
    # ------------------------------------------------------------------

    def _process_pdf(self, path: Path, result: ProcessedDocument) -> None:
        """Extract text/tables from a PDF.

        Production: use ``pdfplumber`` or ``pymupdf``.
        """
        # Placeholder — in production replace with real extraction
        result.text_content = self._read_file_text(path)
        result.page_count = max(1, result.text_content.count("\f") + 1)
        result.metadata["extraction_method"] = "pdf_stub"

    def _process_docx(self, path: Path, result: ProcessedDocument) -> None:
        """Extract text/tables from a DOCX.

        Production: use ``python-docx``.
        """
        result.text_content = self._read_file_text(path)
        result.page_count = 1
        result.metadata["extraction_method"] = "docx_stub"

    def _process_xlsx(self, path: Path, result: ProcessedDocument) -> None:
        """Extract tables from an XLSX workbook.

        Production: use ``openpyxl``.
        """
        # Stub: read as text for now
        raw = self._read_file_text(path)
        result.text_content = raw
        result.page_count = 1
        result.metadata["extraction_method"] = "xlsx_stub"

    def _process_csv(self, path: Path, result: ProcessedDocument) -> None:
        """Parse a CSV into text and an ExtractedTable."""
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                reader = csv.reader(fh)
                rows = list(reader)
            if rows:
                headers = rows[0]
                data_rows = rows[1:]
                result.tables.append(
                    ExtractedTable(headers=headers, rows=data_rows)
                )
                result.text_content = "\n".join(
                    ",".join(row) for row in rows
                )
            else:
                result.text_content = ""
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"CSV parse error: {exc}")
        result.page_count = 1
        result.metadata["extraction_method"] = "csv_native"

    def _process_image(self, path: Path, result: ProcessedDocument) -> None:
        """OCR an image document.

        Production: use ``pytesseract`` or a vision LLM.
        """
        result.text_content = f"[OCR placeholder for {path.name}]"
        result.page_count = 1
        result.metadata["extraction_method"] = "ocr_stub"

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def _classify(self, text: str) -> DocumentType:
        """Classify document type by keyword heuristics."""
        lower = text.lower()
        scores: dict[DocumentType, int] = {}
        for dtype, keywords in self._TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score:
                scores[dtype] = score

        if not scores:
            return DocumentType.UNKNOWN
        return max(scores, key=scores.get)  # type: ignore[arg-type]

    def _compute_confidence(self, result: ProcessedDocument) -> float:
        """Heuristic confidence score (0.0 – 1.0)."""
        if result.errors:
            return 0.0
        if result.document_type == DocumentType.UNKNOWN:
            return 0.2
        # More text + tables → higher confidence
        text_len = len(result.text_content)
        table_count = len(result.tables)
        score = min(1.0, (text_len / 500) * 0.5 + table_count * 0.1 + 0.3)
        return round(score, 3)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _read_file_text(path: Path) -> str:
        """Read a file as UTF-8 text (best-effort)."""
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
