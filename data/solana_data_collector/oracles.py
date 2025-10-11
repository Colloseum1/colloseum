import os
from typing import Any, List, Optional
import requests

PRICE_FEEDS: dict[str, str] = {
    "sol": "0xde87506dabfadbef89af2d5d796ebae80ddaea240fc7667aa808fce3629cd8fb",
    "eth": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
    "jup": "0x0a0408d619e9380abad35060f9192039ed5042fa6f82301d0e48bb52be830996",
    "ray": "0x91568baa8beb53db23eb3fb7f22c6e8bd303d103919e19733f2bb642d3e7987a",
    "orca": "0x37505261e557e251290b8c8899453064e8d760ed5c65a779726f2490980da74c",
    "pyth": "0x0bbf28e9a841a1cc788f6a361b17ca072d0ea3098a1e5df1c3922d06719579ff",
    "bonk": "0x72b021217ca3fe68922a19aaf990109cb9d84e9ad004b4d2025ad6f529314419",
    "wif": "0x4ca4beeca86f0d164160323817a4e42b10010a724c2217c6ee41b54cd4cc61fc",
    "jto": "0xb43660a5f790c69354b0729a5ef9d50d68f1df92107540210b9cccba1f947cc2",
    "hnt": "0x649fdd7ec08e8e2a20f425729854e90293dcbe2376abc47197a14da6ff339756",
    "mobile": "0xff4c53361e36a9b837433c87d290c229e1f01aec5ef98d9f3f70953a20a629ce",
    "iot": "0x6b701e292e0836d18a5904a08fe94534f9ab5c3d4ff37dc02c74dd0f4901944d",
    "btc": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
    "usdc": "0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a",
    "usdt": "0x2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b",
    "msol" : "0xc2289a6a43d2ce91c6f55caec370f4acc38a2ed477f58813334c6d03749ff2a4",
    "jitosol": "0x67be9f519b95cf24338801051f9a808eff0a578ccb388db73b7f6fe1de019ffb",
    "bsol": "0x89875379e70f8fbadc17aef315adf3a8d5d160b811435537e03c97e8aac97d9c"

}

def get_price_feed_id(symbol: str) -> Optional[str]:
    """Return the Pyth price feed id for an asset symbol.

    Accepts forms like 'sol', 'SOL/USD', 'sol/usd', or a raw feed id like '0x...'.
    Returns the canonical hex string (lowercase, with 0x) or None if unknown.
    """
    if not symbol:
        return None
    s = symbol.strip().lower()

    # If already a hex-like feed id, normalize and return
    if s.startswith("0x") and len(s) >= 3:
        return s

    # Accept forms like 'asset/usd' or 'asset-usd'
    if "/" in s:
        s = s.split("/", 1)[0]
    elif "-" in s:
        s = s.split("-", 1)[0]

    return PRICE_FEEDS.get(s)


PYTH_BASE = os.getenv("PYTH_BASE", "https://benchmarks.pyth.network").rstrip("/")

def pyth_prices(price_feed_ids: List[str], timestamp: int) -> Any:
    if not price_feed_ids:
        return None

    params: List[tuple[str,str]] = [("encoding","hex"), ("parsed","true"), ("unique","true")]
    for fid in price_feed_ids:
        params.append(("ids", fid))

    url = f"{PYTH_BASE}/v1/updates/price/{timestamp}"
    r = sess.get(url, params=params, timeout=TIMEOUT)
    if r.status_code >= 400:
        raise requests.HTTPError(f"{r.status_code} {r.reason}: {r.text}", response=r)
    return r.json()