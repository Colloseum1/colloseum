# Strategy Example: BTC Conservative Trend (90d)

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
