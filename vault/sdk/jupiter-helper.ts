import {
  Connection,
  PublicKey,
  VersionedTransaction,
  AccountMeta,
} from "@solana/web3.js";

const JUPITER_PROGRAM_ID = new PublicKey(
  "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
);
const JUPITER_API_URL = "https://lite-api.jup.ag/swap/v1";

export interface JupiterQuote {
  inputMint: string;
  outputMint: string;
  inAmount: string;
  outAmount: string;
  otherAmountThreshold: string;
  swapMode: string;
  slippageBps: number;
  priceImpactPct: string;
}

export interface JupiterSwapData {
  fullInstructionData: Buffer;
  allAccounts: AccountMeta[];
  quote: JupiterQuote;
}

/**
 * Fetch Jupiter quote from API
 */
async function fetchQuote(
  inputMint: PublicKey,
  outputMint: PublicKey,
  amount: number,
  slippageBps: number
): Promise<JupiterQuote> {
  const url =
    `${JUPITER_API_URL}/quote?` +
    `inputMint=${inputMint.toString()}&` +
    `outputMint=${outputMint.toString()}&` +
    `amount=${amount}&` +
    `slippageBps=${slippageBps}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Jupiter quote failed: ${response.statusText}`);
  }
  return (await response.json()) as JupiterQuote;
}

/**
 * Fetch Jupiter swap transaction from API
 */
async function fetchSwapTransaction(
  quote: JupiterQuote,
  userPublicKey: PublicKey
): Promise<string> {
  const response = await fetch(`${JUPITER_API_URL}/swap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      quoteResponse: quote,
      userPublicKey: userPublicKey.toString(),
      wrapAndUnwrapSol: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Jupiter swap failed: ${response.statusText}`);
  }
  const data = (await response.json()) as { swapTransaction: string };
  return data.swapTransaction;
}

/**
 * Load Address Lookup Tables from transaction
 */
async function loadAddressLookupTables(
  message: any,
  connection: Connection
): Promise<PublicKey[]> {
  const lookupAccounts: PublicKey[] = [];

  if (message.addressTableLookups && message.addressTableLookups.length > 0) {
    for (const lookup of message.addressTableLookups) {
      const lookupTable = await connection.getAddressLookupTable(
        lookup.accountKey
      );
      if (lookupTable.value) {
        lookupAccounts.push(...lookupTable.value.state.addresses);
      }
    }
  }

  return lookupAccounts;
}

/**
 * Get Jupiter swap data for vault CPI
 *
 * Fetches quote and transaction from Jupiter API, extracts instruction data
 * and accounts, then replaces dummy accounts with actual vault accounts.
 */
export async function getJupiterSwapData(
  inputMint: PublicKey,
  outputMint: PublicKey,
  amount: number,
  slippageBps: number,
  vaultPda: PublicKey,
  vaultSourceTokenAccount: PublicKey,
  vaultDestTokenAccount: PublicKey,
  connection: Connection
): Promise<JupiterSwapData> {
  // 1. Get quote
  const quote = await fetchQuote(inputMint, outputMint, amount, slippageBps);

  // 2. Get swap transaction
  const swapTxBase64 = await fetchSwapTransaction(quote, vaultPda);
  const tx = VersionedTransaction.deserialize(
    Buffer.from(swapTxBase64, "base64")
  );

  // 3. Load address lookup tables
  const lookupAccounts = await loadAddressLookupTables(tx.message, connection);
  const allAccountKeys = [...tx.message.staticAccountKeys, ...lookupAccounts];

  // 4. Find Jupiter instruction
  const jupiterIx = tx.message.compiledInstructions.find((ix) =>
    tx.message.staticAccountKeys[ix.programIdIndex].equals(JUPITER_PROGRAM_ID)
  );

  if (!jupiterIx) {
    throw new Error("Jupiter instruction not found in transaction");
  }

  // 5. Extract and replace accounts
  // Replace dummy accounts with actual vault accounts at known indices:
  // - Index 2: user_transfer_authority -> vaultPda
  // - Index 3: user_source_token -> vaultSourceTokenAccount
  // - Index 6: user_dest_token -> vaultDestTokenAccount
  const allAccounts: AccountMeta[] = jupiterIx.accountKeyIndexes
    .map((keyIndex, idx) => {
      let pubkey = allAccountKeys[keyIndex];

      // Replace with vault accounts
      if (idx === 2) pubkey = vaultPda;
      if (idx === 3) pubkey = vaultSourceTokenAccount;
      if (idx === 6) pubkey = vaultDestTokenAccount;

      return { pubkey, isSigner: false, isWritable: true };
    })
    .filter((acc) => acc.pubkey); // Remove undefined

  return {
    fullInstructionData: Buffer.from(jupiterIx.data),
    allAccounts,
    quote,
  };
}

/**
 * Calculate route price in 6 decimal fixed point
 * Used for vault validation against oracle price
 */
export function calculateRoutePriceFp6(quote: JupiterQuote): bigint {
  const inAmount = BigInt(quote.inAmount);
  const outAmount = BigInt(quote.outAmount);
  return (outAmount * BigInt(1000000)) / inAmount;
}
