#!/usr/bin/env python3
from __future__ import annotations
import os
import requests
import json
from typing import Any

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

def main():
    rpc = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    try:
        samples = get_recent_prioritization_fees(rpc)
    except Exception as e:
        print("Error fetching prioritization fees:", repr(e))
        raise

    print(f"Fetched {len(samples)} samples from {rpc}")
    if samples:
        print(json.dumps(samples, indent=2))


if __name__ == "__main__":
    main()
