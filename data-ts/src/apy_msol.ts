const BASE_URL = "https://api.marinade.finance";

export async function getMsolApy(period: string, time?: string) {
  const url = new URL(`${BASE_URL}/msol/apy/${period}`);
  if (time) {
    url.searchParams.append("time", time);
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch APY: ${res.status} ${res.statusText}`);
  }

  return await res.json();
}

//example usage 
(async () => {
  try {
    const data = await getMsolApy("7d");   
    console.log("mSOL APY data:", data);
    console.log("mSOL APY:", data.value * 100 + "%");
  } catch (err) {
    console.error(err);
  }
})();
