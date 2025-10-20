"""
Tests for policy configuration schemas (policy.py).

Tests validation logic for:
- PolicyConfig, Policy, Floors, Allowlists
- YAML parsing
- Numeric bounds validation
"""

import pytest
from pydantic import ValidationError
from pathlib import Path
import tempfile

from .policy import (
    PolicyConfig,
    Policy,
    AllowedAssets,
    Floors,
    HFFloors,
    Compatibility,
    Allowlists,
    VenueAllowlists,
    create_example_rules_yaml,
)
from .factories import (
    PolicyConfigFactory,
    PolicyFactory,
    FloorsFactory,
    HFFloorsFactory,
    AllowedAssetsFactory,
)


# =============================================================================
# HFFloors Tests
# =============================================================================

def test_hf_floors_valid():
    """Test that valid HFFloors is accepted."""
    hf = HFFloorsFactory.build()
    assert hf.default >= 1.0
    assert hf.auto_loop >= 1.0
    assert hf.emergency >= 1.0


@pytest.mark.parametrize(
    "default,auto_loop,emergency",
    [
        (1.0, 1.1, 1.0),  # Minimum valid
        (1.5, 1.6, 1.3),  # Typical
        (10.0, 10.0, 10.0),  # Maximum valid
    ],
)
def test_hf_floors_ranges(default, auto_loop, emergency):
    """Test HFFloors accepts valid ranges."""
    hf = HFFloors(default=default, auto_loop=auto_loop, emergency=emergency)
    assert hf.default == default


def test_hf_floors_rejects_out_of_bounds():
    """Test that HFFloors rejects values outside [1.0, 10.0]."""
    with pytest.raises(ValidationError):
        HFFloors(default=0.5, auto_loop=1.6, emergency=1.3)  # Too low

    with pytest.raises(ValidationError):
        HFFloors(default=15.0, auto_loop=1.6, emergency=1.3)  # Too high


# =============================================================================
# Floors Tests
# =============================================================================

def test_floors_valid():
    """Test that valid Floors is accepted."""
    floors = FloorsFactory.build()
    assert isinstance(floors.hf, HFFloors)
    assert 0 <= floors.max_spread_bps <= 10000


def test_floors_bps_validation():
    """Test that bps values are validated."""
    # Valid
    FloorsFactory.build(max_spread_bps=50, oracle_delta_bps_max=100)

    # Out of range
    with pytest.raises(ValidationError):
        FloorsFactory.build(max_spread_bps=15000)

    with pytest.raises(ValidationError):
        FloorsFactory.build(oracle_delta_bps_max=-10)


def test_floors_numeric_validation():
    """Test numeric field validation."""
    # Valid
    FloorsFactory.build(
        min_liquidity_usd=100000.0,
        oracle_staleness_ms_max=10000,
        max_priority_fee_microlamports_per_cu=1500,
    )

    # Negative liquidity
    with pytest.raises(ValidationError):
        FloorsFactory.build(min_liquidity_usd=-1000.0)

    # Negative staleness
    with pytest.raises(ValidationError):
        FloorsFactory.build(oracle_staleness_ms_max=-100)


# =============================================================================
# AllowedAssets Tests
# =============================================================================

def test_allowed_assets_valid():
    """Test that valid AllowedAssets is accepted."""
    assets = AllowedAssetsFactory.build()
    assert len(assets.base) > 0


def test_allowed_assets_validation():
    """Test that asset symbols must be alphanumeric."""
    # Valid (uppercase)
    AllowedAssets(base=["SOL", "BTC", "ETH"])

    # Valid (LSTs with mixed case)
    AllowedAssets(base=["mSOL", "jitoSOL", "bSOL"])

    # Invalid (special characters)
    with pytest.raises(ValidationError, match="Invalid asset symbol"):
        AllowedAssets(base=["SOL-USD"])

    # Invalid (spaces)
    with pytest.raises(ValidationError, match="Invalid asset symbol"):
        AllowedAssets(base=["SOL USD"])


def test_allowed_assets_alphanumeric():
    """Test that asset symbols can have underscores and numbers."""
    # Valid
    AllowedAssets(base=["mSOL", "jitoSOL", "bSOL", "SOL_USD"])


# =============================================================================
# Policy Tests
# =============================================================================

def test_policy_valid():
    """Test that valid Policy is accepted."""
    policy = PolicyFactory.build()
    assert policy.pit_only is True
    assert policy.forbid_freeform_numbers is True
    assert len(policy.allowed_venues) > 0


