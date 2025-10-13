import {SolendMarket} from '@solendprotocol/solend-sdk'
import { Connection } from '@solana/web3.js';

async function getSolendDevnetData() {
  // Use the devnet RPC endpoint
  const connection = new Connection('https://api.devnet.solana.com');
  
  // Initialize the market for the 'devnet' environment
  const market = await SolendMarket.initialize(connection, 'devnet');

  // Load the reserve data from the devnet
  await market.loadReserves();

  const dataForProject = market.reserves.map(reserve => {
    const utilizationRatio = reserve.calculateUtilizationRatio();
    const utilizationBps = utilizationRatio * 10000;
    const supplyApy = reserve.stats.supplyInterestApy;
    const borrowApy = reserve.stats.borrowInterestApy;

    return {
      ts: new Date().toISOString(),
      protocol: 'solend-devnet',
      reserve: reserve.config.symbol,
      utilization_bps: utilizationBps,
      supply_apy: supplyApy,
      borrow_apy: borrowApy
    };
  });

  console.log(dataForProject);
}

getSolendDevnetData();