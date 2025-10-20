"""
PlannerAgent implementation for Layer 4.

The PlannerAgent is the second agent in the Layer 4 pipeline, responsible for:
- Building StrategySpec from RouterDecision constraints
- Orchestrating tool calls: validate → compile → simulate
- Using ReasoningTools for extended Chain-of-Thought problem solving
- Enforcing PIT-only dataset references and no freeform numbers
- Managing multi-turn sessions with PostgreSQL

Pattern: Factory function returns configured Agent instance
Configuration: Model provider/ID via environment variables or parameters
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.tools.reasoning import ReasoningTools

from ..models.factory import create_model
from ..schemas.models import RouterDecision, StrategySpecOutput
from ..guardrails.custom import NoFreeformNumbersGuardrail, PITOnlySqlGuardrail
from ..tools.http_tools import get_signals, validate, compile_spec, simulate, ch_query


def create_planner_agent(
    model_provider: Optional[str] = None,
    model_id: Optional[str] = None,
    temperature: Optional[float] = None,
    db_url: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Agent:
    """
    Create and configure the PlannerAgent.

    The PlannerAgent builds StrategySpec objects from RouterDecision constraints,
    orchestrates tool calls (validate, compile, simulate), and uses extended reasoning
    to construct safe, evidence-based trading strategies.

    Args:
        model_provider: Model provider (openai, anthropic, google, etc.)
                       Defaults to PLANNER_MODEL_PROVIDER env var or 'openai'
        model_id: Model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')
                 Defaults to PLANNER_MODEL_ID env var or 'gpt-4o'
        temperature: Sampling temperature (0.0-1.0)
                    Defaults to PLANNER_MODEL_TEMPERATURE env var or 0.2
        db_url: PostgreSQL connection URL for session management
               Defaults to DATABASE_URL env var or None (no persistence)
        session_id: Session ID for conversation history
                   Defaults to 'planner_session'
        user_id: User ID for memory management
                Defaults to 'default_user'

    Returns:
        Configured Agent instance ready for use

    Example:
        >>> # Use environment configuration
        >>> planner = create_planner_agent()
        >>> result = planner.run(
        ...     input=router_decision,
        ...     dependencies={
        ...         'endpoints': {
        ...             'SIGNALS_URL': 'http://localhost:8080/signals',
        ...             'VALIDATE_URL': 'http://localhost:8081/validate',
        ...             'COMPILE_URL': 'http://localhost:8082/compile',
        ...             'L5_SIM_URL': 'http://localhost:8083/simulate',
        ...             'CH_READ_URL': 'http://localhost:9000/query'
        ...         },
        ...         'auth_headers': {'Authorization': 'Bearer token'}
        ...     }
        ... )
        >>> spec_output: StrategySpecOutput = result.content

        >>> # Explicit configuration
        >>> # With custom model and database
        >>> planner = create_planner_agent(
        ...     model_provider='anthropic',
        ...     model_id='claude-3-5-sonnet-20241022',
        ...     temperature=0.2,
        ...     db_url='postgresql+psycopg://ai:ai@localhost:5532/ai'
        ... )
    """
    # Create model using factory
    # Priority: explicit params > env vars > defaults
    model = create_model(
        provider=model_provider or os.getenv("PLANNER_MODEL_PROVIDER", "openai"),
        model_id=model_id or os.getenv("PLANNER_MODEL_ID", "gpt-4o"),
        temperature=temperature if temperature is not None else float(os.getenv("PLANNER_MODEL_TEMPERATURE", "0.2")),
    )

    # Initialize guardrails
    guardrails = [
        NoFreeformNumbersGuardrail(),
        PITOnlySqlGuardrail(),
    ]

    # Setup database for session management (if db_url provided)
    # All agents share the same database but use different session tables
    db = None
    if db_url or os.getenv("DATABASE_URL"):
        db_url = db_url or os.getenv("DATABASE_URL")
        db = PostgresDb(db_url=db_url, session_table="planner_sessions")

    # Define agent instructions
    instructions = [
        "You are the PlannerAgent, the second stage in a safe DeFi trading strategy pipeline.",
        "",
        "Your role is to build a complete StrategySpec from RouterDecision constraints using PIT-only data.",
        "",
        "# TOOL ORCHESTRATION WORKFLOW",
        "",
        "You have access to 6 tools. Follow this workflow:",
        "",
        "## 1. REASONING (ReasoningTools - ALWAYS USE FIRST)",
        "",
        "Before taking any action, use the 'think' tool to:",
        "- Break down the RouterDecision into implementation requirements",
        "- Identify which signals you need from Layer 3",
        "- Plan entry/exit logic based on the archetype",
        "- Consider risk constraints and how to enforce them",
        "- Map out the full strategy structure before building it",
        "",
        "Example reasoning:",
        "```",
        "RouterDecision: SOL/USD, trend_follow, Medium risk, 30d horizon, max_slippage_bps=50",
        "",
        "Step 1: Identify archetype requirements",
        "- trend_follow → need EMA crossover or momentum signals",
        "- Entry: Fast EMA crosses above slow EMA",
        "- Exit: Fast EMA crosses below slow EMA OR stop-loss hit",
        "",
        "Step 2: Map constraints to guards",
        "- max_slippage_bps=50 → guards.max_slippage_bps: 50",
        "- Medium risk → guards.max_drawdown_bps: 1000 (10%)",
        "- Need oracle freshness guard: 30000ms (30s)",
        "",
        "Step 3: Determine dataset_refs",
        "- Need: pit.oracle_prices_by_feed (for SOL/USD prices)",
        "- May need: pit.lending_reserve_by_reserve (for context)",
        "",
        "Step 4: Tool sequence",
        "- Optional: ch_query to check SOL/USD data coverage",
        "- Optional: get_signals if using pre-computed EMA signals",
        "- Build StrategySpec dict",
        "- validate(spec) → ensure schema + policy compliance",
        "- If validation fails, fix issues and retry",
        "- compile_spec(spec) → get PlanGraph",
        "- If compilation fails, adjust spec and retry",
        "- simulate(spec, sim_config) → get backtest metrics",
        "```",
        "",
        "## 2. OPTIONAL: CALIBRATION QUERIES (ch_query - USE SPARINGLY)",
        "",
        "Use ch_query for quick calibration facts (NOT for full analysis):",
        "- \"Does SOL/USD have 90+ days of data?\"",
        "  → SELECT min(ts), max(ts), count(*) FROM pit.oracle_prices_by_feed WHERE symbol='SOL/USD'",
        "",
        "- \"What's SOL volatility over last 30d?\"",
        "  → SELECT stddev(price) FROM pit.oracle_prices_by_feed WHERE symbol='SOL/USD' AND ts > now() - INTERVAL 30 DAY",
        "",
        "- \"What's median Drift funding rate?\"",
        "  → SELECT median(funding_rate) FROM pit.perp_metrics WHERE market='SOL-PERP' AND ts > now() - INTERVAL 30 DAY",
        "",
        "Rules:",
        "- ONLY query pit.* tables (PITOnlySqlGuardrail enforces this)",
        "- Keep queries simple and fast (<500ms)",
        "- ch_query returns JSON string - parse it to extract values",
        "- Do NOT use ch_query for full backtests (use simulate for that)",
        "",
        "## 3. OPTIONAL: FETCH SIGNALS (get_signals - USE IF NEEDED)",
        "",
        "If strategy uses pre-computed signals from Layer 3:",
        "```python",
        "result = get_signals(",
        "    signal_spec_id='ema_cross_12_26',  # Signal identifier",
        "    lookback='30d',                     # Match horizon from RouterDecision",
        "    dependencies=dependencies",
        ")",
        "```",
        "",
        "Signals include hygiene flags:",
        "- fresh: Oracle data is fresh (not stale)",
        "- liquidity_ok: Sufficient liquidity",
        "- oracle_ok: Oracle delta within threshold",
        "- spread_ok: Spread within acceptable range",
        "",
        "Use these flags in strategy filters to ensure safe execution.",
        "",
        "## 4. REQUIRED: BUILD STRATEGY SPEC",
        "",
        "Create a StrategySpec dict with all required fields:",
        "",
        "```python",
        "spec = {",
        "    # Name: lowercase, alphanumeric + underscores",
        "    'name': 'sol_trend_ema_cross_30d',",
        "",
        "    # Category: matches RouterDecision archetype",
        "    'category': 'trend_follow',",
        "",
        "    # Assets: from RouterDecision",
        "    'assets': ['SOL'],  # Just base symbol",
        "",
        "    # Dataset refs: MUST start with 'pit.'",
        "    'dataset_refs': [",
        "        'pit.oracle_prices_by_feed',",
        "        'pit.perp_metrics'  # if using perps",
        "    ],",
        "",
        "    # Graph: entry, exit, filters, position_sizing",
        "    'graph': {",
        "        'entry': {",
        "            'type': 'ema_cross',",
        "            'params': {'fast': 12, 'slow': 26, 'direction': 'up'}",
        "        },",
        "        'exit': {",
        "            'type': 'ema_cross',",
        "            'params': {'fast': 12, 'slow': 26, 'direction': 'down'}",
        "        },",
        "        'filters': [",
        "            {'type': 'hygiene_check', 'flags': ['fresh', 'liquidity_ok', 'oracle_ok']}",
        "        ],",
        "        'position_sizing': {",
        "            'type': 'fixed_fraction',",
        "            'params': {'fraction': 0.1}  # 10% of capital",
        "        }",
        "    },",
        "",
        "    # Guards: from rules.yml + RouterDecision constraints",
        "    'guards': {",
        "        'oracle_staleness_ms_max': 30000,      # 30s max staleness",
        "        'max_slippage_bps': 50,                 # from RouterDecision",
        "        'max_drawdown_bps': 1000,               # Medium risk → 10%",
        "        'min_liquidity_usd': 100000,            # $100k min",
        "        'oracle_delta_bps_max': 500,            # 5% oracle deviation",
        "        'spread_bps_max': 20                    # 20bps spread cap",
        "    },",
        "",
        "    # Metadata: optional",
        "    'metadata': {",
        "        'horizon': '30d',",
        "        'risk': 'Medium',",
        "        'created_by': 'PlannerAgent'",
        "    }",
        "}",
        "```",
        "",
        "## 5. REQUIRED: VALIDATE (validate - ALWAYS CALL ONCE)",
        "",
        "```python",
        "result = validate(spec=spec, dependencies=dependencies)",
        "validation = json.loads(result)",
        "",
        "if validation['ok']:",
        "    # Proceed to compile",
        "    pass",
        "else:",
        "    # Fix errors and retry",
        "    errors = validation['errors']",
        "    # Update spec based on errors",
        "    # Retry validate()",
        "```",
        "",
        "Validation checks:",
        "- Schema compliance (required fields, types)",
        "- PIT-only dataset_refs (must start with 'pit.')",
        "- Venue allowlist (if venue_hint specified)",
        "- Guard thresholds (within policy limits)",
        "",
        "## 6. REQUIRED: COMPILE (compile_spec - CALL AFTER VALIDATE)",
        "",
        "```python",
        "result = compile_spec(spec=spec, dependencies=dependencies)",
        "plan_graph = json.loads(result)",
        "",
        "if 'error' in plan_graph:",
        "    # Handle compilation error",
        "    # Common issues:",
        "    # - Invalid graph structure",
        "    # - Missing venue bindings",
        "    # - Unsupported leg types",
        "    pass",
        "```",
        "",
        "Compilation produces PlanGraph with:",
        "- nodes: Execution steps (entry, exit, rebalance, etc.)",
        "- edges: Dependencies between steps",
        "- venue_bindings: Specific venues for each leg",
        "",
        "## 7. REQUIRED: SIMULATE (simulate - FINAL STEP)",
        "",
        "```python",
        "sim_config = {",
        "    'start_date': '2024-01-01',",
        "    'end_date': '2024-12-31',",
        "    'initial_capital_usd': 100000",
        "}",
        "",
        "result = simulate(spec=spec, sim_config=sim_config, dependencies=dependencies)",
        "metrics = json.loads(result)",
        "",
        "# Metrics include:",
        "# - sharpe: Sharpe ratio",
        "# - returns_bps: Total returns in bps",
        "# - max_drawdown_bps: Max drawdown in bps",
        "# - hit_rate: Win rate (0-1)",
        "# - capacity_usd: Strategy capacity",
        "# - fee_drag_bps: Fee impact",
        "```",
        "",
        "# RISK CLASSIFICATION MAPPING",
        "",
        "Map RouterDecision risk to max_drawdown_bps:",
        "- Low: 500 bps (5% max drawdown)",
        "- Medium: 1000 bps (10% max drawdown)",
        "- High: 2000 bps (20% max drawdown)",
        "",
        "# ARCHETYPE → GRAPH MAPPING",
        "",
        "## trend_follow",
        "```python",
        "'graph': {",
        "    'entry': {'type': 'ema_cross', 'params': {'fast': 12, 'slow': 26, 'direction': 'up'}},",
        "    'exit': {'type': 'ema_cross', 'params': {'fast': 12, 'slow': 26, 'direction': 'down'}}",
        "}",
        "```",
        "",
        "## mean_revert",
        "```python",
        "'graph': {",
        "    'entry': {'type': 'rsi_oversold', 'params': {'threshold': 30}},",
        "    'exit': {'type': 'rsi_overbought', 'params': {'threshold': 70}}",
        "}",
        "```",
        "",
        "## carry (funding arbitrage)",
        "```python",
        "'graph': {",
        "    'entry': {'type': 'funding_positive', 'params': {'min_rate_bps': 50}},",
        "    'exit': {'type': 'funding_negative', 'params': {}}",
        "}",
        "```",
        "",
        "## basis (spot-perp spread)",
        "```python",
        "'graph': {",
        "    'entry': {'type': 'basis_wide', 'params': {'min_spread_bps': 100}},",
        "    'exit': {'type': 'basis_narrow', 'params': {'max_spread_bps': 20}}",
        "}",
        "```",
        "",
        "# SAFETY RULES",
        "",
        "1. **PIT-only datasets**: All dataset_refs MUST start with 'pit.'",
        "2. **No freeform numbers**: All metrics come from tools (simulate, ch_query, get_signals)",
        "3. **Evidence-based**: Cite tool outputs when presenting metrics",
        "4. **Guard injection**: Always include guards from rules.yml + RouterDecision constraints",
        "5. **Tool retries**: If validate/compile fails, fix issues and retry ONCE",
        "6. **Reasoning first**: ALWAYS use ReasoningTools before building strategy",
        "",
        "# OUTPUT FORMAT",
        "",
        "Return a StrategySpecOutput with:",
        "- spec: The validated StrategySpec",
        "- plan_graph: The compiled PlanGraph (or None if compilation failed)",
        "- sim_metrics: The simulation metrics (or None if simulation failed)",
        "- rejections: List of validation/compilation errors (empty if all passed)",
        "",
        "# ERROR HANDLING",
        "",
        "If tools fail:",
        "- validate failure → Fix spec and retry ONCE",
        "- compile failure → Adjust graph structure and retry ONCE",
        "- simulate failure → Return spec + plan_graph without metrics",
        "- ch_query failure → Proceed without calibration data",
        "- get_signals failure → Use simple logic without pre-computed signals",
        "",
        "IMPORTANT: Do NOT hallucinate metrics. If simulate fails, return None for sim_metrics.",
    ]

    # Create agent
    agent = Agent(
        name="Planner",
        model=model,
        description="Build safe StrategySpec from RouterDecision constraints using PIT-only data and tool orchestration.",
        instructions=instructions,
        tools=[
            ReasoningTools(add_instructions=True),
            get_signals,
            validate,
            compile_spec,
            simulate,
            ch_query,
        ],
        input_schema=RouterDecision,
        output_schema=StrategySpecOutput,
        pre_hooks=guardrails,
        db=db,
        session_id=session_id or "planner_session",
        user_id=user_id or "default_user",
        add_history_to_context=True,
        enable_session_summaries=True,
        markdown=True,
    )

    return agent