def test_policy_flags():
    """Test policy flags."""
    policy = PolicyFactory.build(pit_only=False, forbid_freeform_numbers=False)
    assert policy.pit_only is False
    assert policy.forbid_freeform_numbers is False


def test_policy_allowed_venues_not_empty():
    """Test that allowed_venues must have at least one venue."""
    with pytest.raises(ValidationError):
        PolicyFactory.build(allowed_venues=[])


# =============================================================================
# Compatibility Tests
# =============================================================================

def test_compatibility_valid():
    """Test that valid Compatibility is accepted."""
    compat = Compatibility(
        lp_base_to_perp={
            "SOL": ["SOL-PERP"],
            "BTC": ["BTC-PERP"],
            "ETH": ["ETH-PERP"],
        }
    )
    assert "SOL" in compat.lp_base_to_perp


# =============================================================================
# Allowlists Tests
# =============================================================================

def test_venue_allowlists_valid():
    """Test that valid VenueAllowlists is accepted."""
    allowlists = VenueAllowlists(
        default=["Jupiter", "Phoenix", "Drift"]
    )
    assert len(allowlists.default) == 3


def test_venue_allowlists_not_empty():
    """Test that venue allowlists must have at least one venue."""
    with pytest.raises(ValidationError):
        VenueAllowlists(default=[])


# =============================================================================
# PolicyConfig Tests
# =============================================================================

def test_policy_config_valid():
    """Test that valid PolicyConfig is accepted."""
    config = PolicyConfigFactory.build()
    assert config.version >= 1
    assert isinstance(config.policy, Policy)
    assert isinstance(config.floors, Floors)


def test_policy_config_from_yaml():
    """Test loading PolicyConfig from YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_path = Path(tmpdir) / "rules.yml"
        create_example_rules_yaml(yaml_path)

        config = PolicyConfig.from_yaml(yaml_path)
        assert config.version == 1
        assert config.policy.pit_only is True
        assert config.floors.max_spread_bps == 50


def test_policy_config_from_yaml_file_not_found():
    """Test that from_yaml raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        PolicyConfig.from_yaml(Path("/nonexistent/rules.yml"))


def test_policy_config_to_dict():
    """Test exporting PolicyConfig to dictionary."""
    config = PolicyConfigFactory.build()
    config_dict = config.to_dict()

    assert config_dict["version"] == config.version
    assert config_dict["policy"]["pit_only"] == config.policy.pit_only
    assert config_dict["floors"]["max_spread_bps"] == config.floors.max_spread_bps


def test_policy_config_immutable():
    """Test that PolicyConfig is immutable (frozen=True)."""
    config = PolicyConfigFactory.build()

    with pytest.raises(ValidationError):
        config.version = 2


# =============================================================================
# Integration Tests
# =============================================================================

def test_full_policy_config_creation():
    """Test creating a complete PolicyConfig from scratch."""
    config = PolicyConfig(
        version=1,
        policy=Policy(
            pit_only=True,
            forbid_freeform_numbers=True,
            allowed_assets=AllowedAssets(base=["SOL", "BTC"]),
            allowed_venues=["Jupiter", "Phoenix"],
        ),
        floors=Floors(
            hf=HFFloors(default=1.5, auto_loop=1.6, emergency=1.3),
            max_spread_bps=50,
            min_liquidity_usd=100000.0,
            oracle_delta_bps_max=100,
            oracle_staleness_ms_max=10000,
            max_priority_fee_microlamports_per_cu=1500,
        ),
        compatibility=Compatibility(lp_base_to_perp={"SOL": ["SOL-PERP"]}),
        allowlists=Allowlists(venues=VenueAllowlists(default=["Jupiter"])),
    )

    assert config.version == 1
    assert "SOL" in config.policy.allowed_assets.base


def test_example_yaml_roundtrip():
    """Test that example YAML can be loaded and validated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_path = Path(tmpdir) / "rules.yml"
        create_example_rules_yaml(yaml_path)

        # Load it
        config = PolicyConfig.from_yaml(yaml_path)

        # Export to dict
        config_dict = config.to_dict()

        # Recreate from dict
        config2 = PolicyConfig(**config_dict)

        # Should be identical
        assert config.version == config2.version
        assert config.policy.pit_only == config2.policy.pit_only
        assert config.floors.max_spread_bps == config2.floors.max_spread_bps
