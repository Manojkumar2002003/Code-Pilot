"""CodePilot AI Agents package.

Contains core specialized agents that translate user concepts, project context,
and code repositories into requirements, architectures, and tasks.
"""

from app.agents.prompts import (
    REQUIREMENT_ANALYST_SYSTEM_INITIAL,
    REQUIREMENT_ANALYST_SYSTEM_REFINEMENT,
    REQUIREMENT_ANALYST_SYSTEM_REGENERATION,
    REQUIREMENT_ANALYST_SYSTEM_REPAIR,
    build_analyst_user_prompt,
    build_repair_feedback_prompt,
    get_analyst_system_instruction,
)
from app.agents.requirement_analyst import RequirementAnalystAgent

# Service alias for backward-compatible DI conventions
RequirementAnalystService = RequirementAnalystAgent

__all__ = [
    "RequirementAnalystAgent",
    "RequirementAnalystService",
    "REQUIREMENT_ANALYST_SYSTEM_INITIAL",
    "REQUIREMENT_ANALYST_SYSTEM_REFINEMENT",
    "REQUIREMENT_ANALYST_SYSTEM_REGENERATION",
    "REQUIREMENT_ANALYST_SYSTEM_REPAIR",
    "get_analyst_system_instruction",
    "build_analyst_user_prompt",
    "build_repair_feedback_prompt",
]
