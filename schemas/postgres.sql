CREATE TABLE IF NOT EXISTS assets (
  asset_id   text PRIMARY KEY,    -- mint address
  symbol     text NOT NULL,
  decimals   int  NOT NULL
);

CREATE TABLE IF NOT EXISTS pairs (
  pair_id    text PRIMARY KEY,    -- "<mint_in>/<mint_out>"
  label      text NOT NULL        -- "SOL/USDC"
);