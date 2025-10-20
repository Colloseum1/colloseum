"""
Tests for core agent I/O schemas (models.py).

Tests validation logic for:
- RouterInput, RouterDecision
- PlannerInput, StrategySpec, StrategySpecOutput
- Citation, ExplainedPlan, SimMetrics
"""

import pytest
from pydantic import ValidationError
from hypothesis import given, strategies as st

from .models import (
    RouterInput,
    RouterDecision,
    PlannerInput,
    StrategySpec,
    SimMetrics,
    StrategySpecOutput,
    Citation,
    ExplainedPlan,
)
from .factories import (
    RouterInputFactory,
    RouterDecisionFactory,
    PlannerInputFactory,
    StrategySpecFactory,
    SimMetricsFactory,
    StrategySpecOutputFactory,
    CitationFactory,
    ExplainedPlanFactory,
)


# =============================================================================
# RouterInput Tests
# =============================================================================

def test_router_input_valid():
    """Test that valid RouterInput is accepted."""
    router_input = RouterInputFactory.build()
    assert isinstance(router_input, RouterInput)
    assert len(router_input.ask) > 0


def test_router_input_rejects_empty():
    """Test that empty ask is rejected."""
    with pytest.raises(ValidationError):
        RouterInput(ask="")


def test_router_input_rejects_whitespace_only():
    """Test that whitespace-only ask is rejected."""
    with pytest.raises(ValidationError, match="ask cannot be empty"):
        RouterInput(ask="   ")


def test_router_input_strips_whitespace():
    """Test that leading/trailing whitespace is stripped."""
    router_input = RouterInput(ask="  test ask  ")
    assert router_input.ask == "test ask"


def test_router_input_rejects_too_long():
    """Test that asks longer than 2000 chars are rejected."""
    with pytest.raises(ValidationError):
        RouterInput(ask="x" * 2001)


# =============================================================================
# RouterDecision Tests
# =============================================================================

def test_router_decision_valid():
    """Test that valid RouterDecision is accepted."""
    decision = RouterDecisionFactory.build()
    assert isinstance(decision, RouterDecision)
    assert decision.kind == "strategy"


@pytest.mark.parametrize(
    "assets,should_pass",
    [
        (["SOL/USD"], True),
        (["BTC/USD", "ETH/USD"], True),
        (["BONK/USDC"], True),
        (["sol/usd"], False),  # lowercase
        (["SOL-USD"], False),  # wrong separator
        (["SOLUSD"], False),  # no separator
        (["SOL/"], False),  # missing quote
        (["/USD"], False),  # missing base
    ],
)
def test_router_decision_asset_validation(assets, should_pass):
    """Test asset format validation."""
    if should_pass:
        decision = RouterDecisionFactory.build(assets=assets)
        assert decision.assets == assets
    else:
        with pytest.raises(ValidationError, match="Invalid asset format"):
            RouterDecisionFactory.build(assets=assets)


@pytest.mark.parametrize("risk", ["Low", "Medium", "High"])
def test_router_decision_risk_levels(risk):
    """Test valid risk levels."""
    decision = RouterDecisionFactory.build(risk=risk)
    assert decision.risk == risk


def test_router_decision_invalid_risk():
    """Test that invalid risk level is rejected."""
    with pytest.raises(ValidationError):
        RouterDecisionFactory.build(risk="VeryHigh")


@pytest.mark.parametrize("horizon", ["7d", "24h", "2w", "14d", "168h"])
def test_router_decision_horizon_formats(horizon):
    """Test valid horizon formats."""
    decision = RouterDecisionFactory.build(horizon=horizon)
    assert decision.horizon == horizon


@pytest.mark.parametrize("horizon", ["7", "d7", "7days", "7D"])
def test_router_decision_invalid_horizon(horizon):
    """Test that invalid horizon formats are rejected."""
    with pytest.raises(ValidationError):
        RouterDecisionFactory.build(horizon=horizon)


def test_router_decision_constraints_validation():
    """Test constraint validation."""
    # Valid constraints
    decision = RouterDecisionFactory.build(
        constraints={
            "max_slippage_bps": 50,
            "max_drawdown_bps": 1000,
            "min_sharpe": 1.0,
        }
    )
    assert decision.constraints["max_slippage_bps"] == 50

    # Unknown constraint
    with pytest.raises(ValidationError, match="Unknown constraint keys"):
        RouterDecisionFactory.build(constraints={"unknown_param": 123})

    # Out of range bps
    with pytest.raises(ValidationError, match="must be between 0 and 10000"):
        RouterDecisionFactory.build(constraints={"max_slippage_bps": 15000})


# =============================================================================
# PlannerInput Tests
# =============================================================================

def test_planner_input_valid():
    """Test that valid PlannerInput is accepted."""
    planner_input = PlannerInputFactory.build()
    assert isinstance(planner_input, PlannerInput)
    assert isinstance(planner_input.decision, RouterDecision)


# =============================================================================
# StrategySpec Tests
# =============================================================================

def test_strategy_spec_valid():
    """Test that valid StrategySpec is accepted."""
    spec = StrategySpecFactory.build()
    assert isinstance(spec, StrategySpec)
    assert spec.name == "sol_trend_7d"


