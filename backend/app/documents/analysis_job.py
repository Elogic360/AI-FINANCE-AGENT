"""Analysis job management for the document processing pipeline.

Orchestrates the full pipeline:
  ingestion → extraction → normalization → validation → entity_resolution
  → reconciliation → accounting → metrics → anomaly_detection → forecasting
  → recommendations
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.documents.processor import DocumentProcessor, ProcessedDocument
from app.documents.extractors import (
    extract_transactions,
    extract_invoices,
    extract_expenses,
    extract_bank_transactions,
)
from app.documents.normalizer import DataNormalizer
from app.documents.validator import DataValidator, ValidationResult
from app.documents.entity_resolution import EntityResolver


# ---------------------------------------------------------------------------
# Pipeline stage enum
# ---------------------------------------------------------------------------

class PipelineStage(str, Enum):
    INGESTION = "ingestion"
    EXTRACTION = "extraction"
    NORMALIZATION = "normalization"
    VALIDATION = "validation"
    ENTITY_RESOLUTION = "entity_resolution"
    RECONCILIATION = "reconciliation"
    ACCOUNTING = "accounting"
    METRICS = "metrics"
    ANOMALY_DETECTION = "anomaly_detection"
    FORECASTING = "forecasting"
    RECOMMENDATIONS = "recommendations"


PIPELINE_ORDER: list[PipelineStage] = list(PipelineStage)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Result data-classes
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    """Outcome of a single pipeline stage."""
    stage: PipelineStage
    status: str = "pending"  # "pending" | "completed" | "failed" | "skipped"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class AnalysisJob:
    """A document-analysis job."""
    job_id: uuid.UUID = field(default_factory=uuid.uuid4)
    org_id: str = ""
    document_ids: list[str] = field(default_factory=list)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    stages: dict[str, StageResult] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Final output after all pipeline stages."""
    job_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: str = "completed"
    extracted_records: dict[str, list[dict]] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    entity_matches: dict[str, Any] = field(default_factory=dict)
    reconciliation: dict[str, Any] = field(default_factory=dict)
    accounting_entries: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    forecast: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AnalysisJobManager
# ---------------------------------------------------------------------------

