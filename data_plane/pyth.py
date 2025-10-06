#https://benchmarks.pyth.network
#feeds id gotten from feed ids: https://docs.pyth.network/price-feeds/price-feeds#feed-ids
import requests
import json

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