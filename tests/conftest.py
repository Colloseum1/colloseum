"""
Pytest configuration and shared fixtures for the colloseum test suite.
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables for tests
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)


@pytest.fixture
def project_root_path():
    """Return the project root directory path."""
    return project_root


@pytest.fixture
def core_path():
    """Return the core/ directory path."""
    return project_root / "core"


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Provide mock environment variables for testing."""
    test_env = {
        "OPENAI_API_KEY": "sk-test-mock-key-for-testing",
        "ANTHROPIC_API_KEY": "sk-ant-test-mock-key",
        "POSTGRES_URL": "postgresql+psycopg://test:test@localhost:5432/test",
        "CLICKHOUSE_HTTP": "http://localhost:8123",
        "CLICKHOUSE_USER": "test",
        "CLICKHOUSE_PASSWORD": "test",
        "REDIS_URL": "redis://localhost:6379/0",
        "LANCEDB_PATH": "./test_lancedb",
        "LOG_LEVEL": "DEBUG",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


@pytest.fixture
def sample_router_decision():
    """Provide a sample RouterDecision for testing."""
    return {
        "kind": "strategy",
        "assets": ["SOL/USD"],
        "risk": "Medium",
        "horizon": "7d",
        "archetype": "trend_follow",
        "constraints": {
            "max_slippage_bps": 50,
            "max_drawdown_bps": 1000,
        },
        "next_steps": ["validate", "compile", "simulate"],
    }


@pytest.fixture
def sample_strategy_spec():
    """Provide a sample StrategySpec for testing."""
    return {
        "name": "sol_trend_7d",
        "category": "trend_follow",
        "assets": ["SOL"],
        "dataset_refs": ["pit.oracle_prices_by_feed", "pit.features"],
        "graph": {
            "entry": {"signal": "ema_cross", "params": {"fast": 12, "slow": 26}},
            "exit": {"signal": "stop_loss", "params": {"stop_bps": 500}},
        },
        "guards": {
            "oracle_staleness_ms_max": 30000,
            "max_spread_bps": 50,
            "hf_floor": 1.5,
        },
    }
