"""Requirement Analyst Service facade for CodePilot.

Delegates to the core agent implementation in app.agents.requirement_analyst.
"""

from app.agents.prompts import (
    REQUIREMENT_ANALYST_SYSTEM_INITIAL as DEFAULT_SYSTEM_INSTRUCTION_INITIAL,
    REQUIREMENT_ANALYST_SYSTEM_REFINEMENT as DEFAULT_SYSTEM_INSTRUCTION_REFINEMENT,
    REQUIREMENT_ANALYST_SYSTEM_REGENERATION as DEFAULT_SYSTEM_INSTRUCTION_REGENERATION,
)
from app.agents.requirement_analyst import RequirementAnalystAgent

# Service alias pointing to the core agent
RequirementAnalystService = RequirementAnalystAgent

__all__ = [
    "RequirementAnalystAgent",
    "RequirementAnalystService",
    "DEFAULT_SYSTEM_INSTRUCTION_INITIAL",
    "DEFAULT_SYSTEM_INSTRUCTION_REFINEMENT",
    "DEFAULT_SYSTEM_INSTRUCTION_REGENERATION",
]
