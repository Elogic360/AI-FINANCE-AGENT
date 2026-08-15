"""
GeminiProvider — Google Gemini AI provider for FinPilot.

Capabilities:
- Multimodal reasoning (text + images)
- Complex document analysis
- Chart and table interpretation
- Vision-based OCR
- Chat completions with streaming

Uses google-generativeai or google-genai SDK.
API key from env var GEMINI_API_KEY.

All implementations are MOCK/STUB for development.
"""

import os
import uuid
import json
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
    "Based on your financial data analysis:\n\n"
    "**Revenue Trend**: Your revenue has grown 15% month-over-month, "
    "driven primarily by electronics sales (TZS 8.5M this month).\n\n"
    "**Cash Position**: Current cash balance is TZS 28.4M with a healthy "
    "current ratio of 2.3x.\n\n"
    "**Key Risks**:\n"
    "- TZS 2.3M in overdue receivables (30+ days)\n"
    "- Inventory holding costs increased 8%\n"
    "- Single supplier dependency for Samsung products\n\n"
    "**Recommendation**: Diversify supplier base and implement stricter "
    "credit terms for new customers."
)

_MOCK_VISION_RESPONSE = (
    "I've analyzed the uploaded receipt/invoice image:\n\n"
    "**Document Type**: Commercial Invoice\n"
    "**Vendor**: Kilimanjaro Electronics Ltd\n"
    "**Date**: 2024-08-15\n"
    "**Total Amount**: TZS 11,859,000 (including 18% VAT)\n\n"
    "**Line Items Detected**:\n"
    "1. Samsung Galaxy A54 x10 @ TZS 850,000 = TZS 8,500,000\n"
    "2. iPhone 15 Screen Protector x50 @ TZS 15,000 = TZS 750,000\n"
    "3. USB-C Charging Cable x100 @ TZS 8,000 = TZS 800,000\n\n"
    "The document appears to be a legitimate commercial invoice with "
    "proper TRA (Tanzania Revenue Authority) tax details."
)


# ── Provider implementation ────────────────────────────────────────────────

