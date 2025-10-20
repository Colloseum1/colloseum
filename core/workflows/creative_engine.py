"""
Creative Engine Workflow (Task 10).

Autonomous strategy generation pipeline that runs in the background:
generate_candidate → validate → compile → simulate → score → bucket → persist

Uses Agno Workflow for orchestration with built-in error handling and resumability.
"""

import os
import json
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow import Workflow
from agno.workflow.step import Step
from agno.workflow.types import StepInput, WorkflowExecutionInput

from ..config import get_shared_dependencies
from ..tools.http_tools import validate, compile_spec, simulate
from ..schemas.models import StrategySpec


# ============================================================================
# Configuration
# ============================================================================

CREATIVE_ENGINE_CONFIG = {
    # Scoring weights
    "weight_sharpe": float(os.getenv("CE_WEIGHT_SHARPE", "2.0")),
    "weight_pnl": float(os.getenv("CE_WEIGHT_PNL", "0.0001")),
    "weight_max_dd": float(os.getenv("CE_WEIGHT_MAX_DD", "-2.0")),
    "weight_fill_rate": float(os.getenv("CE_WEIGHT_FILL_RATE", "0.5")),
    "weight_fee_drag": float(os.getenv("CE_WEIGHT_FEE_DRAG", "-0.01")),
    "weight_reliability": float(os.getenv("CE_WEIGHT_RELIABILITY", "0.5")),

    # Bucketing thresholds
    "low_risk_score": float(os.getenv("CE_LOW_RISK_SCORE", "2.0")),
    "low_risk_max_dd": float(os.getenv("CE_LOW_RISK_MAX_DD", "1000")),  # 10% in bps
    "medium_risk_score": float(os.getenv("CE_MEDIUM_RISK_SCORE", "1.0")),
    "medium_risk_max_dd": float(os.getenv("CE_MEDIUM_RISK_MAX_DD", "2000")),  # 20% in bps

    # TTL settings (hours)
    "ttl_low": int(os.getenv("CE_TTL_LOW", "168")),  # 7 days
    "ttl_medium": int(os.getenv("CE_TTL_MEDIUM", "72")),  # 3 days
    "ttl_high": int(os.getenv("CE_TTL_HIGH", "24")),  # 1 day

    # Output directory
    "output_dir": os.getenv("CE_OUTPUT_DIR", "data/creative_engine"),
}


# ============================================================================
# Candidate Generation
# ============================================================================

