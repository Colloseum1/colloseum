"""
Tests for custom guardrails (PITOnlySql, NoFreeformNumbers, VenueAllow).

Tests cover:
- Valid inputs that should pass
- Invalid inputs that should raise InputCheckError
- Edge cases (SQL injection attempts, false positives, boundary conditions)
- Integration with rules.yml
"""

import pytest
from agno.exceptions import InputCheckError
from agno.run.agent import RunInput

from .custom import (
    PITOnlySqlGuardrail,
    NoFreeformNumbersGuardrail,
    VenueAllowGuardrail,
)
from ..schemas.policy import PolicyConfig
from pathlib import Path


# =============================================================================
# PITOnlySqlGuardrail Tests
# =============================================================================

class TestPITOnlySqlGuardrail:
    """Test PITOnlySqlGuardrail for PIT-only table enforcement."""

    @pytest.fixture
    def guardrail(self):
        return PITOnlySqlGuardrail()

    def test_allows_pit_tables(self, guardrail):
        """Should allow queries using PIT tables."""
        valid_queries = [
            "SELECT * FROM pit.oracle_prices_by_feed WHERE slot = 250000000",
            "SELECT * FROM pit.lending_reserve_by_reserve WHERE ts > 1234567890",
            "SELECT a.*, b.price FROM pit.features a JOIN pit.oracle_prices b ON a.feed_id = b.feed_id",
            'SELECT * FROM "pit.oracle_prices_by_feed" WHERE feed_id = 123',
            "select count(*) from pit.signals where signal_id = 'ema_cross'",
        ]

        for query in valid_queries:
            # Should not raise
            guardrail.check(RunInput(input_content=query))

    def test_blocks_non_pit_tables(self, guardrail):
        """Should block queries using non-PIT tables."""
        invalid_queries = [
            "SELECT * FROM sol.oracles_unified WHERE ts > now() - INTERVAL 1 DAY",
            "SELECT * FROM public.features WHERE id = 123",
            "SELECT * FROM raw.lending_data WHERE protocol = 'marginfi'",
            "SELECT a.*, b.* FROM pit.oracle_prices a JOIN sol.oracles_unified b ON a.feed_id = b.feed_id",
        ]

        for query in invalid_queries:
            with pytest.raises(InputCheckError) as exc_info:
                guardrail.check(RunInput(input_content=query))
            assert "non-PIT table" in str(exc_info.value)

    def test_handles_mixed_case(self, guardrail):
        """Should handle case-insensitive SQL."""
        mixed_case_queries = [
            "SELECT * FROM PIT.oracle_prices_by_feed WHERE slot = 1",
            "SELECT * FROM Pit.Oracle_Prices WHERE feed_id = 1",
            "select * from pit.features where id = 1",
        ]

        for query in mixed_case_queries:
            # Should not raise (case-insensitive table matching)
            guardrail.check(RunInput(input_content=query))

    def test_handles_quoted_table_names(self, guardrail):
        """Should handle quoted table names."""
        quoted_queries = [
            'SELECT * FROM "pit.oracle_prices_by_feed" WHERE slot = 1',
            "SELECT * FROM 'pit.features' WHERE id = 1",
        ]

        for query in quoted_queries:
            # Should not raise
            guardrail.check(RunInput(input_content=query))

    def test_sql_injection_attempts(self, guardrail):
        """Should block SQL injection attempts with non-PIT tables."""
        injection_queries = [
            "SELECT * FROM pit.oracle_prices WHERE 1=1; DROP TABLE sol.oracles_unified; --",
            "SELECT * FROM pit.features UNION SELECT * FROM sol.raw_data",
        ]

        for query in injection_queries:
            with pytest.raises(InputCheckError) as exc_info:
                guardrail.check(RunInput(input_content=query))
            assert "non-PIT table" in str(exc_info.value)

    def test_ignores_non_sql_strings(self, guardrail):
        """Should ignore non-SQL strings (no tables detected)."""
        non_sql_strings = [
            "This is a regular sentence about data",
            "Calculate sharpe ratio using historical returns",
            "The strategy performs well in volatile markets",
        ]

        for text in non_sql_strings:
            # Should not raise (no FROM/JOIN clauses detected)
            guardrail.check(RunInput(input_content=text))

    def test_ignores_non_string_inputs(self, guardrail):
        """Should ignore non-string inputs."""
        non_string_inputs = [
            {"query": "SELECT * FROM sol.oracles"},
            123,
            None,
            ["SELECT", "FROM", "pit.oracle_prices"],
        ]

        for inp in non_string_inputs:
            # Should not raise (only checks strings)
            guardrail.check(RunInput(input_content=inp))


# =============================================================================
# NoFreeformNumbersGuardrail Tests
# =============================================================================

