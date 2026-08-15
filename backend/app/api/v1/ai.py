"""AI CFO chat, document analysis, and suggestion endpoints."""

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.ai.prompts import build_prompt_bundle
from app.models.business import User
from app.models.accounting import Transaction, JournalEntry, JournalLine, ChartOfAccounts
from app.models.contacts import Invoice, Customer
from app.models.document import Document
from app.models.ai import Alert
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
settings = get_settings()


# ---------------------------------------------------------------------------
# Helper: Build business context from DB
# ---------------------------------------------------------------------------

async def _build_business_context(db: AsyncSession, business_id) -> str:
    """Query the database and build a text context of the business financials."""
    # Revenue
    rev = (await db.execute(
        select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(ChartOfAccounts.business_id == business_id, ChartOfAccounts.account_type == "revenue", JournalEntry.is_draft.is_(False))
    )).scalar() or 0

    # Expenses
    exp = (await db.execute(
        select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(ChartOfAccounts.business_id == business_id, ChartOfAccounts.account_type == "expense", JournalEntry.is_draft.is_(False))
    )).scalar() or 0

    # Transaction count
    txn_count = (await db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.business_id == business_id)
    )).scalar() or 0

    # Invoices
    inv_total = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.business_id == business_id)
    )).scalar() or 0
    inv_overdue = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.business_id == business_id, Invoice.status == "overdue")
    )).scalar() or 0
    inv_unpaid = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.business_id == business_id, Invoice.status.in_(["unpaid", "overdue"]))
    )).scalar() or 0
    ar_total = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(Invoice.business_id == business_id, Invoice.status.in_(["unpaid", "overdue"]))
    )).scalar() or 0

    # Customers
    cust_count = (await db.execute(
        select(func.count()).select_from(Customer).where(Customer.business_id == business_id)
    )).scalar() or 0

    # Alerts
    alert_count = (await db.execute(
        select(func.count()).select_from(Alert).where(Alert.business_id == business_id, Alert.acknowledged == False)
    )).scalar() or 0

    # Top expense categories
    expense_cats = (await db.execute(
        select(Transaction.ai_category, func.sum(Transaction.amount))
        .where(Transaction.business_id == business_id, Transaction.ai_category.isnot(None))
        .group_by(Transaction.ai_category)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    )).all()

    # Recent transactions
    recent_txns = (await db.execute(
        select(Transaction.description, Transaction.amount, Transaction.txn_date, Transaction.ai_category)
        .where(Transaction.business_id == business_id)
        .order_by(Transaction.txn_date.desc())
        .limit(10)
    )).all()

    net_income = float(rev) - float(exp)

    ctx = f"""BUSINESS FINANCIAL DATA:
- Total Revenue: TZS {float(rev):,.2f}
- Total Expenses: TZS {float(exp):,.2f}
- Net Income: TZS {net_income:,.2f}
- Total Transactions: {txn_count}
- Total Invoices: {inv_total} ({inv_overdue} overdue, {inv_unpaid} unpaid)
- Accounts Receivable: TZS {float(ar_total):,.2f}
- Customers: {cust_count}
- Active Alerts: {alert_count}

TOP EXPENSE CATEGORIES:"""
    for cat, amount in expense_cats:
        ctx += f"\n- {cat}: TZS {float(amount):,.2f}"

    ctx += "\n\nRECENT TRANSACTIONS:"
    for desc, amt, dt, cat in recent_txns:
        ctx += f"\n- {dt}: {desc} - TZS {float(amt):,.2f} ({cat})"

    return ctx


def _resolve_prompt_mode(message: str, prompt_mode: str | None = None) -> str:
    """Infer prompt mode from the user message when the frontend does not send one."""
    if prompt_mode and prompt_mode != "chat_short":
        return prompt_mode

    msg = message.lower()
    if any(phrase in msg for phrase in ["json pitch deck", "pitch deck json", "pitch deck as json", "structured json"]):
        return "pitch_deck_json"
    if any(phrase in msg for phrase in ["pitch deck", "pitchdeck", "investor deck", "deck for investors"]):
        return "pitch_deck"
    return "chat_short"


def _sse_chunk(text: str, event: str = "message") -> str:
    return f"data: {ChatChunk(event=event, data=text).model_dump_json()}\n\n"


async def _stream_gemini(full_prompt: str, prompt_mode: str, conversation_id: str) -> AsyncIterator[str]:
    """Stream a response from Gemini using the official SSE endpoint."""
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key":
        return

    generation_config: dict[str, object] = {
        "temperature": 0.7,
        "maxOutputTokens": 1024,
    }
    if prompt_mode == "pitch_deck_json":
        generation_config["responseMimeType"] = "application/json"

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": generation_config,
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse&key={settings.GEMINI_API_KEY}",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        payload_data = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    candidates = payload_data.get("candidates") or []
                    text = ""
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            text = parts[0].get("text", "") or ""
                    if text:
                        yield _sse_chunk(text, "message")

    yield _sse_chunk(json.dumps({"conversation_id": conversation_id, "message_count": 1}), "done")


