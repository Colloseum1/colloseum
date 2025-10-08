# data_plane/ingest_drift_perps.py
from __future__ import annotations
import os, time, json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import requests, redis
from dotenv import load_dotenv

# --- Env / clients -----------------------------------------------------------
load_dotenv(".env")

CLICKHOUSE_HTTP = os.getenv("CLICKHOUSE_HTTP", "http://localhost:8123")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "ch")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "chpwd")

DRIFT_DATA_API = os.getenv("DRIFT_DATA_API", "https://data.api.drift.trade").rstrip("/")
DRIFT_MARKETS = [m.strip() for m in os.getenv("DRIFT_MARKETS", "SOL-PERP").split(",") if m.strip()]

REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "15"))
TIMEOUT      = 10
DRIFT_DEBUG  = os.getenv("DRIFT_DEBUG", "0") == "1"

rds  = redis.from_url(REDIS_URL, decode_responses=True)
sess = requests.Session()
sess.headers.update({"Accept": "application/json"})

# --- Helpers -----------------------------------------------------------------
def now_ts_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

def canon(name: str) -> str:
    return (name or "").upper().replace("_", "-").strip()

def ch_insert_json_each_row(rows: List[dict]) -> None:
    if not rows: return
    payload = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
    sql = f"INSERT INTO sol.perps_metrics FORMAT JSONEachRow\n{payload}"
    r = requests.post(
        CLICKHOUSE_HTTP,
        data=sql,
        auth=(CLICKHOUSE_USER, CLICKHOUSE_PASSWORD),
        timeout=15,
    )
    if r.status_code >= 400:
        print("[CH] insert error:", r.status_code, r.text)
        r.raise_for_status()

def get_contracts() -> tuple[Dict[str, dict], List[dict]]:
    """
    Build an index by:
      • ticker_id (e.g., 'SOL-PERP')
      • <BASE>-PERP alias (e.g., 'SOL-PERP')
    """
    url = f"{DRIFT_DATA_API}/contracts"
    r = sess.get(url, timeout=TIMEOUT); r.raise_for_status()
    data = r.json()

    arr: List[dict] = []
    if isinstance(data, dict) and isinstance(data.get("contracts"), list):
        arr = [c for c in data["contracts"] if isinstance(c, dict)]
    elif isinstance(data, list):
        arr = [c for c in data if isinstance(c, dict)]

    idx: Dict[str, dict] = {}
    for c in arr:
        tkr  = c.get("ticker_id")
        base = c.get("base_currency")
        if tkr:
            idx[canon(tkr)] = c
        if base:
            idx[canon(f"{base}-PERP")] = c
    return idx, arr

def get_latest_funding_record(market_name: str) -> Optional[dict]:
    url = f"{DRIFT_DATA_API}/fundingRates"
    r = sess.get(url, params={"marketName": market_name}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    arr = data.get("fundingRates", data.get("data", data))
    if isinstance(arr, dict): arr = list(arr.values())
    if not isinstance(arr, list): return None
    arr = [x for x in arr if isinstance(x, dict)]
    if not arr: return None
    # sort by numeric ts
    def ts_key(x: dict):
        try: return int(x.get("ts", 0))
        except Exception: return 0
    arr.sort(key=ts_key, reverse=True)
    return arr[0]

def funding_fraction(rec: dict) -> float:
    """
    Per-interval fraction per docs:
    (fundingRate / 1e9) / (oraclePriceTwap / 1e6)
    """
    try:
        fr = float(rec.get("fundingRate", 0)) / 1e9
        oracle = float(rec.get("oraclePriceTwap", 0)) / 1e6
        if oracle <= 0: return 0.0
        return fr / oracle
    except Exception:
        return 0.0

# --- Poll loop ----------------------------------------------------------------
def poll_once() -> None:
    ts = now_ts_str()
    rows: List[dict] = []
    wrote = 0
    with_funding = 0

    # 1) contracts (for open interest)
    try:
        index_map, contracts_list = get_contracts()
    except Exception as e:
        print("[contracts] fetch/parse error:", repr(e))
        index_map, contracts_list = {}, []

    for m in DRIFT_MARKETS:
        try:
            # resolve contract by exact ticker or base alias
            c = index_map.get(canon(m), {})
            # no “derived” fallback values – use contracts only for OI
            oi_float = 0.0
            oi_raw = c.get("open_interest")
            if oi_raw is not None:
                try: oi_float = float(oi_raw)
                except Exception: oi_float = 0.0

            # 2) funding + twaps from fundingRates
            fr = get_latest_funding_record(m)
            if fr:
                try: index_fp6 = int(fr.get("oraclePriceTwap", 0))
                except: index_fp6 = 0
                try: mark_fp6  = int(fr.get("markPriceTwap", 0))
                except: mark_fp6 = 0

                frac = funding_fraction(fr)             # e.g. 0.000012508
                bps  = float(frac * 10_000.0)           # Float32 column
                ppm  = int(round(frac * 1_000_000.0))   # Int32 column
                with_funding += 1
            else:
                index_fp6 = 0
                mark_fp6  = 0
                bps = 0.0
                ppm = 0

            row = {
                "ts": ts,
                "market": m,
                "index_price_fp6": index_fp6,
                "mark_price_fp6":  mark_fp6,
                "funding_rate_bps": bps,               # Float32 in CH
                "funding_rate_ppm": ppm,               # Int32 in CH
                "open_interest": int(oi_float),        # legacy int (if your table has it)
                "open_interest_float": oi_float,       # exact decimal
                "meta": json.dumps(
                    {"funding": fr, "contracts": c},
                    separators=(",", ":")
                ),
            }
            rows.append(row)

            # Redis cache – store the exacts you care about
            rds.hset(f"latest:perp:{m}", mapping={
                "index_fp6": str(index_fp6),
                "mark_fp6":  str(mark_fp6),
                "funding_bps": f"{bps:.6f}",
                "funding_ppm": str(ppm),
                "oi": str(int(oi_float)),
                "oi_float": f"{oi_float}",
                "ts": ts,
            })
            wrote += 1

        except Exception as e:
            print(f"[{m}] poll error:", repr(e))

    if rows:
        ch_insert_json_each_row(rows)
    print(f"[tick {ts}] perps: requested={len(DRIFT_MARKETS)}, wrote={wrote}, with_funding={with_funding}")

# --- Main ---------------------------------------------------------------------
if __name__ == "__main__":
    if not DRIFT_MARKETS:
        raise SystemExit("No DRIFT_MARKETS in .env")
    print("Starting Drift perps ingestor…")
    print("Markets:", DRIFT_MARKETS, "| DEBUG:", DRIFT_DEBUG)
    while True:
        poll_once()
        time.sleep(POLL_SECONDS)
