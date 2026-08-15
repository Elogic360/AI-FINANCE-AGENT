"""
Abstract AI Provider base class for FinPilot AI.

Defines the canonical interface that all AI providers must implement.
Providers handle chat, document parsing, embeddings, and streaming.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


# ── Enums ──────────────────────────────────────────────────────────────────

class TaskType(str, Enum):
    """Types of AI tasks the system can perform."""
    CHAT = "chat"
    DOCUMENT_PARSE = "document_parse"
    EMBED = "embed"
    STREAM_CHAT = "stream_chat"
    VISION_OCR = "vision_ocr"
    KB_SEARCH = "kb_search"
    CATEGORIZE = "categorize"
    FORECAST = "forecast"
    VALIDATE = "validate"
    SWAHILI = "swahili"


class ProviderCapability(str, Enum):
    """Capabilities that a provider can declare."""
    CHAT = "chat"
    DOCUMENT_PARSE = "document_parse"
    EMBEDDINGS = "embeddings"
    STREAMING = "streaming"
    VISION = "vision"
    TOOL_CALLING = "tool_calling"
    KNOWLEDGE_BASE = "knowledge_base"
    SWAHILI = "swahili"
    AGENT_ORCHESTRATION = "agent_orchestration"


# ── Response models ────────────────────────────────────────────────────────

@dataclass
class AIResponse:
    """Standardized response from any AI provider."""
    provider: str
    task_type: TaskType
    result: Any
    confidence: float = 0.0
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: dict | None = None


@dataclass
class ParsedDocument:
    """Result of document parsing."""
    content: str
    mime_type: str
    pages: int = 0
    tables: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class StreamChunk:
    """A single chunk from a streaming response."""
    content: str
    finish_reason: str | None = None
    tool_calls: list[dict] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Abstract base class ───────────────────────────────────────────────────

class AIProvider(ABC):
    """
    Abstract base class for all AI providers.

    Every provider must implement:
    - chat(): Send messages and get a response (with optional tool calling)
    - parse_document(): Extract content from uploaded files
    - embed(): Generate vector embeddings for text
    - stream_chat(): Async generator for streaming responses

    Providers declare their capabilities via `capabilities` property.
    The orchestrator uses this to route requests to the right provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'pawa', 'gemini')."""
        ...

    @property
    def capabilities(self) -> set[ProviderCapability]:
        """Set of capabilities this provider supports. Override in subclass."""
        return set()

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AIResponse:
        """
        Send a chat completion request.

        Args:
            messages: Conversation history as [{role, content, ...}]
            tools: Optional tool definitions for function calling
            temperature: Sampling temperature (0.0–1.0)
            max_tokens: Maximum tokens in the response

        Returns:
            AIResponse with the model's reply and any tool calls.
        """
        ...

    @abstractmethod
    async def parse_document(
        self,
        file_content: bytes,
        mime_type: str,
        filename: str = "",
        **kwargs: Any,
    ) -> ParsedDocument:
        """
        Parse a document and extract its content.

        Args:
            file_content: Raw file bytes
            mime_type: MIME type (e.g. 'application/pdf')
            filename: Original filename

        Returns:
            ParsedDocument with extracted text, tables, and metadata.
        """
        ...

    @abstractmethod
    async def embed(
        self,
        text: str | list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        """
        Generate vector embeddings for text.

        Args:
            text: Single string or list of strings to embed

        Returns:
            List of embedding vectors (one per input string).
        """
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """
        Streaming chat completion.

        Args:
            messages: Conversation history
            tools: Optional tool definitions
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Yields:
            StreamChunk objects as the response is generated.
        """
        ...

    def supports(self, task_type: TaskType) -> bool:
        """Check if this provider supports a given task type."""
        cap_map = {
            TaskType.CHAT: ProviderCapability.CHAT,
            TaskType.STREAM_CHAT: ProviderCapability.STREAMING,
            TaskType.DOCUMENT_PARSE: ProviderCapability.DOCUMENT_PARSE,
            TaskType.EMBED: ProviderCapability.EMBEDDINGS,
            TaskType.VISION_OCR: ProviderCapability.VISION,
            TaskType.KB_SEARCH: ProviderCapability.KNOWLEDGE_BASE,
            TaskType.SWAHILI: ProviderCapability.SWAHILI,
        }
        required_cap = cap_map.get(task_type)
        if required_cap is None:
            return True
        return required_cap in self.capabilities

    async def health_check(self) -> bool:
        """Quick connectivity check. Override for provider-specific logic."""
        return True


# ── Router (legacy compatibility) ─────────────────────────────────────────

class AIRouter:
    """
    Routes AI tasks to the appropriate provider with fallback.
    Kept for backward compatibility — prefer using AIOrchestrator.
    """

    def __init__(self) -> None:
        self._providers: list[AIProvider] = []

    def register(self, provider: AIProvider) -> None:
        self._providers.append(provider)
        logger.info(f"Registered AI provider: {provider.name}")

    async def route(self, task_type: TaskType, payload: dict) -> AIResponse:
        for provider in self._providers:
            if provider.supports(task_type):
                try:
                    return await provider.execute(task_type, payload)
                except Exception as e:
                    logger.warning(f"Provider {provider.name} failed for {task_type}: {e}")
                    continue
        raise RuntimeError(f"No AI provider available for task type: {task_type}")


# Global singleton router (legacy)
airouter = AIRouter()
