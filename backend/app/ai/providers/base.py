"""
Re-exports from the canonical base module for backward compatibility.

All new code should import from `app.ai.base` directly.
"""

from app.ai.base import (
    AIProvider,
    AIResponse,
    AIRouter,
    ParsedDocument,
    ProviderCapability,
    StreamChunk,
    TaskType,
    airouter,
)

__all__ = [
    "AIProvider",
    "AIResponse",
    "AIRouter",
    "ParsedDocument",
    "ProviderCapability",
    "StreamChunk",
    "TaskType",
    "airouter",
]
