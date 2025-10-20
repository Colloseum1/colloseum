"""
Ingest knowledge content into LanceDB for NarratorAgent.

Loads:
- leg_library.json: Available trading leg types with pre-checks and venues
- rules.yml: Risk policy, guardrails, venue allowlists, and compatibility rules
- Strategy examples: Sample strategies with performance metrics

Usage:
    uv run python scripts/ingest_knowledge.py [--recreate]

Options:
    --recreate: Drop and recreate the knowledge base (default: append to existing)
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.knowledge import setup_knowledge_base


def load_leg_library(knowledge_base):
    """Load leg library JSON into knowledge base."""
    leg_library_path = Path(__file__).parent.parent / "core" / "schemas" / "leg_library.json"

    with open(leg_library_path, "r") as f:
        leg_data = json.load(f)

    # Format as markdown for better retrieval
    content = "# Leg Library: Available Trading Legs\n\n"
    content += f"Version: {leg_data['version']}\n\n"

    for leg in leg_data["legs"]:
        content += f"## {leg['key']}\n\n"
        content += f"**Description**: {leg['description']}\n\n"

        if "venue" in leg:
            content += f"**Venue**: {leg['venue']}\n\n"

        if "program_id" in leg:
            content += f"**Program ID**: `{leg['program_id']}`\n\n"

        content += "**Inputs**:\n"
        for input_name, input_type in leg["inputs"].items():
            content += f"- `{input_name}`: {input_type}\n"
        content += "\n"

        content += "**Pre-checks**:\n"
        for check in leg["pre_checks"]:
            content += f"- {check}\n"
        content += "\n"

    # Save to temp file and add to knowledge base
    temp_file = Path(__file__).parent.parent / "tmp" / "leg_library.md"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_file, "w") as f:
        f.write(content)

    knowledge_base.add_content(
        name="Leg Library",
        path=str(temp_file),
        metadata={"source": "leg_library.json", "type": "legs"}
    )
    print("✅ Loaded leg library")


def load_risk_rules(knowledge_base):
    """Load risk rules YAML into knowledge base."""
    rules_path = Path(__file__).parent.parent / "core" / "schemas" / "rules.yml"

    with open(rules_path, "r") as f:
        rules_content = f.read()

    # Format as markdown for better context
    content = "# Risk Policy and Guardrails\n\n"
    content += "## Raw Rules Configuration\n\n"
    content += "```yaml\n"
    content += rules_content
    content += "\n```\n\n"

    # Add human-readable explanation
    content += "## Policy Overview\n\n"
    content += "### Core Principles\n"
    content += "- **PIT-only**: All data must use Point-in-Time (PIT) tables\n"
    content += "- **No freeform numbers**: All metrics must come from tools (simulate, ch_query, get_signals)\n"
    content += "- **Evidence-based**: Every claim requires tool attribution\n\n"

    content += "### Allowed Assets\n"
    content += "Base assets: SOL, mSOL, jitoSOL, bSOL, BTC, ETH, USDC, USDT\n\n"

    content += "### Allowed Venues\n"
    content += "Jupiter, Phoenix, Drift, Marginfi, Solend, Orca, Raydium, Meteora\n\n"

    content += "### Risk Floors\n"
    content += "- **Health Factor (HF)**: Default 1.5, Auto-loop 1.6, Emergency 1.3\n"
    content += "- **Max Spread**: 50 bps\n"
    content += "- **Min Liquidity**: $100,000 USD\n"
    content += "- **Oracle Delta Max**: 100 bps (1%)\n"
    content += "- **Oracle Staleness Max**: 10,000 ms (10 seconds)\n"
    content += "- **Max Priority Fee**: 1,500 microlamports/CU\n\n"

    content += "### LP-to-Perp Compatibility\n"
    content += "- SOL → SOL-PERP\n"
    content += "- BTC → BTC-PERP\n"
    content += "- ETH → ETH-PERP\n"

    # Save to temp file and add to knowledge base
    temp_file = Path(__file__).parent.parent / "tmp" / "risk_rules.md"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_file, "w") as f:
        f.write(content)

    knowledge_base.add_content(
        name="Risk Policy",
        path=str(temp_file),
        metadata={"source": "rules.yml", "type": "policy"}
    )
    print("✅ Loaded risk rules and policy")


def load_strategy_examples(knowledge_base):
    """Load example strategies with performance metrics."""

    # Example 1: SOL Trend Following
    example1 = """# Strategy Example: SOL Trend Following (30d)

