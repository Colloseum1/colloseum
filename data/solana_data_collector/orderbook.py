# # First, install the necessary library: pip install phoenix-sdk
# import asyncio
# from solders.pubkey import Pubkey
# from phoenix.client import PhoenixClient

# async def get_phoenix_data():

#     RPC_URL = "https://wild-late-season.solana-devnet.quiknode.pro/b0ebcc50a76d22c777b9f18945f0d47e9f71ccaf/"
    
#     # 2. Specify the market public key (example: SOL/USDC)
#     # You can find other market addresses in the Phoenix DEX documentation
#     market_pubkey = Pubkey.from_string("4DoNfFBfF7UokCC2FQzmpbXZ1_CjSbACCe1cd6rP_u4v")

#     try:
#         client = await PhoenixClient.from_http(RPC_URL)
#         market_state = client.get_market_state(market_pubkey)
#         bids_ladder = market_state.get_bids_ladder(levels=10) # Get 10 levels of bids
#         asks_ladder = market_state.get_asks_ladder(levels=10) # Get 10 levels of asks
#         bid_depth = [market_state.ticks_to_price_and_size(p, s) for p, s in bids_ladder.levels]
#         ask_depth = [market_state.ticks_to_price_and_size(p, s) for p, s in asks_ladder.levels]

#         data = {
#             "ts": market_state.header.timestamp,
#             "market": str(market_pubkey),
#             "best_bid_fp64": bids_ladder.levels[0][0] if bids_ladder.levels else None,
#             "best_ask_fp64": asks_ladder.levels[0][0] if asks_ladder.levels else None,
#             "best_bid_price": bid_depth[0][0] if bid_depth else None,
#             "best_ask_price": ask_depth[0][0] if ask_depth else None,
#             "bid_depth": bid_depth,
#             "ask_depth": ask_depth,
#             "last_trade_px_fp64": market_state.header.last_price,
#             "last_trade_price": market_state.ticks_to_price(market_state.header.last_price),
#             "last_trade_qty": market_state.base_lots_to_base_units(market_state.header.last_base_lots_traded),
#             "agg_window_ms": None,
#         }

#         print("--- Phoenix Market Data ---")
#         for key, value in data.items():
#             print(f"{key}: {value}")
#         print("---------------------------")

#     except Exception as e:
#         print(f"An error occurred: {e}")

# if __name__ == "__main__":
#     asyncio.run(get_phoenix_data())


# import base64
# import asyncio
# from solana.rpc.async_api import AsyncClient
# from solders.publickey import PubKey   
# from construct import Struct, Int64ul, Int32ul, Array, Bytes


# RPC_URL = "https://wild-late-season.solana-devnet.quiknode.pro/b0ebcc50a76d22c777b9f18945f0d47e9f71ccaf/"
# MARKET_PUBKEY_STR = "Hf7gRejPNt1ZW5vEvQ5vGV4dtgExjRyqgDBrZuq2QffA"


# MARKET_PUBKEY = PublicKey(MARKET_PUBKEY_STR)

# PhoenixMarketLayout = Struct(
#     "header" / Bytes(8),
#     "market_size" / Int64ul,
#     "best_bid_price_fp6" / Int64ul,
#     "best_ask_price_fp6" / Int64ul,
#     "best_bid_qty" / Int64ul,
#     "best_ask_qty" / Int64ul,
#     "last_trade_price_fp6" / Int64ul,
#     "last_trade_qty" / Int64ul,
#     "num_bids" / Int32ul,
#     "num_asks" / Int32ul,
#     "bid_levels" / Array(10, Int64ul),
#     "ask_levels" / Array(10, Int64ul),
# )

# async def fetch_and_decode_market():
#     async with AsyncClient(RPC_URL) as client:

#         resp = await client.get_account_info(MARKET_PUBKEY)
#         if not resp["result"]["value"]:
#             print("❌ Market account not found.")
#             return

#         data_base64 = resp["result"]["value"]["data"][0]
#         data_bytes = base64.b64decode(data_base64)

#         decoded = PhoenixMarketLayout.parse(data_bytes)

#         print("\n📊 Phoenix Market Snapshot")
#         print(f"Best Bid (fp6): {decoded.best_bid_price_fp6}")
#         print(f"Best Ask (fp6): {decoded.best_ask_price_fp6}")
#         print(f"Last Trade Px (fp6): {decoded.last_trade_price_fp6}")
#         print(f"Last Trade Qty: {decoded.last_trade_qty}")
#         print("\n🧱 Top 5 Bids:", decoded.bid_levels[:5])
#         print("🧱 Top 5 Asks:", decoded.ask_levels[:5])

# if __name__ == "__main__":
#     asyncio.run(fetch_and_decode_market())

from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
import asyncio
import base64
from construct import Struct, Int64ul, Int32ul, Array, Bytes

# RPC_URL = "https://wild-late-season.solana-devnet.quiknode.pro/b0ebcc50a76d22c777b9f18945f0d47e9f71ccaf/"
RPC_URL = "https://api.mainnet-beta.solana.com"
MARKET_PUBKEY = Pubkey.from_string("8B7qVJYgYQv9Egh35JtRfiEY4bVEjN5Rhi7LqD7TQY7H")


PhoenixMarketLayout = Struct(
    "header" / Bytes(8),
    "market_size" / Int64ul,
    "best_bid_price_fp6" / Int64ul,
    "best_ask_price_fp6" / Int64ul,
    "best_bid_qty" / Int64ul,
    "best_ask_qty" / Int64ul,
    "last_trade_price_fp6" / Int64ul,
    "last_trade_qty" / Int64ul,
    "num_bids" / Int32ul,
    "num_asks" / Int32ul,
    "bid_levels" / Array(10, Int64ul),
    "ask_levels" / Array(10, Int64ul),
)
async def fetch_and_decode_market():
    async with AsyncClient(RPC_URL) as client:
        resp = await client.get_account_info(MARKET_PUBKEY)
        account_info = resp.value  # ✅ new API

        if account_info is None:
            print("❌ Market account not found.")
            return
        data_base64 = account_info.data[0]
        data_bytes = base64.b64decode(data_base64)

        decoded = PhoenixMarketLayout.parse(data_bytes)

        print("\n📊 Phoenix Market Snapshot (SOL/USDC)")
        print(f"Best Bid (fp6): {decoded.best_bid_price_fp6} => {decoded.best_bid_price_fp6 / 1_000_000:.2f} USDC")
        print(f"Best Ask (fp6): {decoded.best_ask_price_fp6} => {decoded.best_ask_price_fp6 / 1_000_000:.2f} USDC")
        print(f"Last Trade Px (fp6): {decoded.last_trade_price_fp6} => {decoded.last_trade_price_fp6 / 1_000_000:.2f} USDC")
        print(f"Last Trade Qty: {decoded.last_trade_qty}")

        print("\n🧱 Top 5 Bids:", decoded.bid_levels[:5])
        print("🧱 Top 5 Asks:", decoded.ask_levels[:5])

if __name__ == "__main__":
    asyncio.run(fetch_and_decode_market())
