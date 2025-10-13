import { fetchConcentratedLiquidityPool, setWhirlpoolsConfig } from '@orca-so/whirlpools';
import { createSolanaRpc, devnet, address } from '@solana/kit';

await setWhirlpoolsConfig('solanaDevnet');
const devnetRpc = createSolanaRpc(devnet('https://api.devnet.solana.com'));

const tokenMintOne = address("So11111111111111111111111111111111111111112");
const tokenMintTwo = address("BRjpCHtyQLNCo8gqRUr8jtdAj5AjPYQaoqbvcZiHok1k");
const tickSpacing = 64;

const poolInfo = await fetchConcentratedLiquidityPool(
  devnetRpc,
  tokenMintOne,
  tokenMintTwo,
  tickSpacing
);

if (poolInfo.initialized) {
  console.log("Pool is initialized:", poolInfo);
} else {
  console.log("Pool is not initialized:", poolInfo);
};