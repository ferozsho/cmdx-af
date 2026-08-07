"""Seed default agent templates into the database."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.repositories.agent_template_repo import AgentTemplateRepository
from app.core.config import settings

DEFAULT_AGENTS = [
    {
        "name": "Planning Agent",
        "description": "Analyzes user instructions and creates a detailed implementation plan with tasks and estimates.",
        "capability": "reasoning",
        "system_prompt": "You are a senior software planning agent. Break down requirements into actionable implementation steps.",
        "tools": ["analyze_requirements", "create_plan", "estimate_effort"],
    },
    {
        "name": "Architecture Agent",
        "description": "Designs system architecture, component relationships, and data flow diagrams.",
        "capability": "reasoning",
        "system_prompt": "You are a system architecture agent. Design scalable, maintainable system architectures.",
        "tools": ["design_architecture", "create_diagrams", "define_components"],
    },
    {
        "name": "Visual Analysis Agent",
        "description": "Analyzes visual designs, screenshots, and UI mockups for implementation guidance.",
        "capability": "analysis",
        "system_prompt": "You are a visual analysis agent. Extract design specifications from visual assets.",
        "tools": ["analyze_image", "extract_styles", "generate_specs"],
    },
    {
        "name": "UI/UX Agent",
        "description": "Designs user interfaces and user experiences following best practices.",
        "capability": "coding",
        "system_prompt": "You are a UI/UX design agent. Create beautiful, accessible user interfaces.",
        "tools": ["design_ui", "create_components", "accessibility_check"],
    },
    {
        "name": "Documentation Agent",
        "description": "Generates comprehensive documentation for code, APIs, and project setup.",
        "capability": "reasoning",
        "system_prompt": "You are a documentation agent. Create clear, comprehensive technical documentation.",
        "tools": ["generate_docs", "create_readme", "api_documentation"],
    },
    {
        "name": "Frontend Agent",
        "description": "Implements frontend components, pages, and client-side logic.",
        "capability": "coding",
        "system_prompt": "You are a frontend development agent. Build responsive, performant frontend code.",
        "tools": ["read_file", "write_file", "search_code", "npm_install", "npm_run"],
    },
    {
        "name": "Backend Agent",
        "description": "Implements backend APIs, services, and server-side business logic.",
        "capability": "coding",
        "system_prompt": "You are a backend development agent. Build robust, secure backend services.",
        "tools": ["read_file", "write_file", "search_code", "run_tests"],
    },
    {
        "name": "Database Agent",
        "description": "Designs database schemas, migrations, and optimized queries.",
        "capability": "coding",
        "system_prompt": "You are a database design agent. Create efficient, normalized database schemas.",
        "tools": ["create_migration", "design_schema", "optimize_query"],
    },
    {
        "name": "Test Agent",
        "description": "Writes and runs unit tests, integration tests, and test suites.",
        "capability": "testing",
        "system_prompt": "You are a testing agent. Write comprehensive tests with high coverage.",
        "tools": ["run_pytest", "run_jest", "coverage_report"],
    },
    {
        "name": "Validation Agent",
        "description": "Validates code quality, security, formatting, and best practices.",
        "capability": "validation",
        "system_prompt": "You are a validation agent. Ensure code meets quality and security standards.",
        "tools": ["run_ruff", "run_mypy", "run_bandit", "check_format"],
    },
    {
        "name": "Git Agent",
        "description": "Manages version control operations including commits, branches, and PRs.",
        "capability": "git",
        "system_prompt": "You are a git operations agent. Manage version control with clean commit history.",
        "tools": ["git_commit", "git_branch", "git_status", "git_diff"],
    },
]


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        repo = AgentTemplateRepository(db)
        existing = await repo.list_all()
        if existing:
            print(f"Skipping seed: {len(existing)} agent templates already exist.")
            return

        for agent_data in DEFAULT_AGENTS:
            template = await repo.create(**agent_data)
            print(f"Created: {template.name} (v{template.version})")

        print(f"Seeded {len(DEFAULT_AGENTS)} default agent templates.")


if __name__ == "__main__":
    asyncio.run(seed())
