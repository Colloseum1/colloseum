import { Connection, Keypair } from "@solana/web3.js";
import { MarginfiClient, getConfig } from "@mrgnlabs/marginfi-client-v2";
import { NodeWallet } from "@mrgnlabs/mrgn-common";

async function main() {
  console.log("Script started");
  const rpcUrl = process.env.SOLANA_RPC || "https://api.devnet.solana.com";
  const connection = new Connection(rpcUrl, "confirmed");
  const wallet = NodeWallet.local();
  const config = getConfig("dev");
  const client = await MarginfiClient.fetch(config, wallet, connection);
    let banksArr: any[] = [];
if (Array.isArray(client.banks)) {
  banksArr = client.banks;
} else if (client.banks instanceof Map) {
  banksArr = Array.from(client.banks.values());
} else if (typeof client.banks === "object") {
  banksArr = Object.values(client.banks);
} else {
  banksArr = [];
}

console.log("banksArr contents:", banksArr);

const availableSymbols = banksArr
  .filter(b => b && b.meta && b.meta.tokenSymbol)
  .map(b => b.meta.tokenSymbol);

console.log("Available bank token symbols:", availableSymbols);

  const bankLabels = ["SOL", "USDC"];
  for (const label of bankLabels) {
    const bank = client.getBankByTokenSymbol(label);
    if (!bank) {
      console.log("No bank found for:", label);
      continue;
    }

    const utilization_bps = bank.computeUtilizationRate();
    const { lendingRate: supply_apy_fp6, borrowingRate: borrow_apy_fp6 } = bank.computeInterestRates();

    console.log({
      ts: Date.now(),
      protocol: "marginfi",
      reserve: bank.address.toBase58(),
      symbol: bank.meta.tokenSymbol,
      utilization_bps: utilization_bps.toNumber(),
      supply_apy_fp6: supply_apy_fp6.toNumber(),
      borrow_apy_fp6: borrow_apy_fp6.toNumber(),
    });

  }
}

main().catch(e => console.error("Fatal error:", e));

