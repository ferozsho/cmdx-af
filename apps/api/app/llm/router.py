"""Model Router for Selecting Appropriate LLM Provider."""

from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.llm.mock import MockLLMProvider


class ModelRouter:
    """Selects and returns configured LLM Provider based on system settings."""

    @classmethod
    def get_provider(cls, capability: str = "reasoning") -> BaseLLMProvider:
        """Get LLM Provider instance according to APP_MODE and requested capability."""
        if settings.APP_MODE == "mock" or not settings.DEEPSEEK_API_KEY:
            return MockLLMProvider()

        return DeepSeekProvider(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
