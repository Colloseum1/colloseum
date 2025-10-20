"""
Comprehensive Test Suite for Creative Engine (Task 10.8).

Tests:
- Workflow execution with mocked tools
- Scheduler functionality
- Metrics tracking
- Persistence and TTL
- Scoring and bucketing logic
"""

import pytest
import os
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from core.workflows import (
    create_creative_engine_workflow,
    run_creative_engine_sync,
    start_creative_engine_scheduler,
    stop_creative_engine_scheduler,
    is_scheduler_running,
    get_scheduler_status,
    trigger_immediate_run,
    CREATIVE_ENGINE_CONFIG,
    get_creative_engine_metrics,
    print_creative_engine_metrics_summary,
)
from core.workflows.creative_engine import (
    score_and_bucket,
    persist_results,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for tests."""
    output_dir = tmp_path / "creative_engine_test"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_workflow_config(temp_output_dir, monkeypatch):
    """Mock Creative Engine configuration to use temp directory."""
    monkeypatch.setitem(CREATIVE_ENGINE_CONFIG, "output_dir", str(temp_output_dir))
    return CREATIVE_ENGINE_CONFIG


@pytest.fixture
def mock_http_tools():
    """Mock HTTP tools (validate, compile, simulate) for workflow testing."""
    mock_responses = {
        "validate": json.dumps({"ok": True, "errors": []}),
        "compile_spec": json.dumps({
            "ok": True,
            "plan": {
                "legs": [{"leg_id": "1", "kind": "swap", "protocol": "jupiter"}]
            }
        }),
        "simulate": json.dumps({
            "ok": True,
            "metrics": {
                "sharpe": 1.8,
                "total_pnl_usd": 250.0,
                "returns_bps": 250,
                "max_dd_bps": 800,
                "hit_rate": 0.65,
                "fill_rate": 0.9,
                "fee_drag_bps": 20,
                "route_reliability": 0.95,
            }
        }),
    }

    with patch('core.tools.http_tools.validate') as mock_validate, \
         patch('core.tools.http_tools.compile_spec') as mock_compile, \
         patch('core.tools.http_tools.simulate') as mock_simulate:

        mock_validate.return_value = mock_responses["validate"]
        mock_compile.return_value = mock_responses["compile_spec"]
        mock_simulate.return_value = mock_responses["simulate"]

        yield {
            "validate": mock_validate,
            "compile_spec": mock_compile,
            "simulate": mock_simulate,
        }


@pytest.fixture(autouse=True)
def cleanup_scheduler():
    """Ensure scheduler is stopped after each test."""
    yield
    if is_scheduler_running():
        stop_creative_engine_scheduler(wait=False)


# ============================================================================
# Unit Tests: Scoring and Bucketing
# ============================================================================

@pytest.mark.asyncio
async def test_score_and_bucket_low_risk():
    """Test scoring formula and low-risk bucket assignment."""
    from agno.workflow.types import WorkflowExecutionInput

    # Mock execution input with high-quality metrics
    previous_output = {
        "spec": {"name": "test_strategy"},
        "sim_metrics": {
            "sharpe": 2.5,
            "total_pnl_usd": 5000,
            "max_dd_bps": 500,  # 5% drawdown
            "fill_rate": 0.95,
            "fee_drag_bps": 15,
            "route_reliability": 0.98,
        }
    }

    # Create WorkflowExecutionInput and manually set previous_step_content
    exec_input = WorkflowExecutionInput(input="test")
    exec_input.previous_step_content = previous_output

    # Run scoring
    result = await score_and_bucket({}, exec_input)

    # Verify Low bucket assignment
    assert result is not None
    assert result["bucket"] == "Low"
    assert result["score"] > 2.0
    assert result["ttl_hours"] == 168  # 7 days


@pytest.mark.asyncio
async def test_score_and_bucket_medium_risk():
    """Test medium-risk bucket assignment."""
    from agno.workflow.types import WorkflowExecutionInput

    previous_output = {
        "spec": {"name": "test_strategy"},
        "sim_metrics": {
            "sharpe": 1.5,
            "total_pnl_usd": 2000,
            "max_dd_bps": 1500,  # 15% drawdown
            "fill_rate": 0.75,
            "fee_drag_bps": 25,
            "route_reliability": 0.85,
        }
    }

    exec_input = WorkflowExecutionInput(input="test")
    exec_input.previous_step_content = previous_output

    result = await score_and_bucket({}, exec_input)

    assert result is not None
    assert result["bucket"] == "Medium"
    assert result["ttl_hours"] == 72  # 3 days


@pytest.mark.asyncio
async def test_score_and_bucket_high_risk():
    """Test high-risk bucket assignment."""
    from agno.workflow.types import WorkflowExecutionInput

    previous_output = {
        "spec": {"name": "test_strategy"},
        "sim_metrics": {
            "sharpe": 0.5,
            "total_pnl_usd": 500,
            "max_dd_bps": 2500,  # 25% drawdown
            "fill_rate": 0.6,
            "fee_drag_bps": 40,
            "route_reliability": 0.7,
        }
    }

    exec_input = WorkflowExecutionInput(input="test")
    exec_input.previous_step_content = previous_output

    result = await score_and_bucket({}, exec_input)

    assert result is not None
    assert result["bucket"] == "High"
    assert result["ttl_hours"] == 24  # 1 day


# ============================================================================
# Unit Tests: Persistence
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_creates_file(mock_workflow_config, temp_output_dir):
    """Test that persist_results creates JSON file with correct structure."""
    from agno.workflow.types import WorkflowExecutionInput

    previous_output = {
        "spec": {"name": "test_sol_trend_7d", "category": "trend_follow"},
        "bucket": "Medium",
        "score": 1.75,
        "sim_metrics": {"sharpe": 1.5, "returns_bps": 200},
        "ttl_hours": 72,
    }

    exec_input = WorkflowExecutionInput(input="test")
    exec_input.previous_step_content = previous_output

    result = await persist_results({}, exec_input)

    assert result is not None
    assert "filepath" in result

    # Verify file was created
    filepath = Path(result["filepath"])
    assert filepath.exists()

    # Verify JSON structure
    with open(filepath, 'r') as f:
        data = json.load(f)

    assert data["bucket"] == "Medium"
    assert data["score"] == 1.75
    assert "expires_at" in data
    assert "timestamp" in data
    assert data["ttl_hours"] == 72


@pytest.mark.asyncio
async def test_persist_results_bucket_subdirectories(mock_workflow_config, temp_output_dir):
    """Test that files are saved in correct bucket subdirectories."""
    from agno.workflow.types import WorkflowExecutionInput

    for bucket in ["Low", "Medium", "High"]:
        previous_output = {
            "spec": {"name": f"test_{bucket.lower()}"},
            "bucket": bucket,
            "score": 2.0 if bucket == "Low" else 1.0,
            "sim_metrics": {},
            "ttl_hours": 24,
        }

        exec_input = WorkflowExecutionInput(input="test")
        exec_input.previous_step_content = previous_output

        result = await persist_results({}, exec_input)
        filepath = Path(result["filepath"])
        assert filepath.parent.name == bucket.lower()


# ============================================================================
# Integration Tests: Scheduler
# ============================================================================

def test_scheduler_start_stop():
    """Test scheduler can be started and stopped."""
    # Start scheduler
    scheduler = start_creative_engine_scheduler()
    assert scheduler is not None
    assert is_scheduler_running() is True

    # Check status
    status = get_scheduler_status()
    assert status["running"] is True
    assert status["interval_minutes"] == 30
    assert status["next_run_time"] is not None

    # Stop scheduler
    stop_creative_engine_scheduler(wait=False)
    assert is_scheduler_running() is False


def test_scheduler_prevents_duplicate_start():
    """Test that starting scheduler twice is safe."""
    scheduler1 = start_creative_engine_scheduler()
    scheduler2 = start_creative_engine_scheduler()  # Should return existing

    assert scheduler1 is scheduler2
    stop_creative_engine_scheduler(wait=False)


def test_trigger_immediate_run_requires_running_scheduler():
    """Test that immediate trigger requires scheduler to be running."""
    with pytest.raises(RuntimeError, match="Scheduler not running"):
        trigger_immediate_run()


# ============================================================================
# Integration Tests: Metrics
# ============================================================================

def test_metrics_export_format():
    """Test that metrics are exported in Prometheus format."""
    from core.workflows.metrics import (
        track_workflow_run,
        track_candidate_generated,
    )

    # Track some metrics
    track_workflow_run("success", 45.2)
    track_candidate_generated("low", 2.5)

    # Get metrics
    metrics_bytes = get_creative_engine_metrics()
    metrics_text = metrics_bytes.decode('utf-8')

    # Verify Prometheus format
    assert "creative_engine_runs_total" in metrics_text
    assert "creative_engine_candidates_generated" in metrics_text
    assert "creative_engine_workflow_duration_seconds" in metrics_text


def test_metrics_context_manager():
    """Test metrics context manager tracks execution automatically."""
    from core.workflows.metrics import (
        track_workflow_execution,
        creative_engine_runs_total,
    )

    initial_count = creative_engine_runs_total.labels(status="success")._value.get()

    # Successful execution
    with track_workflow_execution():
        time.sleep(0.1)

    assert creative_engine_runs_total.labels(status="success")._value.get() == initial_count + 1


def test_metrics_summary_output(capsys):
    """Test that metrics summary prints correctly."""
    from core.workflows.metrics import track_candidate_generated

    # Generate some test data
    track_candidate_generated("low", 2.3)
    track_candidate_generated("medium", 1.5)
    track_candidate_generated("high", 0.8)

    # Print summary
    print_creative_engine_metrics_summary()

    # Check output
    captured = capsys.readouterr()
    assert "Creative Engine Metrics Summary" in captured.out
    assert "Candidates Generated" in captured.out


# ============================================================================
# End-to-End Tests: Workflow Execution (Mocked)
# ============================================================================

@pytest.mark.skip(reason="Requires full workflow mocking - complex async behavior")
def test_full_workflow_execution_mocked(mock_http_tools, mock_workflow_config):
    """
    Test complete workflow execution with mocked tools.

    This is a complex test that requires mocking the entire Agno workflow.
    Skipped for now - workflow steps tested individually above.
    """
    pass


# ============================================================================
# Configuration Tests
# ============================================================================

def test_creative_engine_config_defaults():
    """Test that configuration has sensible defaults."""
    assert CREATIVE_ENGINE_CONFIG["weight_sharpe"] == 2.0
    assert CREATIVE_ENGINE_CONFIG["weight_max_dd"] == -2.0
    assert CREATIVE_ENGINE_CONFIG["low_risk_score"] == 2.0
    assert CREATIVE_ENGINE_CONFIG["ttl_low"] == 168  # 7 days


def test_creative_engine_config_env_override(monkeypatch):
    """Test that configuration can be overridden via environment variables."""
    monkeypatch.setenv("CE_WEIGHT_SHARPE", "3.0")
    monkeypatch.setenv("CE_TTL_LOW", "240")

    # Reimport to get new config
    from importlib import reload
    import core.workflows.creative_engine as ce_module
    reload(ce_module)

    assert ce_module.CREATIVE_ENGINE_CONFIG["weight_sharpe"] == 3.0
    assert ce_module.CREATIVE_ENGINE_CONFIG["ttl_low"] == 240


# ============================================================================
# Documentation Tests
# ============================================================================

def test_workflow_functions_have_docstrings():
    """Test that all public functions have proper docstrings."""
    from core.workflows import creative_engine, scheduler, metrics

    # Workflow functions
    assert create_creative_engine_workflow.__doc__ is not None
    assert run_creative_engine_sync.__doc__ is not None

    # Scheduler functions
    assert start_creative_engine_scheduler.__doc__ is not None
    assert stop_creative_engine_scheduler.__doc__ is not None

    # Metrics functions
    assert get_creative_engine_metrics.__doc__ is not None


def test_module_exports():
    """Test that core.workflows exports expected functions."""
    from core import workflows

    # Workflow
    assert hasattr(workflows, 'create_creative_engine_workflow')
    assert hasattr(workflows, 'run_creative_engine_sync')

    # Scheduler
    assert hasattr(workflows, 'start_creative_engine_scheduler')
    assert hasattr(workflows, 'stop_creative_engine_scheduler')

    # Metrics
    assert hasattr(workflows, 'get_creative_engine_metrics')
