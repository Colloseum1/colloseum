# --- top of file ---
from __future__ import annotations
import os, time, json
from datetime import datetime, timezone
from typing import List, Tuple
import requests, redis
from dotenv import load_dotenv
from jupiter_client import JupiterClient

# 1) Load .env FIRST
load_dotenv(dotenv_path=".env")

# 2) Read envs AFTER loading
CLICKHOUSE_HTTP = os.getenv("CLICKHOUSE_HTTP", "http://localhost:8123")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "ch")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "chpwd")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))
SLIPPAGE_BPS = int(os.getenv("SLIPPAGE_BPS", "50"))
AMOUNT = int(os.getenv("AMOUNT_IN_BASE_UNITS", "1000000"))

# Pairs env format: label|in_mint|out_mint per line
PAIRS: List[Tuple[str, str, str]] = []
for line in os.getenv("PAIRS", "").splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        label, in_mint, out_mint = [x.strip() for x in line.split("|")]
        PAIRS.append((label, in_mint, out_mint))
    except ValueError:
        print(f"[WARN] Bad PAIRS line (expected label|in|out): {line}")

rds = redis.from_url(REDIS_URL, decode_responses=True)
client = JupiterClient()

def ch_insert_json_each_row(rows: List[dict]):
    if not rows:
        return
    payload = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
    sql = f"INSERT INTO sol.jup_quotes FORMAT JSONEachRow\n{payload}"
    r = requests.post(
        CLICKHOUSE_HTTP, data=sql, auth=(CLICKHOUSE_USER, CLICKHOUSE_PASSWORD), timeout=15
    )
    if r.status_code >= 400:
        print("[CH] insert error:", r.status_code, r.text)
        r.raise_for_status()

def fp6(x: float) -> int:
    return int(round(x * 1_000_000))

def poll_once():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    rows: List[dict] = []
    got = 0
    for label, in_mint, out_mint in PAIRS:
        try:
            q = client.quote(in_mint, out_mint, AMOUNT, SLIPPAGE_BPS)
            if isinstance(q, dict) and "error" in q:
                print(f"[{label}] Jupiter error: {q.get('error')}")
                continue
            best = JupiterClient.best_route_from_quote(q)
            if not best:
                print(f"[{label}] No route returned")
                continue
            in_amt = int(best.get("inAmount", 0))
            out_amt = int(best.get("outAmount", 0))
            if in_amt <= 0 or out_amt <= 0:
                print(f"[{label}] Non-positive in/out amounts: in={in_amt} out={out_amt}")
                continue
            mid = (out_amt / in_amt)
            route_plan = best.get("routePlan", [])
            if route_plan:
                routes = [ (hop.get("swapInfo") or {}).get("label", "") for hop in route_plan ]
            else:
                routes = [ m.get("label", "") for m in best.get("marketInfos", []) ]    

            rows.append({
                "ts": ts,
                "pair": label,
                "input_mint": in_mint,
                "output_mint": out_mint,
                "in_amount": in_amt,
                "out_amount": out_amt,
                "mid_fp6": fp6(mid),
                "slip_bps": int(best.get("slippageBps", SLIPPAGE_BPS)),
                "routes": routes,
                "meta": json.dumps(best, separators=(",", ":")),  # store JSON as String
            })

            rds.hset(f"latest:pair:{label}", mapping={
                "mid_fp6": str(fp6(mid)),
                "ts": ts,
                "routes": ",".join(routes),
            })
            got += 1
        except Exception as e:
            print(f"[{label}] poll error:", repr(e))
    if rows:
        ch_insert_json_each_row(rows)
    print(f"[tick {ts}] polled {len(PAIRS)} pairs, got {got} routes, inserted {len(rows)} rows")

# --- bottom of file ---
if __name__ == "__main__":
    if not PAIRS:
        raise SystemExit("No PAIRS configured in .env")
    print("Starting Jupiter ingestor…")
    print(f"Pairs: {PAIRS}")
    print(f"Poll every {POLL_SECONDS}s, amount={AMOUNT}, slippage_bps={SLIPPAGE_BPS}")
    while True:
        poll_once()
        time.sleep(POLL_SECONDS)
