# data_plane/pyth.py
from __future__ import annotations
import os, time, json
from datetime import datetime, timezone
from decimal import Decimal, getcontext, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Iterable

import requests, redis
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Env & clients
# -----------------------------------------------------------------------------
load_dotenv(".env")

CLICKHOUSE_HTTP = os.getenv("CLICKHOUSE_HTTP", "http://localhost:8123")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "ch")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "chpwd")
REDIS_URL  = os.getenv("REDIS_URL", "redis://localhost:6379/0")

PYTH_BASE = os.getenv("PYTH_BASE", "https://benchmarks.pyth.network").rstrip("/")
PYTH_FEEDS_RAW = os.getenv("PYTH_FEEDS", "").replace(",", "\n").strip()
PYTH_POLL_SECONDS  = int(os.getenv("PYTH_POLL_SECONDS", "30"))
PYTH_WINDOW_SECONDS= int(os.getenv("PYTH_WINDOW_SECONDS", "60"))  # API requires <= 60
PYTH_FINALITY_LAG  = int(os.getenv("PYTH_FINALITY_LAG", "45"))    # initial slack seconds
MAX_RETRIES        = int(os.getenv("PYTH_MAX_RETRIES", "3"))
PYTH_DEBUG         = os.getenv("PYTH_DEBUG", "0") == "1"