async def _stream_pawa(
    system_prompt: str,
    business_context: str,
    user_message: str,
    conversation_id: str,
) -> AsyncIterator[str]:
    """Stream a response from Pawa by calling its chat API and chunking the result."""
    if not settings.PAWA_API_KEY or settings.PAWA_API_KEY == "your-pawa-api-key":
        return

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.PAWA_API_URL}/v1/chat",
            headers={"Authorization": f"Bearer {settings.PAWA_API_KEY}"},
            json={
                "message": user_message,
                "context": business_context,
                "system": system_prompt,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", data.get("message", ""))
        if not text:
            yield _sse_chunk(json.dumps({"conversation_id": conversation_id, "message_count": 1}), "done")
            return

        words = text.split()
        for i in range(0, len(words), 5):
            chunk_text = " ".join(words[i:i + 5])
            if i + 5 < len(words):
                chunk_text += " "
            yield _sse_chunk(chunk_text, "message")

    yield _sse_chunk(json.dumps({"conversation_id": conversation_id, "message_count": 1}), "done")


# ---------------------------------------------------------------------------
# POST /ai/chat — SSE streaming chat with AI CFO
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat_with_ai(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a conversation with the AI CFO via Server-Sent Events."""
    conversation_id = body.conversation_id or uuid.uuid4()
    resolved_mode = _resolve_prompt_mode(body.message, body.prompt_mode)

    # Build business context from database
    business_context = await _build_business_context(db, current_user.business_id)

    system_prompt, full_prompt = build_prompt_bundle(
        resolved_mode,
        business_context,
        body.message,
    )

    async def event_stream():
        # Try Gemini first for realtime SSE streaming.
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key":
            try:
                async for chunk in _stream_gemini(full_prompt, resolved_mode, str(conversation_id)):
                    yield chunk
                return
            except Exception:
                # Fall through to Pawa if Gemini fails.
                pass

        # Try Pawa next.
        if settings.PAWA_API_KEY and settings.PAWA_API_KEY != "your-pawa-api-key":
            try:
                async for chunk in _stream_pawa(system_prompt, business_context, body.message, str(conversation_id)):
                    yield chunk
                return
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No AI provider is configured. Set GEMINI_API_KEY or PAWA_API_KEY to enable live responses.",
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
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
    # Fetch actual business data to personalize suggestions
    bid = current_user.business_id

    overdue = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.business_id == bid, Invoice.status == "overdue")
    )).scalar() or 0

    txn_count = (await db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.business_id == bid)
    )).scalar() or 0

    rev = (await db.execute(
        select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(ChartOfAccounts.business_id == bid, ChartOfAccounts.account_type == "revenue", JournalEntry.is_draft.is_(False))
    )).scalar() or 0

    exp = (await db.execute(
        select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(ChartOfAccounts.business_id == bid, ChartOfAccounts.account_type == "expense", JournalEntry.is_draft.is_(False))
    )).scalar() or 0

    questions = []

    if overdue > 0:
        questions.append({"id": "1", "text": f"I have {overdue} overdue invoices. What should I do?", "text_sw": f"Nina ankara {overdue} zilizopita wakati. Nifanye nini?", "category": "receivables"})

    if float(exp) > float(rev):
        questions.append({"id": "2", "text": "Why are my expenses higher than revenue?", "text_sw": "Kwa nini gharama zangu ni kubwa kuliko mapato?", "category": "analysis"})

    questions.extend([
        {"id": "3", "text": "What is my current cash position?", "text_sw": "Hali yangu ya pesa ipoje sasa?", "category": "cash"},
        {"id": "4", "text": "Can I afford to hire another employee?", "text_sw": "Je, ninaweza kumudu kuajiri mfanyakazi mwingine?", "category": "planning"},
        {"id": "5", "text": "What are my biggest expenses?", "text_sw": "Gharama zangu kubwa ni zipi?", "category": "analysis"},
        {"id": "6", "text": "How can I improve my profit margins?", "text_sw": "Ninawezaje kuboresha faida yangu?", "category": "advice"},
        {"id": "7", "text": "Summarize my financial health", "text_sw": "Fupisha hali yangu ya kifedha", "category": "summary"},
        {"id": "8", "text": "What happens if sales drop 20%?", "text_sw": "Nini kama mauzo yashuka 20%?", "category": "forecast"},
    ])

    return SuggestResponse(questions=questions[:8])