## Strategy Specification

**Name**: sol_trend_ema_cross_30d
**Category**: trend_follow
**Assets**: SOL/USD
**Horizon**: 30 days
**Risk Classification**: Medium

## Strategy Logic

### Entry
- Type: EMA Crossover
- Fast EMA: 12 periods
- Slow EMA: 26 periods
- Direction: Fast crosses above slow (bullish)

### Exit
- Type: EMA Crossover (reverse)
- Fast crosses below slow (bearish)

### Filters
- Hygiene checks: fresh, liquidity_ok, oracle_ok
- Oracle staleness max: 30,000 ms
- Min liquidity: $100,000 USD

### Position Sizing
- Type: Fixed fraction
- Fraction: 10% of capital (0.1)

## Risk Guards

- **Oracle staleness**: 30,000 ms max (30 seconds)
- **Max slippage**: 50 bps
- **Max drawdown**: 1,000 bps (10% for Medium risk)
- **Min liquidity**: $100,000 USD
- **Oracle delta max**: 500 bps (5%)
- **Spread max**: 20 bps

## Dataset References

All PIT-only:
- `pit.oracle_prices_by_feed` (SOL/USD prices)
- `pit.perp_metrics` (if using perps)

## Backtest Results (from simulate tool)

**Performance Metrics**:
- Sharpe Ratio: 1.5
- Total Returns: 2,500 bps (25%)
- Max Drawdown: 800 bps (8%)
- Hit Rate: 65%
- Strategy Capacity: $500,000 USD
- Fee Drag: 150 bps (1.5%)

**Evidence**: All metrics from simulate tool with sim_config: start_date='2024-01-01', end_date='2024-12-31', initial_capital=100000
"""

    # Example 2: ETH Mean Reversion
    example2 = """# Strategy Example: ETH Mean Reversion (7d)

## Strategy Specification

**Name**: eth_mean_revert_rsi_7d
**Category**: mean_revert
**Assets**: ETH/USD
**Horizon**: 7 days
**Risk Classification**: High

## Strategy Logic

### Entry
- Type: RSI Oversold
- Threshold: 30 (deeply oversold)

### Exit
- Type: RSI Overbought
- Threshold: 70

### Filters
- Hygiene checks: fresh, liquidity_ok, oracle_ok, spread_ok
- Oracle staleness max: 30,000 ms
- Min liquidity: $100,000 USD

### Position Sizing
- Type: Fixed fraction
- Fraction: 20% of capital (0.2 for High risk)

## Risk Guards

- **Oracle staleness**: 30,000 ms max
- **Max slippage**: 50 bps
- **Max drawdown**: 2,000 bps (20% for High risk)
- **Min liquidity**: $100,000 USD
- **Oracle delta max**: 500 bps
- **Spread max**: 20 bps

## Dataset References

All PIT-only:
- `pit.oracle_prices_by_feed` (ETH/USD prices)

## Backtest Results (from simulate tool)

**Performance Metrics**:
- Sharpe Ratio: 1.2
- Total Returns: 3,200 bps (32%)
- Max Drawdown: 1,800 bps (18%)
- Hit Rate: 58%
- Strategy Capacity: $300,000 USD
- Fee Drag: 200 bps (2%)

