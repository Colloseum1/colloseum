# Strategy Example: SOL Trend Following (30d)

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
