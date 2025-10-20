"""
Workflows for Layer 4 (Task 10).

Autonomous background processes for strategy generation and management.
"""

from .creative_engine import (
    create_creative_engine_workflow,
    run_creative_engine_once,
    run_creative_engine_sync,
    CREATIVE_ENGINE_CONFIG,
)

from .scheduler import (
    start_creative_engine_scheduler,
    stop_creative_engine_scheduler,
    is_scheduler_running,
    get_next_run_time,
    trigger_immediate_run,
    get_scheduler_status,
    cleanup_expired_strategies,
    start_cleanup_scheduler,
    SCHEDULER_CONFIG,
)

from .metrics import (
    get_creative_engine_metrics,
    print_creative_engine_metrics_summary,
    track_workflow_run,
    track_step_duration,
    track_candidate_generated,
    track_failure,
    track_workflow_execution,
    track_step_execution,
    CREATIVE_ENGINE_REGISTRY,
)

__all__ = [
    # Workflow
    "create_creative_engine_workflow",
    "run_creative_engine_once",
    "run_creative_engine_sync",
    "CREATIVE_ENGINE_CONFIG",
    # Scheduler
    "start_creative_engine_scheduler",
    "stop_creative_engine_scheduler",
    "is_scheduler_running",
    "get_next_run_time",
    "trigger_immediate_run",
    "get_scheduler_status",
    "cleanup_expired_strategies",
    "start_cleanup_scheduler",
    "SCHEDULER_CONFIG",
    # Metrics
    "get_creative_engine_metrics",
    "print_creative_engine_metrics_summary",
    "track_workflow_run",
    "track_step_duration",
    "track_candidate_generated",
    "track_failure",
    "track_workflow_execution",
    "track_step_execution",
    "CREATIVE_ENGINE_REGISTRY",
]
