"""Document processing pipeline for FinPilot AI.

Handles ingestion, extraction, normalization, validation,
entity resolution, and chunking of financial documents.
"""

from app.documents.processor import DocumentProcessor
from app.documents.extractors import (
    extract_transactions,
    extract_invoices,
    extract_expenses,
    extract_products,
    extract_bank_transactions,
)
from app.documents.normalizer import DataNormalizer
from app.documents.validator import DataValidator, ValidationResult
from app.documents.entity_resolution import EntityResolver
from app.documents.analysis_job import AnalysisJobManager
from app.documents.chunker import DocumentChunker

__all__ = [
    "DocumentProcessor",
    "extract_transactions",
    "extract_invoices",
    "extract_expenses",
    "extract_products",
    "extract_bank_transactions",
    "DataNormalizer",
    "DataValidator",
    "ValidationResult",
    "EntityResolver",
    "AnalysisJobManager",
    "DocumentChunker",
]
