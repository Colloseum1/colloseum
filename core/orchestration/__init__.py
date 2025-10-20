"""
Team Orchestration for Layer 4.

Exports team creation and management functions for coordinating
Router -> Planner -> Narrator pipeline.
"""

from .team import (
    create_strategy_team,
    run_strategy_team,
    run_strategy_team_async,
    get_team_session_summary,
    get_team_chat_history,
    set_team_session_name,
)

__all__ = [
    "create_strategy_team",
    "run_strategy_team",
    "run_strategy_team_async",
    "get_team_session_summary",
    "get_team_chat_history",
    "set_team_session_name",
]
