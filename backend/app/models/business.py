import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TZS")
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="TZ")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship("User", back_populates="business")
    chart_of_accounts: Mapped[list["ChartOfAccounts"]] = relationship("ChartOfAccounts", back_populates="business")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="business")
    journal_entries: Mapped[list["JournalEntry"]] = relationship("JournalEntry", back_populates="business")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="business")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="owner")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    business: Mapped["Business"] = relationship("Business", back_populates="users")
