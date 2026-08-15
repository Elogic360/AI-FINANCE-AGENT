from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    DOCUMENT_PARSE = "document_parse"
    VISION_OCR = "vision_ocr"
    KB_SEARCH = "kb_search"
    CHAT = "chat"
    CATEGORIZE = "categorize"
    FORECAST = "forecast"
    VALIDATE = "validate"
    SWAHILI = "swahili"


@dataclass
class AIResponse:
    provider: str
    task_type: TaskType
    result: Any
    confidence: float
    raw: dict | None = None


class AIProvider(ABC):
    """Base interface for all AI providers. Never call vendors directly — always through AIRouter."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def execute(self, task_type: TaskType, payload: dict) -> AIResponse: ...

    @abstractmethod
    def supports(self, task_type: TaskType) -> bool: ...


class AIRouter:
    """Routes AI tasks to the appropriate provider with fallback."""

    def __init__(self):
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


# Global singleton
airouter = AIRouter()
