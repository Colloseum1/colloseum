"""
HTTP tool wrappers for Layer 4 agents.

Exports 5 tools for agent-to-service communication:
- get_signals: Fetch signal data from Layer 3
- validate: Validate StrategySpec schema and policy
- compile_spec: Compile StrategySpec to PlanGraph
- simulate: Run backtest simulation
- ch_query: Execute ClickHouse queries (PIT-only)
"""

from .http_tools import (
    get_signals,
    validate,
    compile_spec,
    simulate,
    ch_query,
)

__all__ = [
    "get_signals",
    "validate",
    "compile_spec",
    "simulate",
    "ch_query",
]
