"""Base Agent Class."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from app.llm.router import ModelRouter


class BaseAgent(ABC):
    """Abstract base class for specialized software development agents."""

    def __init__(self, agent_name: str, capability: str = "reasoning") -> None:
        self.agent_name = agent_name
        self.provider = ModelRouter.get_provider(capability)

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task and return result dictionary."""
        pass