class GeminiProvider(AIProvider):
    """
    Google Gemini — complex PDF/vision, charts/tables, multimodal reasoning.

    MOCK implementation for development. Replace with real Gemini SDK calls
    when the integration is ready.

    SDK: google-generativeai
    Auth: GEMINI_API_KEY env var
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._mock_mode = not bool(self._api_key)
        if self._mock_mode:
            logger.info("GeminiProvider running in MOCK mode (no GEMINI_API_KEY set)")

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def capabilities(self) -> set[ProviderCapability]:
        return {
            ProviderCapability.CHAT,
            ProviderCapability.DOCUMENT_PARSE,
            ProviderCapability.EMBEDDINGS,
            ProviderCapability.STREAMING,
            ProviderCapability.VISION,
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
        """Send a chat request to Gemini (mock)."""
        logger.debug(f"GeminiProvider.chat: {len(messages)} messages, tools={bool(tools)}")

        # Check if this is a vision request (has image parts)
        has_image = False
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image":
                        has_image = True
                        break

        # Mock tool call
        if tools:
            tool_calls = [
                {
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": "get_revenue",
                        "arguments": json.dumps({"org_id": "mock-org-001", "period": "month"}),
                    },
                }
            ]
            return AIResponse(
                provider="gemini",
                task_type=TaskType.CHAT,
                result="",
                confidence=0.92,
                usage={"prompt_tokens": 320, "completion_tokens": 150, "total_tokens": 470},
                metadata={"tool_calls": tool_calls, "finish_reason": "tool_calls"},
                raw={"mock": True},
            )

        result = _MOCK_VISION_RESPONSE if has_image else _MOCK_CHAT_RESPONSE
        return AIResponse(
            provider="gemini",
            task_type=TaskType.CHAT,
            result=result,
            confidence=0.90,
            usage={"prompt_tokens": 200, "completion_tokens": 180, "total_tokens": 380},
            metadata={"model": "gemini-1.5-pro", "vision": has_image},
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
        """Parse a document using Gemini's multimodal capabilities (mock)."""
        logger.debug(f"GeminiProvider.parse_document: {mime_type}, {filename}")

        # Gemini excels at complex PDFs with charts/images
        return ParsedDocument(
            content=(
                "FINANCIAL STATEMENT — Q2 2024\n"
                "Kilimanjaro Electronics Ltd\n\n"
                "Revenue: TZS 37,500,000 (+15% vs Q1)\n"
                "Cost of Goods Sold: TZS 22,500,000\n"
                "Gross Profit: TZS 15,000,000 (40% margin)\n"
                "Operating Expenses: TZS 8,200,000\n"
                "Net Profit: TZS 6,800,000\n\n"
                "Key Metrics:\n"
                "- Current Ratio: 2.3x\n"
                "- Debt-to-Equity: 0.4x\n"
                "- Return on Assets: 12.5%\n"
                "- Inventory Turnover: 4.2x"
            ),
            mime_type=mime_type,
            pages=3,
            tables=[
                {
                    "headers": ["Metric", "Q1 2024", "Q2 2024", "Change"],
                    "rows": [
                        ["Revenue", "TZS 32.6M", "TZS 37.5M", "+15%"],
                        ["Gross Profit", "TZS 12.8M", "TZS 15.0M", "+17%"],
                        ["Net Profit", "TZS 5.2M", "TZS 6.8M", "+31%"],
                    ],
                }
            ],
            metadata={
                "filename": filename,
                "provider": "gemini",
                "model": "gemini-1.5-pro",
                "multimodal": True,
            },
            confidence=0.93,
        )

    # ── Embeddings ───────────────────────────────────────────────────────

    async def embed(
        self,
        text: str | list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        """Generate embeddings via Gemini embedding model (mock)."""
        if isinstance(text, str):
            text = [text]
        logger.debug(f"GeminiProvider.embed: {len(text)} texts")
        # Gemini uses 768-dim embeddings
        mock_embedding = [0.0234, -0.0567, 0.0891, -0.0123, 0.0456] * 154  # 770 -> close to 768
        return [mock_embedding[:768] for _ in text]

    # ── Streaming ────────────────────────────────────────────────────────

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat response from Gemini (mock)."""
        logger.debug(f"GeminiProvider.stream_chat: {len(messages)} messages")

        response_text = _MOCK_CHAT_RESPONSE
        words = response_text.split()

        for i in range(0, len(words), 4):
            chunk_text = " ".join(words[i : i + 4])
            if i + 4 < len(words):
                chunk_text += " "
            yield StreamChunk(
                content=chunk_text,
                finish_reason=None,
                metadata={"provider": "gemini", "model": "gemini-1.5-pro"},
            )

        yield StreamChunk(
            content="",
            finish_reason="stop",
            metadata={"provider": "gemini", "usage": {"total_tokens": 380}},
        )

    # ── Gemini-specific methods ──────────────────────────────────────────

    async def analyze_image(
        self,
        image_content: bytes,
        prompt: str = "Analyze this financial document",
        mime_type: str = "image/png",
    ) -> AIResponse:
        """Analyze an image using Gemini's vision capabilities (mock)."""
        logger.debug(f"GeminiProvider.analyze_image: {mime_type}, prompt='{prompt[:50]}'")
        return AIResponse(
            provider="gemini",
            task_type=TaskType.VISION_OCR,
            result=_MOCK_VISION_RESPONSE,
            confidence=0.89,
            usage={"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700},
            metadata={"model": "gemini-1.5-pro-vision", "mime_type": mime_type},
            raw={"mock": True},
        )

    async def interpret_chart(
        self,
        image_content: bytes,
        question: str = "What does this chart show?",
    ) -> str:
        """Interpret a chart or graph image (mock)."""
        logger.debug(f"GeminiProvider.interpret_chart: question='{question}'")
        return (
            "The chart shows a monthly revenue trend for Kilimanjaro Electronics Ltd. "
            "Revenue increased steadily from TZS 28M in January to TZS 37.5M in June 2024, "
            "representing a 34% growth over 6 months. The steepest growth occurred in "
            "March-April (12% increase) coinciding with the Easter sales period."
        )

    async def health_check(self) -> bool:
        """Check Gemini API connectivity."""
        if self._mock_mode:
            return True
        # TODO: Real health check when SDK is integrated
        return True
