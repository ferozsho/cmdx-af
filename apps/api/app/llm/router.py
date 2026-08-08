"""Model Router for Selecting Appropriate LLM Provider."""

from app.core.config import settings, get_setting
from app.llm.base import BaseLLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.llm.mock import MockLLMProvider
from app.llm.tracking import UsageTrackingProvider


class ModelRouter:
    """Selects and returns configured LLM Provider based on system settings."""

    @classmethod
    def get_provider(cls, capability: str = "reasoning") -> BaseLLMProvider:
        """Get LLM Provider instance according to APP_MODE and capability."""
        api_key = get_setting("DEEPSEEK_API_KEY", settings.DEEPSEEK_API_KEY)
        base_url = get_setting("DEEPSEEK_BASE_URL", settings.DEEPSEEK_BASE_URL)

        if settings.APP_MODE == "mock" or not api_key:
            provider: BaseLLMProvider = MockLLMProvider()
        else:
            provider = DeepSeekProvider(api_key=api_key, base_url=base_url)

        # Wrap with usage tracking so every call is persisted to llm_usage
        return UsageTrackingProvider(provider)
