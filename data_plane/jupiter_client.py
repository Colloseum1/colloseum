from __future__ import annotations
import json
from typing import Any, Dict, Optional
import requests

class JupiterClient:
    def __init__(self, base_url: str = "https://lite-api.jup.ag", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.s = requests.Session()
        self.timeout = timeout
        self.s.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        r = self.s.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = self.s.post(
            f"{self.base_url}{path}",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    # ------------------------------
    # Public endpoints
    # ------------------------------
    def search(self, query: str) -> Dict[str, Any]:
        return self._get("/ultra/v1/search", params={"query": query})

    def holdings(self, address: str) -> Dict[str, Any]:
        return self._get("/ultra/v1/holdings", params={"address": address})

    def shield(self, mint: str) -> Dict[str, Any]:
        return self._get("/ultra/v1/shield", params={"mints": mint})

    def quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int) -> Dict[str, Any]:
        # NOTE: Jupiter Ultra returns a payload with `data: [best, ...]`.
        j = self._get(
            "/ultra/v1/quote",
            params={
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": slippage_bps,
            },
        )
        return j

    @staticmethod
    def best_route_from_quote(quote_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Try `data[0]` fallback to raw (if the API shape differs)
        data = quote_json.get("data")
        if isinstance(data, list) and data:
            return data[0]
        # If already a single-route dict
        if isinstance(quote_json, dict) and "inAmount" in quote_json:
            return quote_json
        return None

    @staticmethod
    def prepare_quote_for_swap(best: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "inputMint": best["inputMint"],
            "inAmount": best["inAmount"],
            "outputMint": best["outputMint"],
            "outAmount": best["outAmount"],
            "otherAmountThreshold": best.get("otherAmountThreshold", best.get("outAmount")),
            "swapMode": best.get("swapMode", "ExactIn"),
            "slippageBps": best.get("slippageBps", 50),
            "platformFee": best.get("platformFee"),
            "priceImpactPct": best.get("priceImpactPct", "0"),
            "routePlan": best.get("routePlan", []),
        }

    def swap_instructions(self, user_pubkey: str, quote_response: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(
            "/swap/v1/swap-instructions",
            payload={
                "userPublicKey": user_pubkey,
                "quoteResponse": quote_response,
                "prioritizationFeeLamports": {
                    "priorityLevelWithMaxLamports": {
                        "maxLamports": 10_000_000,
                        "priorityLevel": "veryHigh",
                    }
                },
                "dynamicComputeUnitLimit": True,
            },
        )