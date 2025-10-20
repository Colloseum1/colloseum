"""
Tests for NarratorAgent with agentic RAG and knowledge base integration.

Tests cover:
- Agent initialization with various configurations
- Knowledge base integration (LanceDB + OpenAI embeddings)
- Agentic RAG (automatic knowledge retrieval)
- Guardrail enforcement (NoFreeformNumbers)
- Citation requirements
- Input/output schema compliance
- Session management with PostgreSQL
- End-to-end explanation workflow
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from core.agents import create_narrator_agent
from core.schemas.models import (
    StrategySpecOutput,
    StrategySpec,
    SimMetrics,
    ExplainedPlan,
    Citation,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def strategy_spec_output():
    """Sample StrategySpecOutput for testing."""
    return StrategySpecOutput(
        spec=StrategySpec(
            name="sol_trend_ema_cross_30d",
            category="trend_follow",
            assets=["SOL"],
            dataset_refs=["pit.oracle_prices_by_feed"],
            graph={
                "entry": {
                    "type": "ema_cross",
                    "params": {"fast": 12, "slow": 26, "direction": "up"}
                },
                "exit": {
                    "type": "ema_cross",
                    "params": {"fast": 12, "slow": 26, "direction": "down"}
                },
                "filters": [
                    {"type": "hygiene_check", "flags": ["fresh", "liquidity_ok", "oracle_ok"]}
                ],
                "position_sizing": {
                    "type": "fixed_fraction",
                    "params": {"fraction": 0.1}
                }
            },
            guards={
                "oracle_staleness_ms_max": 30000,
                "max_slippage_bps": 50,
                "max_drawdown_bps": 1000,
                "min_liquidity_usd": 100000,
                "oracle_delta_bps_max": 500,
                "spread_bps_max": 20
            },
            metadata={"horizon": "30d", "risk": "Medium"}
        ),
        plan_graph={
            "nodes": ["entry", "exit"],
            "edges": [{"from": "entry", "to": "exit"}]
        },
        sim_metrics=SimMetrics(
            sharpe=1.5,
            returns_bps=2500,
            max_drawdown_bps=800,
            hit_rate=0.65,
            capacity_usd=500000,
            fee_drag_bps=150
        ),
        rejections=[]
    )


@pytest.fixture
def narrator_agent():
    """Create NarratorAgent with default configuration for testing."""
    return create_narrator_agent()


# =============================================================================
# Agent Initialization Tests
# =============================================================================

class TestNarratorAgentInitialization:
    """Test NarratorAgent creation and configuration."""

    def test_create_narrator_agent_default_config(self):
        """Should create agent with default configuration."""
        agent = create_narrator_agent()

        assert agent is not None
        assert agent.name == "Narrator"
        assert agent.model.__class__.__name__ == "OpenAIChat"
        assert agent.knowledge is not None
        assert agent.search_knowledge is True
        assert len(agent.pre_hooks) == 1  # NoFreeformNumbers
        assert agent.input_schema == StrategySpecOutput
        assert agent.output_schema == ExplainedPlan
        assert agent.add_history_to_context is True
        assert agent.enable_session_summaries is True

    def test_create_narrator_agent_custom_provider(self):
        """Should create agent with custom model provider."""
        agent = create_narrator_agent(
            model_provider="anthropic",
            model_id="claude-3-5-haiku-20241022",
            temperature=0.2
        )

        assert agent is not None
        assert agent.model.__class__.__name__ == "Claude"

    def test_create_narrator_agent_with_db(self):
        """Should create agent with PostgreSQL session management."""
        db_url = "postgresql+psycopg://test:test@localhost:5532/test"

        agent = create_narrator_agent(
            db_url=db_url,
            session_id="test_session",
            user_id="test_user"
        )

        assert agent.db is not None
        assert agent.session_id == "test_session"
        assert agent.user_id == "test_user"

    def test_knowledge_base_attached(self):
        """Should have knowledge base attached for agentic RAG."""
        agent = create_narrator_agent()

        assert agent.knowledge is not None
        assert agent.search_knowledge is True
        assert agent.knowledge.name == "Layer 4 Strategy Knowledge Base"

    def test_guardrails_attached_correctly(self):
        """Should have NoFreeformNumbers guardrail."""
        agent = create_narrator_agent()

        guardrail_names = [g.__class__.__name__ for g in agent.pre_hooks]
        assert "NoFreeformNumbersGuardrail" in guardrail_names


# =============================================================================
# Knowledge Base Integration Tests
# =============================================================================

class TestKnowledgeBaseIntegration:
    """Test knowledge base integration and RAG functionality."""

    def test_knowledge_base_exists(self):
        """Should have a pre-configured knowledge base."""
        agent = create_narrator_agent()

        assert agent.knowledge is not None
        assert agent.knowledge.vector_db is not None
        assert agent.knowledge.max_results == 5

    def test_agentic_rag_enabled(self):
        """Should have search_knowledge=True for automatic retrieval."""
        agent = create_narrator_agent()

        assert agent.search_knowledge is True


# =============================================================================
# Guardrail Tests
# =============================================================================

class TestGuardrails:
    """Test guardrail enforcement."""

    def test_no_freeform_numbers_guardrail_blocks_metrics(self, narrator_agent):
        """Should block freeform numeric claims without tool attribution."""
        from core.guardrails.custom import NoFreeformNumbersGuardrail
        from agno.run.agent import RunInput

        guardrail = NoFreeformNumbersGuardrail()

        # Should block freeform numbers
        bad_output = "The strategy has sharpe = 1.5 and returns of 2500 bps"
        with pytest.raises(Exception):  # InputCheckError
            guardrail.check(RunInput(input_content=bad_output))

    def test_no_freeform_numbers_guardrail_allows_tool_attribution(self, narrator_agent):
        """Should allow numbers with tool attribution."""
        from core.guardrails.custom import NoFreeformNumbersGuardrail
        from agno.run.agent import RunInput

        guardrail = NoFreeformNumbersGuardrail()

        # Should allow with tool attribution
        good_output = "The simulate tool returned sharpe=1.5 and returns=2500bps"
        # Should not raise
        guardrail.check(RunInput(input_content=good_output))


# =============================================================================
# Schema Compliance Tests
# =============================================================================

class TestSchemaCompliance:
    """Test ExplainedPlan schema validation."""

    @pytest.mark.skip(reason="LLM tests disabled by default - use --run-llm-tests to enable")
    def test_output_matches_explainedplan_schema(self, narrator_agent, strategy_spec_output):
        """Should return valid ExplainedPlan object."""
        result = narrator_agent.run(input=strategy_spec_output)

        explained = result.content
        # Verify all required fields present
        assert hasattr(explained, 'summary')
        assert hasattr(explained, 'citations')
        assert hasattr(explained, 'caps_enforced')
        assert hasattr(explained, 'sim_metrics')

        # Verify types
        assert isinstance(explained.summary, str)
        assert isinstance(explained.citations, list)
        assert isinstance(explained.caps_enforced, list)
        assert len(explained.summary) > 0
        assert len(explained.caps_enforced) > 0

    @pytest.mark.skip(reason="LLM tests disabled by default - use --run-llm-tests to enable")
    def test_citations_have_required_fields(self, narrator_agent, strategy_spec_output):
        """Should return citations with source, snippet, and relevance."""
        result = narrator_agent.run(input=strategy_spec_output)

        explained: ExplainedPlan = result.content
        if explained.citations:
            for citation in explained.citations:
                assert hasattr(citation, 'source')
                assert hasattr(citation, 'snippet')
                assert hasattr(citation, 'relevance')
                assert isinstance(citation.source, str)
                assert isinstance(citation.snippet, str)
                assert isinstance(citation.relevance, float)
                assert 0.0 <= citation.relevance <= 1.0


# =============================================================================
# Citation Requirements Tests
# =============================================================================

class TestCitationRequirements:
    """Test citation requirements and enforcement."""

    @pytest.mark.skip(reason="LLM tests disabled by default - use --run-llm-tests to enable")
    def test_explanation_includes_citations(self, narrator_agent, strategy_spec_output):
        """Should include citations for factual claims."""
        result = narrator_agent.run(input=strategy_spec_output)

        explained: ExplainedPlan = result.content
        assert len(explained.citations) > 0, "Explanation must include citations"

    @pytest.mark.skip(reason="LLM tests disabled by default - use --run-llm-tests to enable")
    def test_guardrails_listed_in_caps_enforced(self, narrator_agent, strategy_spec_output):
        """Should list all guardrails from spec.guards."""
        result = narrator_agent.run(input=strategy_spec_output)

        explained: ExplainedPlan = result.content
        assert len(explained.caps_enforced) >= 3, "Should list multiple guardrails"

        # Check for specific guardrails
        caps_str = " ".join(explained.caps_enforced)
        assert "oracle_staleness" in caps_str or "staleness" in caps_str
        assert "slippage" in caps_str
        assert "drawdown" in caps_str


# =============================================================================
# Session Management Tests
# =============================================================================

class TestSessionManagement:
    """Test session management and history."""

    def test_session_config_without_db(self):
        """Should configure session without database."""
        agent = create_narrator_agent(
            session_id="test_session",
            user_id="test_user"
        )

        assert agent.session_id == "test_session"
        assert agent.user_id == "test_user"
        assert agent.db is None  # No db_url provided

    def test_session_config_with_db_url(self):
        """Should configure session with database URL."""
        db_url = "postgresql+psycopg://test:test@localhost:5532/test"

        agent = create_narrator_agent(
            db_url=db_url,
            session_id="test_session",
            user_id="test_user"
        )

        assert agent.db is not None
        assert agent.session_id == "test_session"
        assert agent.user_id == "test_user"
        assert agent.add_history_to_context is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.skip(reason="LLM tests disabled by default - use --run-llm-tests to enable")
    def test_end_to_end_explanation(self, narrator_agent, strategy_spec_output):
        """Test complete workflow from StrategySpecOutput to ExplainedPlan."""
        result = narrator_agent.run(input=strategy_spec_output)

        explained: ExplainedPlan = result.content

        # Verify summary exists and is substantial
        assert len(explained.summary) > 100, "Summary should be detailed"

        # Verify citations are provided
        assert len(explained.citations) > 0, "Should include citations"

        # Verify guardrails are listed
        assert len(explained.caps_enforced) > 0, "Should list enforced guardrails"

        # Verify sim_metrics are included
        assert explained.sim_metrics is not None
        assert explained.sim_metrics.sharpe == 1.5
        assert explained.sim_metrics.returns_bps == 2500

    @pytest.mark.skip(reason="LLM tests disabled by default - use --run-llm-tests to enable")
    def test_explanation_with_rejections(self, narrator_agent):
        """Should handle StrategySpecOutput with rejections."""
        spec_with_rejections = StrategySpecOutput(
            spec=StrategySpec(
                name="failed_strategy",
                category="trend_follow",
                assets=["SOL"],
                dataset_refs=["pit.oracle_prices_by_feed"],
                graph={"entry": {}, "exit": {}},
                guards={}
            ),
            plan_graph=None,
            sim_metrics=None,
            rejections=["Dataset refs must start with 'pit.'", "Missing required guards"]
        )

        result = narrator_agent.run(input=spec_with_rejections)

        explained: ExplainedPlan = result.content
        # Should acknowledge rejections in summary
        assert "rejection" in explained.summary.lower() or "fail" in explained.summary.lower()


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Test response time and performance benchmarks."""

    def test_agent_initialization_fast(self):
        """Should initialize agent quickly (<5s)."""
        import time
        start_time = time.time()

        agent = create_narrator_agent()

        elapsed = time.time() - start_time
        assert elapsed < 5.0  # 5s threshold for initialization


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
