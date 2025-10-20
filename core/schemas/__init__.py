"""
Core schemas for Layer 4 agent I/O and policy configuration.

This package contains:
- models.py: Agent I/O schemas (RouterInput, RouterDecision, StrategySpec, etc.)
- policy.py: Policy configuration (rules.yml parsing)
- leg_library.py: Leg library (leg_library.json parsing)
- factories.py: Test data factories
"""

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

from .leg_library import (
    LegDefinition,
    LegLibrary,
)

__all__ = [
    # models.py
    "RouterInput",
    "RouterDecision",
    "PlannerInput",
    "StrategySpec",
    "SimMetrics",
    "StrategySpecOutput",
    "Citation",
    "ExplainedPlan",
    # policy.py
    "PolicyConfig",
    "Policy",
    "AllowedAssets",
    "Floors",
    "HFFloors",
    "Compatibility",
    "Allowlists",
    "VenueAllowlists",
    # leg_library.py
    "LegDefinition",
    "LegLibrary",
]
