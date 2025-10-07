import { Connection, PublicKey, VersionedTransaction, AccountMeta } from "@solana/web3.js";

export interface JupiterQuote {
  inputMint: string;
  outputMint: string;
  inAmount: string;
  outAmount: string;
  otherAmountThreshold: string;
  swapMode: string;
  slippageBps: number;
  priceImpactPct: string;
  routePlan: any[];
}

export interface JupiterSwapData {
  routeId: number;
  routePlan: Buffer;
  jupiterAccounts: {
    programAuthority: PublicKey;
    programSourceTokenAccount: PublicKey;
    programDestTokenAccount: PublicKey;
  };
  remainingAccounts: AccountMeta[];
  quote: JupiterQuote;
  platformFeeBps: number;
}

export async function getJupiterQuote(
  inputMint: PublicKey,
  outputMint: PublicKey,
  amount: number,
  slippageBps: number = 50
): Promise<JupiterQuote> {
  const response = await fetch(
    `https://quote-api.jup.ag/v6/quote?` +
    `inputMint=${inputMint.toString()}&` +
    `outputMint=${outputMint.toString()}&` +
    `amount=${amount}&` +
    `slippageBps=${slippageBps}`
  );

  if (!response.ok) {
    throw new Error(`Jupiter quote failed: ${response.statusText}`);
  }

  return await response.json();
}

export async function getJupiterSwapInstructions(
  quote: JupiterQuote,
  userPublicKey: PublicKey
): Promise<any> {
  const response = await fetch("https://quote-api.jup.ag/v6/swap", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      quoteResponse: quote,
      userPublicKey: userPublicKey.toString(),
      wrapAndUnwrapSol: true,
      dynamicComputeUnitLimit: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Jupiter swap instructions failed: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Extract Jupiter swap data from API response for vault CPI
 * This parses the Jupiter transaction to extract route_id, route_plan, and accounts
 */
export async function getJupiterSwapData(
  inputMint: PublicKey,
  outputMint: PublicKey,
  amount: number,
  slippageBps: number,
  vaultPda: PublicKey
): Promise<JupiterSwapData> {
  // 1. Get quote from Jupiter
  const quote = await getJupiterQuote(inputMint, outputMint, amount, slippageBps);

  // 2. Get swap transaction
  const swapResponse = await getJupiterSwapInstructions(quote, vaultPda);

  // 3. Deserialize the transaction
  const transaction = VersionedTransaction.deserialize(
    Buffer.from(swapResponse.swapTransaction, 'base64')
  );

  // 4. Find the Jupiter swap instruction (usually the first or main instruction)
  const message = transaction.message;
  const jupiterProgramId = new PublicKey('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4');

  let jupiterInstructionIndex = -1;
  for (let i = 0; i < message.compiledInstructions.length; i++) {
    const programIdIndex = message.compiledInstructions[i].programIdIndex;
    const programId = message.staticAccountKeys[programIdIndex];
    if (programId.equals(jupiterProgramId)) {
      jupiterInstructionIndex = i;
      break;
    }
  }

  if (jupiterInstructionIndex === -1) {
    throw new Error('Jupiter instruction not found in transaction');
  }

  const jupiterInstruction = message.compiledInstructions[jupiterInstructionIndex];
  const instructionData = Buffer.from(jupiterInstruction.data);

  // 5. Parse instruction data
  // Format: [discriminator:8][id:1][route_plan:variable][in_amount:8][quoted_out_amount:8][slippage_bps:2][platform_fee_bps:1]
  const routeId = instructionData.readUInt8(8); // After 8-byte discriminator

  // Find where route_plan ends (this is tricky - we need to parse the route plan structure)
  // For now, we'll extract the full instruction data after the discriminator and route_id
  // The client will need to send this to the vault program
  const routePlanStart = 9;
  // Route plan is variable length, so we extract everything after route_id up to the fixed params at the end
  // Fixed params at end: in_amount(8) + quoted_out_amount(8) + slippage_bps(2) + platform_fee_bps(1) = 19 bytes
  const routePlanEnd = instructionData.length - 19;
  const routePlan = instructionData.slice(routePlanStart, routePlanEnd);

  // Extract platform fee (last byte)
  const platformFeeBps = instructionData.readUInt8(instructionData.length - 1);

  // 6. Extract account metas
  const accounts = jupiterInstruction.accountKeyIndexes.map((keyIndex: number) => {
    const pubkey = message.staticAccountKeys[keyIndex];
    // Determine if writable/signer from message
    const isWritable = message.compiledInstructions[jupiterInstructionIndex].accountKeyIndexes.includes(keyIndex);
    return {
      pubkey,
      isSigner: false,
      isWritable,
    };
  });

  // 7. Identify Jupiter-specific accounts
  // These are typically in fixed positions for SharedAccountsRoute
  const programAuthority = accounts[1]?.pubkey; // Jupiter's program authority
  const programSourceTokenAccount = accounts[4]?.pubkey; // Jupiter's temp source account
  const programDestTokenAccount = accounts[5]?.pubkey; // Jupiter's temp dest account

  // Remaining accounts are route-specific (DEX accounts, pools, etc.)
  const remainingAccounts = accounts.slice(11); // After the fixed SharedAccountsRoute accounts

  return {
    routeId,
    routePlan,
    jupiterAccounts: {
      programAuthority: programAuthority || PublicKey.default,
      programSourceTokenAccount: programSourceTokenAccount || PublicKey.default,
      programDestTokenAccount: programDestTokenAccount || PublicKey.default,
    },
    remainingAccounts,
    quote,
    platformFeeBps,
  };
}

/**
 * Calculate route mid price in 6 decimal fixed point
 */
export function calculateRoutePriceFp6(quote: JupiterQuote): bigint {
  const inAmount = BigInt(quote.inAmount);
  const outAmount = BigInt(quote.outAmount);

  // Price = outAmount / inAmount, scaled to 6 decimals
  // For example: if swapping 1 USDC (1000000) to get 0.005 SOL (5000000 lamports)
  // Price = 5000000 / 1000000 = 5 (scaled to 6 decimals = 5000000)
  const priceFp6 = (outAmount * BigInt(1000000)) / inAmount;

  return priceFp6;
}