import httpx
import logging
from app.ai.providers.base import AIProvider, AIResponse, TaskType
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PawaProvider(AIProvider):
    """Pawa AI — Africa-first document parsing, KB/RAG, Swahili, agents, voice."""

    @property
    def name(self) -> str:
        return "pawa"

    def supports(self, task_type: TaskType) -> bool:
        return task_type in {
            TaskType.DOCUMENT_PARSE,
            TaskType.KB_SEARCH,
            TaskType.CHAT,
            TaskType.CATEGORIZE,
            TaskType.SWAHILI,
        }

    async def execute(self, task_type: TaskType, payload: dict) -> AIResponse:
        if not settings.PAWA_API_KEY:
            raise RuntimeError("PAWA_API_KEY not configured")

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.PAWA_API_URL}/v1/{task_type.value}",
                headers={"Authorization": f"Bearer {settings.PAWA_API_KEY}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return AIResponse(
            provider="pawa",
            task_type=task_type,
            result=data.get("result", data),
            confidence=data.get("confidence", 0.0),
            raw=data,
        )
