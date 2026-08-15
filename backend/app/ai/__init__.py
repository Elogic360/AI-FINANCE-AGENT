"""
FinPilot AI — Provider abstraction layer.

This package provides:
- Base classes for AI providers (base.py)
- Provider implementations: Pawa, Gemini (providers/)
- Tool definitions for AI agents (tools.py)
- Agent definitions for specialized financial AI (agents.py)
- Orchestrator for routing requests (orchestrator.py)
"""

from app.ai.base import (
    AIProvider,
    AIResponse,
    AIRouter,
    ParsedDocument,
    ProviderCapability,
    StreamChunk,
    TaskType,
)
from app.ai.providers.pawa import PawaProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.agents import (
    AgentDefinition,
    AGENT_REGISTRY,
    ALL_AGENTS,
    CFO_AGENT,
    DOCUMENT_AGENT,
    ACCOUNTING_AGENT,
    FINANCIAL_ANALYST_AGENT,
    FORECAST_AGENT,
    AUDIT_AGENT,
    BUSINESS_ADVISOR_AGENT,
)
from app.ai.orchestrator import AIOrchestrator, orchestrator
from app.ai.tools import TOOL_REGISTRY, TOOL_DEFINITIONS

__all__ = [
    # Base
    "AIProvider",
    "AIResponse",
    "AIRouter",
    "ParsedDocument",
    "ProviderCapability",
    "StreamChunk",
    "TaskType",
    # Providers
    "PawaProvider",
    "GeminiProvider",
    # Agents
    "AgentDefinition",
    "AGENT_REGISTRY",
    "ALL_AGENTS",
    "CFO_AGENT",
    "DOCUMENT_AGENT",
    "ACCOUNTING_AGENT",
    "FINANCIAL_ANALYST_AGENT",
    "FORECAST_AGENT",
    "AUDIT_AGENT",
    "BUSINESS_ADVISOR_AGENT",
    # Orchestrator
    "AIOrchestrator",
    "orchestrator",
    # Tools
    "TOOL_REGISTRY",
    "TOOL_DEFINITIONS",
]
