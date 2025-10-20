"""
Pydantic schemas for leg library (leg_library.json parsing).

Defines the schema for trading "legs" (atomic DeFi operations) that the
Planner can compose into strategies. Each leg has:
- Input schema (typed parameters)
- Pre-checks (guardrails that must pass before execution)
- Venue/program bindings

The leg library is evidence-only: all legs must reference real Solana programs
with verified addresses.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pathlib import Path
import json
import re


# =============================================================================
# Leg Library Schemas (Task 2.5)
# =============================================================================

class LegDefinition(BaseModel):
    """
    Definition of a single trading leg (atomic DeFi operation).

    Examples:
    - swap_route: Jupiter/Phoenix swap
    - stake: LST staking (SOL → mSOL/jitoSOL/bSOL)
    - hedge_perp: Drift/Mango perp hedge
    - lend: Marginfi/Solend lending
    - provide_liquidity: Orca/Raydium LP
    """

    key: str = Field(
        ...,
        pattern=r"^[a-z_]+$",
        min_length=2,
        max_length=50,
        description="Unique leg identifier (lowercase, underscores only)",
    )

    inputs: Dict[str, str] = Field(
        ...,
        min_length=1,
        description="Input schema: param_name -> type_spec (e.g., 'decimal', 'int', 'mint')",
    )

    pre_checks: List[str] = Field(
        default_factory=list,
        description="Required pre-checks (e.g., 'min_liquidity', 'max_spread', 'venue_allow')",
    )

    program_id: Optional[str] = Field(
        None,
        description="Solana program ID (base58 public key)",
    )

    venue: Optional[str] = Field(
        None,
        description="Venue name (e.g., Jupiter, Phoenix, Drift)",
    )

    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Human-readable description of what this leg does",
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("inputs")
    @classmethod
    def validate_input_types(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate input type specs are known."""
        known_types = {
            "decimal",
            "int",
            "mint",
            "pubkey",
            "string",
            "bool",
            "long|short",  # Enum-like
            "SOL",  # Asset literal
            "mSOL|jitoSOL|bSOL",  # LST enum
            "SOL-PERP",  # Perp market
            "base_qty",  # Quantity type
        }

        # Check each type spec
        for param, type_spec in v.items():
            # Allow exact matches or pipe-separated enums
            if type_spec not in known_types and "|" not in type_spec:
                # Check if it's a valid enum-like type
                parts = type_spec.split("|")
                if not all(p.replace("-", "").replace("_", "").isalnum() for p in parts):
                    raise ValueError(
                        f"Unknown type spec for '{param}': {type_spec}. "
                        f"Must be one of {known_types} or a pipe-separated enum."
                    )

        return v

    @field_validator("pre_checks")
    @classmethod
    def validate_pre_checks(cls, v: List[str]) -> List[str]:
        """Validate pre-check names are known."""
        known_checks = {
            "min_liquidity",
            "max_spread",
            "venue_allow",
            "oracle_fresh",
            "peg_ok",
            "funding_ceiling",
            "hf_above_floor",
            "utilization_ok",
        }

        unknown = set(v) - known_checks
        if unknown:
            raise ValueError(f"Unknown pre-checks: {unknown}")

        return v

    @field_validator("program_id")
    @classmethod
    def validate_program_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate Solana program ID is base58."""
        if v is None:
            return v

        # Base58 pattern (simple check - actual validation would use base58 decode)
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", v):
            raise ValueError(f"Invalid Solana program ID (base58): {v}")

        return v


class LegLibrary(BaseModel):
    """
    Complete leg library containing all available trading legs.

    This is the evidence-only catalog that the Planner uses to build strategies.
    No hallucinated legs allowed - all must be defined here with verified program IDs.
    """

    version: int = Field(..., ge=1, description="Library schema version")

    legs: List[LegDefinition] = Field(
        ..., min_length=1, description="List of available leg definitions"
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("legs")
    @classmethod
    def validate_unique_keys(cls, v: List[LegDefinition]) -> List[LegDefinition]:
        """Ensure leg keys are unique."""
        keys = [leg.key for leg in v]
        duplicates = [k for k in keys if keys.count(k) > 1]
        if duplicates:
            raise ValueError(f"Duplicate leg keys: {set(duplicates)}")
        return v

    @field_validator("legs")
    @classmethod
    def validate_no_circular_dependencies(cls, v: List[LegDefinition]) -> List[LegDefinition]:
        """
        Check for circular dependencies in leg definitions.

        For now, this is a placeholder. In the future, if legs can reference
        other legs, we'd need to detect cycles.
        """
        # Placeholder: current leg schema doesn't have dependencies field
        # If added in future, implement cycle detection here
        return v

    @classmethod
    def from_json(cls, path: Path) -> "LegLibrary":
        """
        Load LegLibrary from JSON file.

        Args:
            path: Path to leg_library.json file

        Returns:
            Validated LegLibrary instance

        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON is malformed or validation fails
        """
        if not path.exists():
            raise FileNotFoundError(f"Leg library file not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)

        return cls(**data)

    def get_leg(self, key: str) -> Optional[LegDefinition]:
        """
        Get leg definition by key.

        Args:
            key: Leg identifier

        Returns:
            LegDefinition if found, None otherwise
        """
        for leg in self.legs:
            if leg.key == key:
                return leg
        return None

    def get_legs_by_venue(self, venue: str) -> List[LegDefinition]:
        """
        Get all legs for a specific venue.

        Args:
            venue: Venue name

        Returns:
            List of LegDefinition instances
        """
        return [leg for leg in self.legs if leg.venue == venue]

    def to_dict(self) -> Dict:
        """Export LegLibrary as dictionary for tool dependencies."""
        return self.model_dump()


# =============================================================================
# Example Usage and Validation
# =============================================================================

def create_example_leg_library_json(output_path: Path) -> None:
    """
    Create an example leg_library.json file for reference.

    Args:
        output_path: Where to write the example file
    """
    example = {
        "version": 1,
        "legs": [
            {
                "key": "swap_route",
                "inputs": {
                    "from": "mint",
                    "to": "mint",
                    "amount": "decimal",
                    "slippage_bps_max": "int",
                },
                "pre_checks": ["min_liquidity", "max_spread", "venue_allow"],
                "program_id": "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",
                "venue": "Jupiter",
                "description": "Swap tokens via Jupiter aggregator with slippage protection",
            },
            {
                "key": "stake",
                "inputs": {
                    "asset_in": "SOL",
                    "lst_out": "mSOL|jitoSOL|bSOL",
                    "amount": "decimal",
                },
                "pre_checks": ["oracle_fresh", "peg_ok", "venue_allow"],
                "venue": "Marinade",
                "description": "Stake SOL for liquid staking token (LST)",
            },
            {
                "key": "hedge_perp",
                "inputs": {
                    "symbol": "string",
                    "side": "long|short",
                    "size": "base_qty",
                },
                "pre_checks": ["funding_ceiling", "max_spread", "oracle_fresh"],
                "program_id": "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
                "venue": "Drift",
                "description": "Open perpetual hedge position on Drift",
            },
            {
                "key": "lend",
                "inputs": {
                    "asset": "mint",
                    "amount": "decimal",
                },
                "pre_checks": ["utilization_ok", "oracle_fresh", "venue_allow"],
                "program_id": "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA",
                "venue": "Marginfi",
                "description": "Lend assets to Marginfi money market",
            },
            {
                "key": "provide_liquidity",
                "inputs": {
                    "pool_id": "pubkey",
                    "token_a_amount": "decimal",
                    "token_b_amount": "decimal",
                },
                "pre_checks": ["min_liquidity", "oracle_fresh", "venue_allow"],
                "program_id": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
                "venue": "Orca",
                "description": "Provide liquidity to Orca CLMM pool",
            },
        ],
    }

    with open(output_path, "w") as f:
        json.dump(example, f, indent=2)
