"""
Pydantic schemas for Layer 4 agent I/O.

Defines type-safe input/output models for:
- RouterAgent: Parse user asks into structured constraints
- PlannerAgent: Build StrategySpec with tool calls
- NarratorAgent: Explain with citations

All schemas enforce strict validation to prevent malformed data from
propagating through the agent pipeline.
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


# =============================================================================
# Router Agent Schemas (Task 2.1)
# =============================================================================

class RouterInput(BaseModel):
    """Input to RouterAgent: raw user ask."""

    ask: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's natural language request for a trading strategy",
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("ask")
    @classmethod
    def validate_ask_not_empty(cls, v: str) -> str:
        """Ensure ask is not just whitespace."""
        if not v.strip():
            raise ValueError("ask cannot be empty or only whitespace")
        return v.strip()


class RouterDecision(BaseModel):
    """Output from RouterAgent: structured constraints for Planner."""

    kind: Literal["strategy", "research", "explain"] = Field(
        ..., description="Type of request: strategy, research, or explain"
    )

    assets: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Asset pairs (e.g., SOL/USD, BTC/USD)",
    )

    risk: Literal["Low", "Medium", "High"] = Field(
        ..., description="Risk tolerance level"
    )

    horizon: str = Field(
        ...,
        pattern=r"^\d+[dhw]$",
        description="Time horizon: e.g., 7d, 24h, 2w",
    )

    archetype: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Strategy archetype: trend_follow, mean_revert, arb, etc.",
    )

    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional constraints: max_slippage_bps, max_drawdown_bps, etc.",
    )

    next_steps: List[str] = Field(
        default_factory=lambda: ["validate", "compile", "simulate"],
        description="Pipeline steps to execute",
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("assets")
    @classmethod
    def validate_asset_format(cls, v: List[str]) -> List[str]:
        """Validate asset pairs follow BASE/QUOTE format."""
        asset_pattern = re.compile(r"^[A-Z0-9]{2,10}/[A-Z]{3,4}$")
        for asset in v:
            if not asset_pattern.match(asset):
                raise ValueError(
                    f"Invalid asset format: {asset}. Expected BASE/QUOTE (e.g., SOL/USD)"
                )
        return v

    @field_validator("constraints")
    @classmethod
    def validate_constraint_keys(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate constraint keys are known."""
        known_keys = {
            "max_slippage_bps",
            "max_drawdown_bps",
            "min_sharpe",
            "max_leverage",
            "min_liquidity_usd",
            "max_concentration_bps",
        }
        unknown = set(v.keys()) - known_keys
        if unknown:
            raise ValueError(f"Unknown constraint keys: {unknown}")

        # Validate bps values are in range [0, 10000]
        for key in ["max_slippage_bps", "max_drawdown_bps", "max_concentration_bps"]:
            if key in v:
                val = v[key]
                if not isinstance(val, (int, float)) or not (0 <= val <= 10000):
                    raise ValueError(f"{key} must be between 0 and 10000 bps")

        return v


# =============================================================================
# Planner Agent Schemas (Task 2.2)
# =============================================================================

class PlannerInput(BaseModel):
    """Input to PlannerAgent: RouterDecision from previous stage."""

    decision: RouterDecision = Field(
        ..., description="Structured constraints from RouterAgent"
    )

    model_config = ConfigDict(frozen=True)


class StrategySpec(BaseModel):
    """Core strategy specification that Planner builds."""

    name: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+$",
        min_length=3,
        max_length=50,
        description="Strategy name: lowercase, alphanumeric + underscores only",
    )

    category: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Strategy category: trend_follow, mean_revert, arb, etc.",
    )

    assets: List[str] = Field(
        ..., min_length=1, description="Asset symbols (e.g., SOL, BTC)"
    )

    dataset_refs: List[str] = Field(
        ..., min_length=1, description="PIT table references (e.g., pit.oracle_prices)"
    )

    graph: Dict[str, Any] = Field(
        ..., description="Strategy logic: entry, exit, filters, position_sizing"
    )

    guards: Dict[str, Any] = Field(
        ..., description="Safety guardrails: oracle_staleness_ms_max, etc."
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional metadata: tags, version, etc."
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("dataset_refs")
    @classmethod
    def validate_pit_only(cls, v: List[str]) -> List[str]:
        """Ensure all dataset refs are PIT tables."""
        for ref in v:
            if not ref.startswith("pit."):
                raise ValueError(f"Dataset ref must start with 'pit.': {ref}")
        return v

    @field_validator("graph")
    @classmethod
    def validate_graph_structure(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate graph has required keys."""
        required_keys = {"entry", "exit"}
        missing = required_keys - set(v.keys())
        if missing:
            raise ValueError(f"Graph missing required keys: {missing}")
        return v


class SimMetrics(BaseModel):
    """Simulation metrics from backtester."""

    sharpe: float = Field(..., description="Sharpe ratio")
    returns_bps: float = Field(..., description="Total returns in bps")
    max_drawdown_bps: float = Field(..., description="Max drawdown in bps")
    hit_rate: float = Field(..., ge=0.0, le=1.0, description="Win rate (0-1)")
    capacity_usd: Optional[float] = Field(None, description="Strategy capacity in USD")
    fee_drag_bps: Optional[float] = Field(None, description="Fee impact in bps")

    model_config = ConfigDict(frozen=True)


class StrategySpecOutput(BaseModel):
    """Output from PlannerAgent: validated spec + simulation results."""

    spec: StrategySpec = Field(..., description="Validated strategy specification")

    plan_graph: Optional[Dict[str, Any]] = Field(
        None, description="Compiled plan graph from compiler"
    )

    sim_metrics: Optional[SimMetrics] = Field(
        None, description="Simulation metrics from backtester"
    )

    rejections: List[str] = Field(
        default_factory=list,
        description="List of guardrail violations or validation errors",
    )

    model_config = ConfigDict(frozen=True)


# =============================================================================
# Narrator Agent Schemas (Task 2.3)
# =============================================================================

class Citation(BaseModel):
    """Evidence citation from knowledge base."""

    source: str = Field(
        ..., min_length=1, description="Source reference (e.g., pit.oracle_prices)"
    )

    snippet: str = Field(
        ..., min_length=1, max_length=500, description="Relevant text snippet"
    )

    relevance: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score (0-1)"
    )

    model_config = ConfigDict(frozen=True)


class ExplainedPlan(BaseModel):
    """Output from NarratorAgent: explained strategy with citations."""

    summary: str = Field(
        ..., min_length=1, max_length=2000, description="Human-readable explanation"
    )

    citations: List[Citation] = Field(
        default_factory=list, description="Evidence citations from knowledge base"
    )

    caps_enforced: List[str] = Field(
        default_factory=list, description="List of guardrails enforced"
    )

    sim_metrics: Optional[SimMetrics] = Field(
        None, description="Simulation metrics for reference"
    )

    model_config = ConfigDict(frozen=True)
