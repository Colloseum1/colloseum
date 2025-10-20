# Strategy Example: ETH Mean Reversion (7d)

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
