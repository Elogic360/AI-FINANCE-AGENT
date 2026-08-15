import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    uploaded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    business: Mapped["Business"] = relationship("Business", back_populates="documents")
    extracted_records: Mapped[list["ExtractedRecord"]] = relationship("ExtractedRecord", back_populates="document")

    __table_args__ = (
        CheckConstraint("parse_status IN ('pending','parsed','failed','needs_review')"),
    )


class ExtractedRecord(Base):
    __tablename__ = "extracted_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    record_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    validation_status: Mapped[str] = mapped_column(Text, nullable=False, default="unvalidated")
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="extracted_records")

    __table_args__ = (
        CheckConstraint("validation_status IN ('unvalidated','valid','inconsistent','needs_human_review')"),
    )
