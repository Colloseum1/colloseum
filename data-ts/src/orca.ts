import { fetchConcentratedLiquidityPool, setWhirlpoolsConfig } from '@orca-so/whirlpools';
import { createSolanaRpc, devnet, address } from '@solana/kit';

await setWhirlpoolsConfig('solanaDevnet');
const devnetRpc = createSolanaRpc(devnet('https://api.devnet.solana.com'));

// const tokenMintOne = address("So11111111111111111111111111111111111111112");
// const tokenMintTwo = address("BRjpCHtyQLNCo8gqRUr8jtdAj5AjPYQaoqbvcZiHok1k");
// const tickSpacing = 64;

// const poolInfo = await fetchConcentratedLiquidityPool(
//   devnetRpc,
//   tokenMintOne,
//   tokenMintTwo,
//   tickSpacing
// );

// if (poolInfo.initialized) {
//   console.log("Pool is initialized:", poolInfo);
// } else {
//   console.log("Pool is not initialized:", poolInfo);
// };

const getCLMMPoolInfo= async (tokenMintA: string, tokenMintB: string, tickSpacing: number) => {
  const poolInfo = await fetchConcentratedLiquidityPool(
    devnetRpc,
    address(tokenMintA),
    address(tokenMintB),
    tickSpacing
  );

  if (poolInfo.initialized) {
    return poolInfo;
  } else {
    throw new Error("Pool is not initialized");
  }
}

// Example usage
getCLMMPoolInfo("So11111111111111111111111111111111111111112", "BRjpCHtyQLNCo8gqRUr8jtdAj5AjPYQaoqbvcZiHok1k", 64)
  .then(poolInfo => console.log("Fetched pool info:", poolInfo))
  .catch(error => console.error(error));