const BASE_URL = "https://stake.solblaze.org";

interface SolBlazeApyResponse {
  success: boolean;
  apy: number;  
}


export async function getSolBlazeApy(): Promise<SolBlazeApyResponse> {
  const url = `${BASE_URL}/api/v1/apy`;
  const res = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch BlazeStake APY: ${res.status} ${res.statusText}`);
  }

  const data = await res.json() as SolBlazeApyResponse;
  return data;
}

// Example usage
(async () => {
  try {
    const apyResp = await getSolBlazeApy();
    console.log("BlazeStake APY:", apyResp.apy, "success:", apyResp.success);
  } catch (err) {
    console.error("Error fetching BlazeStake APY:", err);
  }
})();
