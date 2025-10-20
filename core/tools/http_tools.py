"""
HTTP tool wrappers for Layer 4 agents.

Implements 5 tools for agent-to-service communication:
1. get_signals - Fetch signal data from Layer 3
2. validate - Validate StrategySpec schema and policy
3. compile_spec - Compile StrategySpec to PlanGraph
4. simulate - Run backtest simulation
5. ch_query - Execute ClickHouse queries (PIT-only)

All tools follow Agno's tool pattern:
- Accept dependencies parameter for endpoints and auth
- Return string responses (JSON)
- Use httpx with HTTPTransport(retries=2) for automatic retry
"""

from typing import Dict, Any, Optional
import httpx
import re
import json


# =============================================================================
# Helper Functions
# =============================================================================

def _get_auth_headers(dependencies: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract and validate auth headers from dependencies.

    Args:
        dependencies: Dict containing 'auth_headers' key

    Returns:
        Dict of HTTP headers for authentication

    Raises:
        ValueError: If auth_headers missing or invalid
    """
    if not dependencies:
        raise ValueError("dependencies parameter is required")

    auth_headers = dependencies.get("auth_headers")
    if not auth_headers:
        raise ValueError(
            "auth_headers not found in dependencies. "
            "Ensure agent.run() includes dependencies={'auth_headers': {...}}"
        )

    if not isinstance(auth_headers, dict):
        raise ValueError(f"auth_headers must be dict, got {type(auth_headers)}")

    return auth_headers


def _get_endpoint(dependencies: Dict[str, Any], key: str) -> str:
    """
    Extract endpoint URL from dependencies.

    Args:
        dependencies: Dict containing 'endpoints' key
        key: Endpoint key (e.g., 'SIGNALS_URL', 'VALIDATE_URL')

    Returns:
        Endpoint URL string

    Raises:
        ValueError: If endpoint missing
    """
    if not dependencies:
        raise ValueError("dependencies parameter is required")

    endpoints = dependencies.get("endpoints")
    if not endpoints:
        raise ValueError(
            "endpoints not found in dependencies. "
            "Ensure agent.run() includes dependencies={'endpoints': {...}}"
        )

    url = endpoints.get(key)
    if not url:
        raise ValueError(
            f"Endpoint '{key}' not found in dependencies.endpoints. "
            f"Available: {list(endpoints.keys())}"
        )

    return url


# =============================================================================
# HTTP Tools (Agno-compatible)
# =============================================================================

def get_signals(
    signal_spec_id: str,
    lookback: str,
    dependencies: Optional[Dict[str, Any]] = None
) -> str:
    """
    Fetch signal data from Layer 3 signals service.

    Retrieves pre-computed signals with hygiene flags (fresh, liquidity_ok,
    oracle_ok, spread_ok) for use in strategy construction.

    Args:
        signal_spec_id: Signal specification ID (e.g., 'ema_cross_12_26')
        lookback: Lookback period (e.g., '7d', '30d', '90d')
        dependencies: Dict with 'endpoints' and 'auth_headers'

    Returns:
        JSON string with signal data

    Raises:
        httpx.HTTPError: If request fails after retries
        ValueError: If dependencies missing required keys

    Example:
        >>> deps = {
        ...     'endpoints': {'SIGNALS_URL': 'http://signals:8080/api/signals'},
        ...     'auth_headers': {'Authorization': 'Bearer token123'}
        ... }
        >>> result = get_signals('ema_cross_12_26', '30d', deps)
    """
    url = _get_endpoint(dependencies, "SIGNALS_URL")
    headers = _get_auth_headers(dependencies)

    # Create httpx client with automatic retry (2x with exponential backoff)
    transport = httpx.HTTPTransport(retries=2)
    with httpx.Client(transport=transport, timeout=5.0) as client:
        response = client.post(
            url,
            json={"signal_spec_id": signal_spec_id, "lookback": lookback},
            headers=headers
        )
        response.raise_for_status()
        return response.text


def validate(
    spec: Dict[str, Any],
    dependencies: Optional[Dict[str, Any]] = None
) -> str:
    """
    Validate StrategySpec schema and policy guardrails.

    Performs validation against:
    - Pydantic schema (required fields, types)
    - Policy guardrails from rules.yml (PIT-only, venue allowlist, etc.)

    Args:
        spec: StrategySpec dict with name, category, assets, graph, guards
        dependencies: Dict with 'endpoints' and 'auth_headers'

    Returns:
        JSON string with validation result: {"ok": bool, "errors": []}

    Raises:
        httpx.HTTPError: If request fails after retries
        ValueError: If dependencies missing required keys

    Example:
        >>> spec = {
        ...     'name': 'sol_trend_7d',
        ...     'category': 'trend_follow',
        ...     'assets': ['SOL'],
        ...     'dataset_refs': ['pit.oracle_prices_by_feed'],
        ...     'graph': {'entry': {...}, 'exit': {...}},
        ...     'guards': {'oracle_staleness_ms_max': 30000}
        ... }
        >>> result = validate(spec, deps)
    """
    url = _get_endpoint(dependencies, "VALIDATE_URL")
    headers = _get_auth_headers(dependencies)

    transport = httpx.HTTPTransport(retries=2)
    with httpx.Client(transport=transport, timeout=10.0) as client:
        response = client.post(
            url,
            json={"kind": "strategy", "spec": spec},
            headers=headers
        )
        response.raise_for_status()
        return response.text


def compile_spec(
    spec: Dict[str, Any],
    dependencies: Optional[Dict[str, Any]] = None
) -> str:
    """
    Compile StrategySpec to executable PlanGraph.

    Binds venues, resolves leg dependencies, and generates execution graph.

    Args:
        spec: Validated StrategySpec dict
        dependencies: Dict with 'endpoints' and 'auth_headers'

    Returns:
        JSON string with compiled PlanGraph

    Raises:
        httpx.HTTPError: If request fails after retries (compilation errors)
        ValueError: If dependencies missing required keys

    Example:
        >>> result = compile_spec(validated_spec, deps)
        >>> plan = json.loads(result)
        >>> print(plan['nodes'], plan['edges'])
    """
    url = _get_endpoint(dependencies, "COMPILE_URL")
    headers = _get_auth_headers(dependencies)

    transport = httpx.HTTPTransport(retries=2)
    with httpx.Client(transport=transport, timeout=10.0) as client:
        response = client.post(
            url,
            json={"spec": spec},
            headers=headers
        )
        response.raise_for_status()
        return response.text


def simulate(
    spec: Dict[str, Any],
    sim_config: Dict[str, Any],
    dependencies: Optional[Dict[str, Any]] = None
) -> str:
    """
    Run backtest simulation on StrategySpec.

    Executes PIT-based backtest and returns performance metrics.

    Args:
        spec: Compiled StrategySpec dict
        sim_config: Simulation config with start_date, end_date, initial_capital
        dependencies: Dict with 'endpoints' and 'auth_headers'

    Returns:
        JSON string with simulation metrics: sharpe, returns, drawdown, etc.

    Raises:
        httpx.HTTPError: If request fails after retries
        ValueError: If dependencies missing required keys

    Example:
        >>> sim_config = {
        ...     'start_date': '2024-01-01',
        ...     'end_date': '2024-12-31',
        ...     'initial_capital_usd': 100000
        ... }
        >>> result = simulate(spec, sim_config, deps)
        >>> metrics = json.loads(result)
        >>> print(f"Sharpe: {metrics['sharpe']}")
    """
    url = _get_endpoint(dependencies, "L5_SIM_URL")
    headers = _get_auth_headers(dependencies)

    # Longer timeout for backtests (30s)
    transport = httpx.HTTPTransport(retries=2)
    with httpx.Client(transport=transport, timeout=30.0) as client:
        response = client.post(
            url,
            json={"spec": spec, "config": sim_config},
            headers=headers
        )
        response.raise_for_status()
        return response.text


def ch_query(
    sql: str,
    dependencies: Optional[Dict[str, Any]] = None
) -> str:
    """
    Execute ClickHouse query (PIT-only enforced by PITOnlySqlGuardrail).

    Automatically appends 'FORMAT JSON' if not present.

    Args:
        sql: SQL query string (must reference pit.* tables only)
        dependencies: Dict with 'endpoints' and 'auth_headers'

    Returns:
        JSON string with query results

    Raises:
        httpx.HTTPError: If request fails after retries
        ValueError: If dependencies missing required keys

    Example:
        >>> sql = "SELECT avg(price) FROM pit.oracle_prices_by_feed WHERE slot > 250000000"
        >>> result = ch_query(sql, deps)
        >>> data = json.loads(result)

    Note:
        PITOnlySqlGuardrail should be attached to agent pre_hooks to enforce
        PIT-only table access before this tool is called.
    """
    url = _get_endpoint(dependencies, "CH_READ_URL")
    headers = _get_auth_headers(dependencies)

    # Auto-append FORMAT JSON if not present
    sql_upper = sql.upper().strip()
    if "FORMAT JSON" not in sql_upper and "FORMAT" not in sql_upper:
        sql = sql.strip() + " FORMAT JSON"

    transport = httpx.HTTPTransport(retries=2)
    with httpx.Client(transport=transport, timeout=5.0) as client:
        response = client.post(
            url,
            json={"sql": sql},
            headers=headers
        )
        response.raise_for_status()
        return response.text
