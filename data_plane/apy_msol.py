import requests

BASE_URL = "https://api.marinade.finance"

def get_msol_apy(period: str, time: str = None):
    url = f"{BASE_URL}/msol/apy/{period}"
    params = {}
    if time:
        params["time"] = time

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    print(get_msol_apy("7d")) 