async def generate_candidate(
    session_state: Dict[str, Any],
    execution_input: WorkflowExecutionInput,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Generate diverse strategy candidates using randomization and AI.

    Creates varied StrategySpec candidates with:
    - Random asset selection from allowlist
    - Varied risk parameters
    - Different archetypes
    - Time horizon variations

    Returns:
        Dict with candidate StrategySpec
    """
    deps = get_shared_dependencies()

    # Asset pool (from venue allowlist)
    asset_pool = ["SOL/USD", "BTC/USD", "ETH/USD", "BONK/USD", "JUP/USD"]

    # Archetype pool
    archetypes = [
        "trend_follow",
        "mean_revert",
        "breakout",
        "momentum",
        "carry",
    ]

    # Time horizons
    horizons = ["1d", "3d", "7d", "14d", "30d"]

    # Risk levels
    risk_levels = ["Low", "Medium", "High"]

    # Generate candidate with randomization
    num_assets = random.randint(1, 3)
    selected_assets = random.sample(asset_pool, num_assets)
    archetype = random.choice(archetypes)
    horizon = random.choice(horizons)
    risk = random.choice(risk_levels)

    # Create StrategySpec
    spec = {
        "name": f"{archetype}_{selected_assets[0].split('/')[0].lower()}_{horizon}",
        "category": archetype,
        "assets": [asset.split("/")[0] for asset in selected_assets],  # Just base currency
        "dataset_refs": ["pit.oracle_prices_by_feed"],
        "entry": {
            "kind": "signal",
            "signal_id": f"{archetype}_entry",
            "threshold": random.uniform(0.5, 0.9),
        },
        "exit": {
            "kind": "signal",
            "signal_id": f"{archetype}_exit",
            "threshold": random.uniform(0.3, 0.7),
        },
        "filters": [],
        "guards": {
            "max_slippage_bps": random.randint(30, 100),
            "max_drawdown_bps": random.randint(500, 2000) if risk == "High" else random.randint(200, 1000),
            "min_liquidity_usd": 10000,
        },
        "graph": {
            "legs": [
                {
                    "leg_id": "1",
                    "kind": "swap",
                    "protocol": "jupiter",
                    "from_asset": "USDC",
                    "to_asset": selected_assets[0].split("/")[0],
                }
            ]
        },
    }

    # Return the result (Agno handles progress streaming automatically)
    return {"spec": spec, "risk": risk, "horizon": horizon}


# ============================================================================
# Validation Step
# ============================================================================

async def validate_candidate(
    session_state: Dict[str, Any],
    execution_input: WorkflowExecutionInput,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Validate candidate StrategySpec using validation service.

    Calls validate() tool to check:
    - Schema compliance
    - Policy guardrails
    - Asset allowlist
    - Guard values in range

    Returns:
        Dict with validation result
    """
    # Get spec from previous step
    previous_output = execution_input.previous_step_content
    if not previous_output or "spec" not in previous_output:
        raise ValueError("No spec from generate_candidate step")

    spec = previous_output["spec"]

    # Get dependencies for validation
    deps = get_shared_dependencies()

    try:
        # Call validation service with retry
        result_json = validate(spec, dependencies=deps)
        result = json.loads(result_json)

        if not result.get("ok"):
            errors = result.get("errors", [])
            raise ValueError(f"Validation failed: {errors}")

        return {
            **previous_output,
            "validation_result": result,
        }

    except Exception as e:
        raise


# ============================================================================
# Compilation Step
# ============================================================================

async def compile_candidate(
    session_state: Dict[str, Any],
    execution_input: WorkflowExecutionInput,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Compile StrategySpec to executable PlanGraph.

    Calls compile_spec() tool to:
    - Bind venues
    - Generate execution plan
    - Validate leg library references

    Returns:
        Dict with compiled plan
    """
    previous_output = execution_input.previous_step_content
    if not previous_output or "spec" not in previous_output:
        raise ValueError("No spec from previous step")

    spec = previous_output["spec"]
    deps = get_shared_dependencies()

    try:
        result_json = compile_spec(spec, dependencies=deps)
        result = json.loads(result_json)

        if not result.get("ok"):
            errors = result.get("errors", [])
            raise ValueError(f"Compilation failed: {errors}")

        plan = result.get("plan", {})

        return {
            **previous_output,
            "plan": plan,
            "compilation_result": result,
        }

    except Exception as e:
        raise


# ============================================================================
# Simulation Step
# ============================================================================

async def simulate_candidate(
    session_state: Dict[str, Any],
    execution_input: WorkflowExecutionInput,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Run backtest simulation on compiled strategy.

    Calls simulate() tool to:
    - Execute PIT-only backtest
    - Calculate metrics (Sharpe, PnL, DD, etc.)
    - Generate performance report

    Returns:
        Dict with simulation metrics
    """
    previous_output = execution_input.previous_step_content
    if not previous_output or "spec" not in previous_output:
        raise ValueError("No spec from previous step")

    spec = previous_output["spec"]
    deps = get_shared_dependencies()

    # Simulation config
    sim_config = {
        "start_date": (datetime.now() - timedelta(days=90)).isoformat(),
        "end_date": datetime.now().isoformat(),
        "initial_capital_usd": 10000,
    }

    try:
        result_json = simulate(spec, sim_config, dependencies=deps)
        result = json.loads(result_json)

        if not result.get("ok"):
            errors = result.get("errors", [])
            raise ValueError(f"Simulation failed: {errors}")

        metrics = result.get("metrics", {})

        return {
            **previous_output,
            "sim_metrics": metrics,
            "simulation_result": result,
        }

    except Exception as e:
        raise


# ============================================================================
# Scoring and Bucketing
# ============================================================================

async def score_and_bucket(
    session_state: Dict[str, Any],
    execution_input: WorkflowExecutionInput,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Score strategy and assign risk bucket.

    Scoring formula (converts bps to decimal):
    score = 2*sharpe + 0.0001*pnl - 2*(max_dd_bps/10000) + 0.5*fill_rate - 0.01*(fee_drag_bps/10000) + 0.5*route_reliability

    Example: sharpe=2.5, pnl=5000, max_dd=500bps (0.05), fill_rate=0.95, fee_drag=15bps, reliability=0.98:
    score = 2*2.5 + 0.0001*5000 - 2*0.05 + 0.5*0.95 - 0.01*0.0015 + 0.5*0.98
          = 5.0 + 0.5 - 0.1 + 0.475 - 0.000015 + 0.49
          = 6.365 → Low bucket

    Bucketing:
    - Low: score >= 2.0 AND max_dd <= 1000 bps (10%)
    - Medium: score >= 1.0 AND max_dd <= 2000 bps (20%)
    - High: all others

    Returns:
        Dict with score and bucket
    """
    previous_output = execution_input.previous_step_content
    if not previous_output or "sim_metrics" not in previous_output:
        raise ValueError("No metrics from simulation step")

    metrics = previous_output["sim_metrics"]

    # Extract metrics with defaults
    sharpe = metrics.get("sharpe", 0.0)
    pnl = metrics.get("total_pnl_usd", 0.0)
    max_dd_bps = abs(metrics.get("max_dd_bps", 0.0))
    fill_rate = metrics.get("fill_rate", 0.5)
    fee_drag_bps = abs(metrics.get("fee_drag_bps", 0.0))
    route_reliability = metrics.get("route_reliability", 0.8)

    # Convert basis points to decimal fractions for scoring
    # 500 bps = 5% = 0.05 in decimal form
    max_dd_decimal = max_dd_bps / 10000.0  # 500 bps = 0.05
    fee_drag_decimal = fee_drag_bps / 10000.0  # 20 bps = 0.002

    # Calculate score
    config = CREATIVE_ENGINE_CONFIG
    score = (
        config["weight_sharpe"] * sharpe +
        config["weight_pnl"] * pnl +
        config["weight_max_dd"] * max_dd_decimal +  # Weight is negative, decimal is positive
        config["weight_fill_rate"] * fill_rate +
        config["weight_fee_drag"] * fee_drag_decimal +  # Weight is negative, decimal is positive
        config["weight_reliability"] * route_reliability
    )

    # Determine bucket
    if score >= config["low_risk_score"] and max_dd_bps <= config["low_risk_max_dd"]:
        bucket = "Low"
        ttl_hours = config["ttl_low"]
    elif score >= config["medium_risk_score"] and max_dd_bps <= config["medium_risk_max_dd"]:
        bucket = "Medium"
        ttl_hours = config["ttl_medium"]
    else:
        bucket = "High"
        ttl_hours = config["ttl_high"]

    return {
        **previous_output,
        "score": score,
        "bucket": bucket,
        "ttl_hours": ttl_hours,
    }


# ============================================================================
# Persistence
# ============================================================================

async def persist_results(
    session_state: Dict[str, Any],
    execution_input: WorkflowExecutionInput,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Persist strategy to JSON file with TTL.

    Structure:
    {
        "timestamp": "2025-10-20T...",
        "bucket": "Low",
        "score": 2.34,
        "spec": {...},
        "metrics": {...},
        "expires_at": "2025-10-27T...",
        "ttl_hours": 168
    }

    Returns:
        Dict with file path
    """
    previous_output = execution_input.previous_step_content
    if not previous_output:
        raise ValueError("No data from previous steps")

    spec = previous_output.get("spec", {})
    bucket = previous_output.get("bucket", "High")
    score = previous_output.get("score", 0.0)
    metrics = previous_output.get("sim_metrics", {})
    ttl_hours = previous_output.get("ttl_hours", 24)

    # Create output directory
    output_dir = Path(CREATIVE_ENGINE_CONFIG["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create bucket subdirectory
    bucket_dir = output_dir / bucket.lower()
    bucket_dir.mkdir(exist_ok=True)

    # Generate filename
    timestamp = datetime.now()
    filename = f"{spec['name']}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = bucket_dir / filename

    # Calculate expiry
    expires_at = timestamp + timedelta(hours=ttl_hours)

    # Prepare data
    data = {
        "timestamp": timestamp.isoformat(),
        "bucket": bucket,
        "score": score,
        "spec": spec,
        "metrics": metrics,
        "expires_at": expires_at.isoformat(),
        "ttl_hours": ttl_hours,
    }

    # Write to file (atomic)
    temp_path = filepath.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        json.dump(data, f, indent=2)
    temp_path.rename(filepath)

    return {
        **previous_output,
        "filepath": str(filepath),
        "expires_at": expires_at.isoformat(),
    }


# ============================================================================
# Workflow Definition
# ============================================================================

def create_creative_engine_workflow(
    db_url: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Workflow:
    """
    Create the Creative Engine workflow.

    Pipeline:
    1. generate_candidate - Create varied StrategySpec
    2. validate_candidate - Schema + policy validation
    3. compile_candidate - Compile to PlanGraph
    4. simulate_candidate - Run backtest
    5. score_and_bucket - Calculate score and assign bucket
    6. persist_results - Save to JSON with TTL

    Args:
        db_url: Optional database URL for session persistence
        session_id: Optional session ID for tracking

    Returns:
        Configured Workflow instance
    """
    # Define steps
    generate_step = Step(
        name="generate_candidate",
        description="Generate diverse strategy candidates",
        fn=generate_candidate,
    )

    validate_step = Step(
        name="validate_candidate",
        description="Validate candidate against schema and policy",
        fn=validate_candidate,
    )

    compile_step = Step(
        name="compile_candidate",
        description="Compile to executable plan",
        fn=compile_candidate,
    )

    simulate_step = Step(
        name="simulate_candidate",
        description="Run backtest simulation",
        fn=simulate_candidate,
    )

    score_bucket_step = Step(
        name="score_and_bucket",
        description="Score and assign risk bucket",
        fn=score_and_bucket,
    )

    persist_step = Step(
        name="persist_results",
        description="Persist to JSON with TTL",
        fn=persist_results,
    )

    # Create workflow
    workflow = Workflow(
        name="Creative Engine",
        description="Autonomous strategy generation pipeline",
        steps=[
            generate_step,
            validate_step,
            compile_step,
            simulate_step,
            score_bucket_step,
            persist_step,
        ],
        session_id=session_id,
        # db=db if db_url else None,  # Uncomment when DB persistence needed
    )

    return workflow


# ============================================================================
# Convenience Functions
# ============================================================================

async def run_creative_engine_once(
    session_id: Optional[str] = None,
    stream: bool = True,
) -> Any:
    """
    Run Creative Engine workflow once.

    Args:
        session_id: Optional session ID for tracking
        stream: If True, stream intermediate steps

    Returns:
        Workflow run result
    """
    workflow = create_creative_engine_workflow(session_id=session_id)

    result = await workflow.arun(
        input="Generate and evaluate new strategy candidate",
        stream=stream,
        stream_intermediate_steps=stream,
    )

    return result


def run_creative_engine_sync(
    session_id: Optional[str] = None,
    enable_metrics: bool = True,
) -> Any:
    """
    Run Creative Engine workflow synchronously (blocking).

    Args:
        session_id: Optional session ID
        enable_metrics: If True, track Prometheus metrics

    Returns:
        Workflow run result
    """
    import asyncio

    if enable_metrics:
        from .metrics import track_workflow_execution, track_candidate_generated

        with track_workflow_execution():
            result = asyncio.run(run_creative_engine_once(session_id=session_id))

            # Track the generated candidate if successful
            if result and hasattr(result, 'content'):
                content = result.content
                if isinstance(content, dict):
                    bucket = content.get('bucket', 'high')
                    score = content.get('score', 0.0)
                    track_candidate_generated(bucket, score)

            return result
    else:
        return asyncio.run(run_creative_engine_once(session_id=session_id))
