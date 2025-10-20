"""
Tests for leg library schemas (leg_library.py).

Tests validation logic for:
- LegDefinition, LegLibrary
- JSON parsing
- Input type validation
- Pre-check validation
- Solana program ID validation
"""

import pytest
from pydantic import ValidationError
from pathlib import Path
import tempfile

from .leg_library import (
    LegDefinition,
    LegLibrary,
    create_example_leg_library_json,
)
from .factories import LegDefinitionFactory, LegLibraryFactory


# =============================================================================
# LegDefinition Tests
# =============================================================================

def test_leg_definition_valid():
    """Test that valid LegDefinition is accepted."""
    leg = LegDefinitionFactory.build()
    assert isinstance(leg, LegDefinition)
    assert leg.key == "swap_route"


@pytest.mark.parametrize(
    "key,should_pass",
    [
        ("swap_route", True),
        ("hedge_perp", True),
        ("provide_liquidity", True),
        ("SwapRoute", False),  # uppercase
        ("swap-route", False),  # hyphen
        ("swap.route", False),  # dot
        ("swap route", False),  # space
        ("s", False),  # too short
    ],
)
def test_leg_definition_key_validation(key, should_pass):
    """Test leg key validation."""
    if should_pass:
        leg = LegDefinitionFactory.build(key=key)
        assert leg.key == key
    else:
        with pytest.raises(ValidationError):
            LegDefinitionFactory.build(key=key)


def test_leg_definition_input_types_validation():
    """Test that input type specs are validated."""
    # Valid types
    LegDefinitionFactory.build(
        inputs={
            "from": "mint",
            "to": "mint",
            "amount": "decimal",
            "slippage_bps_max": "int",
        }
    )

    # Valid enum
    LegDefinitionFactory.build(
        inputs={"side": "long|short"}
    )

    # Valid LST enum
    LegDefinitionFactory.build(
        inputs={"lst_out": "mSOL|jitoSOL|bSOL"}
    )


def test_leg_definition_pre_checks_validation():
    """Test that pre-checks are validated."""
    # Valid
    LegDefinitionFactory.build(
        pre_checks=["min_liquidity", "max_spread", "venue_allow"]
    )

    # Invalid
    with pytest.raises(ValidationError, match="Unknown pre-checks"):
        LegDefinitionFactory.build(pre_checks=["unknown_check"])


def test_leg_definition_program_id_validation():
    """Test Solana program ID validation."""
    # Valid program IDs
    valid_ids = [
        "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",
        "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
        "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA",
    ]

    for program_id in valid_ids:
        leg = LegDefinitionFactory.build(program_id=program_id)
        assert leg.program_id == program_id

    # Invalid program IDs
    with pytest.raises(ValidationError, match="Invalid Solana program ID"):
        LegDefinitionFactory.build(program_id="not-a-valid-base58-address")

    with pytest.raises(ValidationError, match="Invalid Solana program ID"):
        LegDefinitionFactory.build(program_id="tooshort")


def test_leg_definition_optional_fields():
    """Test that optional fields can be omitted."""
    leg = LegDefinition(
        key="test_leg",
        inputs={"amount": "decimal"},
    )
    assert leg.program_id is None
    assert leg.venue is None
    assert leg.description is None


# =============================================================================
# LegLibrary Tests
# =============================================================================

def test_leg_library_valid():
    """Test that valid LegLibrary is accepted."""
    library = LegLibraryFactory.build()
    assert isinstance(library, LegLibrary)
    assert library.version >= 1
    assert len(library.legs) > 0


def test_leg_library_unique_keys():
    """Test that duplicate leg keys are rejected."""
    with pytest.raises(ValidationError, match="Duplicate leg keys"):
        LegLibrary(
            version=1,
            legs=[
                LegDefinition(key="swap", inputs={"amount": "decimal"}),
                LegDefinition(key="swap", inputs={"amount": "decimal"}),  # Duplicate
            ],
        )


def test_leg_library_from_json():
    """Test loading LegLibrary from JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "leg_library.json"
        create_example_leg_library_json(json_path)

        library = LegLibrary.from_json(json_path)
        assert library.version == 1
        assert len(library.legs) == 5


def test_leg_library_from_json_file_not_found():
    """Test that from_json raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        LegLibrary.from_json(Path("/nonexistent/leg_library.json"))


