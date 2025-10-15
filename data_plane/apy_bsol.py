import requests
from typing import TypedDict, Optional

class SolBlazeApyResponse(TypedDict):
    success: bool
    apy: float  

BASE_URL = "https://stake.solblaze.org"

def get_solblaze_apy() -> SolBlazeApyResponse:
    url = f"{BASE_URL}/api/v1/apy"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    try:
        result = get_solblaze_apy()
        print("BlazeStake APY:", result["apy"], "success:", result["success"])
    except Exception as e:
        print("Error:", e)
