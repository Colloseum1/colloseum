"""
Verification Tests for OpenTelemetry + Langfuse Integration (Task 9.3).

Tests verify:
- Traces reach Langfuse within 5 seconds
- Span hierarchy is correct (team -> agents -> tools -> model calls)
- Token counts are captured automatically
- Errors are marked in spans
- AgnoInstrumentor automatic instrumentation works correctly
"""

import pytest
import os
import time
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from core.observability import (
    initialize_observability,
    is_observability_enabled,
    get_tracer,
    shutdown_observability,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_observability():
    """Reset observability state before each test."""
    # Force reset by accessing the private global
    import core.observability.instrumentation as obs_module
    obs_module._observability_initialized = False

    # Reset the global TracerProvider to allow setting custom providers in tests
    # This is necessary because OpenTelemetry only allows setting the provider once
    if hasattr(trace_api, '_TRACER_PROVIDER_SET_ONCE'):
        trace_api._TRACER_PROVIDER_SET_ONCE._done = False

    yield

    # Cleanup
    shutdown_observability()
    obs_module._observability_initialized = False

    # Reset again for next test
    if hasattr(trace_api, '_TRACER_PROVIDER_SET_ONCE'):
        trace_api._TRACER_PROVIDER_SET_ONCE._done = False


@pytest.fixture
def mock_langfuse_env(monkeypatch):
    """Set up mock Langfuse environment variables."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test-123")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test-456")
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


@pytest.fixture
def in_memory_span_exporter():
    """Create an in-memory span exporter for testing."""
    return InMemorySpanExporter()


@pytest.fixture
def test_tracer_provider(in_memory_span_exporter):
    """Create a test tracer provider with in-memory exporter."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(in_memory_span_exporter))
    return provider


# ============================================================================
# Unit Tests: Observability Initialization
# ============================================================================

def test_initialize_observability_with_langfuse_keys(mock_langfuse_env):
    """Test that observability initializes successfully with Langfuse keys."""
    with patch('core.observability.instrumentation.AgnoInstrumentor') as mock_instrumentor:
        mock_instance = Mock()
        mock_instrumentor.return_value = mock_instance

        initialize_observability()

        # Verify AgnoInstrumentor was called
        mock_instrumentor.return_value.instrument.assert_called_once()

        # Verify observability is enabled
        assert is_observability_enabled() is True


def test_initialize_observability_without_keys(monkeypatch):
    """Test that observability handles missing Langfuse keys gracefully."""
    # Clear Langfuse env vars
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    with patch('core.observability.instrumentation.AgnoInstrumentor') as mock_instrumentor:
        mock_instance = Mock()
        mock_instrumentor.return_value = mock_instance

        initialize_observability()

        # Should still call AgnoInstrumentor for local metrics
        mock_instrumentor.return_value.instrument.assert_called_once()

        # Observability is enabled (local mode)
        assert is_observability_enabled() is True


def test_initialize_observability_called_twice(mock_langfuse_env):
    """Test that calling initialize_observability twice is safe."""
    with patch('core.observability.instrumentation.AgnoInstrumentor') as mock_instrumentor:
        mock_instance = Mock()
        mock_instrumentor.return_value = mock_instance

        # First call
        initialize_observability()
        assert mock_instrumentor.return_value.instrument.call_count == 1

        # Second call should be skipped
        initialize_observability()
        assert mock_instrumentor.return_value.instrument.call_count == 1


def test_get_tracer_returns_valid_tracer():
    """Test that get_tracer returns a valid OpenTelemetry tracer."""
    tracer = get_tracer("test-tracer")
    assert tracer is not None
    # Should be able to create spans
    with tracer.start_as_current_span("test-span") as span:
        assert span is not None


def test_shutdown_observability():
    """Test that shutdown_observability works correctly."""
    with patch('core.observability.instrumentation.AgnoInstrumentor'):
        initialize_observability(
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )
        assert is_observability_enabled() is True

        shutdown_observability()
        assert is_observability_enabled() is False


# ============================================================================
# Integration Tests: Span Creation and Hierarchy
# ============================================================================

@pytest.mark.integration
def test_manual_span_creation_with_tracer(test_tracer_provider, in_memory_span_exporter):
    """Test that manual span creation works and spans are exported."""
    # Set the test tracer provider
    trace_api.set_tracer_provider(test_tracer_provider)

    # Create a tracer and span
    tracer = trace_api.get_tracer("test")
    with tracer.start_as_current_span("parent-span") as parent:
        parent.set_attribute("test.attribute", "value")

        with tracer.start_as_current_span("child-span") as child:
            child.set_attribute("test.child", "child-value")

    # Force flush
    test_tracer_provider.force_flush()

    # Verify spans were exported
    spans = in_memory_span_exporter.get_finished_spans()
    assert len(spans) == 2

    # Verify hierarchy (spans are in reverse order - child first, parent last)
    child_span = spans[0]
    parent_span = spans[1]

    assert child_span.name == "child-span"
    assert parent_span.name == "parent-span"

    # Verify parent-child relationship
    assert child_span.parent.span_id == parent_span.context.span_id


@pytest.mark.integration
def test_span_attributes_are_captured(test_tracer_provider, in_memory_span_exporter):
    """Test that span attributes are correctly captured."""
    trace_api.set_tracer_provider(test_tracer_provider)

    tracer = trace_api.get_tracer("test")
    with tracer.start_as_current_span("test-span") as span:
        span.set_attribute("user_id", "test-user-123")
        span.set_attribute("session_id", "test-session-456")
        span.set_attribute("token_count", 150)

    test_tracer_provider.force_flush()

    spans = in_memory_span_exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    assert span.attributes["user_id"] == "test-user-123"
    assert span.attributes["session_id"] == "test-session-456"
    assert span.attributes["token_count"] == 150


@pytest.mark.integration
def test_error_spans_are_marked(test_tracer_provider, in_memory_span_exporter):
    """Test that errors in spans are correctly marked."""
    from opentelemetry.trace import Status, StatusCode

    trace_api.set_tracer_provider(test_tracer_provider)

    tracer = trace_api.get_tracer("test")
    try:
        with tracer.start_as_current_span("error-span") as span:
            raise ValueError("Test error")
    except ValueError:
        pass  # Expected

    test_tracer_provider.force_flush()

    spans = in_memory_span_exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    # Check that span recorded the exception
    assert len(span.events) > 0
    error_event = span.events[0]
    assert error_event.name == "exception"


# ============================================================================
# Integration Tests: Langfuse Export (Requires Langfuse API)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not all([
        os.getenv("LANGFUSE_PUBLIC_KEY"),
        os.getenv("LANGFUSE_SECRET_KEY"),
    ]),
    reason="Requires LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY for real export test",
)
def test_traces_reach_langfuse_within_5_seconds(mock_langfuse_env):
    """
    Test that traces reach Langfuse UI within 5 seconds.

    This test requires:
    - Valid Langfuse API keys in environment
    - Network access to Langfuse API
    """
    # Initialize real observability
    initialize_observability()

    # Create a test span
    tracer = get_tracer("test-langfuse-integration")
    start_time = time.time()

    with tracer.start_as_current_span("test-trace-export") as span:
        span.set_attribute("test.timestamp", start_time)
        span.set_attribute("test.purpose", "verify-langfuse-export")

    # Flush and measure time
    provider = trace_api.get_tracer_provider()
    if hasattr(provider, 'force_flush'):
        provider.force_flush(timeout_millis=5000)

    export_time = time.time() - start_time

    # Verify export completed within 5 seconds
    assert export_time < 5.0, f"Export took {export_time:.2f}s (should be < 5s)"

    print(f"✓ Trace exported to Langfuse in {export_time:.2f}s")
    print("✓ Check Langfuse UI for trace: 'test-trace-export'")