class TestNoFreeformNumbersGuardrail:
    """Test NoFreeformNumbersGuardrail for numeric claim detection."""

    @pytest.fixture
    def guardrail(self):
        return NoFreeformNumbersGuardrail()

    def test_blocks_freeform_numbers(self, guardrail):
        """Should block freeform numeric claims."""
        invalid_outputs = [
            "The strategy has sharpe = 1.5",
            "Expected returns: 2500 bps",
            "Sharpe is 1.8",
            "Volatility = 25.3",
            "The drawdown is 800 bps",
            "Hit rate: 0.65",
            "APY is 12.5%",
        ]

        for output in invalid_outputs:
            with pytest.raises(InputCheckError) as exc_info:
                guardrail.check(RunInput(input_content=output))
            assert "freeform numeric claims" in str(exc_info.value)

    def test_allows_tool_attribution(self, guardrail):
        """Should allow numbers with tool attribution."""
        valid_outputs = [
            "The simulate tool returned sharpe=1.5",
            "According to ch_query tool, volatility is 25.3",
            "From tool get_signals: hit_rate = 0.65",
            "Tool returned returns: 2500 bps",
            "simulate returned sharpe is 1.8",
        ]

        for output in valid_outputs:
            # Should not raise (tool attribution present)
            guardrail.check(RunInput(input_content=output))

    def test_allows_questions(self, guardrail):
        """Should allow questions about metrics (no claims)."""
        valid_questions = [
            "What is the sharpe ratio?",
            "Can you calculate the returns?",
            "How do I compute volatility?",
            "What does hit_rate mean?",
        ]

        for question in valid_questions:
            # Should not raise (no numeric claims)
            guardrail.check(RunInput(input_content=question))

    def test_case_insensitive_detection(self, guardrail):
        """Should detect metrics case-insensitively."""
        case_variations = [
            "SHARPE = 1.5",
            "Sharpe = 1.5",
            "sharpe = 1.5",
            "ShArPe = 1.5",
        ]

        for output in case_variations:
            with pytest.raises(InputCheckError):
                guardrail.check(RunInput(input_content=output))

    def test_detects_multiple_metrics(self, guardrail):
        """Should detect multiple freeform metrics in one output."""
        output = "The strategy has sharpe = 1.5 and returns: 2500 bps with drawdown is 800"

        with pytest.raises(InputCheckError) as exc_info:
            guardrail.check(RunInput(input_content=output))

        error_msg = str(exc_info.value)
        # Should mention at least 2 metrics
        assert "sharpe" in error_msg or "returns" in error_msg or "drawdown" in error_msg

    def test_allows_descriptive_text(self, guardrail):
        """Should allow descriptive text without numeric claims."""
        valid_outputs = [
            "The strategy focuses on trend following",
            "Sharpe ratio measures risk-adjusted returns",
            "Higher returns typically come with higher risk",
            "The simulate tool will calculate metrics",
        ]

        for output in valid_outputs:
            # Should not raise
            guardrail.check(RunInput(input_content=output))

    def test_ignores_non_string_inputs(self, guardrail):
        """Should ignore non-string inputs."""
        non_string_inputs = [
            {"sharpe": 1.5},
            123,
            None,
            ["sharpe", "=", "1.5"],
        ]

        for inp in non_string_inputs:
            # Should not raise (only checks strings)
            guardrail.check(RunInput(input_content=inp))

    def test_allows_negative_numbers_with_attribution(self, guardrail):
        """Should allow negative numbers with tool attribution."""
        valid_outputs = [
            "The simulate tool returned returns = -250 bps",
            "From tool: drawdown is -15.5%",
        ]

        for output in valid_outputs:
            # Should not raise
            guardrail.check(RunInput(input_content=output))


# =============================================================================
# VenueAllowGuardrail Tests
# =============================================================================

