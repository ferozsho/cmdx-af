"""Model Router for Selecting Appropriate LLM Provider."""

from app.core.config import (
    DEFAULT_DEEPSEEK_BASE_URL,
    get_setting,
    settings,
)
from app.llm.base import BaseLLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.llm.openai import OpenAIProvider
from app.llm.gemini import GeminiProvider
from app.llm.claude import ClaudeProvider
from app.llm.mock import MockLLMProvider
from app.llm.tracking import UsageTrackingProvider

# Model name prefix → provider routing map
MODEL_PREFIX_MAP = {
    "deepseek": "deepseek",
    "gpt": "openai",
    "gemini": "gemini",
    "claude": "claude",
}

# Full model registry: model_name → {provider, context_limit, vision, label}
MODEL_REGISTRY = {
    "deepseek-chat": {
        "provider": "deepseek",
        "context_limit": 65536,
        "vision": False,
        "label": "DeepSeek-V3",
    },
    "deepseek-coder": {
        "provider": "deepseek",
        "context_limit": 131072,
        "vision": False,
        "label": "DeepSeek-Coder",
    },
    "deepseek-reasoner": {
        "provider": "deepseek",
        "context_limit": 65536,
        "vision": False,
        "label": "DeepSeek-R1",
    },
    "gpt-4o": {
        "provider": "openai",
        "context_limit": 131072,
        "vision": True,
        "label": "GPT-4o",
    },
    "gpt-4-turbo": {
        "provider": "openai",
        "context_limit": 131072,
        "vision": True,
        "label": "GPT-4 Turbo",
    },
    "gpt-3.5-turbo": {
        "provider": "openai",
        "context_limit": 16385,
        "vision": False,
        "label": "GPT-3.5 Turbo",
    },
    "gemini-2.5-pro": {
        "provider": "gemini",
        "context_limit": 1048576,
        "vision": True,
        "label": "Gemini 2.5 Pro",
    },
    "gemini-2.5-flash": {
        "provider": "gemini",
        "context_limit": 1048576,
        "vision": True,
        "label": "Gemini 2.5 Flash",
    },
    "gemini-1.5-pro": {
        "provider": "gemini",
        "context_limit": 2097152,
        "vision": True,
        "label": "Gemini 1.5 Pro",
    },
    "claude-3.5-sonnet": {
        "provider": "claude",
        "context_limit": 204800,
        "vision": True,
        "label": "Claude 3.5 Sonnet",
    },
    "claude-3-5-sonnet-20241022": {
        "provider": "claude",
        "context_limit": 204800,
        "vision": True,
        "label": "Claude 3.5 Sonnet",
    },
    "claude-3-opus": {
        "provider": "claude",
        "context_limit": 204800,
        "vision": True,
        "label": "Claude 3 Opus",
    },
    "claude-3-haiku": {
        "provider": "claude",
        "context_limit": 204800,
        "vision": True,
        "label": "Claude 3 Haiku",
    },
}


def get_model_list() -> list[dict]:
    """Return all registered models for frontend dropdowns."""
    return [
        {
            "name": name,
            "provider": info["provider"],
            "context_limit": info["context_limit"],
            "vision": info["vision"],
            "label": info["label"],
        }
        for name, info in MODEL_REGISTRY.items()
    ]


def is_vision_model(model_name: str | None) -> bool:
    """Check if a model supports vision/image analysis."""
    if model_name and model_name in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_name].get("vision", False)
    return False


def _resolve_provider_name(model_name: str | None) -> str:
    """Determine which provider to use based on model name prefix."""
    if not model_name:
        return "deepseek"
    for prefix, provider in MODEL_PREFIX_MAP.items():
        if model_name.startswith(prefix):
            return provider
    return "deepseek"


def get_context_limit(model_name: str | None) -> int:
    """Get the context window token limit for a given model."""
    if model_name and model_name in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_name]["context_limit"]
    return 65536


class ModelRouter:
    """Selects and returns configured LLM Provider based on model name."""

    @classmethod
    def get_provider(
        cls, model_name: str | None = None
    ) -> BaseLLMProvider:
        """Get LLM Provider instance based on model name prefix routing.

        Model name determines provider: gpt-* → OpenAI, gemini-* → Gemini,
        claude-* → Claude, deepseek-* → DeepSeek (default).
        Falls back to MockLLMProvider if no API key is configured for the
        selected provider.
        """
        provider_name = _resolve_provider_name(model_name)

        if settings.APP_MODE == "mock":
            return UsageTrackingProvider(MockLLMProvider())

        if provider_name == "openai":
            api_key = get_setting("OPENAI_API_KEY", "")
            if not api_key:
                return UsageTrackingProvider(MockLLMProvider())
            base_url = get_setting(
                "OPENAI_BASE_URL", "https://api.openai.com/v1"
            )
            return UsageTrackingProvider(
                OpenAIProvider(api_key=api_key, base_url=base_url)
            )

        if provider_name == "gemini":
            api_key = get_setting("GEMINI_API_KEY", "")
            if not api_key:
                return UsageTrackingProvider(MockLLMProvider())
            return UsageTrackingProvider(GeminiProvider(api_key=api_key))

        if provider_name == "claude":
            api_key = get_setting("CLAUDE_API_KEY", "")
            if not api_key:
                return UsageTrackingProvider(MockLLMProvider())
            return UsageTrackingProvider(ClaudeProvider(api_key=api_key))

        # Default: DeepSeek
        api_key = get_setting("DEEPSEEK_API_KEY", "")
        if not api_key:
            return UsageTrackingProvider(MockLLMProvider())
        base_url = get_setting(
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        )
        return UsageTrackingProvider(
            DeepSeekProvider(api_key=api_key, base_url=base_url)
        )
