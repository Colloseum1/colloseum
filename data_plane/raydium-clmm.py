#https://api-v3-devnet.raydium.io/docs/#/POOLS
#https://api-v3-devnet.raydium.io/
import requests
import json

BASE_URL = "https://api-v3-devnet.raydium.io/"  

def get_pools_info_list_v2(
    poolType=None,
    mintFilter=None,
    hasReward=None,
    sortField=None,
    sortType=None,
    size=10,
    nextPageId=None,
    mint1=None,
    mint2=None
):
    """
    Calls the /pools/info/list-v2 endpoint with the given query parameters.
    """
    url = f"{BASE_URL}/pools/info/list-v2"
    params = {}

    if poolType:
        params["poolType"] = poolType
    if mintFilter:
        params["mintFilter"] = mintFilter
    if hasReward is not None:
        params["hasReward"] = str(hasReward).lower()  # true/false
    if sortField:
        params["sortField"] = sortField
    if sortType:
        params["sortType"] = sortType
    if size:
        params["size"] = size
    if nextPageId:
        params["nextPageId"] = nextPageId
    if mint1:
        params["mint1"] = mint1
    if mint2:
        params["mint2"] = mint2

    response = requests.get(url, params=params)
    response.raise_for_status()  
    return response.json()

if __name__ == "__main__":
    result = get_pools_info_list_v2(
        poolType="Concentrated",
        hasReward=True,
        sortField="liquidity",
        sortType="desc",
        size=5
    )

    print("✅ Pools info:")
    # for pool in result.get("data", []):
    #     print(pool)
    print(json.dumps(result, indent=2))
