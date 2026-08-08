"""Agent Name → Class Registry.

Maps agent template names (as stored in agent_templates.name) to their
corresponding Python classes so the pipeline can instantiate the right
agent for each per-project configuration.
"""

from app.agents.architecture import ArchitectureAgent
from app.agents.backend import BackendAgent
from app.agents.base import BaseAgent
from app.agents.database import DatabaseAgent
from app.agents.documentation import DocumentationAgent
from app.agents.frontend import FrontendAgent
from app.agents.git_agent import GitAgent
from app.agents.planning import PlanningAgent
from app.agents.test_agent import TestAgent
from app.agents.ui_ux import UIUXAgent
from app.agents.validation import ValidationAgent
from app.agents.visual_analysis import VisualAnalysisAgent

# Maps AgentTemplate.name → agent class (subclass of BaseAgent).
# Names MUST match those seeded in seed_agents.py.
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "Planning Agent": PlanningAgent,
    "Architecture Agent": ArchitectureAgent,
    "Visual Analysis Agent": VisualAnalysisAgent,
    "UI/UX Agent": UIUXAgent,
    "Documentation Agent": DocumentationAgent,
    "Frontend Agent": FrontendAgent,
    "Backend Agent": BackendAgent,
    "Database Agent": DatabaseAgent,
    "Test Agent": TestAgent,
    "Validation Agent": ValidationAgent,
    "Git Agent": GitAgent,
}

# Default sort order for the hardcoded fallback (when no ProjectAgent rows exist).
DEFAULT_AGENT_ORDER: list[str] = list(AGENT_REGISTRY.keys())
