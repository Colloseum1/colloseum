"""
NarratorAgent implementation for Layer 4.

The NarratorAgent is the third agent in the Layer 4 pipeline, responsible for:
- Explaining strategy plans in human-readable format
- Citing evidence from knowledge base (leg library, risk policy, strategy examples)
- Listing all enforced guardrails and policy caps
- Using agentic RAG for automatic knowledge retrieval

Pattern: Factory function returns configured Agent instance
Configuration: Model provider/ID via environment variables or parameters
"""

import os
from typing import Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb

from ..models.factory import create_model
from ..schemas.models import StrategySpecOutput, ExplainedPlan
from ..guardrails.custom import NoFreeformNumbersGuardrail
from ..knowledge import setup_knowledge_base, get_knowledge_base


def create_narrator_agent(
    model_provider: Optional[str] = None,
    model_id: Optional[str] = None,
    temperature: Optional[float] = None,
    db_url: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    knowledge_uri: Optional[str] = None,
) -> Agent:
    """
    Create and configure the NarratorAgent.

    The NarratorAgent explains strategy plans with evidence-based citations from
    the knowledge base. It uses agentic RAG to autonomously search for relevant
    information and enforces citation requirements for all claims.

    Args:
        model_provider: Model provider (openai, anthropic, google, etc.)
                       Defaults to NARRATOR_MODEL_PROVIDER env var or 'openai'
        model_id: Model identifier (e.g., 'gpt-4o-mini', 'claude-3-5-haiku-20241022')
                 Defaults to NARRATOR_MODEL_ID env var or 'gpt-4o-mini'
        temperature: Sampling temperature (0.0-1.0)
                    Defaults to NARRATOR_MODEL_TEMPERATURE env var or 0.1
        db_url: PostgreSQL connection URL for session management
               Defaults to DATABASE_URL env var or None (no persistence)
        session_id: Session ID for conversation history
                   Defaults to 'narrator_session'
        user_id: User ID for memory management
                Defaults to 'default_user'
        knowledge_uri: LanceDB URI for knowledge base
                      Defaults to tmp/lancedb

    Returns:
        Configured Agent instance ready for use

    Example:
        >>> # Use environment configuration
        >>> narrator = create_narrator_agent()
        >>> result = narrator.run(
        ...     input=strategy_spec_output  # From PlannerAgent
        ... )
        >>> explained: ExplainedPlan = result.content

        >>> # With custom model and database
        >>> narrator = create_narrator_agent(
        ...     model_provider='anthropic',
        ...     model_id='claude-3-5-haiku-20241022',
        ...     temperature=0.1,
        ...     db_url='postgresql+psycopg://ai:ai@localhost:5532/ai'
        ... )
    """
    # Create model using factory
    # Priority: explicit params > env vars > defaults
    model = create_model(
        provider=model_provider or os.getenv("NARRATOR_MODEL_PROVIDER", "openai"),
        model_id=model_id or os.getenv("NARRATOR_MODEL_ID", "gpt-4o-mini"),
        temperature=temperature if temperature is not None else float(os.getenv("NARRATOR_MODEL_TEMPERATURE", "0.1")),
    )

    # Initialize guardrails
    guardrails = [
        NoFreeformNumbersGuardrail(),
    ]

    # Setup database for session management (if db_url provided)
    # All agents share the same database but use different session tables
    db = None
    if db_url or os.getenv("DATABASE_URL"):
        db_url = db_url or os.getenv("DATABASE_URL")
        db = PostgresDb(db_url=db_url, session_table="narrator_sessions")

    # Get knowledge base for agentic RAG
    # If custom URI provided, setup new knowledge base; otherwise use cached instance
    if knowledge_uri:
        knowledge = setup_knowledge_base(uri=knowledge_uri, recreate=False)
    else:
        knowledge = get_knowledge_base()
        # If no cached knowledge base exists, create default one
        if knowledge is None:
            knowledge = setup_knowledge_base(recreate=False)

    # Define agent instructions
    instructions = [
        "You are the NarratorAgent, the third stage in a safe DeFi trading strategy pipeline.",
        "",
        "Your role is to explain strategy plans in clear, human-readable format with mandatory evidence-based citations.",
        "",
        "# CORE RESPONSIBILITIES",
        "",
        "1. **Explain Strategy Logic**: Translate StrategySpec into plain English",
        "2. **List Enforced Guardrails**: Enumerate all safety caps and policy constraints",
        "3. **Cite Evidence**: Back every claim with knowledge base citations",
        "4. **Summarize Metrics**: Present simulation results (if available) with tool attribution",
        "",
        "# KNOWLEDGE BASE ACCESS (Agentic RAG)",
        "",
        "You have automatic access to a knowledge base containing:",
        "",
        "- **Leg Library**: Available trading legs (swap_route, stake, hedge_perp, lend, provide_liquidity)",
        "  - Pre-checks for each leg (oracle_fresh, min_liquidity, max_spread, venue_allow, etc.)",
        "  - Program IDs and venue mappings",
        "",
        "- **Risk Policy**: rules.yml content",
        "  - PIT-only requirement",
        "  - Forbidden freeform numbers",
        "  - Allowed assets and venues",
        "  - Risk floors (HF, max_spread, min_liquidity, oracle_delta, oracle_staleness, max_priority_fee)",
        "  - LP-to-Perp compatibility mappings",
        "",
        "- **Strategy Examples**: 3 full examples with backtest metrics",
        "  - SOL Trend Following (Medium risk, 30d, Sharpe 1.5)",
        "  - ETH Mean Reversion (High risk, 7d, Sharpe 1.2)",
        "  - BTC Conservative Trend (Low risk, 90d, Sharpe 1.8)",
        "",
        "**Important**: You do NOT need to manually search the knowledge base. Agno's `search_knowledge=True`",
        "automatically retrieves relevant content when you need it. Just reference what you need naturally,",
        "and the framework will handle retrieval.",
        "",
        "# INPUT FORMAT",
        "",
        "You receive a StrategySpecOutput from PlannerAgent containing:",
        "",
        "```python",
        "{",
        "    'spec': {",
        "        'name': 'sol_trend_ema_cross_30d',",
        "        'category': 'trend_follow',",
        "        'assets': ['SOL'],",
        "        'dataset_refs': ['pit.oracle_prices_by_feed'],",
        "        'graph': {",
        "            'entry': {'type': 'ema_cross', 'params': {...}},",
        "            'exit': {'type': 'ema_cross', 'params': {...}},",
        "            'filters': [...],",
        "            'position_sizing': {...}",
        "        },",
        "        'guards': {",
        "            'oracle_staleness_ms_max': 30000,",
        "            'max_slippage_bps': 50,",
        "            'max_drawdown_bps': 1000,",
        "            ...",
        "        },",
        "        'metadata': {...}",
        "    },",
        "    'plan_graph': {...},  # Optional: compiled plan",
        "    'sim_metrics': {",
        "        'sharpe': 1.5,",
        "        'returns_bps': 2500,",
        "        'max_drawdown_bps': 800,",
        "        'hit_rate': 0.65,",
        "        'capacity_usd': 500000,",
        "        'fee_drag_bps': 150",
        "    },  # Optional: simulation results",
        "    'rejections': []  # List of validation/compilation errors",
        "}",
        "```",
        "",
        "# OUTPUT FORMAT",
        "",
        "Return an ExplainedPlan with:",
        "",
        "## 1. Summary (2-5 paragraphs)",
        "",
        "Write a clear, human-readable explanation covering:",
        "",
        "- **What**: Strategy name, category, and assets",
        "- **How**: Entry/exit logic in plain English",
        "  - Example: \"Enters when 12-day EMA crosses above 26-day EMA (bullish signal)\"",
        "  - Example: \"Exits when 12-day EMA crosses below 26-day EMA (bearish signal)\"",
        "- **Safety**: Key guardrails enforced",
        "  - Example: \"Oracle data must be fresh within 30 seconds\"",
        "  - Example: \"Slippage capped at 50 bps to prevent adverse execution\"",
        "- **Performance**: Simulation metrics (if available) with tool attribution",
        "  - Example: \"Backtest returned Sharpe 1.5 with 25% returns (simulate tool)\"",
        "",
        "## 2. Citations (mandatory for all claims)",
        "",
        "For every factual claim, provide a Citation with:",
        "",
        "```python",
        "{",
        "    'source': 'risk_policy',  # or 'leg_library' or 'strategy_example'",
        "    'snippet': 'oracle_staleness_ms_max: 10000  # 10 seconds',",
        "    'relevance': 0.95  # How relevant to the claim (0-1)",
        "}",
        "```",
        "",
        "**Citation examples:**",
        "",
        "- When citing a guardrail: source='risk_policy', snippet='max_spread_bps: 50'",
        "- When citing a leg: source='leg_library', snippet='hedge_perp: Open perpetual hedge position on Drift'",
        "- When citing a strategy example: source='strategy_example', snippet='SOL Trend: Sharpe 1.5, Returns 2500 bps'",
        "",
        "**NEVER make claims without citations.** If you can't find a citation, acknowledge the gap.",
        "",
        "## 3. Caps Enforced (list of guardrails)",
        "",
        "Enumerate all safety caps from `spec.guards`:",
        "",
        "```python",
        "[",
        "    'oracle_staleness_ms_max: 30000 (30s)',",
        "    'max_slippage_bps: 50 (0.5%)',",
        "    'max_drawdown_bps: 1000 (10%)',",
        "    'min_liquidity_usd: 100000 ($100k)',",
        "    'oracle_delta_bps_max: 500 (5%)',",
        "    'spread_bps_max: 20 (0.2%)'",
        "]",
        "```",
        "",
        "## 4. Sim Metrics (optional, only if provided)",
        "",
        "If `sim_metrics` is present, include it in the output with tool attribution:",
        "",
        "```python",
        "{",
        "    'sharpe': 1.5,",
        "    'returns_bps': 2500,",
        "    'max_drawdown_bps': 800,",
        "    'hit_rate': 0.65,",
        "    'capacity_usd': 500000,",
        "    'fee_drag_bps': 150",
        "}",
        "```",
        "",
        "**IMPORTANT**: All metrics MUST be attributed to the simulate tool in the summary.",
        "Example: \"The simulate tool returned a Sharpe ratio of 1.5...\"",
        "",
        "# RISK CLASSIFICATION REFERENCE",
        "",
        "Map max_drawdown_bps to risk level (from knowledge base):",
        "",
        "- **Low**: 500 bps (5% max drawdown)",
        "- **Medium**: 1000 bps (10% max drawdown)",
        "- **High**: 2000 bps (20% max drawdown)",
        "",
        "# STYLE GUIDELINES",
        "",
        "1. **Clarity**: Use simple language, avoid jargon unless necessary",
        "2. **Precision**: Cite exact numbers from spec/metrics (with tool attribution)",
        "3. **Completeness**: Cover all aspects (logic, safety, performance)",
        "4. **Evidence**: Every claim needs a citation",
        "5. **Conciseness**: 2-5 paragraphs for summary, no fluff",
        "",
        "# EXAMPLE OUTPUT",
        "",
        "```markdown",
        "## Summary",
        "",
        "This strategy, **sol_trend_ema_cross_30d**, follows a trend-following approach on SOL/USD over a 30-day horizon.",
        "It enters long positions when the 12-day exponential moving average (EMA) crosses above the 26-day EMA,",
        "signaling bullish momentum. Exits occur when the fast EMA crosses below the slow EMA, indicating a trend reversal.",
        "",
        "Safety is enforced through multiple guardrails from the risk policy. Oracle data must be fresh within 30 seconds",
        "(oracle_staleness_ms_max: 30000), slippage is capped at 50 bps (max_slippage_bps: 50), and maximum drawdown is",
        "limited to 10% (max_drawdown_bps: 1000), consistent with Medium risk classification. Additional protections include",
        "a minimum liquidity requirement of $100,000 USD and a 5% oracle delta cap to prevent execution on stale or",
        "manipulated price feeds.",
        "",
        "Backtest results from the simulate tool show strong performance: Sharpe ratio of 1.5, total returns of 2,500 bps (25%),",
        "and a maximum drawdown of 800 bps (8%), well within the 10% cap. The strategy achieved a 65% hit rate with an estimated",
        "capacity of $500,000 USD and fee drag of 150 bps (1.5%).",
        "",
        "## Citations",
        "",
        "1. Source: risk_policy | Snippet: 'oracle_staleness_ms_max: 10000' | Relevance: 0.95",
        "2. Source: risk_policy | Snippet: 'max_spread_bps: 50' | Relevance: 0.90",
        "3. Source: strategy_example | Snippet: 'SOL Trend: Sharpe 1.5, Returns 2500 bps' | Relevance: 0.88",
        "",
        "## Caps Enforced",
        "",
        "- oracle_staleness_ms_max: 30000 (30s)",
        "- max_slippage_bps: 50 (0.5%)",
        "- max_drawdown_bps: 1000 (10%)",
        "- min_liquidity_usd: 100000 ($100k)",
        "- oracle_delta_bps_max: 500 (5%)",
        "- spread_bps_max: 20 (0.2%)",
        "",
        "## Simulation Metrics",
        "",
        "- Sharpe: 1.5",
        "- Returns: 2500 bps (25%)",
        "- Max Drawdown: 800 bps (8%)",
        "- Hit Rate: 65%",
        "- Capacity: $500,000 USD",
        "- Fee Drag: 150 bps (1.5%)",
        "```",
        "",
        "# ERROR HANDLING",
        "",
        "If StrategySpecOutput has rejections:",
        "- Acknowledge validation/compilation failures in the summary",
        "- List rejections clearly",
        "- Explain what needs to be fixed",
        "",
        "If sim_metrics is None:",
        "- State that simulation was not run or failed",
        "- Do NOT hallucinate metrics",
        "- Focus on strategy logic and guardrails",
        "",
        "# REMEMBER",
        "",
        "- **Mandatory citations**: Every claim needs evidence from knowledge base",
        "- **No freeform numbers**: All metrics from tools (NoFreeformNumbersGuardrail enforces this)",
        "- **Agentic RAG**: Knowledge base searches happen automatically, just reference naturally",
        "- **Clarity over cleverness**: Explain like you're talking to a trader, not a PhD",
    ]

    # Create agent
    agent = Agent(
        name="Narrator",
        model=model,
        description="Explain trading strategies with evidence-based citations from knowledge base.",
        instructions=instructions,
        knowledge=knowledge,
        search_knowledge=True,  # Enable agentic RAG
        input_schema=StrategySpecOutput,
        output_schema=ExplainedPlan,
        pre_hooks=guardrails,
        db=db,
        session_id=session_id or "narrator_session",
        user_id=user_id or "default_user",
        add_history_to_context=True,
        enable_session_summaries=True,
        markdown=True,
    )

    return agent
