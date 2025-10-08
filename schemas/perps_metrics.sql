CREATE TABLE IF NOT EXISTS sol.perps_metrics (
  ts               DateTime64(3, 'UTC'),
  market           String,          -- e.g., "SOL-PERP"
  index_price_fp6  UInt64,          -- index/oracle TWAP * 1e6
  mark_price_fp6   UInt64,          -- mark TWAP * 1e6
  funding_rate_bps Int32,           -- per-interval funding in bps
  open_interest    UInt64,          -- OI as reported by API
  meta             String,          -- raw JSON as text
  ingest_ts        DateTime64(3, 'UTC') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (market, ts);
