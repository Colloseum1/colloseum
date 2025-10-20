"""
Simple session monitoring metrics for Layer 4 Team.

Provides basic Prometheus-style metrics for tracking team execution health:
- Session counts (active, total)
- Team run counts (success, failure)
- Agent-level metrics (via AgnoInstrumentor automatic instrumentation)

This is Task 8.4: Simplified metrics with minimal custom implementation.
For full observability (distributed tracing, Langfuse), see Task 9.
"""

import time
from typing import Optional
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest

from openinference.instrumentation.agno import AgnoInstrumentor


# ============================================================================
# Prometheus Registry
# ============================================================================

# Use custom registry to avoid conflicts with other Prometheus instances
METRICS_REGISTRY = CollectorRegistry()


# ============================================================================
# Session Metrics (Simple Gauges/Counters)
# ============================================================================

# Gauge: Current number of active sessions
session_count = Gauge(
    name="layer4_active_sessions",
    documentation="Number of active Layer 4 team sessions",
    registry=METRICS_REGISTRY,
)

# Counter: Total sessions created
sessions_total = Counter(
    name="layer4_sessions_total",
    documentation="Total number of Layer 4 team sessions created",
    labelnames=["user_id"],
    registry=METRICS_REGISTRY,
)


# ============================================================================
# Team Run Metrics
# ============================================================================

# Counter: Total team runs
team_runs_total = Counter(
    name="layer4_team_runs_total",
    documentation="Total number of team runs executed",
    labelnames=["status"],  # success, error
    registry=METRICS_REGISTRY,
)

# Histogram: Team run duration
team_run_duration_seconds = Histogram(
    name="layer4_team_run_duration_seconds",
    documentation="Duration of team runs in seconds",
    labelnames=["status"],
    registry=METRICS_REGISTRY,
    buckets=(1, 5, 10, 30, 60, 120, 300),  # 1s to 5min
)


# ============================================================================
# AgnoInstrumentor Setup (ONE LINE!)
# ============================================================================

_instrumentation_enabled = False


def initialize_agno_instrumentation() -> None:
    """
    Initialize AgnoInstrumentor for automatic LLM observability.

    This is the SIMPLIFIED version for Task 8.4 - just enables automatic
    instrumentation without complex OTLP exporters or tracing configuration.

    AgnoInstrumentor provides automatic metrics for:
    - LLM token usage (prompt, completion, total)
    - LLM call latency
    - Tool execution counts and latency
    - Agent run success/failure rates

    Example:
        >>> # Call once at app startup
        >>> initialize_agno_instrumentation()
        >>>
        >>> # All subsequent agent/team runs are automatically instrumented!
        >>> team = create_strategy_team()
        >>> team.run("Build me a strategy")  # Metrics collected automatically
    """
    global _instrumentation_enabled

    if _instrumentation_enabled:
        print("⚠️  AgnoInstrumentation already initialized")
        return

    # ONE LINE setup for automatic instrumentation!
    AgnoInstrumentor().instrument()

    _instrumentation_enabled = True
    print("✓ AgnoInstrumentation initialized - automatic LLM metrics enabled!")


# ============================================================================
# Session Tracking Helpers
# ============================================================================

def track_session_start(session_id: str, user_id: Optional[str] = None) -> None:
    """
    Track the start of a new session.

    Args:
        session_id: Unique session identifier
        user_id: Optional user identifier for labeling

    Example:
        >>> track_session_start("session_123", "user_456")
    """
    session_count.inc()
    sessions_total.labels(user_id=user_id or "anonymous").inc()


def track_session_end(session_id: str) -> None:
    """
    Track the end of a session.

    Args:
        session_id: Unique session identifier

    Example:
        >>> track_session_end("session_123")
    """
    session_count.dec()


def track_team_run(status: str, duration_seconds: float) -> None:
    """
    Track a team run execution.

    Args:
        status: "success" or "error"
        duration_seconds: Run duration in seconds

    Example:
        >>> start = time.time()
        >>> # ... run team ...
        >>> track_team_run("success", time.time() - start)
    """
    team_runs_total.labels(status=status).inc()
    team_run_duration_seconds.labels(status=status).observe(duration_seconds)


# ============================================================================
# Context Manager for Automatic Tracking
# ============================================================================

class track_team_execution:
    """
    Context manager for automatic team run tracking.

    Automatically tracks:
    - Run duration
    - Success/failure status
    - Increments appropriate counters

    Example:
        >>> with track_team_execution():
        >>>     result = team.run("Build me a strategy")
        >>>
        >>> # On success: team_runs_total{status="success"} += 1
        >>> # On error: team_runs_total{status="error"} += 1
        >>> # Both: team_run_duration_seconds observed
    """

    def __init__(self):
        self.start_time = None
        self.status = "success"

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type is not None:
            self.status = "error"

        track_team_run(self.status, duration)

        # Return False to propagate exceptions
        return False


# ============================================================================
# Metrics Endpoint (for Prometheus scraping)
# ============================================================================

def get_metrics() -> bytes:
    """
    Get Prometheus-formatted metrics for scraping.

    Returns:
        Bytes in Prometheus text exposition format

    Example:
        >>> # In your FastAPI/Flask app:
        >>> @app.get("/metrics")
        >>> def metrics():
        >>>     return Response(get_metrics(), media_type="text/plain")
    """
    return generate_latest(METRICS_REGISTRY)


# ============================================================================
# Metrics Summary (for debugging)
# ============================================================================

def print_metrics_summary() -> None:
    """Print current metrics values for debugging."""
    print("=" * 70)
    print("Layer 4 Metrics Summary")
    print("=" * 70)
    print(f"Active Sessions: {session_count._value.get()}")

    # Print session totals by user
    session_totals = {}
    for metric in sessions_total.collect()[0].samples:
        user_id = metric.labels.get('user_id', 'unknown')
        session_totals[user_id] = metric.value
    print(f"Total Sessions by User: {session_totals}")

    # Print team run totals by status
    run_totals = {}
    for metric in team_runs_total.collect()[0].samples:
        status = metric.labels.get('status', 'unknown')
        run_totals[status] = metric.value
    print(f"Team Runs by Status: {run_totals}")

    print(f"AgnoInstrumentation: {'✓ Enabled' if _instrumentation_enabled else '✗ Disabled'}")
    print("=" * 70)
    print("\nFor full metrics output, call get_metrics() and expose via HTTP endpoint.")


# ============================================================================
# Auto-initialization on module import (OPTIONAL)
# ============================================================================

# You can enable auto-initialization by uncommenting this:
# initialize_agno_instrumentation()
#
# OR call it explicitly in your app startup:
# from core.monitoring.metrics import initialize_agno_instrumentation
# initialize_agno_instrumentation()