**Evidence**: All metrics from simulate tool with sim_config: start_date='2024-06-01', end_date='2024-12-31', initial_capital=100000
"""

    # Example 3: BTC Low Risk Conservative
    example3 = """# Strategy Example: BTC Conservative Trend (90d)

## Strategy Specification

**Name**: btc_conservative_trend_90d
**Category**: trend_follow
**Assets**: BTC/USD
**Horizon**: 90 days
**Risk Classification**: Low

## Strategy Logic

### Entry
- Type: EMA Crossover
- Fast EMA: 20 periods
- Slow EMA: 50 periods
- Direction: Fast crosses above slow

### Exit
- Type: EMA Crossover (reverse)
- Fast crosses below slow

### Filters
- Hygiene checks: fresh, liquidity_ok, oracle_ok, spread_ok
- Oracle staleness max: 30,000 ms
- Min liquidity: $200,000 USD (higher for BTC)

### Position Sizing
- Type: Fixed fraction
- Fraction: 5% of capital (0.05 for Low risk)

## Risk Guards

- **Oracle staleness**: 30,000 ms max
- **Max slippage**: 30 bps (tighter for Low risk)
- **Max drawdown**: 500 bps (5% for Low risk)
- **Min liquidity**: $200,000 USD
- **Oracle delta max**: 300 bps (3%)
- **Spread max**: 15 bps

## Dataset References

All PIT-only:
- `pit.oracle_prices_by_feed` (BTC/USD prices)

## Backtest Results (from simulate tool)

**Performance Metrics**:
- Sharpe Ratio: 1.8
- Total Returns: 1,500 bps (15%)
- Max Drawdown: 400 bps (4%)
- Hit Rate: 72%
- Strategy Capacity: $1,000,000 USD
- Fee Drag: 80 bps (0.8%)

**Evidence**: All metrics from simulate tool with sim_config: start_date='2024-01-01', end_date='2024-12-31', initial_capital=100000
"""

    # Save examples to temp files and add to knowledge base
    temp_dir = Path(__file__).parent.parent / "tmp" / "strategy_examples"
    temp_dir.mkdir(parents=True, exist_ok=True)

    example1_file = temp_dir / "sol_trend_30d.md"
    with open(example1_file, "w") as f:
        f.write(example1)
    knowledge_base.add_content(
        name="SOL Trend Strategy",
        path=str(example1_file),
        metadata={"source": "strategy_examples", "type": "strategy", "name": "sol_trend_30d"}
    )

    example2_file = temp_dir / "eth_mean_revert_7d.md"
    with open(example2_file, "w") as f:
        f.write(example2)
    knowledge_base.add_content(
        name="ETH Mean Reversion Strategy",
        path=str(example2_file),
        metadata={"source": "strategy_examples", "type": "strategy", "name": "eth_mean_revert_7d"}
    )

    example3_file = temp_dir / "btc_conservative_90d.md"
    with open(example3_file, "w") as f:
        f.write(example3)
    knowledge_base.add_content(
        name="BTC Conservative Strategy",
        path=str(example3_file),
        metadata={"source": "strategy_examples", "type": "strategy", "name": "btc_conservative_90d"}
    )
    print("✅ Loaded 3 strategy examples")


def main():
    """Main ingestion workflow."""
    import argparse

    parser = argparse.ArgumentParser(description="Ingest knowledge content into LanceDB")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the knowledge base (default: append to existing)"
    )
    args = parser.parse_args()

    print("🔄 Initializing knowledge base...")
    knowledge_base = setup_knowledge_base(recreate=args.recreate)

    print("\n📚 Ingesting content...")
    load_leg_library(knowledge_base)
    load_risk_rules(knowledge_base)
    load_strategy_examples(knowledge_base)

    print("\n✅ Knowledge base ingestion complete!")
    print(f"   Location: tmp/lancedb/layer4_knowledge")
    print(f"   Total documents loaded: leg library + risk rules + 3 strategy examples")


if __name__ == "__main__":
    main()
