#https://benchmarks.pyth.network
#feeds id gotten from feed ids: https://docs.pyth.network/price-feeds/price-feeds#feed-ids
import os
import requests
import json
import redis
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# load .env so env vars (CLICKHOUSE_HTTP, REDIS_URL, etc.) work when running this module
load_dotenv(dotenv_path=".env")

# ClickHouse/Redis settings (fall back to sensible locals)
CLICKHOUSE_HTTP = os.getenv("CLICKHOUSE_HTTP", "http://localhost:8123")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "ch")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "chpwd")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# redis client used for PIT/latest
rds = redis.from_url(REDIS_URL, decode_responses=True)

# timestamp = 1752004800  # July 8, 2025, 4PM ET
# price_feed_id = "ef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d"  # SOL/USD
# url = f"https://benchmarks.pyth.network/v1/updates/price/{timestamp}"
# params = {
#     "ids": price_feed_id,
#     "encoding": "hex",
#     "parsed": "true"
# }

# response = requests.get(url, params=params)
# if response.status_code == 200:
#     data = response.json()
#     if 'binary' in data:
#         data.pop('binary')
#     print(json.dumps(data, indent=4))
# else:
#     print("Error:", response.status_code, response.text)

def get_data_from_pyth(price_feed_id: str, timestamp: int):
    params={
        "ids": price_feed_id,
        "encoding": "hex",
        "parsed": "true"
    }
    url = f"https://benchmarks.pyth.network/v1/updates/price/{timestamp}"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'binary' in data:
            data.pop('binary')
            print(json.dumps(data, indent=4))
        return data
    else:
        print("Error:", response.status_code, response.text)


def _ch_insert(table: str, rows: List[Dict[str, Any]]):
    """Insert rows into ClickHouse using JSONEachRow via HTTP endpoint."""
    if not rows:
        return
    payload = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
    sql = f"INSERT INTO {table} FORMAT JSONEachRow\n{payload}"
    r = requests.post(CLICKHOUSE_HTTP, data=sql, auth=(CLICKHOUSE_USER, CLICKHOUSE_PASSWORD), timeout=15)
    if r.status_code >= 400:
        # propagate error so caller can decide how to handle
        raise RuntimeError(f"ClickHouse insert error {r.status_code}: {r.text}")


def parse_and_store_pyth(response_json: Dict[str, Any]):
    """Parse Pyth `parsed` array and store:
      - raw row(s) into ClickHouse table `sol.oracles_unified`
      - latest per-feed PIT into Redis key `latest:feed:{feed_id}` as JSON

    Extracted fields (minimum):
      - ts (from price.publish_time) -> stored as RFC timestamp string
      - slot (from metadata.slot)
      - feed_id (from id)
      - price_fp6 (from price.price) -> int
      - expo (from price.expo) -> int
    """
    parsed = response_json.get("parsed") or []
    if not parsed:
        return

    rows = []
    # format ingest_ts and ts fields to match ClickHouse DateTime64(3) (milliseconds, no timezone)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    for entry in parsed:
        feed_id = entry.get("id")
        price_obj = entry.get("price") or {}
        metadata = entry.get("metadata") or {}

        try:
            publish_time = price_obj.get("publish_time")
            slot = metadata.get("slot")
            price_raw = price_obj.get("price")
            expo = price_obj.get("expo")

            if feed_id is None or publish_time is None or slot is None or price_raw is None or expo is None:
                # skip incomplete
                continue

            ts_int = int(publish_time)
            slot_i = int(slot)
            price_fp6 = int(price_raw)
            expo_i = int(expo)

            ts_str = datetime.fromtimestamp(ts_int, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # prepare ClickHouse raw row
            rows.append({
                "ts": ts_str,
                "slot": slot_i,
                "feed_id": feed_id,
                "source": "pyth",
                "price_fp6": price_fp6,
                "expo": expo_i,
                "ingest_ts": now_iso,
                "raw": json.dumps(entry, separators=(",", ":")),
            })

            # Update Redis PIT/latest: keep structured JSON under key latest:feed:<feed_id>
            latest_key = f"latest:feed:{feed_id}"
            latest_payload = {
                "ts": ts_str,
                "slot": slot_i,
                "feed_id": feed_id,
                "price_fp6": price_fp6,
                "expo": expo_i,
                "source": "pyth",
                "ingest_ts": now_iso,
            }
            try:
                rds.set(latest_key, json.dumps(latest_payload, separators=(",", ":")))
            except Exception:
                # don't fail entire batch if Redis write fails
                pass

        except Exception:
            # skip malformed entry
            continue

    if rows:
        _ch_insert("sol.oracles_unified", rows)


def fetch_and_process_pyth(price_feed_id: str, timestamp: int):
    """Helper: fetch from Pyth and store results (ClickHouse raw + Redis PIT)."""
    data = get_data_from_pyth(price_feed_id, timestamp)
    if data:
        parse_and_store_pyth(data)


def main():
    """Poll configured PYTH_FEEDS at PYTH_POLL_SECONDS and process updates.

    Environment variables:
      PYTH_FEEDS - multiline string, each line a price feed id
      PYTH_POLL_SECONDS - seconds between polls (default 60)
      PYTH_TIMESTAMP - optional fixed timestamp to request (int); if not set uses current unix time
    """
    import os, time

    feeds_env = os.getenv("PYTH_FEEDS", "").strip()
    if not feeds_env:
        print("No PYTH_FEEDS configured in env; set PYTH_FEEDS with feed ids (one per line)")
        return

    feeds = [line.strip() for line in feeds_env.splitlines() if line.strip()]
    poll_seconds = int(os.getenv("PYTH_POLL_SECONDS", "60"))
    fixed_ts = os.getenv("PYTH_TIMESTAMP")

    print(f"Starting Pyth poller for {len(feeds)} feeds, interval={poll_seconds}s")
    while True:
        ts = int(fixed_ts) if fixed_ts else int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        for feed in feeds:
            try:
                fetch_and_process_pyth(feed, ts)
            except Exception as e:
                print(f"[feed:{feed}] error: {e}")
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()

# get_data_from_pyth("ef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d", 1752004800)
# def get_data_from_pyth_interval(price_feed_id:str, timestamp:str, interval:int):
#     params={
#         "ids": price_feed_id,
#         "encoding": "hex",
#         "parsed": "true",
#         "unique": "true",
#     }
#     url = f"https://benchmarks.pyth.network/v1/updates/price/{timestamp}/{interval}"
#     response = requests.get(url, params=params)
#     if response.status_code == 200:
#         data = response.json()
#         if 'binary' in data:
#             data.pop('binary')
#             print(json.dumps(data, indent=4))
#         return data
#     else:
#         print("Error:", response.status_code, response.text)

# get_data_from_pyth_interval("e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43", 1752004800,60)