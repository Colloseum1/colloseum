"""
OpenTelemetry Observability for Layer 4 (Task 9).

Distributed tracing with Langfuse integration for complete visibility into:
- Agent runs (Router, Planner, Narrator)
- Tool executions (validate, compile, simulate, ch_query, get_signals)
- LLM calls (token usage, latency, errors)
- Team orchestration flow

Usage:
    from core.observability import initialize_observability

    # At application startup (ONCE)
    initialize_observability()

    # Now all team runs, agent executions, and tool calls are automatically traced!
"""

from .instrumentation import (
    initialize_observability,
    is_observability_enabled,
    get_tracer,
    shutdown_observability,
)

__all__ = [
    "initialize_observability",
    "is_observability_enabled",
    "get_tracer",
    "shutdown_observability",
]
