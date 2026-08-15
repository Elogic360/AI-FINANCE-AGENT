"""
PawaProvider — Africa-first AI provider for FinPilot.

Capabilities:
- Document parsing (PDF, DOCX, XLSX, images)
- Knowledge base / RAG search
- Agent orchestration
- Tool calling
- Swahili language support
- Chat completions with streaming

All implementations are MOCK/STUB for development. Real API calls will be
added when the Pawa API integration is ready.
"""

import os
import json
import uuid
import logging
from typing import Any, AsyncIterator

from app.ai.base import (
    AIProvider,
    AIResponse,
    ParsedDocument,
    ProviderCapability,
    StreamChunk,
    TaskType,
)

logger = logging.getLogger(__name__)

# ── Mock response data ─────────────────────────────────────────────────────

_MOCK_CHAT_RESPONSE = (
    "Kulingana na data yako ya kifedha, biashara yako ina afya nzuri. "
    "Mapato ya mwezi huu ni TZS 12,500,000, ongezeko la 15% kutoka mwezi uliopita. "
    "Mapato yaliongezeka hasa kutokana na mauzo ya bidhaa za elektroniki.\n\n"
    "Mapendekezo:\n"
    "1. Ongeza akiba ya dharura kwa 10% ya mapato\n"
    "2. Fuatilia deni za wateja — TZS 2,300,000 bado haijalipwa\n"
    "3. Fikiria kuwekeza faida ya ziada katika hisa za serikali"
)

_MOCK_SWAHILI_RESPONSE = (
    "Habari! Mimi ni msaidizi wako wa kifedha wa FinPilot. "
    "Naweza kukusaidia na maswali kuhusu biashara yako, ripoti za kifedha, "
    "na ushauri wa uwekezaji. Ungependa kujua nini?"
)

_MOCK_DOCUMENT_PARSED = ParsedDocument(
    content=(
        "INVOICE #INV-2024-0156\n"
        "Date: 2024-08-15\n"
        "From: Kilimanjaro Electronics Ltd\n"
        "To: Serengeti Trading Co.\n\n"
        "Item                          Qty    Unit Price    Total\n"
        "─────────────────────────────────────────────────────────\n"
        "Samsung Galaxy A54             10     TZS 850,000   TZS 8,500,000\n"
        "iPhone 15 Screen Protector     50     TZS 15,000    TZS 750,000\n"
        "USB-C Charging Cable           100    TZS 8,000     TZS 800,000\n"
        "─────────────────────────────────────────────────────────\n"
        "Subtotal:                                TZS 10,050,000\n"
        "VAT (18%):                               TZS 1,809,000\n"
        "TOTAL:                                   TZS 11,859,000\n\n"
        "Payment Terms: Net 30\n"
        "Bank: CRDB Bank, Account: 0150-XXXX-XXXX"
    ),
    mime_type="application/pdf",
    pages=1,
    tables=[
        {
            "headers": ["Item", "Qty", "Unit Price", "Total"],
            "rows": [
                ["Samsung Galaxy A54", "10", "TZS 850,000", "TZS 8,500,000"],
                ["iPhone 15 Screen Protector", "50", "TZS 15,000", "TZS 750,000"],
                ["USB-C Charging Cable", "100", "TZS 8,000", "TZS 800,000"],
            ],
        }
    ],
    metadata={"invoice_number": "INV-2024-0156", "currency": "TZS"},
    confidence=0.94,
)

_MOCK_EMBEDDING = [0.0123, -0.0456, 0.0789, -0.0012, 0.0345] * 100  # 500-dim


# ── Provider implementation ────────────────────────────────────────────────