def test_leg_library_get_leg():
    """Test getting leg by key."""
    library = LegLibraryFactory.build()

    # Existing leg
    leg = library.get_leg("swap_route")
    assert leg is not None
    assert leg.key == "swap_route"

    # Non-existent leg
    leg = library.get_leg("nonexistent")
    assert leg is None


def test_leg_library_get_legs_by_venue():
    """Test getting legs by venue."""
    library = LegLibrary(
        version=1,
        legs=[
            LegDefinition(key="jup_swap", inputs={"amount": "decimal"}, venue="Jupiter"),
            LegDefinition(key="phx_swap", inputs={"amount": "decimal"}, venue="Phoenix"),
            LegDefinition(key="drift_perp", inputs={"size": "decimal"}, venue="Drift"),
        ],
    )

    jupiter_legs = library.get_legs_by_venue("Jupiter")
    assert len(jupiter_legs) == 1
    assert jupiter_legs[0].key == "jup_swap"

    drift_legs = library.get_legs_by_venue("Drift")
    assert len(drift_legs) == 1

    unknown_legs = library.get_legs_by_venue("Unknown")
    assert len(unknown_legs) == 0


def test_leg_library_to_dict():
    """Test exporting LegLibrary to dictionary."""
    library = LegLibraryFactory.build()
    library_dict = library.to_dict()

    assert library_dict["version"] == library.version
    assert len(library_dict["legs"]) == len(library.legs)


def test_leg_library_immutable():
    """Test that LegLibrary is immutable (frozen=True)."""
    library = LegLibraryFactory.build()

    with pytest.raises(ValidationError):
        library.version = 2


# =============================================================================
# Integration Tests
# =============================================================================

def test_full_leg_library_creation():
    """Test creating a complete LegLibrary from scratch."""
    library = LegLibrary(
        version=1,
        legs=[
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
                description="Swap tokens via Jupiter",
            ),
            LegDefinition(
                key="hedge_perp",
                inputs={
                    "symbol": "string",
                    "side": "long|short",
                    "size": "base_qty",
                },
                pre_checks=["funding_ceiling", "max_spread", "oracle_fresh"],
                program_id="dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
                venue="Drift",
                description="Open perp hedge on Drift",
            ),
        ],
    )

    assert library.version == 1
    assert len(library.legs) == 2
    assert library.get_leg("swap_route") is not None
    assert library.get_leg("hedge_perp") is not None


def test_example_json_roundtrip():
    """Test that example JSON can be loaded and validated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "leg_library.json"
        create_example_leg_library_json(json_path)

        # Load it
        library = LegLibrary.from_json(json_path)

        # Export to dict
        library_dict = library.to_dict()

        # Recreate from dict
        library2 = LegLibrary(**library_dict)

        # Should be identical
        assert library.version == library2.version
        assert len(library.legs) == len(library2.legs)


def test_leg_library_with_all_known_types():
    """Test LegLibrary with all known input types."""
    library = LegLibrary(
        version=1,
        legs=[
            LegDefinition(
                key="test_all_types",
                inputs={
                    "decimal_param": "decimal",
                    "int_param": "int",
                    "mint_param": "mint",
                    "pubkey_param": "pubkey",
                    "string_param": "string",
                    "bool_param": "bool",
                    "enum_param": "long|short",
                    "asset_param": "SOL",
                    "lst_param": "mSOL|jitoSOL|bSOL",
                    "perp_param": "SOL-PERP",
                    "qty_param": "base_qty",
                },
            ),
        ],
    )

    assert len(library.legs) == 1
    assert len(library.legs[0].inputs) == 11


def test_leg_library_with_all_known_pre_checks():
    """Test LegLibrary with all known pre-checks."""
    library = LegLibrary(
        version=1,
        legs=[
            LegDefinition(
                key="test_all_checks",
                inputs={"amount": "decimal"},
                pre_checks=[
                    "min_liquidity",
                    "max_spread",
                    "venue_allow",
                    "oracle_fresh",
                    "peg_ok",
                    "funding_ceiling",
                    "hf_above_floor",
                    "utilization_ok",
                ],
            ),
        ],
    )

    assert len(library.legs[0].pre_checks) == 8
