CREATE TABLE IF NOT EXISTS sol.oracles_unified (
  ts         DateTime64(3, 'UTC'),
  slot       UInt64,
  feed_id    String,
  source     LowCardinality(String),
  price_fp6  Int64,               -- price in fixed 1e6 (Pyth price+expo -> fp6)
  expo       Int32,               -- Pyth exponent (for traceability)
  ingest_ts  DateTime64(3, 'UTC') DEFAULT now(),
  raw        String               -- raw parsed entry as JSON string
)
ENGINE = ReplacingMergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (feed_id, ts, slot);
