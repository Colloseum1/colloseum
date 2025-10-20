"""
Custom guardrails for Layer 4 agent safety.

Implements three critical guardrails:
1. PITOnlySqlGuardrail: Enforce PIT-only table access in SQL queries
2. NoFreeformNumbersGuardrail: Block freeform numeric claims without tool provenance
3. VenueAllowGuardrail: Validate venue_hint against rules.yml allowlist

All guardrails follow Agno's BaseGuardrail pattern with check() and async_check() methods.
"""

import re
from typing import Dict, Any, Optional, List
from pathlib import Path

from agno.guardrails import BaseGuardrail
from agno.exceptions import CheckTrigger, InputCheckError
from agno.run.agent import RunInput


# =============================================================================
# PITOnlySqlGuardrail - Prevent lookahead bias
# =============================================================================

class PITOnlySqlGuardrail(BaseGuardrail):
    """
    Enforce PIT-only table access in SQL queries.

    Blocks queries that reference non-PIT tables to prevent lookahead bias.
    All ClickHouse queries must use tables in the 'pit.*' namespace.

    Pattern: Extracts table names from FROM/JOIN clauses using regex:
    r'\b(?:from|join)\s+(["]?[a-z0-9_.]+["]?)'

    Rejects any table name that doesn't start with 'pit.'

    Examples:
        ✅ Allowed: "SELECT * FROM pit.oracle_prices_by_feed WHERE slot = 250000000"
        ❌ Blocked: "SELECT * FROM sol.oracles_unified WHERE ts > now() - INTERVAL 1 DAY"
        ❌ Blocked: "SELECT * FROM public.features WHERE ..."
    """

    # Regex to extract table names from FROM/JOIN/DROP/TRUNCATE clauses
    # Matches: FROM table_name, JOIN table_name, DROP TABLE table_name, etc.
    TABLE_PATTERN = re.compile(
        r'\b(?:from|join|(?:drop|truncate)\s+table)\s+(["]?[a-z0-9_.]+["]?)',
        re.IGNORECASE
    )

    def check(self, run_input: RunInput) -> None:
        """
        Check SQL query for non-PIT table references.

        Args:
            run_input: Agno RunInput containing the SQL query string

        Raises:
            InputCheckError: If query references non-PIT tables
        """
        # Only check string inputs (SQL queries)
        if not isinstance(run_input.input_content, str):
            return

        query = run_input.input_content.lower()

        # Extract all table names from FROM/JOIN clauses
        matches = self.TABLE_PATTERN.findall(query)

        if not matches:
            # No tables found - might not be a SQL query, allow it
            return

        # Check each table name
        non_pit_tables = []
        for match in matches:
            # Remove quotes if present
            table_name = match.strip('"\'')

            # Check if table starts with 'pit.'
            if not table_name.startswith('pit.'):
                non_pit_tables.append(table_name)

        # Reject if any non-PIT tables found
        if non_pit_tables:
            raise InputCheckError(
                f"SQL query references non-PIT table(s): {', '.join(non_pit_tables)}. "
                f"All queries must use 'pit.*' tables to prevent lookahead bias. "
                f"Example: Use 'pit.oracle_prices_by_feed' instead of 'sol.oracles_unified'.",
                check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
            )

    async def async_check(self, run_input: RunInput) -> None:
        """Async version of check (delegates to sync implementation)."""
        self.check(run_input)


# =============================================================================
# NoFreeformNumbersGuardrail - Prevent hallucinated metrics
# =============================================================================

class NoFreeformNumbersGuardrail(BaseGuardrail):
    """
    Block freeform numeric claims without tool provenance.

    Detects patterns where the agent outputs numeric claims like:
    - "sharpe is 1.5"
    - "sharpe = 1.5"
    - "sharpe: 1.5"
    - "returns are 2500 bps"

    All numeric metrics must come from tool calls (simulate, ch_query, get_signals).

    Pattern: Detects metric keywords followed by assignment operators and numbers.
    Common metrics: sharpe, returns, drawdown, hit_rate, capacity, fee_drag, vol, spread

    Examples:
        ❌ Blocked: "The strategy has sharpe = 1.5"
        ❌ Blocked: "Expected returns: 2500 bps"
        ✅ Allowed: "The simulate tool returned sharpe=1.5" (tool attribution)
        ✅ Allowed: "What is the sharpe ratio?" (question, not claim)
    """

    # Metric keywords to detect
    METRIC_KEYWORDS = [
        'sharpe',
        'returns',
        'drawdown',
        'hit_rate',
        'capacity',
        'fee_drag',
        'volatility',
        'vol',
        'spread',
        'slippage',
        'liquidity',
        'apy',
        'apr',
        'yield',
    ]

    # Pattern: metric_keyword + (is|=|:) + number
    # Examples: "sharpe is 1.5", "returns = 2500", "apy: 12.5", "hit rate: 0.65"
    def _build_pattern(self) -> re.Pattern:
        """Build regex pattern for freeform number detection."""
        # Replace underscores with pattern that matches either underscore or space
        # e.g., "hit_rate" becomes "hit[_ ]rate" to match both "hit_rate" and "hit rate"
        keywords_with_flexible_separators = [
            kw.replace('_', '[_ ]') for kw in self.METRIC_KEYWORDS
        ]
        keywords_alternation = '|'.join(keywords_with_flexible_separators)
        pattern = (
            rf'\b({keywords_alternation})\s*'  # Metric keyword (with flexible separators)
            rf'(?:is|=|:)\s*'                   # Assignment operator
            rf'([-+]?\d+\.?\d*)'                # Numeric value
        )
        return re.compile(pattern, re.IGNORECASE)

    # Tool attribution patterns (allow if present)
    TOOL_ATTRIBUTION_PATTERNS = [
        r'\btool\s+returned\b',
        r'\bsimulate\b.*\breturned\b',
        r'\bch_query\b.*\breturned\b',
        r'\bget_signals\b.*\breturned\b',
        r'\bfrom\s+tool\b',
        r'\baccording\s+to\s+\w+\s+tool\b',
    ]

    def __init__(self):
        super().__init__()
        self.number_pattern = self._build_pattern()
        self.attribution_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.TOOL_ATTRIBUTION_PATTERNS
        ]

    def check(self, run_input: RunInput) -> None:
        """
        Check output for freeform numeric claims.

        Args:
            run_input: Agno RunInput containing the agent output

        Raises:
            InputCheckError: If output contains freeform numbers without tool attribution
        """
        # Only check string outputs
        if not isinstance(run_input.input_content, str):
            return

        output = run_input.input_content

        # Check for freeform number patterns
        matches = self.number_pattern.findall(output)

        if not matches:
            # No freeform numbers detected
            return

        # Check if output has tool attribution
        has_attribution = any(
            pattern.search(output) for pattern in self.attribution_patterns
        )

        if has_attribution:
            # Tool attribution present - allow the numbers
            return

        # Extract metric names from matches
        metric_names = [match[0] for match in matches]

        # Reject output with freeform numbers
        raise InputCheckError(
            f"Output contains freeform numeric claims for: {', '.join(set(metric_names))}. "
            f"All metrics must come from tool calls (simulate, ch_query, get_signals). "
            f"Include tool attribution like 'simulate tool returned sharpe=1.5'.",
            check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
        )

    async def async_check(self, run_input: RunInput) -> None:
        """Async version of check (delegates to sync implementation)."""
        self.check(run_input)