@pytest.mark.parametrize(
    "name,should_pass",
    [
        ("sol_trend_7d", True),
        ("btc_mean_revert", True),
        ("test_123", True),
        ("SOL_trend", False),  # uppercase
        ("sol-trend", False),  # hyphen
        ("sol trend", False),  # space
        ("sol.trend", False),  # dot
        ("ab", False),  # too short
    ],
)
def test_strategy_spec_name_validation(name, should_pass):
    """Test strategy name validation."""
    if should_pass:
        spec = StrategySpecFactory.build(name=name)
        assert spec.name == name
    else:
        with pytest.raises(ValidationError):
            StrategySpecFactory.build(name=name)


def test_strategy_spec_pit_only_dataset_refs():
    """Test that dataset_refs must start with 'pit.'."""
    # Valid
    spec = StrategySpecFactory.build(
        dataset_refs=["pit.oracle_prices", "pit.features"]
    )
    assert len(spec.dataset_refs) == 2

    # Invalid
    with pytest.raises(ValidationError, match="Dataset ref must start with 'pit.'"):
        StrategySpecFactory.build(dataset_refs=["raw.oracle_prices"])


def test_strategy_spec_graph_structure():
    """Test that graph has required keys."""
    # Valid
    spec = StrategySpecFactory.build(
        graph={
            "entry": {"signal": "test"},
            "exit": {"signal": "test"},
            "filters": {},
        }
    )
    assert "entry" in spec.graph
    assert "exit" in spec.graph

    # Missing entry
    with pytest.raises(ValidationError, match="Graph missing required keys"):
        StrategySpecFactory.build(graph={"exit": {"signal": "test"}})

    # Missing exit
    with pytest.raises(ValidationError, match="Graph missing required keys"):
        StrategySpecFactory.build(graph={"entry": {"signal": "test"}})


# =============================================================================
# SimMetrics Tests
# =============================================================================

def test_sim_metrics_valid():
    """Test that valid SimMetrics is accepted."""
    metrics = SimMetricsFactory.build()
    assert isinstance(metrics, SimMetrics)
    assert metrics.sharpe > 0


def test_sim_metrics_hit_rate_bounds():
    """Test that hit_rate must be between 0 and 1."""
    # Valid
    SimMetricsFactory.build(hit_rate=0.65)
    SimMetricsFactory.build(hit_rate=0.0)
    SimMetricsFactory.build(hit_rate=1.0)

    # Invalid
    with pytest.raises(ValidationError):
        SimMetricsFactory.build(hit_rate=1.5)
    with pytest.raises(ValidationError):
        SimMetricsFactory.build(hit_rate=-0.1)


# =============================================================================
# StrategySpecOutput Tests
# =============================================================================

def test_strategy_spec_output_valid():
    """Test that valid StrategySpecOutput is accepted."""
    output = StrategySpecOutputFactory.build()
    assert isinstance(output, StrategySpecOutput)
    assert isinstance(output.spec, StrategySpec)


def test_strategy_spec_output_with_rejections():
    """Test StrategySpecOutput with validation rejections."""
    output = StrategySpecOutputFactory.build(
        rejections=["Oracle staleness > 30s", "Spread > 50 bps"]
    )
    assert len(output.rejections) == 2


# =============================================================================
# Citation Tests
# =============================================================================

def test_citation_valid():
    """Test that valid Citation is accepted."""
    citation = CitationFactory.build()
    assert isinstance(citation, Citation)
    assert 0 <= citation.relevance <= 1


def test_citation_relevance_bounds():
    """Test that relevance must be between 0 and 1."""
    # Valid
    CitationFactory.build(relevance=0.0)
    CitationFactory.build(relevance=0.5)
    CitationFactory.build(relevance=1.0)

    # Invalid
    with pytest.raises(ValidationError):
        CitationFactory.build(relevance=1.5)
    with pytest.raises(ValidationError):
        CitationFactory.build(relevance=-0.1)


# =============================================================================
# ExplainedPlan Tests
# =============================================================================

def test_explained_plan_valid():
    """Test that valid ExplainedPlan is accepted."""
    plan = ExplainedPlanFactory.build()
    assert isinstance(plan, ExplainedPlan)
    assert len(plan.summary) > 0


def test_explained_plan_with_citations():
    """Test ExplainedPlan with citations."""
    citations = [
        CitationFactory.build(source="pit.oracle_prices", relevance=0.9),
        CitationFactory.build(source="pit.features", relevance=0.85),
    ]
    plan = ExplainedPlanFactory.build(citations=citations)
    assert len(plan.citations) == 2


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================

@given(
    ask=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip())
)
def test_router_input_property(ask):
    """Property test: any non-empty string should be valid RouterInput."""
    router_input = RouterInput(ask=ask)
    assert len(router_input.ask) > 0


@given(
    sharpe=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False),
    returns_bps=st.floats(min_value=-10000.0, max_value=10000.0, allow_nan=False),
    max_drawdown_bps=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
    hit_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_sim_metrics_property(sharpe, returns_bps, max_drawdown_bps, hit_rate):
    """Property test: SimMetrics accepts valid numeric ranges."""
    metrics = SimMetrics(
        sharpe=sharpe,
        returns_bps=returns_bps,
        max_drawdown_bps=max_drawdown_bps,
        hit_rate=hit_rate,
    )
    assert metrics.hit_rate >= 0.0
    assert metrics.hit_rate <= 1.0
