"""
Factory pattern for generating test data for schema validation.

Uses factory_boy to create valid test instances of all Pydantic models.
"""

import factory
from factory import Factory, SubFactory, LazyAttribute, LazyFunction, Faker
from typing import Dict, Any

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
from .policy import (
    PolicyConfig,
    Policy,
    AllowedAssets,
    Floors,
    HFFloors,
    Compatibility,
    Allowlists,
    VenueAllowlists,
)
from .leg_library import LegDefinition, LegLibrary


# =============================================================================
# Router Agent Factories
# =============================================================================

class RouterInputFactory(Factory):
    class Meta:
        model = RouterInput

    ask = Faker("sentence", nb_words=10)


class RouterDecisionFactory(Factory):
    class Meta:
        model = RouterDecision

    kind = "strategy"
    assets = ["SOL/USD"]
    risk = "Medium"
    horizon = "7d"
    archetype = "trend_follow"
    constraints = factory.LazyFunction(lambda: {"max_slippage_bps": 50})
    next_steps = factory.LazyFunction(lambda: ["validate", "compile", "simulate"])


# =============================================================================
# Planner Agent Factories
# =============================================================================

class PlannerInputFactory(Factory):
    class Meta:
        model = PlannerInput

    decision = SubFactory(RouterDecisionFactory)


class StrategySpecFactory(Factory):
    class Meta:
        model = StrategySpec

    name = "sol_trend_7d"
    category = "trend_follow"
    assets = ["SOL"]
    dataset_refs = ["pit.oracle_prices_by_feed", "pit.features"]
    graph = factory.LazyFunction(
        lambda: {
            "entry": {"signal": "ema_cross", "params": {"fast": 12, "slow": 26}},
            "exit": {"signal": "stop_loss", "params": {"stop_bps": 500}},
        }
    )
    guards = factory.LazyFunction(
        lambda: {
            "oracle_staleness_ms_max": 30000,
            "max_spread_bps": 50,
            "hf_floor": 1.5,
        }
    )
    metadata = factory.LazyFunction(lambda: {})


class SimMetricsFactory(Factory):
    class Meta:
        model = SimMetrics

    sharpe = 1.5
    returns_bps = 2500
    max_drawdown_bps = 800
    hit_rate = 0.65
    capacity_usd = 1000000.0
    fee_drag_bps = 15


class StrategySpecOutputFactory(Factory):
    class Meta:
        model = StrategySpecOutput

    spec = SubFactory(StrategySpecFactory)
    plan_graph = factory.LazyFunction(lambda: {"nodes": [], "edges": []})
    sim_metrics = SubFactory(SimMetricsFactory)
    rejections = factory.LazyFunction(lambda: [])


# =============================================================================
# Narrator Agent Factories
# =============================================================================

class CitationFactory(Factory):
    class Meta:
        model = Citation

    source = "pit.oracle_prices_by_feed"
    snippet = Faker("sentence", nb_words=20)
    relevance = 0.85


class ExplainedPlanFactory(Factory):
    class Meta:
        model = ExplainedPlan

    summary = Faker("text", max_nb_chars=500)
    citations = factory.LazyFunction(lambda: [])
    caps_enforced = factory.LazyFunction(
        lambda: ["hf_floor=1.5", "oracle_staleness_ms_max=30000"]
    )
    sim_metrics = SubFactory(SimMetricsFactory)


# =============================================================================
# Policy Configuration Factories
# =============================================================================

class HFFloorsFactory(Factory):
    class Meta:
        model = HFFloors

    default = 1.5
    auto_loop = 1.6
    emergency = 1.3


class FloorsFactory(Factory):
    class Meta:
        model = Floors

    hf = SubFactory(HFFloorsFactory)
    max_spread_bps = 50
    min_liquidity_usd = 100000.0
    oracle_delta_bps_max = 100
    oracle_staleness_ms_max = 10000
    max_priority_fee_microlamports_per_cu = 1500


class AllowedAssetsFactory(Factory):
    class Meta:
        model = AllowedAssets

    base = factory.LazyFunction(
        lambda: ["SOL", "mSOL", "jitoSOL", "bSOL", "BTC", "ETH", "USDC", "USDT"]
    )


class PolicyFactory(Factory):
    class Meta:
        model = Policy

    pit_only = True
    forbid_freeform_numbers = True
    allowed_assets = SubFactory(AllowedAssetsFactory)
    allowed_venues = factory.LazyFunction(
        lambda: ["Jupiter", "Phoenix", "Drift", "Marginfi", "Solend"]
    )


class CompatibilityFactory(Factory):
    class Meta:
        model = Compatibility

    lp_base_to_perp = factory.LazyFunction(
        lambda: {"SOL": ["SOL-PERP"], "BTC": ["BTC-PERP"], "ETH": ["ETH-PERP"]}
    )


class VenueAllowlistsFactory(Factory):
    class Meta:
        model = VenueAllowlists

    default = factory.LazyFunction(
        lambda: ["Jupiter", "Phoenix", "Drift", "Marginfi", "Solend"]
    )


class AllowlistsFactory(Factory):
    class Meta:
        model = Allowlists

    venues = SubFactory(VenueAllowlistsFactory)


class PolicyConfigFactory(Factory):
    class Meta:
        model = PolicyConfig

    version = 1
    policy = SubFactory(PolicyFactory)
    floors = SubFactory(FloorsFactory)
    compatibility = SubFactory(CompatibilityFactory)
    allowlists = SubFactory(AllowlistsFactory)


# =============================================================================
# Leg Library Factories
# =============================================================================

class LegDefinitionFactory(Factory):
    class Meta:
        model = LegDefinition

    key = "swap_route"
    inputs = factory.LazyFunction(
        lambda: {
            "from": "mint",
            "to": "mint",
            "amount": "decimal",
            "slippage_bps_max": "int",
        }
    )
    pre_checks = factory.LazyFunction(
        lambda: ["min_liquidity", "max_spread", "venue_allow"]
    )
    program_id = "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB"
    venue = "Jupiter"
    description = "Swap tokens via Jupiter aggregator"


class LegLibraryFactory(Factory):
    class Meta:
        model = LegLibrary

    version = 1
    legs = factory.LazyFunction(
        lambda: [
            LegDefinition(
                key="swap_route",
                inputs={
                    "from": "mint",
                    "to": "mint",
                    "amount": "decimal",
                    "slippage_bps_max": "int",
                },
                pre_checks=["min_liquidity", "max_spread", "venue_allow"],
                program_id="JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",
                venue="Jupiter",
            ),
            LegDefinition(
                key="hedge_perp",
                inputs={"symbol": "string", "side": "long|short", "size": "base_qty"},
                pre_checks=["funding_ceiling", "max_spread", "oracle_fresh"],
                program_id="dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
                venue="Drift",
            ),
        ]
    )
