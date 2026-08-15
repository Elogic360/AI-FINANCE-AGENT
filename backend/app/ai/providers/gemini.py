import httpx
import logging
from app.ai.providers.base import AIProvider, AIResponse, TaskType
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiProvider(AIProvider):
    """Gemini — complex PDF/vision, charts/tables, fallback provider."""

    @property
    def name(self) -> str:
        return "gemini"

    def supports(self, task_type: TaskType) -> bool:
        return task_type in {
            TaskType.VISION_OCR,
            TaskType.DOCUMENT_PARSE,
            TaskType.FORECAST,
            TaskType.VALIDATE,
        }

    async def execute(self, task_type: TaskType, payload: dict) -> AIResponse:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not configured")

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                params={"key": settings.GEMINI_API_KEY},
                json={
                    "contents": [{"parts": [{"text": payload.get("prompt", "")}]}],
                    "generationConfig": {"temperature": 0.1},
                },
            )
            response.raise_for_status()
            data = response.json()

        result_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        return AIResponse(
            provider="gemini",
            task_type=task_type,
            result=result_text,
            confidence=0.85,
            raw=data,
        )
