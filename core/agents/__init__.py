"""
Layer 4 agent implementations.

Exports factory functions for creating configured agents:
- RouterAgent: Parse user asks into structured constraints
- PlannerAgent: Build StrategySpec with tool orchestration (ReasoningTools + HTTP tools)
- NarratorAgent: Explain with citations (agentic RAG)
"""

from .router import create_router_agent
from .planner import create_planner_agent
from .narrator import create_narrator_agent

__all__ = [
    "create_router_agent",
    "create_planner_agent",
    "create_narrator_agent",
]
