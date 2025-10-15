import requests
from datetime import datetime

def handler():
    api_url = "https://kobe.mainnet.jito.network/api/v1/stake_pool_stats"

    start = datetime.fromisoformat("2022-10-31T00:00:00+00:00")
    end = datetime.utcnow()

    stats_request = {
        "bucket_type": "Daily",
        "range_filter": {
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
        },
        "sort_by": {
            "field": "BlockTime",
            "order": "Asc",
        },
    }

    try:
        response = requests.post(api_url, json=stats_request, headers={"Content-Type": "application/json"})
        response.raise_for_status()  # raise exception if not 2xx

        data = response.json()

        if data:
            aggregated_mev_rewards = data.get("aggregated_mev_rewards")
            apy = data.get("apy", [])
            mev_rewards = data.get("mev_rewards")
            num_validators = data.get("num_validators")
            supply = data.get("supply")
            tvl = data.get("tvl")

            camel_case_data = {
                "getStakePoolStats": {
                    "aggregatedMevRewards": aggregated_mev_rewards,
                    "apy": apy,
                    "mevRewards": mev_rewards,
                    "numValidators": num_validators,
                    "supply": supply,
                    "tvl": tvl,
                }
            }

            if not apy:
                raise ValueError("No APY data found in response")

            latest_apy_data = apy[-1].get("data")
            latest_apy_percent = latest_apy_data * 100 if latest_apy_data is not None else None

            print("latest apy %:", latest_apy_percent)
            return latest_apy_percent

        else:
            raise ValueError("No data found in response")

    except Exception as e:
        print("Error fetching data:", e)
        return None


if __name__ == "__main__":
    handler()
