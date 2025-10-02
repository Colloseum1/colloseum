import http.client

#search: Request a search by token's symbol, name or mint address
conn = http.client.HTTPSConnection("lite-api.jup.ag")

def search(query: str):
  headers = {
    'Accept': 'application/json'
  }
  conn.request("GET", f"/ultra/v1/search?query={query}", headers=headers)
  res = conn.getresponse()
  data = res.read()
#   print(data.decode("utf-8"))
  return data.decode("utf-8")

#holdings:Request for detailed token holdings of an account including token account information

def holdings(address: str):
  headers = {
    'Accept': 'application/json'
  }
  conn.request("GET", f"/ultra/v1/holdings?address={address}", headers=headers)
  res = conn.getresponse()
  data = res.read()
  # print(data.decode("utf-8"))
  return data.decode("utf-8")

# search("SOL")

#Request for token information and warnings of mints
#example: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
def shield(address: str):
    payload=''
    headers={
        'Accept': 'application/json'
    }
    # conn.request("GET", "/ultra/v1/shield?mints={address}", payload, headers)
    conn.request("GET", f"/ultra/v1/shield?mints={address}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))
    return data.decode("utf-8")

# shield("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")


#quote 
#inputMint:The pubkey or token mint address e.g. So11111111111111111111111111111111111111112
#outputMint	The pubkey or token mint address e.g. EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
#amount: in lamports 
#slippageBps e.g. 1% = 100bps

def quote(inputMint: str, outputMint: str, amount: int, slippageBps: int):
    payload = ''
    headers = {
        'Accept': 'application/json'
    }
    conn.request("GET", f"/ultra/v1/quote?inputMint={inputMint}&outputMint={outputMint}&amount={amount}&slippageBps={slippageBps}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))
    return data.decode("utf-8")

# quote("So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 100000, 100)
#more at https://dev.jup.ag/docs/api/swap-api/quote