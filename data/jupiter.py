# import http.client

# #search: Request a search by token's symbol, name or mint address
# conn = http.client.HTTPSConnection("lite-api.jup.ag")

# def search(query: str):
#   headers = {
#     'Accept': 'application/json'
#   }
#   conn.request("GET", f"/ultra/v1/search?query={query}", headers=headers)
#   res = conn.getresponse()
#   data = res.read()
# #   print(data.decode("utf-8"))
#   return data.decode("utf-8")

# #holdings:Request for detailed token holdings of an account including token account information

# def holdings(address: str):
#   headers = {
#     'Accept': 'application/json'
#   }
#   conn.request("GET", f"/ultra/v1/holdings?address={address}", headers=headers)
#   res = conn.getresponse()
#   data = res.read()
#   # print(data.decode("utf-8"))
#   return data.decode("utf-8")

# # search("SOL")

# #Request for token information and warnings of mints
# #example: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
# def shield(address: str):
#     payload=''
#     headers={
#         'Accept': 'application/json'
#     }
#     # conn.request("GET", "/ultra/v1/shield?mints={address}", payload, headers)
#     conn.request("GET", f"/ultra/v1/shield?mints={address}", payload, headers)
#     res = conn.getresponse()
#     data = res.read()
#     print(data.decode("utf-8"))
#     return data.decode("utf-8")

# # shield("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")


# #quote 
# #inputMint:The pubkey or token mint address e.g. So11111111111111111111111111111111111111112
# #outputMint	The pubkey or token mint address e.g. EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
# #amount: in lamports 
# #slippageBps e.g. 1% = 100bps

# def quote(inputMint: str, outputMint: str, amount: int, slippageBps: int):
#     payload = ''
#     headers = {
#         'Accept': 'application/json'
#     }
#     conn.request("GET", f"/ultra/v1/quote?inputMint={inputMint}&outputMint={outputMint}&amount={amount}&slippageBps={slippageBps}", payload, headers)
#     res = conn.getresponse()
#     data = res.read()
#     print(data.decode("utf-8"))
#     return data.decode("utf-8")

# # quote("So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 10000000, 100)
# #more at https://dev.jup.ag/docs/api/swap-api/quote

# #swap-instructions
# #Request for swap instructions that you can use from the quote you get from /quote
# def swap_instructions(pubKey: str):
# payload = json.dumps({
#   "userPublicKey": {pubKey},
#   "quoteResponse": {
#     "inputMint": "So11111111111111111111111111111111111111112",
#     "inAmount": "1000000",
#     "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
#     "outAmount": "125630",
#     "otherAmountThreshold": "125002",
#     "swapMode": "ExactIn",
#     "slippageBps": 50,
#     "platformFee": None,
#     "priceImpactPct": "0",
#     "routePlan": [
#       {
#         "swapInfo": {
#           "ammKey": "AvBSC1KmFNceHpD6jyyXBV6gMXFxZ8BJJ3HVUN8kCurJ",
#           "label": "Obric V2",
#           "inputMint": "So11111111111111111111111111111111111111112",
#           "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
#           "inAmount": "1000000",
#           "outAmount": "125630",
#           "feeAmount": "5",
#           "feeMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
#         },
#         "percent": 100
#       }
#     ]
#   },
#   "prioritizationFeeLamports": {
#     "priorityLevelWithMaxLamports": {
#       "maxLamports": 10000000,
#       "priorityLevel": "veryHigh"
#     }
#   },
#   "dynamicComputeUnitLimit": True
# })
#     headers = {
#         'Content-Type': 'application/json',
#         'Accept': 'application/json'
#     }
#     conn.request("POST", "/swap/v1/swap-instructions", payload, headers)
#     res = conn.getresponse()
#     data = res.read()
#     print(data.decode("utf-8"))

import http.client
import json

conn = http.client.HTTPSConnection("lite-api.jup.ag")


# ------------------------------
# Search
# ------------------------------
def search(query: str):
    headers = {'Accept': 'application/json'}
    conn.request("GET", f"/ultra/v1/search?query={query}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")


# ------------------------------
# Holdings
# ------------------------------
def holdings(address: str):
    headers = {'Accept': 'application/json'}
    conn.request("GET", f"/ultra/v1/holdings?address={address}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")


# ------------------------------
# Shield
# ------------------------------
def shield(address: str):
    headers = {'Accept': 'application/json'}
    conn.request("GET", f"/ultra/v1/shield?mints={address}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")


# ------------------------------
# Quote
# ------------------------------
def quote(inputMint: str, outputMint: str, amount: int, slippageBps: int):
    headers = {'Accept': 'application/json'}
    conn.request(
        "GET",
        f"/ultra/v1/quote?inputMint={inputMint}&outputMint={outputMint}&amount={amount}&slippageBps={slippageBps}",
        headers=headers
    )
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")


# ------------------------------
# Transform quote into swap-ready format
# ------------------------------
def prepare_quote_for_swap(quote: dict) -> dict:
    return {
        "inputMint": quote["inputMint"],
        "inAmount": quote["inAmount"],
        "outputMint": quote["outputMint"],
        "outAmount": quote["outAmount"],
        "otherAmountThreshold": quote["otherAmountThreshold"],
        "swapMode": quote["swapMode"],
        "slippageBps": quote["slippageBps"],
        "platformFee": quote.get("platformFee", None),   # safe
        "priceImpactPct": quote.get("priceImpactPct", "0"),
        "routePlan": quote["routePlan"],
    }



# ------------------------------
# Swap Instructions
# ------------------------------
def swap_instructions(pubKey: str, quote_response: dict):
    payload = json.dumps({
        "userPublicKey": pubKey,
        "quoteResponse": quote_response,
        "prioritizationFeeLamports": {
            "priorityLevelWithMaxLamports": {
                "maxLamports": 10000000,
                "priorityLevel": "veryHigh"
            }
        },
        "dynamicComputeUnitLimit": True
    })

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    conn.request("POST", "/swap/v1/swap-instructions", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")


# ------------------------------
# Example Usage
# ------------------------------
# if __name__ == "__main__":
#     # Step 1: Get Quote
#     quote_raw = quote(
#         "So11111111111111111111111111111111111111112",  # SOL
#         "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
#         1000000,   # 0.001 SOL (lamports)
#         50         # 0.5% slippage
#     )
#     print("RAW QUOTE RESPONSE:", quote_raw)

#     # Step 2: Parse Quote
#     quote_json = json.loads(quote_raw)
#     quote_ready = prepare_quote_for_swap(quote_json)

#     # Step 3: Swap Instructions
#     swap_resp = swap_instructions(
#         "jdocuPgEAjMfihABsPgKEvYtsmMzjUHeq9LX4Hvs7f3",  #  Solana wallet pubkey
#         quote_ready
#     )
#     # print("SWAP INSTRUCTIONS RESPONSE:", swap_resp)
#     swap_resp_json = json.loads(swap_resp)
#     print("SWAP INSTRUCTIONS RESPONSE (PRETTY):")
#     print(json.dumps(swap_resp_json, indent=2))