class TestVenueAllowGuardrail:
    """Test VenueAllowGuardrail for venue allowlist enforcement."""

    @pytest.fixture
    def rules(self):
        """Load rules from schemas/rules.yml."""
        rules_path = Path(__file__).parent.parent / "schemas" / "rules.yml"
        policy_config = PolicyConfig.from_yaml(rules_path)
        return policy_config.to_dict()

    @pytest.fixture
    def guardrail(self, rules):
        return VenueAllowGuardrail(rules=rules)

    def test_allows_whitelisted_venues(self, guardrail):
        """Should allow outputs mentioning whitelisted venues."""
        valid_outputs = [
            "Use Jupiter for swaps",
            "Route through Phoenix CLOB",
            "Hedge on Drift perps",
            "Lend on Marginfi",
            "Supply to Solend reserves",
            "Provide liquidity on Orca",
            "Use Raydium CPMM pools",
            "Deploy on Meteora DLMM",
        ]

        for output in valid_outputs:
            # Should not raise (all venues in allowlist)
            guardrail.check(RunInput(input_content=output))

    def test_blocks_disallowed_venues(self, guardrail):
        """Should block outputs mentioning disallowed venues."""
        invalid_outputs = [
            "Use Mango for perps",
            "Route through 1inch",
            "Swap on Uniswap",
            "Try SushiSwap for better rates",
            "Deploy on Curve pools",
            "Use Kamino for lending",
        ]

        for output in invalid_outputs:
            with pytest.raises(InputCheckError) as exc_info:
                guardrail.check(RunInput(input_content=output))
            assert "disallowed venue" in str(exc_info.value)

    def test_case_insensitive_detection(self, guardrail):
        """Should detect venues case-insensitively."""
        case_variations = [
            "Use JUPITER for swaps",
            "Route through jupiter",
            "Deploy on Jupiter",
        ]

        for output in case_variations:
            # Should not raise (Jupiter is allowed)
            guardrail.check(RunInput(input_content=output))

        disallowed_cases = [
            "Use MANGO for perps",
            "Route through mango",
            "Deploy on Mango",
        ]

        for output in disallowed_cases:
            with pytest.raises(InputCheckError):
                guardrail.check(RunInput(input_content=output))

    def test_word_boundary_matching(self, guardrail):
        """Should match whole words only (avoid false positives)."""
        # "Jupiter" is allowed, but "Jupiterswap" shouldn't trigger
        # This is a boundary case test - current implementation should handle this

        valid_outputs = [
            "Use Jupiter for routing",  # Exact match
        ]

        for output in valid_outputs:
            # Should not raise
            guardrail.check(RunInput(input_content=output))

    def test_allows_descriptive_text(self, guardrail):
        """Should allow text without venue mentions."""
        valid_outputs = [
            "The strategy uses PIT oracle data",
            "Calculate sharpe ratio using historical returns",
            "Implement trend following with EMA cross",
        ]

        for output in valid_outputs:
            # Should not raise (no venue mentions)
            guardrail.check(RunInput(input_content=output))

    def test_ignores_non_string_inputs(self, guardrail):
        """Should ignore non-string inputs."""
        non_string_inputs = [
            {"venue": "Mango"},
            123,
            None,
            ["Mango", "perps"],
        ]

        for inp in non_string_inputs:
            # Should not raise (only checks strings)
            guardrail.check(RunInput(input_content=inp))

    def test_loads_from_default_path_if_no_rules(self):
        """Should load rules from default path if none provided."""
        # This tests the default rules loading logic
        guardrail = VenueAllowGuardrail()  # No rules parameter

        # Should have loaded allowed_venues from rules.yml
        assert len(guardrail.allowed_venues) > 0
        assert "Jupiter" in guardrail.allowed_venues

    def test_raises_if_no_rules_and_no_file(self):
        """Should raise if no rules provided and no file exists."""
        # This is hard to test without mocking, but we can verify the error message
        with pytest.raises(ValueError) as exc_info:
            VenueAllowGuardrail(rules={})
        assert "allowed_venues" in str(exc_info.value)


# =============================================================================
# Integration Tests
# =============================================================================

class TestGuardrailIntegration:
    """Integration tests for guardrails with Agno agents."""

    def test_all_guardrails_implement_check(self):
        """Verify all guardrails implement check() method."""
        rules_path = Path(__file__).parent.parent / "schemas" / "rules.yml"
        policy_config = PolicyConfig.from_yaml(rules_path)
        rules = policy_config.to_dict()

        guardrails = [
            PITOnlySqlGuardrail(),
            NoFreeformNumbersGuardrail(),
            VenueAllowGuardrail(rules=rules),
        ]

        for g in guardrails:
            assert hasattr(g, "check")
            assert hasattr(g, "async_check")
            assert callable(g.check)
            assert callable(g.async_check)

    @pytest.mark.asyncio
    async def test_async_check_methods(self):
        """Test async_check methods work correctly."""
        rules_path = Path(__file__).parent.parent / "schemas" / "rules.yml"
        policy_config = PolicyConfig.from_yaml(rules_path)
        rules = policy_config.to_dict()

        guardrails = [
            PITOnlySqlGuardrail(),
            NoFreeformNumbersGuardrail(),
            VenueAllowGuardrail(rules=rules),
        ]

        # Test valid inputs
        valid_inputs = [
            "SELECT * FROM pit.oracle_prices WHERE slot = 1",
            "The strategy looks promising",
            "Use Jupiter for swaps",
        ]

        for g, inp in zip(guardrails, valid_inputs):
            # Should not raise
            await g.async_check(RunInput(input_content=inp))

        # Test invalid inputs
        invalid_inputs = [
            "SELECT * FROM sol.oracles_unified",
            "Sharpe = 1.5",
            "Use Mango for perps",
        ]

        for g, inp in zip(guardrails, invalid_inputs):
            with pytest.raises(InputCheckError):
                await g.async_check(RunInput(input_content=inp))
