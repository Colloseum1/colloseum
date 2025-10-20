# Risk Policy and Guardrails

## Raw Rules Configuration

```yaml
version: 1
policy:
  pit_only: true
  forbid_freeform_numbers: true
  allowed_assets:
    base:
    - SOL
    - mSOL
    - jitoSOL
    - bSOL
    - BTC
    - ETH
    - USDC
    - USDT
  allowed_venues:
  - Jupiter
  - Phoenix
  - Drift
  - Marginfi
  - Solend
  - Orca
  - Raydium
  - Meteora
floors:
  hf:
    default: 1.5
    auto_loop: 1.6
    emergency: 1.3
  max_spread_bps: 50
  min_liquidity_usd: 100000
  oracle_delta_bps_max: 100
  oracle_staleness_ms_max: 10000
  max_priority_fee_microlamports_per_cu: 1500
compatibility:
  lp_base_to_perp:
    SOL:
    - SOL-PERP
    BTC:
    - BTC-PERP
    ETH:
    - ETH-PERP
allowlists:
  venues:
    default:
    - Jupiter
    - Phoenix
    - Drift
    - Marginfi
    - Solend
    - Orca
    - Raydium
    - Meteora

```

## Policy Overview

### Core Principles
- **PIT-only**: All data must use Point-in-Time (PIT) tables
- **No freeform numbers**: All metrics must come from tools (simulate, ch_query, get_signals)
- **Evidence-based**: Every claim requires tool attribution

### Allowed Assets
Base assets: SOL, mSOL, jitoSOL, bSOL, BTC, ETH, USDC, USDT

### Allowed Venues
Jupiter, Phoenix, Drift, Marginfi, Solend, Orca, Raydium, Meteora

### Risk Floors
- **Health Factor (HF)**: Default 1.5, Auto-loop 1.6, Emergency 1.3
- **Max Spread**: 50 bps
- **Min Liquidity**: $100,000 USD
- **Oracle Delta Max**: 100 bps (1%)
- **Oracle Staleness Max**: 10,000 ms (10 seconds)
- **Max Priority Fee**: 1,500 microlamports/CU

### LP-to-Perp Compatibility
- SOL → SOL-PERP
- BTC → BTC-PERP
- ETH → ETH-PERP
