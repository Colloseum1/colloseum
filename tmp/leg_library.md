# Leg Library: Available Trading Legs

Version: 1

## swap_route

**Description**: Swap tokens via Jupiter aggregator with slippage protection

**Venue**: Jupiter

**Program ID**: `JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB`

**Inputs**:
- `from`: mint
- `to`: mint
- `amount`: decimal
- `slippage_bps_max`: int

**Pre-checks**:
- min_liquidity
- max_spread
- venue_allow

## stake

**Description**: Stake SOL for liquid staking token (LST)

**Venue**: Marinade

**Inputs**:
- `asset_in`: SOL
- `lst_out`: mSOL|jitoSOL|bSOL
- `amount`: decimal

**Pre-checks**:
- oracle_fresh
- peg_ok
- venue_allow

## hedge_perp

**Description**: Open perpetual hedge position on Drift

**Venue**: Drift

**Program ID**: `dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH`

**Inputs**:
- `symbol`: string
- `side`: long|short
- `size`: base_qty

**Pre-checks**:
- funding_ceiling
- max_spread
- oracle_fresh

## lend

**Description**: Lend assets to Marginfi money market

**Venue**: Marginfi

**Program ID**: `MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA`

**Inputs**:
- `asset`: mint
- `amount`: decimal

**Pre-checks**:
- utilization_ok
- oracle_fresh
- venue_allow

## provide_liquidity

**Description**: Provide liquidity to Orca CLMM pool

**Venue**: Orca

**Program ID**: `whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc`

**Inputs**:
- `pool_id`: pubkey
- `token_a_amount`: decimal
- `token_b_amount`: decimal

**Pre-checks**:
- min_liquidity
- oracle_fresh
- venue_allow

