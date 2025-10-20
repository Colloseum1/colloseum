"""
Shared dependencies for multi-agent context sharing in Layer 4.

This module provides dependency injection for Agno agents and teams,
enabling automatic context propagation via template variables.

Usage:
    >>> from core.config.shared_deps import get_shared_dependencies
    >>> shared_deps = get_shared_dependencies()
    >>> agent = Agent(model=..., dependencies=shared_deps, instructions="{endpoint_names}")
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

import yaml

from ..schemas.policy import PolicyConfig


# ============================================================================
# Shared Dependencies Builder
# ============================================================================

def get_shared_dependencies(
    rules_path: Optional[Path] = None,
    override_endpoints: Optional[Dict[str, str]] = None,
    override_auth: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build shared dependencies dict for agent/team context sharing.

    Dependencies are automatically injected into agent instructions via
    template variables (e.g., {venue_allowlist}, {signals_url}, etc.).

    Args:
        rules_path: Path to rules.yml file (defaults to core/schemas/rules.yml)
        override_endpoints: Override endpoint URLs (for testing)
        override_auth: Override authentication headers (for testing)

    Returns:
        Dict with shared dependencies for all agents:
        - rules: Complete rules.yml configuration
        - endpoints: Service URLs (signals, validate, compile, simulate, ch_query)
        - auth_headers: Authentication headers for service calls
        - venue_allowlist: Allowed venues from rules.yml
        - oracle_floors: Oracle freshness/delta floors from rules.yml
        - spread_floors: Spread/slippage caps from rules.yml
        - liquidity_floors: Minimum liquidity requirements from rules.yml

    Example:
        >>> deps = get_shared_dependencies()
        >>> agent = Agent(
        ...     model=...,
        ...     dependencies=deps,
        ...     instructions=[
        ...         "Use only these venues: {venue_allowlist}",
        ...         "Call validation service at: {endpoints[validate]}"
        ...     ]
        ... )
        >>> # Agno automatically substitutes template variables!
    """
    # Load rules configuration
    if rules_path is None:
        rules_path = Path(__file__).parent.parent / "schemas" / "rules.yml"

    policy_config = PolicyConfig.from_yaml(rules_path)
    rules = policy_config.to_dict()

    # Build endpoints configuration
    endpoints = override_endpoints or {
        "signals": os.getenv("SIGNALS_URL", "http://localhost:8082/signals"),
        "validate": os.getenv("VALIDATE_URL", "http://localhost:8081/validate"),
        "compile": os.getenv("COMPILE_URL", "http://localhost:8081/compile"),
        "simulate": os.getenv("L5_SIM_URL", "http://localhost:7090/simulate"),
        "ch_query": os.getenv("CH_READ_URL", "http://localhost:8123/query"),
    }

    # Build auth headers
    auth_headers = override_auth or {
        "CH_USER": os.getenv("CH_USER", "default"),
        "CH_PASS": os.getenv("CH_PASS", ""),
    }

    # Extract key policy settings for template variables
    venue_allowlist = rules.get("allowlists", {}).get("venues", {}).get("default", [])
    oracle_floors = rules.get("floors", {}).get("oracles", {})
    spread_floors = rules.get("caps", {}).get("spreads", {})
    liquidity_floors = rules.get("floors", {}).get("liquidity", {})

    # Build shared dependencies dict
    shared_deps = {
        # Complete rules configuration (for guardrails and validation)
        "rules": rules,

        # Service endpoints (for HTTP tool calls)
        "endpoints": endpoints,

        # Authentication (for HTTP tool calls)
        "auth_headers": auth_headers,

        # Policy settings (for agent instructions via template variables)
        "venue_allowlist": venue_allowlist,
        "oracle_floors": oracle_floors,
        "spread_floors": spread_floors,
        "liquidity_floors": liquidity_floors,

        # Human-readable names for agent instructions
        "endpoint_names": list(endpoints.keys()),
        "num_venues": len(venue_allowlist),
    }

    return shared_deps


