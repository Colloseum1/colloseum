"""
Simple session monitoring for Layer 4 Team.

Exports metrics tracking functions and AgnoInstrumentor setup.
"""

from .metrics import (
    # Initialization
    initialize_agno_instrumentation,

    # Tracking functions
    track_session_start,
    track_session_end,
    track_team_run,

    # Context manager
    track_team_execution,

    # Metrics endpoint
    get_metrics,

    # Debugging
    print_metrics_summary,

    # Raw metrics (for advanced usage)
    session_count,
    sessions_total,
    team_runs_total,
    team_run_duration_seconds,
)

__all__ = [
    # Initialization
    "initialize_agno_instrumentation",

    # Tracking functions
    "track_session_start",
    "track_session_end",
    "track_team_run",

    # Context manager
    "track_team_execution",

    # Metrics endpoint
    "get_metrics",

    # Debugging
    "print_metrics_summary",

    # Raw metrics
    "session_count",
    "sessions_total",
    "team_runs_total",
    "team_run_duration_seconds",
]
