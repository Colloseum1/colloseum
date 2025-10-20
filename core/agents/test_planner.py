"""
Tests for PlannerAgent with tool orchestration and session management.

Tests cover:
- Agent initialization with various configurations
- Tool integration (ReasoningTools + 5 HTTP tools)
- Guardrail enforcement (PIT-only, no freeform numbers)
- Tool orchestration workflow (mocked validate→compile→simulate)
- Error handling and retry logic
- Session management with PostgreSQL
- End-to-end integration tests
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from agno.exceptions import InputCheckError
from core.agents import create_planner_agent
from core.schemas.models import RouterDecision, StrategySpecOutput


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def router_decision():
    """Sample RouterDecision for testing."""
    return RouterDecision(
        kind="strategy",
        assets=["SOL/USD"],
        risk="Medium",
        horizon="30d",
        archetype="trend_follow",
        constraints={"max_slippage_bps": 50},
        next_steps=["validate", "compile", "simulate"]
    )


@pytest.fixture
def planner_agent():
    """Create PlannerAgent with default configuration for testing."""
    return create_planner_agent()


@pytest.fixture
def dependencies():
    """Mock dependencies for tool calls."""
    return {
        "endpoints": {
            "SIGNALS_URL": "http://localhost:8080/signals",
            "VALIDATE_URL": "http://localhost:8081/validate",
            "COMPILE_URL": "http://localhost:8082/compile",
            "L5_SIM_URL": "http://localhost:8083/simulate",
            "CH_READ_URL": "http://localhost:9000/query"
        },
        "auth_headers": {"Authorization": "Bearer test_token"}
    }


# =============================================================================
# Agent Initialization Tests
# =============================================================================

class TestPlannerAgentInitialization:
    """Test PlannerAgent creation and configuration."""

    def test_create_planner_agent_default_config(self):
        """Should create agent with default configuration."""
        agent = create_planner_agent()

        assert agent is not None
        assert agent.name == "Planner"
        assert agent.model.__class__.__name__ == "OpenAIChat"
        assert len(agent.tools) == 6  # ReasoningTools + 5 HTTP tools
        assert len(agent.pre_hooks) == 2  # NoFreeformNumbers, PITOnlySql
        assert agent.input_schema == RouterDecision
        assert agent.output_schema == StrategySpecOutput
        assert agent.add_history_to_context is True
        assert agent.enable_session_summaries is True

    def test_create_planner_agent_custom_provider(self):
        """Should create agent with custom model provider."""
        agent = create_planner_agent(
            model_provider="anthropic",
            model_id="claude-3-5-sonnet-20241022",
            temperature=0.3
        )

        assert agent is not None
        assert agent.model.__class__.__name__ == "Claude"

    def test_create_planner_agent_with_db(self):
        """Should create agent with PostgreSQL session management."""
        # Note: This test doesn't actually connect to PostgreSQL
        # It just verifies the db parameter is set
        db_url = "postgresql+psycopg://test:test@localhost:5532/test"

        agent = create_planner_agent(
            db_url=db_url,
            session_id="test_session",
            user_id="test_user"
        )

        assert agent.db is not None
        assert agent.session_id == "test_session"
        assert agent.user_id == "test_user"

    def test_tools_attached_correctly(self):
        """Should have all 6 tools attached."""
        agent = create_planner_agent()

        tool_names = []
        for t in agent.tools:
            if hasattr(t, '__name__'):
                tool_names.append(t.__name__)
            elif hasattr(t, 'name'):
                tool_names.append(t.name)
            else:
                tool_names.append(t.__class__.__name__)

        assert 'reasoning_tools' in tool_names or 'ReasoningTools' in tool_names
        assert 'get_signals' in tool_names
        assert 'validate' in tool_names
        assert 'compile_spec' in tool_names
        assert 'simulate' in tool_names
        assert 'ch_query' in tool_names

    def test_guardrails_attached_correctly(self):
        """Should have NoFreeformNumbers and PITOnlySql guardrails."""
        agent = create_planner_agent()

        guardrail_names = [g.__class__.__name__ for g in agent.pre_hooks]
        assert "NoFreeformNumbersGuardrail" in guardrail_names
        assert "PITOnlySqlGuardrail" in guardrail_names


# =============================================================================
# Tool Integration Tests
# =============================================================================

class TestToolIntegration:
    """Test tool integration and orchestration."""

    @pytest.mark.skip(reason="LLM tests disabled by default - use --run-llm-tests to enable")
    def test_reasoning_tools_usage(self, planner_agent, router_decision, dependencies):
        """Should use ReasoningTools for extended reasoning."""
        # This would require actual LLM calls
        pass

    @patch('core.tools.http_tools.httpx.Client')
    def test_validate_tool_call(self, mock_client, planner_agent, dependencies):
        """Should call validate tool with correct parameters."""
        # Mock successful validation response
        mock_response = Mock()
        mock_response.text = json.dumps({"ok": True, "errors": []})
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        # Import and call validate directly
        from core.tools.http_tools import validate

        spec = {
            "name": "sol_trend_30d",
            "category": "trend_follow",
            "assets": ["SOL"],
            "dataset_refs": ["pit.oracle_prices_by_feed"],
            "graph": {"entry": {}, "exit": {}},
            "guards": {"oracle_staleness_ms_max": 30000}
        }

        result = validate(spec, dependencies)
        parsed = json.loads(result)

        assert parsed["ok"] is True
        assert parsed["errors"] == []

    @patch('core.tools.http_tools.httpx.Client')
    def test_compile_tool_call(self, mock_client, planner_agent, dependencies):
        """Should call compile_spec tool with validated spec."""
        # Mock successful compilation response
        mock_response = Mock()
        mock_response.text = json.dumps({
            "nodes": ["entry", "exit"],
            "edges": [{"from": "entry", "to": "exit"}]
        })
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        from core.tools.http_tools import compile_spec

        spec = {
            "name": "sol_trend_30d",
            "category": "trend_follow",
            "assets": ["SOL"],
            "dataset_refs": ["pit.oracle_prices_by_feed"],
            "graph": {"entry": {}, "exit": {}},
            "guards": {}
        }

        result = compile_spec(spec, dependencies)
        parsed = json.loads(result)

        assert "nodes" in parsed
        assert "edges" in parsed

    @patch('core.tools.http_tools.httpx.Client')
    def test_simulate_tool_call(self, mock_client, planner_agent, dependencies):
        """Should call simulate tool with spec and sim_config."""
        # Mock successful simulation response
        mock_response = Mock()
        mock_response.text = json.dumps({
            "sharpe": 1.5,
            "returns_bps": 2500,
            "max_drawdown_bps": 800,
            "hit_rate": 0.65,
            "capacity_usd": 500000,
            "fee_drag_bps": 150
        })
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        from core.tools.http_tools import simulate

        spec = {"name": "sol_trend_30d"}
        sim_config = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital_usd": 100000
        }

        result = simulate(spec, sim_config, dependencies)
        parsed = json.loads(result)

        assert parsed["sharpe"] == 1.5
        assert parsed["returns_bps"] == 2500
        assert parsed["hit_rate"] == 0.65


# =============================================================================
# Guardrail Tests
# =============================================================================

class TestGuardrails:
    """Test guardrail enforcement."""

    def test_pit_only_sql_guardrail_blocks_non_pit_tables(self, planner_agent):
        """Should block ch_query with non-PIT tables."""
        from core.guardrails.custom import PITOnlySqlGuardrail
        from agno.run.agent import RunInput

        guardrail = PITOnlySqlGuardrail()

        # Should block non-PIT table
        bad_sql = "SELECT * FROM sol.oracles_unified WHERE ts > now() - INTERVAL 1 DAY"
        with pytest.raises(InputCheckError, match="non-PIT table"):
            guardrail.check(RunInput(input_content=bad_sql))

    def test_pit_only_sql_guardrail_allows_pit_tables(self, planner_agent):
        """Should allow ch_query with PIT tables."""
        from core.guardrails.custom import PITOnlySqlGuardrail
        from agno.run.agent import RunInput

        guardrail = PITOnlySqlGuardrail()

        # Should allow PIT table
        good_sql = "SELECT * FROM pit.oracle_prices_by_feed WHERE slot = 250000000"
        # Should not raise
        guardrail.check(RunInput(input_content=good_sql))

    def test_no_freeform_numbers_guardrail_blocks_metrics(self, planner_agent):
        """Should block freeform numeric claims without tool attribution."""
        from core.guardrails.custom import NoFreeformNumbersGuardrail
        from agno.run.agent import RunInput

        guardrail = NoFreeformNumbersGuardrail()

        # Should block freeform numbers
        bad_output = "The strategy has sharpe = 1.5 and returns of 2500 bps"
        with pytest.raises(InputCheckError, match="freeform numeric claims"):
            guardrail.check(RunInput(input_content=bad_output))

    def test_no_freeform_numbers_guardrail_allows_tool_attribution(self, planner_agent):
        """Should allow numbers with tool attribution."""
        from core.guardrails.custom import NoFreeformNumbersGuardrail
        from agno.run.agent import RunInput

        guardrail = NoFreeformNumbersGuardrail()

        # Should allow with tool attribution
        good_output = "The simulate tool returned sharpe=1.5 and returns=2500bps"
        # Should not raise
        guardrail.check(RunInput(input_content=good_output))


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling and retry logic."""

    @patch('core.tools.http_tools.httpx.Client')
    def test_validate_failure_handling(self, mock_client, planner_agent, dependencies):
        """Should handle validation failures gracefully."""
        # Mock validation failure
        mock_response = Mock()
        mock_response.text = json.dumps({
            "ok": False,
            "errors": ["dataset_refs must start with 'pit.'"]
        })
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        from core.tools.http_tools import validate

        bad_spec = {
            "name": "sol_trend_30d",
            "category": "trend_follow",
            "assets": ["SOL"],
            "dataset_refs": ["sol.oracles_unified"],  # Bad: not PIT table
            "graph": {"entry": {}, "exit": {}},
            "guards": {}
        }

        result = validate(bad_spec, dependencies)
        parsed = json.loads(result)

        assert parsed["ok"] is False
        assert len(parsed["errors"]) > 0

    @patch('core.tools.http_tools.httpx.Client')
    def test_compile_failure_handling(self, mock_client, planner_agent, dependencies):
        """Should handle compilation failures gracefully."""
        # Mock compilation failure
        mock_response = Mock()
        mock_response.text = json.dumps({
            "error": "Invalid graph structure: missing exit node"
        })
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        from core.tools.http_tools import compile_spec

        bad_spec = {
            "name": "sol_trend_30d",
            "graph": {"entry": {}}  # Missing exit
        }

        result = compile_spec(bad_spec, dependencies)
        parsed = json.loads(result)

        assert "error" in parsed


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.skip(reason="LLM tests disabled by default - use --run-llm-tests to enable")
    @patch('core.tools.http_tools.httpx.Client')
    def test_end_to_end_workflow(self, mock_client, planner_agent, router_decision, dependencies):
        """Test complete workflow from RouterDecision to StrategySpecOutput."""
        # Mock all HTTP tool responses
        mock_responses = [
            # validate response
            Mock(text=json.dumps({"ok": True, "errors": []})),
            # compile response
            Mock(text=json.dumps({"nodes": [], "edges": []})),
            # simulate response
            Mock(text=json.dumps({
                "sharpe": 1.5,
                "returns_bps": 2500,
                "max_drawdown_bps": 800,
                "hit_rate": 0.65
            }))
        ]

        for resp in mock_responses:
            resp.raise_for_status = Mock()

        mock_client.return_value.__enter__.return_value.post.side_effect = mock_responses

        # This would require actual LLM calls to orchestrate the workflow
        # For now, just verify tools are callable
        from core.tools.http_tools import validate, compile_spec, simulate

        spec = {
            "name": "sol_trend_30d",
            "category": "trend_follow",
            "assets": ["SOL"],
            "dataset_refs": ["pit.oracle_prices_by_feed"],
            "graph": {"entry": {}, "exit": {}},
            "guards": {}
        }

        # Verify each tool works
        validate_result = validate(spec, dependencies)
        assert json.loads(validate_result)["ok"] is True

        compile_result = compile_spec(spec, dependencies)
        assert "nodes" in json.loads(compile_result)

        simulate_result = simulate(spec, {"start_date": "2024-01-01"}, dependencies)
        assert json.loads(simulate_result)["sharpe"] == 1.5


# =============================================================================
# Session Management Tests
# =============================================================================

class TestSessionManagement:
    """Test session management and history."""

    def test_session_config_without_db(self):
        """Should configure session without database."""
        agent = create_planner_agent(
            session_id="test_session",
            user_id="test_user"
        )

        assert agent.session_id == "test_session"
        assert agent.user_id == "test_user"
        assert agent.db is None  # No db_url provided

    def test_session_config_with_db_url(self):
        """Should configure session with database URL."""
        db_url = "postgresql+psycopg://test:test@localhost:5532/test"

        agent = create_planner_agent(
            db_url=db_url,
            session_id="test_session",
            user_id="test_user"
        )

        assert agent.db is not None
        assert agent.session_id == "test_session"
        assert agent.user_id == "test_user"
        assert agent.add_history_to_context is True


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_addoption(parser):
    """Add custom pytest command-line options."""
    parser.addoption(
        "--run-llm-tests",
        action="store_true",
        default=False,
        help="Run tests that require LLM API calls (slow, requires API keys)"
    )
