"""AI CFO chat, document analysis, and suggestion endpoints."""

import json
import uuid
from datetime import datetime
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
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

    # Build business context from database
    business_context = await _build_business_context(db, current_user.business_id)

    system_prompt = """You are FinPilot AI, an expert CFO advisor for small businesses in Tanzania.
You analyze financial data and give clear, actionable advice.
Use TZS (Tanzania Shillings) for all amounts.
Be concise but thorough. Use bullet points for recommendations.
If the user asks in Swahili, respond in Swahili.
Never invent data — only reference what's in the provided business data."""

    full_prompt = f"{system_prompt}\n\n{business_context}\n\nUser question: {body.message}"

    async def event_stream():
        # Try Gemini API first
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key":
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}",
                        json={
                            "contents": [{"parts": [{"text": full_prompt}]}],
                            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            # Stream the response in chunks
                            words = text.split(" ")
                            chunk_size = 5
                            for i in range(0, len(words), chunk_size):
                                chunk_text = " ".join(words[i:i + chunk_size]) + " "
                                chunk = ChatChunk(event="message", data=chunk_text)
                                yield f"data: {chunk.model_dump_json()}\n\n"

                            done_chunk = ChatChunk(
                                event="done",
                                data=json.dumps({"conversation_id": str(conversation_id), "message_count": 1}),
                            )
                            yield f"data: {done_chunk.model_dump_json()}\n\n"
                            return
            except Exception as e:
                pass  # Fall through to Pawa

        # Try Pawa API
        if settings.PAWA_API_KEY and settings.PAWA_API_KEY != "your-pawa-api-key":
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{settings.PAWA_API_URL}/v1/chat",
                        headers={"Authorization": f"Bearer {settings.PAWA_API_KEY}"},
                        json={
                            "message": body.message,
                            "context": business_context,
                            "system": system_prompt,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data.get("response", data.get("message", ""))
                        if text:
                            words = text.split(" ")
                            chunk_size = 5
                            for i in range(0, len(words), chunk_size):
                                chunk_text = " ".join(words[i:i + chunk_size]) + " "
                                chunk = ChatChunk(event="message", data=chunk_text)
                                yield f"data: {chunk.model_dump_json()}\n\n"

                            done_chunk = ChatChunk(
                                event="done",
                                data=json.dumps({"conversation_id": str(conversation_id), "message_count": 1}),
                            )
                            yield f"data: {done_chunk.model_dump_json()}\n\n"
                            return
            except Exception as e:
                pass  # Fall through to local analysis

        # Fallback: intelligent local analysis using actual business data
        net = float(rev) - float(exp) if 'rev' in dir() else 0
        response_parts = _generate_local_analysis(body.message, business_context)
        for part in response_parts:
            chunk = ChatChunk(event="message", data=part)
            yield f"data: {chunk.model_dump_json()}\n\n"

        done_chunk = ChatChunk(
            event="done",
            data=json.dumps({"conversation_id": str(conversation_id), "message_count": len(response_parts) + 1}),
        )
        yield f"data: {done_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


def _generate_local_analysis(message: str, context: str) -> list[str]:
    """Generate analysis from actual business data when LLM APIs are unavailable."""
    msg = message.lower()

    # Parse key metrics from context
    lines = context.split("\n")
    metrics = {}
    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip("- ").strip()
            val = parts[1].strip()
            metrics[key] = val

    rev = metrics.get("Total Revenue", "TZS 0")
    exp = metrics.get("Total Expenses", "TZS 0")
    net = metrics.get("Net Income", "TZS 0")
    ar = metrics.get("Accounts Receivable", "TZS 0")
    overdue = metrics.get("Total Invoices", "0").split("(")[1].split(" ")[0] if "(" in metrics.get("Total Invoices", "") else "0"
    txns = metrics.get("Total Transactions", "0")

    if "profit" in msg or "falling" in msg or "loss" in msg:
        return [
            f"**Profit Analysis:**\n\n",
            f"Your current financial position:\n",
            f"- Revenue: {rev}\n",
            f"- Expenses: {exp}\n",
            f"- Net Income: {net}\n\n",
            f"**Key Findings:**\n",
            f"- You have {txns} transactions in your records\n",
            f"- Accounts receivable stands at {ar}\n",
            f"- There are {overdue} overdue invoices affecting cash flow\n\n",
            f"**Recommendations:**\n",
            f"1. Focus on collecting overdue invoices to improve cash position\n",
            f"2. Review your top expense categories for potential savings\n",
            f"3. Consider renegotiating supplier terms to reduce COGS\n",
            f"4. Track daily sales to identify trends early",
        ]
    elif "cash" in msg or "afford" in msg or "hire" in msg:
        return [
            f"**Cash Position Analysis:**\n\n",
            f"- Net Income: {net}\n",
            f"- Accounts Receivable: {ar}\n",
            f"- Active Invoices: {metrics.get('Total Invoices', '0')}\n\n",
            f"**Assessment:**\n",
            f"Before hiring, consider:\n",
            f"1. Your current cash runway and monthly burn rate\n",
            f"2. Whether revenue growth justifies the additional expense\n",
            f"3. Expected salary cost vs. productivity gain\n\n",
            f"**Recommendation:** Collect outstanding receivables first, then evaluate hiring based on consistent monthly revenue.",
        ]
    elif "invoice" in msg or "overdue" in msg or "receivable" in msg:
        return [
            f"**Receivables Analysis:**\n\n",
            f"- Total Accounts Receivable: {ar}\n",
            f"- Overdue Invoices: {overdue}\n\n",
            f"**Action Items:**\n",
            f"1. Follow up on overdue invoices immediately\n",
            f"2. Offer early payment discounts (e.g., 2% for payment within 7 days)\n",
            f"3. Set up automated payment reminders\n",
            f"4. Consider invoice factoring for large receivables",
        ]
    elif "expense" in msg or "cost" in msg or "reduce" in msg:
        return [
            f"**Expense Analysis:**\n\n",
            f"- Total Expenses: {exp}\n",
            f"- Total Revenue: {rev}\n\n",
            f"**Top areas to review:**\n",
            f"1. Rent - negotiate lease terms or consider relocating\n",
            f"2. Transport - optimize delivery routes\n",
            f"3. Inventory - reduce dead stock, buy in bulk\n",
            f"4. Utilities - energy-efficient equipment\n\n",
            f"**Target:** Reduce expenses by 10-15% to improve margins.",
        ]
    else:
        return [
            f"**Financial Overview:**\n\n",
            f"- Revenue: {rev}\n",
            f"- Expenses: {exp}\n",
            f"- Net Income: {net}\n",
            f"- Transactions: {txns}\n",
            f"- Accounts Receivable: {ar}\n\n",
            f"**Key Insights:**\n",
            f"1. Your business has {txns} transactions recorded\n",
            f"2. {overdue} invoices are overdue and need follow-up\n",
            f"3. Focus on collecting receivables to improve cash flow\n\n",
            f"Ask me about specific areas: profit, expenses, cash flow, invoices, or forecasting.",
        ]


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