# =============================================================================
# VenueAllowGuardrail - Enforce venue allowlist
# =============================================================================

class VenueAllowGuardrail(BaseGuardrail):
    """
    Validate venue_hint against rules.yml allowlist.

    Ensures that all venue references in agent outputs are in the allowed list
    from rules.yml. Prevents agents from recommending unapproved venues.

    Configuration:
        rules: Dict containing PolicyConfig.to_dict() output
        Example: {"policy": {"allowed_venues": ["Jupiter", "Phoenix", "Drift", ...]}}

    Detection: Looks for venue mentions in output text and checks against allowlist.

    Examples:
        ✅ Allowed: "Use Jupiter for swaps" (Jupiter in allowlist)
        ❌ Blocked: "Use Mango for perps" (Mango not in allowlist)
        ❌ Blocked: "Route through 1inch" (1inch not in allowlist)
    """

    def __init__(self, rules: Optional[Dict[str, Any]] = None):
        """
        Initialize VenueAllowGuardrail.

        Args:
            rules: PolicyConfig dict with allowed_venues list.
                   If None, will attempt to load from default rules.yml path.
        """
        super().__init__()

        if rules is None:
            # Try to load from default path
            from ..schemas.policy import PolicyConfig
            default_path = Path(__file__).parent.parent / "schemas" / "rules.yml"
            if default_path.exists():
                policy_config = PolicyConfig.from_yaml(default_path)
                rules = policy_config.to_dict()
            else:
                raise ValueError(
                    "VenueAllowGuardrail requires rules dict. "
                    "Pass rules parameter or ensure schemas/rules.yml exists."
                )

        # Extract allowed venues from rules
        self.allowed_venues: List[str] = rules.get("policy", {}).get("allowed_venues", [])

        if not self.allowed_venues:
            raise ValueError(
                "VenueAllowGuardrail requires non-empty allowed_venues list in rules.policy"
            )

        # Build case-insensitive pattern for venue detection
        # Matches whole words only to avoid false positives
        venue_alternation = '|'.join(re.escape(v) for v in self.allowed_venues)
        self.allowed_pattern = re.compile(
            rf'\b({venue_alternation})\b',
            re.IGNORECASE
        )

        # Common venue keywords to detect (case-insensitive)
        # These are known DeFi venues NOT in typical allowlists
        self.known_venues = [
            'Uniswap', 'SushiSwap', 'Curve', 'Balancer', 'PancakeSwap',
            '1inch', 'Mango', 'Zeta', 'Kamino', 'Lifinity',
        ]

    def check(self, run_input: RunInput) -> None:
        """
        Check output for disallowed venue references.

        Args:
            run_input: Agno RunInput containing the agent output

        Raises:
            InputCheckError: If output references disallowed venues
        """
        # Only check string outputs
        if not isinstance(run_input.input_content, str):
            return

        output = run_input.input_content

        # Check for known disallowed venues
        disallowed_mentions = []
        for venue in self.known_venues:
            # Case-insensitive word boundary match
            pattern = re.compile(rf'\b{re.escape(venue)}\b', re.IGNORECASE)
            if pattern.search(output):
                # Found a known venue - check if it's in allowlist
                if venue not in self.allowed_venues:
                    disallowed_mentions.append(venue)

        # Reject if any disallowed venues found
        if disallowed_mentions:
            raise InputCheckError(
                f"Output references disallowed venue(s): {', '.join(disallowed_mentions)}. "
                f"Only these venues are allowed: {', '.join(self.allowed_venues)}. "
                f"Remove disallowed venue references or update rules.yml allowlist.",
                check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
            )

    async def async_check(self, run_input: RunInput) -> None:
        """Async version of check (delegates to sync implementation)."""
        self.check(run_input)