class PawaProvider(AIProvider):
    """
    Pawa AI — Africa-first document parsing, KB/RAG, Swahili, agents, voice.

    MOCK implementation for development. Replace with real Pawa API calls
    when the integration is ready.

    API: https://api.pawa-ai.com
    Auth: PAWA_API_KEY env var
    """

    def __init__(self, api_key: str | None = None, api_url: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("PAWA_API_KEY", "")
        self._api_url = api_url or os.environ.get("PAWA_API_URL", "https://api.pawa-ai.com")
        self._mock_mode = not bool(self._api_key)
        if self._mock_mode:
            logger.info("PawaProvider running in MOCK mode (no PAWA_API_KEY set)")

    @property
    def name(self) -> str:
        return "pawa"

    @property
    def capabilities(self) -> set[ProviderCapability]:
        return {
            ProviderCapability.CHAT,
            ProviderCapability.DOCUMENT_PARSE,
            ProviderCapability.EMBEDDINGS,
            ProviderCapability.STREAMING,
            ProviderCapability.TOOL_CALLING,
            ProviderCapability.KNOWLEDGE_BASE,
            ProviderCapability.SWAHILI,
            ProviderCapability.AGENT_ORCHESTRATION,
        }

    # ── Chat ─────────────────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AIResponse:
        """Send a chat request to Pawa AI (mock)."""
        logger.debug(f"PawaProvider.chat: {len(messages)} messages, tools={bool(tools)}")

        # Determine if this is a Swahili request based on system prompt or last message
        last_content = messages[-1].get("content", "") if messages else ""
        is_swahili = any(
            kw in last_content.lower()
            for kw in ["swahili", "kiswahili", "habari", "tafadhali", "nchi"]
        )

        # Mock tool call response
        if tools and any(
            "get_" in (t.get("function", {}).get("name", "") or t.get("name", ""))
            for t in tools
        ):
            tool_calls = [
                {
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": "get_business_profile",
                        "arguments": json.dumps({"org_id": "mock-org-001"}),
                    },
                }
            ]
            return AIResponse(
                provider="pawa",
                task_type=TaskType.CHAT,
                result="",
                confidence=0.9,
                usage={"prompt_tokens": 250, "completion_tokens": 80, "total_tokens": 330},
                metadata={"tool_calls": tool_calls, "finish_reason": "tool_calls"},
                raw={"mock": True},
            )

        result = _MOCK_SWAHILI_RESPONSE if is_swahili else _MOCK_CHAT_RESPONSE
        return AIResponse(
            provider="pawa",
            task_type=TaskType.CHAT,
            result=result,
            confidence=0.88,
            usage={"prompt_tokens": 180, "completion_tokens": 120, "total_tokens": 300},
            metadata={"language": "sw" if is_swahili else "en"},
            raw={"mock": True},
        )

    # ── Document parsing ─────────────────────────────────────────────────

    async def parse_document(
        self,
        file_content: bytes,
        mime_type: str,
        filename: str = "",
        **kwargs: Any,
    ) -> ParsedDocument:
        """Parse a document using Pawa's document intelligence (mock)."""
        logger.debug(f"PawaProvider.parse_document: {mime_type}, {filename}, {len(file_content)} bytes")

        supported_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "image/png",
            "image/jpeg",
            "image/tiff",
        }

        if mime_type not in supported_types:
            logger.warning(f"Unsupported MIME type for Pawa: {mime_type}")

        return ParsedDocument(
            content=_MOCK_DOCUMENT_PARSED.content,
            mime_type=mime_type,
            pages=_MOCK_DOCUMENT_PARSED.pages,
            tables=_MOCK_DOCUMENT_PARSED.tables,
            metadata={
                **_MOCK_DOCUMENT_PARSED.metadata,
                "filename": filename,
                "provider": "pawa",
                "swahili_extracted": True,
            },
            confidence=0.92,
        )

    # ── Embeddings ───────────────────────────────────────────────────────

    async def embed(
        self,
        text: str | list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        """Generate embeddings via Pawa (mock)."""
        if isinstance(text, str):
            text = [text]
        logger.debug(f"PawaProvider.embed: {len(text)} texts")
        # Return mock 500-dimensional embeddings
        return [_MOCK_EMBEDDING for _ in text]

    # ── Streaming ────────────────────────────────────────────────────────

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat response from Pawa (mock)."""
        logger.debug(f"PawaProvider.stream_chat: {len(messages)} messages")

        # Simulate streaming by yielding chunks
        response_text = _MOCK_CHAT_RESPONSE
        words = response_text.split()

        # Yield ~5 words per chunk
        for i in range(0, len(words), 5):
            chunk_text = " ".join(words[i : i + 5])
            if i + 5 < len(words):
                chunk_text += " "
            yield StreamChunk(
                content=chunk_text,
                finish_reason=None,
                metadata={"provider": "pawa"},
            )

        # Final chunk
        yield StreamChunk(
            content="",
            finish_reason="stop",
            metadata={"provider": "pawa", "usage": {"total_tokens": 300}},
        )

    # ── Pawa-specific methods ────────────────────────────────────────────

    async def knowledge_base_search(
        self,
        query: str,
        org_id: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search the organization's knowledge base via Pawa RAG (mock)."""
        logger.debug(f"PawaProvider.kb_search: query='{query}', org_id={org_id}")
        return [
            {
                "content": "Monthly revenue summary for Q2 2024 shows 15% growth in electronics sales.",
                "source": "reports/q2_summary.pdf",
                "score": 0.92,
                "metadata": {"page": 3, "section": "Revenue Analysis"},
            },
            {
                "content": "Outstanding receivables total TZS 2,300,000 as of August 2024.",
                "source": "reports/receivables_aug2024.pdf",
                "score": 0.87,
                "metadata": {"page": 1, "section": "Accounts Receivable"},
            },
            {
                "content": "Customer Serengeti Trading has consistently paid on time for the last 6 months.",
                "source": "contacts/serengeti_trading.json",
                "score": 0.78,
                "metadata": {"type": "customer_profile"},
            },
        ]

    async def classify_transaction(
        self,
        description: str,
        amount: float,
        currency: str = "TZS",
    ) -> dict[str, Any]:
        """Auto-classify a transaction using Pawa's categorization (mock)."""
        logger.debug(f"PawaProvider.classify: '{description}' {amount} {currency}")
        return {
            "category": "Sales Revenue",
            "subcategory": "Electronics",
            "confidence": 0.91,
            "account_code": "4000",
            "tax_applicable": True,
            "vat_rate": 0.18,
        }

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "sw",
    ) -> str:
        """Translate text using Pawa's Swahili model (mock)."""
        logger.debug(f"PawaProvider.translate: {source_lang} -> {target_lang}")
        if target_lang == "sw":
            return "Mapato ya mwezi huu ni TZS 12,500,000, ongezeko la 15%."
        return text

    async def health_check(self) -> bool:
        """Check Pawa API connectivity."""
        if self._mock_mode:
            return True
        # TODO: Real health check when API is integrated
        return True