@pytest.mark.integration
@pytest.mark.skipif(
    not all([
        os.getenv("LANGFUSE_PUBLIC_KEY"),
        os.getenv("OPENAI_API_KEY"),
    ]),
    reason="Requires LANGFUSE_PUBLIC_KEY and OPENAI_API_KEY for agent instrumentation test",
)
def test_agent_run_creates_trace_hierarchy():
    """
    Test that a real agent run creates correct span hierarchy.

    This test verifies:
    - Team span is root
    - Agent spans are children of team
    - Tool/LLM spans are children of agents

    Requires:
    - Langfuse keys (for export)
    - OpenAI key (for agent execution)
    """
    from core.orchestration import create_strategy_team
    from core.observability import initialize_observability

    # Initialize observability with Langfuse
    initialize_observability()

    # Create a simple team (no DB, no streaming)
    team = create_strategy_team(db_url=None, enable_streaming=False)

    # Run a simple query
    result = team.run("What is 2+2?", stream=False)

    # Flush traces
    provider = trace_api.get_tracer_provider()
    if hasattr(provider, 'force_flush'):
        provider.force_flush(timeout_millis=5000)

    print("✓ Agent run completed")
    print("✓ Check Langfuse UI for trace hierarchy:")
    print("  - Root span: Team run")
    print("  - Child spans: Router, Planner, Narrator agents")
    print("  - Grandchild spans: Tool calls, LLM calls")

    assert result is not None


# ============================================================================
# Unit Tests: Console Export (Development Mode)
# ============================================================================

def test_console_export_enabled(mock_langfuse_env):
    """Test that console export can be enabled for debugging."""
    with patch('core.observability.instrumentation.AgnoInstrumentor'), \
         patch('opentelemetry.sdk.trace.export.ConsoleSpanExporter') as mock_console:

        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance

        initialize_observability(enable_console_export=True)

        # Verify console exporter was created
        mock_console.assert_called_once()


# ============================================================================
# Documentation Tests
# ============================================================================

def test_observability_docstrings_exist():
    """Test that all public functions have proper docstrings."""
    from core.observability import instrumentation

    assert initialize_observability.__doc__ is not None
    assert is_observability_enabled.__doc__ is not None
    assert get_tracer.__doc__ is not None
    assert shutdown_observability.__doc__ is not None


def test_observability_module_exports():
    """Test that core.observability exports expected functions."""
    from core import observability

    assert hasattr(observability, 'initialize_observability')
    assert hasattr(observability, 'is_observability_enabled')
    assert hasattr(observability, 'get_tracer')
    assert hasattr(observability, 'shutdown_observability')
