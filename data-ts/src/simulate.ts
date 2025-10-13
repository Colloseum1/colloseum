import {
    Connection,
    clusterApiUrl,
    Keypair,
    SystemProgram,
    Transaction,
    LAMPORTS_PER_SOL,
  } from "@solana/web3.js";
  
  (async () => {
    // 1️⃣ Connect to Devnet
    const connection = new Connection(clusterApiUrl("devnet"), "confirmed");
  
    // 2️⃣ Generate a temporary payer keypair
    const payer = Keypair.generate();
  
    // Airdrop some SOL to payer so the tx has balance context
    const airdropSig = await connection.requestAirdrop(
      payer.publicKey,
      1 * LAMPORTS_PER_SOL
    );
    await connection.confirmTransaction(airdropSig, "confirmed");
  
    // 3️⃣ Create a dummy recipient
    const recipient = Keypair.generate();
  
    // 4️⃣ Build a simple transfer instruction
    const ix = SystemProgram.transfer({
      fromPubkey: payer.publicKey,
      toPubkey: recipient.publicKey,
      lamports: 0.1 * LAMPORTS_PER_SOL,
    });
  
    // 5️⃣ Construct a transaction
    const tx = new Transaction().add(ix);
    tx.feePayer = payer.publicKey;
    tx.recentBlockhash = (await connection.getLatestBlockhash()).blockhash;
  
    // 6️⃣ **Sign but don't send**
    tx.sign(payer);
  
    // 7️⃣ **Simulate the transaction**
    const simulationResult = await connection.simulateTransaction(tx);
  
    console.log("Simulation logs:", simulationResult.value.logs);
    console.log("Simulation error:", simulationResult.value.err);
  })();
  