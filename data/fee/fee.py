from __future__ import annotations
import os
import json
import requests
from datetime import datetime, timezone
from statistics import median
from typing import Any

CLICKHOUSE_HTTP = os.getenv("CLICKHOUSE_HTTP", "http://localhost:8123")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "ch")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "chpwd")


def ch_insert_json_each_row(rows):
    if not rows:
        return
    tables = {}
    for r in rows:
        tbl = r.pop("_table", "sol.jup_quotes")
        tables.setdefault(tbl, []).append(r)

    for tbl, recs in tables.items():
        payload = "\n".join(json.dumps(r, separators=(",", ":")) for r in recs)
        sql = f"INSERT INTO {tbl} FORMAT JSONEachRow\n{payload}"
        r = requests.post(CLICKHOUSE_HTTP, data=sql, auth=(CLICKHOUSE_USER, CLICKHOUSE_PASSWORD), timeout=15)
        if r.status_code >= 400:
            print(f"[CH] insert error into {tbl}:", r.status_code, r.text)
            r.raise_for_status()

def get_recent_prioritization_fees(rpc_url: str | None = None) -> list[dict[str, Any]]:
    rpc_url = rpc_url or os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getRecentPrioritizationFees", "params": []}
    
    r = requests.post(rpc_url, json=payload, timeout=10)
    r.raise_for_status()
    
    response_json = r.json()
    if isinstance(response_json, dict):
        result_list = response_json.get("result")
        if isinstance(result_list, list):
            return result_list     
    return []


def compute_p50_from_samples(samples: list) -> int | None:
    fees = [int(s.get("prioritizationFee")) for s in samples if s.get("prioritizationFee") is not None]
    if not fees:
        return None
    med = median(fees)
    return int(med)


def compute_and_write_prioritization_p50(rpc_url: str | None = None):
    try:
        samples = get_recent_prioritization_fees(rpc_url)
    except requests.RequestException as e:
        print(f"[fee] Error fetching prioritization fees: {e}")
        return

    if not samples:
        print("[fee] no prioritization fee samples")
        return
    p50 = compute_p50_from_samples(samples)
    if p50 is None:
        print("[fee] unable to compute p50 from samples")
        return
    latest_slot = 0
    try:
        latest_slot = max(int(s.get("slot", 0)) for s in samples)
    except Exception:
        latest_slot = 0

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    row = {
        "_table": "sol.prioritization_fees",
        "ts": ts,
        "slot": latest_slot,
        "p50_fee_microlamports_per_cu": int(p50),
    }
    ch_insert_json_each_row([row])
    print(f"[fee] wrote prioritization p50={p50} slot={latest_slot} ts={ts}")


if __name__ == "__main__":
    compute_and_write_prioritization_p50()