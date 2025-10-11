CREATE TABLE IF NOT EXISTS sol.jup_quotes (
  ts              DateTime64(3, 'UTC'),
  pair            String,                     -- e.g. "SOL/USDC"
  input_mint      String,
  output_mint     String,
  in_amount       UInt128,                    -- base units
  out_amount      UInt128,                    -- base units
  mid_fp6         UInt64,                     -- fixed-point 1e6
  slip_bps        UInt16,
  routes          Array(String),              -- market labels in the route
  meta            String,
  ingest_ts       DateTime64(3, 'UTC') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (pair, ts);