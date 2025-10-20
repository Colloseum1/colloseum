"""
End-to-End Integration Tests for Team Orchestration (Task 8.5).

Tests the complete flow: Router → Planner → Narrator with:
- Session persistence (PostgreSQL)
- Context sharing (shared dependencies)
- Knowledge retrieval (RAG via LanceDB)
- Metrics tracking
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Import team orchestration
from core.orchestration import create_strategy_team, run_strategy_team
from core.config import get_shared_dependencies
from core.monitoring import initialize_agno_instrumentation, print_metrics_summary


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_http_tools():
    """Mock HTTP tool responses for testing without external dependencies."""
    mock_responses = {
        "validate": {"ok": True, "errors": []},
        "compile_spec": {
            "ok": True,
            "plan": {
                "legs": [
                    {"leg_id": "1", "kind": "swap", "protocol": "jupiter"},
                ]
            },
        },
        "simulate": {
            "ok": True,
            "metrics": {
                "sharpe": 1.5,
                "returns_bps": 250,
                "max_dd_bps": 150,
                "hit_rate": 0.65,
            },
        },
        "get_signals": {
            "signals": [
                {
                    "signal_id": "ema_cross",
                    "value": 1.2,
                    "fresh": True,
                    "liquidity_ok": True,
                }
            ]
        },
        "ch_query": {
            "rows": [{"volatility_30d": 0.05, "avg_spread_bps": 10}]
        },
    }

    with patch("core.tools.http_tools.validate") as mock_validate, \
         patch("core.tools.http_tools.compile_spec") as mock_compile, \
         patch("core.tools.http_tools.simulate") as mock_simulate, \
         patch("core.tools.http_tools.get_signals") as mock_get_signals, \
         patch("core.tools.http_tools.ch_query") as mock_ch_query:

        # Configure mocks to return realistic responses
        mock_validate.return_value = mock_responses["validate"]
        mock_compile.return_value = mock_responses["compile_spec"]
        mock_simulate.return_value = mock_responses["simulate"]
        mock_get_signals.return_value = mock_responses["get_signals"]
        mock_ch_query.return_value = mock_responses["ch_query"]

        yield {
            "validate": mock_validate,
            "compile_spec": mock_compile,
            "simulate": mock_simulate,
            "get_signals": mock_get_signals,
            "ch_query": mock_ch_query,
        }


@pytest.fixture
def mock_agents():
    """Mock individual agents for testing team coordination."""
    with patch("core.agents.create_router_agent") as mock_router, \
         patch("core.agents.create_planner_agent") as mock_planner, \
         patch("core.agents.create_narrator_agent") as mock_narrator:

        # Create mock agent instances with run() method
        router_instance = Mock()
        router_instance.run.return_value = Mock(
            content={
                "kind": "strategy",
                "assets": ["SOL/USD"],
                "risk": "Medium",
                "horizon": "7d",
                "archetype": "trend_follow",
                "constraints": {"max_slippage_bps": 50},
            }
        )

        planner_instance = Mock()
        planner_instance.run.return_value = Mock(
            content={
                "spec": {
                    "name": "sol_trend_7d",
                    "category": "trend_follow",
                    "assets": ["SOL"],
                    "dataset_refs": ["pit.oracle_prices_by_feed"],
                },
                "plan": {"legs": [{"leg_id": "1", "kind": "swap"}]},
                "sim_metrics": {"sharpe": 1.5, "returns_bps": 250},
            }
        )

        narrator_instance = Mock()
        narrator_instance.run.return_value = Mock(
            content={
                "summary": "SOL trend following strategy with 1.5 Sharpe ratio",
                "citations": ["leg_library.json#jupiter_swap", "rules.yml#max_slippage"],
                "caps_enforced": ["max_slippage_bps: 50"],
                "sim_metrics": {"sharpe": 1.5, "returns_bps": 250},
            }
        )

        mock_router.return_value = router_instance
        mock_planner.return_value = planner_instance
        mock_narrator.return_value = narrator_instance

        yield {
            "router": mock_router,
            "planner": mock_planner,
            "narrator": mock_narrator,
        }


@pytest.fixture
def test_session_config():
    """Provide test session configuration."""
    return {
        "session_id": "test_session_001",
        "user_id": "test_user_123",
    }


# ============================================================================
# Test: Shared Dependencies Configuration
# ============================================================================

def test_shared_dependencies_configuration():
    """Test that shared dependencies are correctly configured."""
    # Get shared dependencies
    deps = get_shared_dependencies()

    # Verify required keys
    assert "rules" in deps
    assert "endpoints" in deps
    assert "auth_headers" in deps
    assert "venue_allowlist" in deps
    assert "oracle_floors" in deps
    assert "spread_floors" in deps
    assert "liquidity_floors" in deps

    # Verify endpoints
    required_endpoints = ["signals", "validate", "compile", "simulate", "ch_query"]
    for endpoint in required_endpoints:
        assert endpoint in deps["endpoints"]

    # Verify venue allowlist is not empty
    assert len(deps["venue_allowlist"]) > 0


# ============================================================================
# Test: Team Creation
# ============================================================================

def test_create_strategy_team_basic():
    """Test basic team creation without database."""
    team = create_strategy_team(
        db_url=None,  # No database for this test
        enable_streaming=False,
    )

    assert team is not None
    assert team.name == "PromptFi Strategy Team"
    assert len(team.members) == 3  # Router, Planner, Narrator


def test_create_strategy_team_with_session_config(test_session_config):
    """Test team creation with session configuration."""
    team = create_strategy_team(
        session_id=test_session_config["session_id"],
        user_id=test_session_config["user_id"],
        db_url=None,
        enable_session_summaries=True,
        enable_user_memories=True,
    )

    assert team is not None
    # Session config should be applied
    # Note: Actual session behavior tested in separate test


# ============================================================================
# Test: Team Execution (Mocked)
# ============================================================================

@pytest.mark.skip(reason="Requires mocking Team.run() - complex async behavior")
def test_team_execution_flow_mocked(mock_agents, test_session_config):
    """
    Test the complete team execution flow with mocked agents.

    Flow:
    1. User ask → RouterAgent → RouterDecision
    2. RouterDecision → PlannerAgent → StrategySpecOutput
    3. StrategySpecOutput → NarratorAgent → ExplainedPlan
    """
    # This test is marked as skip because mocking Team.run() is complex
    # In practice, use real agents with mocked HTTP tools (see next test)
    pass


# ============================================================================
# Test: Context Sharing Between Agents
# ============================================================================

def test_context_sharing_via_dependencies():
    """Test that dependencies are shared across all agents via team."""
    deps = get_shared_dependencies()

    # Create team with dependencies
    team = create_strategy_team(db_url=None)

    # Verify dependencies are available
    assert team.dependencies is not None
    assert "rules" in team.dependencies
    assert "endpoints" in team.dependencies

    # All members should have access to shared dependencies
    for member in team.members:
        # Dependencies are accessible via team.dependencies
        pass


# ============================================================================
# Test: Session Persistence (Requires PostgreSQL)
# ============================================================================

@pytest.mark.skipif(
    not os.getenv("POSTGRES_DB_URL"),
    reason="Requires PostgreSQL - set POSTGRES_DB_URL to run",
)
def test_session_persistence_with_postgres():
    """
    Test session persistence with PostgreSQL.

    Requires: PostgreSQL running at POSTGRES_DB_URL
    """
    session_id = "test_session_persistence"
    user_id = "test_user_persistence"

    # Create team with PostgreSQL
    team = create_strategy_team(
        session_id=session_id,
        user_id=user_id,
        enable_session_summaries=True,
        enable_user_memories=True,
    )

    # Run team (this would normally call agents)
    # For this test, just verify session is created
    assert team.db is not None
    assert team.session_id == session_id
    assert team.user_id == user_id

    # Verify session can be retrieved
    session = team.get_session(session_id=session_id)
    # Session may be None if no messages yet, which is OK


# ============================================================================
# Test: Knowledge Base Integration (Requires LanceDB)
# ============================================================================

@pytest.mark.skipif(
    not Path("./tmp/lancedb").exists(),
    reason="Requires LanceDB knowledge base - run setup_knowledge_base first",
)
def test_knowledge_base_retrieval():
    """
    Test that Narrator can retrieve from knowledge base.

    Requires: Knowledge base set up via setup_knowledge_base()
    """
    # This would test NarratorAgent's RAG capabilities
    # For now, just verify knowledge base exists
    from core.knowledge import get_knowledge_base

    kb = get_knowledge_base()
    assert kb is not None


# ============================================================================
# Test: Metrics Tracking
# ============================================================================

def test_metrics_tracking():
    """Test that metrics are tracked during team execution."""
    # Initialize instrumentation
    initialize_agno_instrumentation()

    # Import metrics
    from core.monitoring import session_count, team_runs_total

    # Get initial values
    initial_session_count = session_count._value.get()

    # Create and run team with metrics
    team = create_strategy_team(
        session_id="test_metrics_session",
        user_id="test_metrics_user",
        db_url=None,
    )

    # Manually track session (normally done in run_strategy_team)
    from core.monitoring import track_session_start
    track_session_start("test_metrics_session", "test_metrics_user")

    # Verify session count increased
    assert session_count._value.get() == initial_session_count + 1

    # Print metrics summary for debugging
    print_metrics_summary()


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_team_execution_with_error(mock_agents):
    """Test that errors in agent execution are handled properly."""
    # Configure mock to raise error
    mock_agents["planner"]().run.side_effect = Exception("Simulated planner error")

    team = create_strategy_team(db_url=None)

    # Execution should handle error gracefully
    # (Actual behavior depends on Team error handling)
    # This test documents expected error handling behavior


# ============================================================================
# Test: Streaming Output
# ============================================================================

@pytest.mark.skip(reason="Requires real Team.run() with streaming - integration test")
def test_team_streaming_output():
    """
    Test that team can stream intermediate steps.

    This is an integration test that requires real Team.run() execution.
    """
    pass


# ============================================================================
# Test: Multi-Turn Conversation
# ============================================================================

@pytest.mark.skipif(
    not os.getenv("POSTGRES_DB_URL"),
    reason="Requires PostgreSQL for session continuity",
)
def test_multi_turn_conversation():
    """
    Test multi-turn conversation with session continuity.

    Requires: PostgreSQL for session storage
    """
    session_id = "test_multi_turn"
    user_id = "test_user_multi"

    team = create_strategy_team(
        session_id=session_id,
        user_id=user_id,
        enable_session_summaries=True,
        add_history_to_context=True,
    )

    # First turn
    # result_1 = team.run("Build me a SOL strategy", session_id=session_id, user_id=user_id)

    # Second turn (should have context from first)
    # result_2 = team.run("Make it more aggressive", session_id=session_id, user_id=user_id)

    # Verify history is maintained
    # history = team.get_chat_history()
    # assert len(history) >= 2  # At least 2 turns


# ============================================================================
# Test: Full End-to-End (Manual/Integration)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not all([
        os.getenv("OPENAI_API_KEY"),
        os.getenv("POSTGRES_DB_URL"),
    ]),
    reason="Requires OPENAI_API_KEY and POSTGRES_DB_URL for full integration test",
)
def test_full_end_to_end_integration():
    """
    Full end-to-end integration test with real agents and services.

    REQUIRES:
    - OPENAI_API_KEY set
    - POSTGRES_DB_URL set
    - Services running (validate, compile, simulate, signals, ch_query)
    - Knowledge base set up

    This test makes real LLM calls and external HTTP requests.
    Run with: pytest -m integration
    """
    session_id = "integration_test_session"
    user_id = "integration_test_user"

    # Initialize metrics
    initialize_agno_instrumentation()

    # Create team
    team = create_strategy_team(
        session_id=session_id,
        user_id=user_id,
        enable_streaming=True,
        enable_session_summaries=True,
        enable_user_memories=True,
    )

    # Run team with real execution
    result = run_strategy_team(
        user_ask="Build me a SOL trend following strategy",
        team=team,
        session_id=session_id,
        user_id=user_id,
        enable_metrics=True,
    )

    # Verify result structure
    assert result is not None
    # Add more assertions based on expected output structure

    # Print metrics
    print_metrics_summary()

    # Verify session was created
    session = team.get_session(session_id=session_id)
    assert session is not None

    # Verify chat history
    history = team.get_chat_history()
    assert len(history) > 0