class AnalysisJobManager:
    """Create and run analysis jobs across documents."""

    def __init__(self) -> None:
        self._processor = DocumentProcessor()
        self._normalizer = DataNormalizer()
        self._validator = DataValidator()
        self._resolver = EntityResolver()
        # In-memory job store (replace with DB in production)
        self._jobs: dict[uuid.UUID, AnalysisJob] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_analysis_job(
        self,
        org_id: str,
        document_ids: list[str],
    ) -> AnalysisJob:
        """Create a new analysis job.

        Parameters
        ----------
        org_id : str
            Organization/business identifier.
        document_ids : list[str]
            Document IDs to include in this analysis run.

        Returns
        -------
        AnalysisJob
        """
        job = AnalysisJob(org_id=org_id, document_ids=document_ids)
        for stage in PipelineStage:
            job.stages[stage.value] = StageResult(stage=stage)
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: uuid.UUID) -> AnalysisJob | None:
        return self._jobs.get(job_id)

    def run_analysis_job(self, job_id: uuid.UUID) -> AnalysisResult:
        """Execute the full pipeline for a job.

        Parameters
        ----------
        job_id : uuid.UUID
            ID of a previously created job.

        Returns
        -------
        AnalysisResult
        """
        job = self._jobs.get(job_id)
        if job is None:
            return AnalysisResult(
                status="failed",
                errors=[f"Job {job_id} not found"],
            )

        job.status = JobStatus.RUNNING
        job.updated_at = datetime.utcnow()
        final = AnalysisResult(job_id=job.job_id)

        try:
            # 1. Ingestion — process each document
            processed_docs = self._run_stage_ingestion(job, final)

            # 2. Extraction
            extracted = self._run_stage_extraction(job, final, processed_docs)

            # 3. Normalization
            normalized = self._run_stage_normalization(job, final, extracted)

            # 4. Validation
            validation_results = self._run_stage_validation(job, final, normalized)

            # 5. Entity resolution
            self._run_stage_entity_resolution(job, final, normalized)

            # 6–11. Placeholder stages (would call real services)
            self._run_stage_reconciliation(job, final, normalized)
            self._run_stage_accounting(job, final, normalized)
            self._run_stage_metrics(job, final, normalized)
            self._run_stage_anomaly_detection(job, final, normalized)
            self._run_stage_forecasting(job, final, normalized)
            self._run_stage_recommendations(job, final)

            final.status = "completed"
            job.status = JobStatus.COMPLETED

        except Exception as exc:  # noqa: BLE001
            final.status = "failed"
            final.errors.append(str(exc))
            job.status = JobStatus.FAILED

        job.updated_at = datetime.utcnow()
        return final

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _run_stage_ingestion(
        self,
        job: AnalysisJob,
        result: AnalysisResult,
    ) -> list[ProcessedDocument]:
        """Ingest documents — placeholder paths for demo."""
        stage = job.stages[PipelineStage.INGESTION.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()

        docs: list[ProcessedDocument] = []
        for doc_id in job.document_ids:
            # In production, look up file path and mime type from DB.
            # Here we create a stub ProcessedDocument.
            pd = ProcessedDocument(
                document_id=uuid.UUID(doc_id) if self._is_uuid(doc_id) else uuid.uuid4(),
                file_path=f"storage://{doc_id}",
                mime_type="text/csv",
                text_content="",
            )
            docs.append(pd)

        stage.status = "completed"
        stage.completed_at = datetime.utcnow()
        stage.data = {"document_count": len(docs)}
        return docs

    def _run_stage_extraction(
        self,
        job: AnalysisJob,
        result: AnalysisResult,
        docs: list[ProcessedDocument],
    ) -> dict[str, list[dict]]:
        stage = job.stages[PipelineStage.EXTRACTION.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()

        extracted: dict[str, list[dict]] = {
            "transactions": [],
            "invoices": [],
            "expenses": [],
            "bank_transactions": [],
        }

        for doc in docs:
            content = {"text": doc.text_content, "tables": []}
            for t in doc.tables:
                content["tables"].append({
                    "headers": t.headers,
                    "rows": t.rows,
                })

            # Run extractors based on document type
            from dataclasses import asdict

            txns = extract_transactions(content)
            extracted["transactions"].extend(asdict(t) for t in txns)

            invs = extract_invoices(content)
            extracted["invoices"].extend(asdict(i) for i in invs)

            exps = extract_expenses(content)
            extracted["expenses"].extend(asdict(e) for e in exps)

            btxns = extract_bank_transactions(content)
            extracted["bank_transactions"].extend(asdict(b) for b in btxns)

        result.extracted_records = extracted
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()
        stage.data = {k: len(v) for k, v in extracted.items()}
        return extracted

    def _run_stage_normalization(
        self,
        job: AnalysisJob,
        result: AnalysisResult,
        extracted: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        stage = job.stages[PipelineStage.NORMALIZATION.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()

        normalized: dict[str, list[dict]] = {}
        for key, records in extracted.items():
            normalized[key] = self._normalizer.normalize_all(records)

        result.extracted_records = normalized
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()
        return normalized

    def _run_stage_validation(
        self,
        job: AnalysisJob,
        result: AnalysisResult,
        normalized: dict[str, list[dict]],
    ) -> dict[str, ValidationResult]:
        stage = job.stages[PipelineStage.VALIDATION.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()

        all_results: dict[str, ValidationResult] = {}
        for key, records in normalized.items():
            vr = self._validator.validate(records, record_type=key.rstrip("s"))
            all_results[key] = vr

        result.validation = {
            k: {
                "is_valid": v.is_valid,
                "record_count": v.record_count,
                "error_count": v.error_count,
                "warning_count": v.warning_count,
                "issues": [
                    {"field": i.field, "message": i.message, "severity": i.severity}
                    for i in v.issues
                ],
            }
            for k, v in all_results.items()
        }

        stage.status = "completed"
        stage.completed_at = datetime.utcnow()
        return all_results

    def _run_stage_entity_resolution(
        self,
        job: AnalysisJob,
        result: AnalysisResult,
        normalized: dict[str, list[dict]],
    ) -> None:
        stage = job.stages[PipelineStage.ENTITY_RESOLUTION.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()

        # In production, fetch existing entities from DB.
        existing_customers: list[dict[str, Any]] = []
        existing_vendors: list[dict[str, Any]] = []
        existing_transactions: list[dict[str, Any]] = []

        matches: dict[str, Any] = {}

        if normalized.get("invoices"):
            cust_results = self._resolver.resolve_customers(
                normalized["invoices"], existing_customers,
            )
            matches["customers"] = [
                {"name": r.extracted_name, "matched": r.matched, "action": r.action}
                for r in cust_results
            ]

        if normalized.get("expenses"):
            vendor_results = self._resolver.resolve_vendors(
                normalized["expenses"], existing_vendors,
            )
            matches["vendors"] = [
                {"name": r.extracted_name, "matched": r.matched, "action": r.action}
                for r in vendor_results
            ]

        if normalized.get("transactions"):
            txn_results = self._resolver.resolve_transactions(
                normalized["transactions"], existing_transactions,
            )
            matches["transactions"] = [
                {"name": r.extracted_name, "matched": r.matched, "action": r.action}
                for r in txn_results
            ]

        result.entity_matches = matches
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()

    # Placeholder stages — would integrate with real services

    def _run_stage_reconciliation(self, job: AnalysisJob, result: AnalysisResult, data: dict) -> None:
        stage = job.stages[PipelineStage.RECONCILIATION.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()
        # Placeholder: flag unmatched transactions
        result.reconciliation = {
            "matched_count": 0,
            "unmatched_count": len(data.get("transactions", [])),
            "notes": "Reconciliation stub — integrate with bank feed matcher",
        }
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()

    def _run_stage_accounting(self, job: AnalysisJob, result: AnalysisResult, data: dict) -> None:
        stage = job.stages[PipelineStage.ACCOUNTING.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()
        # Placeholder: suggest journal entries
        result.accounting_entries = []
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()

    def _run_stage_metrics(self, job: AnalysisJob, result: AnalysisResult, data: dict) -> None:
        stage = job.stages[PipelineStage.METRICS.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()
        total_txns = len(data.get("transactions", []))
        total_invoices = len(data.get("invoices", []))
        result.metrics = {
            "total_transactions": total_txns,
            "total_invoices": total_invoices,
            "total_expenses": len(data.get("expenses", [])),
            "total_bank_transactions": len(data.get("bank_transactions", [])),
        }
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()

    def _run_stage_anomaly_detection(self, job: AnalysisJob, result: AnalysisResult, data: dict) -> None:
        stage = job.stages[PipelineStage.ANOMALY_DETECTION.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()
        # Placeholder: flag large transactions
        for txn in data.get("transactions", []):
            try:
                from decimal import Decimal
                amt = Decimal(str(txn.get("amount", "0")))
                if abs(amt) > Decimal("10000000"):
                    result.anomalies.append({
                        "type": "large_transaction",
                        "record": txn,
                        "reason": f"Amount {amt} exceeds threshold",
                    })
            except Exception:
                pass
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()

    def _run_stage_forecasting(self, job: AnalysisJob, result: AnalysisResult, data: dict) -> None:
        stage = job.stages[PipelineStage.FORECASTING.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()
        # Placeholder
        result.forecast = {
            "method": "stub",
            "horizon_days": 30,
            "predicted_revenue": None,
            "predicted_expenses": None,
            "notes": "Forecasting stub — integrate with ML service",
        }
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()

    def _run_stage_recommendations(self, job: AnalysisJob, result: AnalysisResult) -> None:
        stage = job.stages[PipelineStage.RECOMMENDATIONS.value]
        stage.status = "running"
        stage.started_at = datetime.utcnow()
        recs: list[str] = []
        if result.anomalies:
            recs.append(f"Review {len(result.anomalies)} flagged anomaly/anomalies.")
        if result.validation:
            total_errors = sum(v.get("error_count", 0) for v in result.validation.values())
            if total_errors:
                recs.append(f"Fix {total_errors} validation error(s) before posting.")
        if not recs:
            recs.append("No issues detected. Data looks clean.")
        result.recommendations = recs
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _is_uuid(val: str) -> bool:
        try:
            uuid.UUID(val)
            return True
        except (ValueError, AttributeError):
            return False
