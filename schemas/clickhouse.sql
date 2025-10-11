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
<<<<<<< HEAD


/* Raw Pyth oracle feed history: one row per parsed update */
CREATE TABLE IF NOT EXISTS sol.oracles_unified (
  ts            DateTime64(3, 'UTC'),
  slot          UInt64,
  feed_id       String,
  source        String,
  price_fp6     UInt128,
  expo          Int8,
  ingest_ts     DateTime64(3, 'UTC') DEFAULT now(),
  raw           String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (feed_id, ts);

/* Recent prioritization fee median per sample window */
CREATE TABLE IF NOT EXISTS sol.prioritization_fees (
  ts                          DateTime64(3, 'UTC'),
  slot                        UInt64,
  p50_fee_microlamports_per_cu UInt64,
  ingest_ts                   DateTime64(3, 'UTC') DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (ts, slot);
=======
>>>>>>> fce4847 (grafana)
