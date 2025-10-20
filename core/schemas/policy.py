"""
Pydantic schemas for policy configuration (rules.yml parsing).

Defines the schema for Layer 6 risk controls that are enforced at:
- Compile time (RouterAgent/PlannerAgent)
- Runtime (ExecutorAgent)
- On-chain (Vault contract)

All policy values must be consistent across these layers to maintain
the safety contract.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pathlib import Path
import yaml


# =============================================================================
# Policy Configuration Schemas (Task 2.4)
# =============================================================================

class HFFloors(BaseModel):
    """Health factor floor configurations."""

    default: float = Field(..., ge=1.0, le=10.0, description="Default HF floor")
    auto_loop: float = Field(..., ge=1.0, le=10.0, description="Auto-loop HF floor")
    emergency: float = Field(..., ge=1.0, le=10.0, description="Emergency HF floor")

    model_config = ConfigDict(frozen=True)


class Floors(BaseModel):
    """Numeric floor constraints."""

    hf: HFFloors = Field(..., description="Health factor floors")

    max_spread_bps: int = Field(
        ..., ge=0, le=10000, description="Max spread in bps"
    )

    min_liquidity_usd: float = Field(
        ..., ge=0.0, description="Min liquidity in USD"
    )

    oracle_delta_bps_max: int = Field(
        ..., ge=0, le=10000, description="Max oracle delta in bps"
    )

    oracle_staleness_ms_max: int = Field(
        ..., ge=0, description="Max oracle staleness in milliseconds"
    )

    max_priority_fee_microlamports_per_cu: int = Field(
        ..., ge=0, description="Max priority fee in microlamports per CU"
    )

    model_config = ConfigDict(frozen=True)


class AllowedAssets(BaseModel):
    """Allowed asset configurations."""

    base: List[str] = Field(
        ..., min_length=1, description="Allowed base assets"
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("base")
    @classmethod
    def validate_asset_symbols(cls, v: List[str]) -> List[str]:
        """Validate asset symbols are alphanumeric (allow mixed case for LSTs like mSOL)."""
        for asset in v:
            # Allow alphanumeric + underscores (SOL, mSOL, jitoSOL, SOL_USD all valid)
            if not asset.replace("_", "").isalnum():
                raise ValueError(f"Invalid asset symbol: {asset}. Must be alphanumeric.")
        return v


class Policy(BaseModel):
    """Core policy flags and allowlists."""

    pit_only: bool = Field(..., description="Enforce PIT-only data access")

    forbid_freeform_numbers: bool = Field(
        ..., description="Block freeform numbers in agent outputs"
    )

    allowed_assets: AllowedAssets = Field(
        ..., description="Allowed asset configurations"
    )

    allowed_venues: List[str] = Field(
        ..., min_length=1, description="Allowed venue names"
    )

    model_config = ConfigDict(frozen=True)


class Compatibility(BaseModel):
    """Cross-venue compatibility mappings."""

    lp_base_to_perp: Dict[str, List[str]] = Field(
        ..., description="LP base asset to perp market mappings"
    )

    model_config = ConfigDict(frozen=True)


class VenueAllowlists(BaseModel):
    """Venue allowlists by context."""

    default: List[str] = Field(
        ..., min_length=1, description="Default allowed venues"
    )

    model_config = ConfigDict(frozen=True)


class Allowlists(BaseModel):
    """Allowlist configurations."""

    venues: VenueAllowlists = Field(..., description="Venue allowlists")

    model_config = ConfigDict(frozen=True)


class PolicyConfig(BaseModel):
    """
    Complete policy configuration from rules.yml.

    This is the single source of truth for risk controls that are enforced
    across all layers (compile-time, runtime, on-chain).
    """

    version: int = Field(..., ge=1, description="Config schema version")

    policy: Policy = Field(..., description="Core policy flags and allowlists")

    floors: Floors = Field(..., description="Numeric floor constraints")

    compatibility: Compatibility = Field(
        ..., description="Cross-venue compatibility mappings"
    )

    allowlists: Allowlists = Field(..., description="Allowlist configurations")

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_yaml(cls, path: Path) -> "PolicyConfig":
        """
        Load PolicyConfig from YAML file.

        Args:
            path: Path to rules.yml file

        Returns:
            Validated PolicyConfig instance

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML is malformed or validation fails
        """
        if not path.exists():
            raise FileNotFoundError(f"Policy file not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def to_dict(self) -> Dict:
        """Export PolicyConfig as dictionary for tool dependencies."""
        return self.model_dump()


# =============================================================================
# Example Usage and Validation
# =============================================================================

def create_example_rules_yaml(output_path: Path) -> None:
    """
    Create an example rules.yml file for reference.

    Args:
        output_path: Where to write the example file
    """
    example = {
        "version": 1,
        "policy": {
            "pit_only": True,
            "forbid_freeform_numbers": True,
            "allowed_assets": {
                "base": ["SOL", "mSOL", "jitoSOL", "bSOL", "BTC", "ETH", "USDC", "USDT"]
            },
            "allowed_venues": [
                "Jupiter",
                "Phoenix",
                "Drift",
                "Marginfi",
                "Solend",
                "Orca",
                "Raydium",
                "Meteora",
            ],
        },
        "floors": {
            "hf": {"default": 1.5, "auto_loop": 1.6, "emergency": 1.3},
            "max_spread_bps": 50,
            "min_liquidity_usd": 100000,
            "oracle_delta_bps_max": 100,
            "oracle_staleness_ms_max": 10000,
            "max_priority_fee_microlamports_per_cu": 1500,
        },
        "compatibility": {
            "lp_base_to_perp": {
                "SOL": ["SOL-PERP"],
                "BTC": ["BTC-PERP"],
                "ETH": ["ETH-PERP"],
            }
        },
        "allowlists": {
            "venues": {
                "default": [
                    "Jupiter",
                    "Phoenix",
                    "Drift",
                    "Marginfi",
                    "Solend",
                    "Orca",
                    "Raydium",
                    "Meteora",
                ]
            }
        },
    }

    with open(output_path, "w") as f:
        yaml.dump(example, f, default_flow_style=False, sort_keys=False)
