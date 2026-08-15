"""AI CFO chat, document analysis, and suggestion endpoints."""

import json
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.business import User
from app.models.document import Document
from app.schemas.ai import (
    ChatRequest,
    ChatChunk,
    ConversationSummary,
    ConversationDetail,
    ChatMessage,
    AnalyzeRequest,
    AnalyzeResponse,
    SuggestRequest,
    SuggestResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /ai/chat — SSE streaming chat with AI CFO
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat_with_ai(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a conversation with the AI CFO via Server-Sent Events.

    In production this calls the configured LLM provider (Pawa / Gemini).
    For now it returns a structured placeholder response.
    """
    conversation_id = body.conversation_id or uuid.uuid4()

    async def event_stream():
        # Simulate streaming chunks
        response_parts = [
            f"Based on your business data, here's my analysis:\n\n",
            f"**Current Financial Position:**\n",
            f"- Your revenue trend shows healthy growth\n",
            f"- Cash flow is positive for the current period\n",
            f"- Accounts receivable needs attention — some invoices are overdue\n\n",
            f"**Recommendation:**\n",
            f"Focus on collecting outstanding receivables to improve cash position. ",
            f"Consider offering early payment discounts to accelerate collections.",
        ]

        for part in response_parts:
            chunk = ChatChunk(event="message", data=part)
            yield f"data: {chunk.model_dump_json()}\n\n"

        # Final done event
        done_chunk = ChatChunk(
            event="done",
            data=json.dumps({
                "conversation_id": str(conversation_id),
                "message_count": len(response_parts) + 1,
            }),
        )
        yield f"data: {done_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# POST /ai/analyze — Analyze uploaded documents
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(
    body: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run AI analysis on an uploaded document."""
    result = await db.execute(
        select(Document).where(
            Document.id == body.document_id,
            Document.business_id == current_user.business_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Placeholder analysis — in production this calls the AI provider
    return AnalyzeResponse(
        document_id=doc.id,
        summary=f"Analysis of {doc.original_filename}: This document appears to be a "
                f"{doc.file_type.upper()} file containing financial data. "
                f"The document has been processed and key data points extracted.",
        extracted_data={
            "document_type": doc.file_type,
            "pages": 1,
            "line_items": [],
            "total_amount": None,
            "currency": "TZS",
        },
        confidence=Decimal("0.85"),
        suggestions=[
            "Review extracted line items for accuracy",
            "Verify total amounts match the original document",
            "Consider linking this document to a transaction",
        ],
    )


# ---------------------------------------------------------------------------
# GET /ai/conversations — List conversations
# ---------------------------------------------------------------------------

@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List AI chat conversations for the current user's business."""
    # Placeholder — in production, a Conversation model would store these
    return [
        ConversationSummary(
            id=uuid.uuid4(),
            title="Cash flow analysis discussion",
            message_count=6,
            last_message_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        ),
        ConversationSummary(
            id=uuid.uuid4(),
            title="Invoice follow-up strategy",
            message_count=4,
            last_message_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        ),
    ]


# ---------------------------------------------------------------------------
# GET /ai/conversations/{id} — Get conversation detail
# ---------------------------------------------------------------------------

@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full conversation with message history."""
    # Placeholder — in production, fetch from Conversation + Message tables
    return ConversationDetail(
        id=conversation_id,
        title="Cash flow analysis discussion",
        messages=[
            ChatMessage(role="user", content="How is my cash flow looking this month?"),
            ChatMessage(
                role="assistant",
                content="Your cash flow for this month shows a positive trend. "
                        "Total inflows are TZS 4,250,000 while outflows are TZS 3,100,000, "
                        "giving you a net positive cash flow of TZS 1,150,000.",
            ),
        ],
        created_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# POST /ai/suggest — Get suggested questions
# ---------------------------------------------------------------------------

@router.post("/suggest", response_model=SuggestResponse)
async def get_suggestions(
    body: SuggestRequest = SuggestRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-suggested questions based on current business context."""
    context = body.context or "general"

    suggestions_map = {
        "general": [
            "What is my current cash position?",
            "Which invoices are overdue and need follow-up?",
            "How does my revenue compare to last month?",
            "What are my top expense categories?",
            "Am I on track to meet my financial targets?",
        ],
        "dashboard": [
            "Why did revenue change this month?",
            "Which expenses can I reduce?",
            "What is my projected cash balance for next month?",
            "How healthy is my accounts receivable?",
        ],
        "documents": [
            "Can you summarize the latest bank statement?",
            "What transactions are missing from my records?",
            "Are there any discrepancies in the uploaded invoices?",
        ],
        "reports": [
            "Generate a profit and loss summary for this quarter",
            "What does my balance sheet tell about my business health?",
            "Show me the cash flow forecast for the next 90 days",
        ],
    }

    return SuggestResponse(
        questions=suggestions_map.get(context, suggestions_map["general"]),
    )