# ============================================================================
# Template Variable Helpers
# ============================================================================

def get_policy_summary(deps: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate human-readable policy summary for agent instructions.

    Args:
        deps: Shared dependencies dict (defaults to get_shared_dependencies())

    Returns:
        Multi-line string summarizing policy rules

    Example:
        >>> summary = get_policy_summary()
        >>> agent = Agent(model=..., instructions=[summary])
    """
    if deps is None:
        deps = get_shared_dependencies()

    venue_list = ", ".join(deps["venue_allowlist"])
    oracle_freshness = deps["oracle_floors"].get("freshness_seconds", 60)
    oracle_delta = deps["oracle_floors"].get("max_delta_bps", 500)
    max_spread = deps["spread_floors"].get("max_spread_bps", 100)
    max_slippage = deps["spread_floors"].get("max_slippage_bps", 50)
    min_liquidity = deps["liquidity_floors"].get("min_usd", 10000)

    summary = f"""
Policy Rules (from rules.yml):
- Allowed Venues: {venue_list}
- Oracle Freshness: Max {oracle_freshness}s stale
- Oracle Delta: Max {oracle_delta} bps deviation
- Max Spread: {max_spread} bps
- Max Slippage: {max_slippage} bps
- Min Liquidity: ${min_liquidity:,} USD

These rules are ENFORCED by guardrails. Do not suggest strategies that violate them.
"""
    return summary.strip()


def get_endpoint_summary(deps: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate human-readable endpoint summary for agent instructions.

    Args:
        deps: Shared dependencies dict (defaults to get_shared_dependencies())

    Returns:
        Multi-line string summarizing available service endpoints

    Example:
        >>> summary = get_endpoint_summary()
        >>> agent = Agent(model=..., instructions=[summary])
    """
    if deps is None:
        deps = get_shared_dependencies()

    endpoints = deps["endpoints"]

    summary = f"""
Available Tools (via HTTP endpoints):
- get_signals: Fetch signals from Layer 3 ({endpoints['signals']})
- validate: Validate StrategySpec schema and policy ({endpoints['validate']})
- compile_spec: Compile spec to executable PlanGraph ({endpoints['compile']})
- simulate: Backtest strategy on PIT data ({endpoints['simulate']})
- ch_query: Query PIT tables for calibration ({endpoints['ch_query']})

All tools have built-in retry logic and timeout handling.
"""
    return summary.strip()


# ============================================================================
# Agent-Specific Instructions Builder
# ============================================================================

def get_router_instructions(deps: Optional[Dict[str, Any]] = None) -> list[str]:
    """
    Generate Router-specific instructions with template variables.

    Args:
        deps: Shared dependencies dict (defaults to get_shared_dependencies())

    Returns:
        List of instruction strings for RouterAgent

    Example:
        >>> instructions = get_router_instructions()
        >>> router = Agent(model=..., dependencies=deps, instructions=instructions)
    """
    if deps is None:
        deps = get_shared_dependencies()

    return [
        "You are the RouterAgent, the first stage in a safe DeFi trading strategy pipeline.",
        "",
        "Your role is to parse user requests into structured constraints.",
        "",
        get_policy_summary(deps),
        "",
        "Output: RouterDecision with kind, assets, risk, horizon, archetype, constraints",
    ]


def get_planner_instructions(deps: Optional[Dict[str, Any]] = None) -> list[str]:
    """
    Generate Planner-specific instructions with template variables.

    Args:
        deps: Shared dependencies dict (defaults to get_shared_dependencies())

    Returns:
        List of instruction strings for PlannerAgent

    Example:
        >>> instructions = get_planner_instructions()
        >>> planner = Agent(model=..., dependencies=deps, instructions=instructions)
    """
    if deps is None:
        deps = get_shared_dependencies()

    return [
        "You are the PlannerAgent, the strategy construction specialist.",
        "",
        "Your role: Build safe, validated StrategySpec from RouterDecision.",
        "",
        "Workflow (ALWAYS follow this order):",
        "1. Use ReasoningTools for extended chain-of-thought",
        "2. Optionally call get_signals for Layer 3 signal data",
        "3. Optionally call ch_query for PIT calibration data",
        "4. Build StrategySpec with PIT-only dataset_refs",
        "5. Call validate (REQUIRED - validates schema + policy)",
        "6. If validation passes, call compile_spec (REQUIRED)",
        "7. If compilation passes, call simulate (REQUIRED)",
        "8. Return StrategySpecOutput with spec, plan, sim_metrics",
        "",
        get_policy_summary(deps),
        "",
        get_endpoint_summary(deps),
        "",
        "CRITICAL: All dataset_refs MUST use pit.* tables (no raw tables!).",
    ]


def get_narrator_instructions(deps: Optional[Dict[str, Any]] = None) -> list[str]:
    """
    Generate Narrator-specific instructions with template variables.

    Args:
        deps: Shared dependencies dict (defaults to get_shared_dependencies())

    Returns:
        List of instruction strings for NarratorAgent

    Example:
        >>> instructions = get_narrator_instructions()
        >>> narrator = Agent(model=..., dependencies=deps, instructions=instructions)
    """
    if deps is None:
        deps = get_shared_dependencies()

    return [
        "You are the NarratorAgent, the strategy explanation specialist.",
        "",
        "Your role: Explain StrategySpec with evidence-based citations.",
        "",
        "Requirements:",
        "- Use Knowledge (RAG) for citations to leg library, policy rules",
        "- Explain WHY this strategy is safe (caps enforced, venues allowed)",
        "- Summarize simulation metrics (Sharpe, returns/DD, hit-rate)",
        "- NO free-form numbers (all metrics must come from simulate tool)",
        "",
        get_policy_summary(deps),
        "",
        "Output: ExplainedPlan with summary, citations, caps_enforced, sim_metrics",
    ]


# ============================================================================
# Validation
# ============================================================================

def validate_dependencies(deps: Dict[str, Any]) -> bool:
    """
    Validate that shared dependencies dict has all required keys.

    Args:
        deps: Shared dependencies dict to validate

    Returns:
        True if valid

    Raises:
        ValueError: If required keys are missing
    """
    required_keys = [
        "rules",
        "endpoints",
        "auth_headers",
        "venue_allowlist",
        "oracle_floors",
        "spread_floors",
        "liquidity_floors",
    ]

    for key in required_keys:
        if key not in deps:
            raise ValueError(f"Missing required key in shared dependencies: {key}")

    # Validate endpoints
    required_endpoints = ["signals", "validate", "compile", "simulate", "ch_query"]
    for endpoint in required_endpoints:
        if endpoint not in deps["endpoints"]:
            raise ValueError(f"Missing required endpoint: {endpoint}")

    return True


# ============================================================================
# Debug Helper
# ============================================================================

def print_dependencies_summary(deps: Optional[Dict[str, Any]] = None):
    """Print human-readable summary of shared dependencies."""
    if deps is None:
        deps = get_shared_dependencies()

    print("=" * 70)
    print("Shared Dependencies Summary")
    print("=" * 70)
    print(f"Venues Allowed: {', '.join(deps['venue_allowlist'])}")
    print(f"Endpoints Configured: {', '.join(deps['endpoints'].keys())}")
    print(f"Oracle Freshness Floor: {deps['oracle_floors'].get('freshness_seconds', 'N/A')}s")
    print(f"Max Spread: {deps['spread_floors'].get('max_spread_bps', 'N/A')} bps")
    print(f"Min Liquidity: ${deps['liquidity_floors'].get('min_usd', 'N/A'):,}")
    print("=" * 70)
