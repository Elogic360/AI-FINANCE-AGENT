"""AI chat & analysis schemas for FinPilot AI."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    """Request body for the AI CFO chat endpoint."""
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[uuid.UUID] = None
    prompt_mode: Literal["chat_short", "pitch_deck", "pitch_deck_json"] = "chat_short"


class ChatChunk(BaseModel):
    """One SSE chunk streamed back to the client."""
    event: str = Field(default="message")  # message | done | error
    data: str


class ConversationSummary(BaseModel):
    """Lightweight conversation listing item."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    message_count: int
    last_message_at: datetime
    created_at: datetime


class ConversationDetail(BaseModel):
    """Full conversation with messages."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    messages: list[ChatMessage]
    created_at: datetime


# ---------------------------------------------------------------------------
# Document analysis
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Trigger analysis on an uploaded document."""
    document_id: uuid.UUID
    question: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Result of document analysis."""
    document_id: uuid.UUID
    summary: str
    extracted_data: dict
    confidence: Decimal
    suggestions: list[str]


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

class SuggestRequest(BaseModel):
    """Request for suggested questions."""
    context: Optional[str] = None  # e.g. "dashboard", "documents", "reports"


class SuggestedQuestionItem(BaseModel):
    """A single suggested question."""
    id: str
    text: str
    text_sw: Optional[str] = None
    category: str


class SuggestResponse(BaseModel):
    """Suggested questions for the user."""
    questions: list[SuggestedQuestionItem]