TIMEOUT = 15
sess = requests.Session(); sess.headers.update({"Accept": "application/json"})
rds  = redis.from_url(REDIS_URL, decode_responses=True)
getcontext().prec = 40

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def now_ts_str_ms() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def to_fp6_from_price_expo(price: int | str, expo: int | str) -> int:
    """
    Pyth value = price * 10^expo
    We store fixed-point 1e6: round(value * 1e6)
    """
    try:
        p = Decimal(str(price))
        e = int(expo)
        val = p * (Decimal(10) ** Decimal(e))
        fp6 = (val * Decimal(1_000_000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(fp6)
    except Exception:
        return 0

def ch_insert_json_each_row(table: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    payload = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
    sql = f"INSERT INTO {table} FORMAT JSONEachRow\n{payload}"
    r = sess.post(CLICKHOUSE_HTTP, data=sql, auth=(CLICKHOUSE_USER, CLICKHOUSE_PASSWORD), timeout=TIMEOUT)
    if r.status_code >= 400:
        raise RuntimeError(f"ClickHouse insert error {r.status_code}: {r.text}")

# -----------------------------------------------------------------------------
# Pyth fetchers
# -----------------------------------------------------------------------------
def pyth_updates_window(price_feed_ids: List[str], end_ts: int, window_sec: int) -> Any:
    """
    GET /v1/updates/price/{end_ts}/{window_sec}
      - ids must be repeated params
      - window_sec must be <= 60
    Response may be:
      - dict with key 'parsed' (list), or
      - top-level list of parsed entries
    """
    if not price_feed_ids:
        return None

    window_sec = min(max(window_sec, 1), 60)
    params: List[tuple[str,str]] = [("encoding","hex"), ("parsed","true"), ("unique","true")]
    for fid in price_feed_ids:
        params.append(("ids", fid))

    url = f"{PYTH_BASE}/v1/updates/price/{end_ts}/{window_sec}"
    r = sess.get(url, params=params, timeout=TIMEOUT)
    if r.status_code >= 400:
        raise requests.HTTPError(f"{r.status_code} {r.reason}: {r.text}", response=r)
    return r.json()

def extract_parsed_entries(resp: Any) -> List[dict]:
    """
    Normalize the response into a flat list of parsed entries with fields:
      id, price.{price, expo, publish_time}, metadata.slot, ...
    Handles:
      - {"parsed": [ ... ]}
      - [ ... ]  (top-level list of entries or list of items each with 'parsed')
    """
    out: List[dict] = []
    if resp is None:
        return out

    if isinstance(resp, dict):
        # dict with 'parsed' or 'data'
        arr = resp.get("parsed") or resp.get("data")
        if isinstance(arr, list):
            out = [x for x in arr if isinstance(x, dict)]
        else:
            # sometimes the dict itself may look like a parsed entry
            if isinstance(resp.get("price"), dict) and resp.get("id"):
                out = [resp]
    elif isinstance(resp, list):
        # could be list of parsed entries, or list of wrappers (each with parsed)
        for item in resp:
            if isinstance(item, dict):
                if "parsed" in item and isinstance(item["parsed"], list):
                    out.extend([x for x in item["parsed"] if isinstance(x, dict)])
                else:
                    # direct parsed-like entry
                    if item.get("id") and isinstance(item.get("price"), dict):
                        out.append(item)

    if PYTH_DEBUG:
        print(f"[DEBUG] extract_parsed_entries: type={type(resp).__name__} -> {len(out)} entries")
        if out[:1]:
            print("[DEBUG] sample keys:", list(out[0].keys()))
    return out

# -----------------------------------------------------------------------------
# Parse & store
# -----------------------------------------------------------------------------
def parse_and_store_pyth(response_json: Any) -> int:
    entries = extract_parsed_entries(response_json)
    if not entries:
        return 0

    rows: List[Dict[str, Any]] = []
    ingest_ts = now_ts_str_ms()

    for entry in entries:
        try:
            feed_id = entry.get("id")
            price_obj = entry.get("price") or {}
            meta = entry.get("metadata") or {}

            publish_time = price_obj.get("publish_time")
            price_raw = price_obj.get("price")
            expo = price_obj.get("expo")
            slot = meta.get("slot")

            if not (feed_id and publish_time is not None and price_raw is not None and expo is not None and slot is not None):
                if PYTH_DEBUG:
                    print("[DEBUG] skipping incomplete entry:", json.dumps(entry)[:200])
                continue

            ts_str = datetime.fromtimestamp(int(publish_time), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            price_fp6 = to_fp6_from_price_expo(price_raw, expo)

            row = {
                "ts": ts_str,
                "slot": int(slot),
                "feed_id": str(feed_id),
                "source": "pyth",
                "price_fp6": price_fp6,
                "expo": int(expo),
                "ingest_ts": ingest_ts,
                "raw": json.dumps(entry, separators=(",", ":")),
            }
            rows.append(row)

            # Redis latest snapshot
            rds.set(f"latest:feed:{feed_id}", json.dumps({
                "ts": ts_str, "slot": int(slot), "feed_id": str(feed_id),
                "price_fp6": price_fp6, "expo": int(expo),
                "source": "pyth", "ingest_ts": ingest_ts
            }, separators=(",", ":")))
        except Exception as e:
            if PYTH_DEBUG:
                print("[DEBUG] entry parse error:", repr(e))
            continue

    if rows:
        ch_insert_json_each_row("sol.oracles_unified", rows)
    return len(rows)

# -----------------------------------------------------------------------------
# Backoff wrapper (avoid future timestamps)
# -----------------------------------------------------------------------------
def fetch_with_backoff(feeds: List[str], window: int) -> Any:
    last_err: Optional[Exception] = None
    for attempt in range(MAX_RETRIES + 1):
        slack = PYTH_FINALITY_LAG + attempt * 30  # +30s per retry
        end_ts = int(time.time()) - slack
        try:
            return pyth_updates_window(feeds, end_ts, window)
        except requests.HTTPError as e:
            last_err = e
            msg = (e.response.text if getattr(e, "response", None) else str(e))[:200]
            if "Timestamp cannot be in the future" in msg and attempt < MAX_RETRIES:
                if PYTH_DEBUG:
                    print(f"[DEBUG] future ts; retrying with more slack (attempt {attempt+1})")
                continue
            raise
        except Exception as e:
            last_err = e
            break
    if last_err:
        raise last_err

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
def main():
    if not PYTH_FEEDS_RAW:
        print("No PYTH_FEEDS configured. Set PYTH_FEEDS in .env (comma or newline separated feed IDs).")
        return

    feeds = [ln.strip() for ln in PYTH_FEEDS_RAW.splitlines() if ln.strip()]
    window = min(max(PYTH_WINDOW_SECONDS, 1), 60)
    print(f"Starting Pyth poller… feeds={len(feeds)} window={window}s interval={PYTH_POLL_SECONDS}s (initial lag={PYTH_FINALITY_LAG}s)")

    while True:
        try:
            data = fetch_with_backoff(feeds, window)
            wrote = parse_and_store_pyth(data)
            print(f"[tick {now_ts_str_ms()}] pyth: wrote={wrote}")
        except requests.HTTPError as e:
            print("[pyth] HTTP error:", e)
        except Exception as e:
            print("[pyth] error:", e)
        time.sleep(PYTH_POLL_SECONDS)

if __name__ == "__main__":
    main()
