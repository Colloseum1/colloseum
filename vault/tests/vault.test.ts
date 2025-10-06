import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { Vault } from "../target/types/vault";
import { PublicKey, Keypair, SystemProgram } from "@solana/web3.js";
import {
  TOKEN_PROGRAM_ID,
  createMint,
  createAccount,
  mintTo,
  ASSOCIATED_TOKEN_PROGRAM_ID,
  getAssociatedTokenAddressSync,
  createAssociatedTokenAccountInstruction,
} from "@solana/spl-token";
import { assert } from "chai";

describe("vault", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Vault as Program<Vault>;
  const admin = provider.wallet as anchor.Wallet;
  
  let mint: PublicKey;
  let userTokenAccount: PublicKey;
  let vaultTokenAccount: PublicKey;
  let vaultPda: PublicKey;
  let policyPda: PublicKey;
  let registryPda: PublicKey;

  before(async () => {
    // Create mint
    mint = await createMint(
      provider.connection,
      admin.payer,
      admin.publicKey,
      null,
      6
    );

    // Create user token account
    userTokenAccount = await createAccount(
      provider.connection,
      admin.payer,
      mint,
      admin.publicKey
    );

    // Mint tokens to user
    await mintTo(
      provider.connection,
      admin.payer,
      mint,
      userTokenAccount,
      admin.payer,
      1000000000 // 1000 tokens
    );

    // Derive PDAs
    [vaultPda] = PublicKey.findProgramAddressSync(
      [Buffer.from("vault"), admin.publicKey.toBuffer()],
      program.programId
    );
  });

  it("Initializes vault infrastructure", async () => {
    // Initialize policy
    const policyKeypair = Keypair.generate();
    await program.methods
      .initializePolicy({
        maxSlippageBps: 50, // 0.5%
        maxOracleDeltaBps: 100, // 1%
        maxOracleAgeSlots: new anchor.BN(150),
        maxConfidenceBps: 200, // 2%
        perOrderNotionalUsdCents: new anchor.BN(100000), // $1,000
        dailyNotionalUsdCents: new anchor.BN(1000000), // $10,000
        maxComputeUnits: 400000,
        maxPriorityFeeLamports: new anchor.BN(100000),
      })
      .accounts({
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([policyKeypair])
      .rpc();

    // Initialize registry
    const registryKeypair = Keypair.generate();
    const jupiterProgram = new PublicKey("JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"); // Mainnet Jupiter
    
    await program.methods
      .initializeRegistry(jupiterProgram)
      .accounts({
        registry: registryKeypair.publicKey,
        admin: admin.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([registryKeypair])
      .rpc();

    // Initialize vault
    await program.methods
      .initializeVault(mint)
      .accounts({
        vault: vaultPda,
        admin: admin.publicKey,
        policy: policyKeypair.publicKey,
        registry: registryKeypair.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    // Create vault token account using associated token address with allowOwnerOffCurve
    vaultTokenAccount = getAssociatedTokenAddressSync(
      mint,
      vaultPda,
      true // allowOwnerOffCurve
    );

    // Manually create the associated token account for PDA
    const createAtaIx = createAssociatedTokenAccountInstruction(
      admin.publicKey,
      vaultTokenAccount,
      vaultPda,
      mint,
      TOKEN_PROGRAM_ID,
      ASSOCIATED_TOKEN_PROGRAM_ID
    );

    const tx = new anchor.web3.Transaction().add(createAtaIx);
    await provider.sendAndConfirm(tx);

    // Verify vault was created
    const vaultAccount = await program.account.vault.fetch(vaultPda);
    assert.equal(vaultAccount.admin.toString(), admin.publicKey.toString());
    assert.equal(vaultAccount.baseMint.toString(), mint.toString());

    console.log("✅ Vault infrastructure initialized");
  });

  it("Deposits tokens into vault", async () => {
    const depositAmount = new anchor.BN(100000000); // 100 tokens

    await program.methods
      .deposit(depositAmount)
      .accounts({
        vault: vaultPda,
        user: admin.publicKey,
        userTokenAccount: userTokenAccount,
        vaultTokenAccount: vaultTokenAccount,
      })
      .rpc();

    // Verify balance
    const vaultTokenInfo = await provider.connection.getTokenAccountBalance(vaultTokenAccount);
    assert.equal(vaultTokenInfo.value.amount, depositAmount.toString());

    console.log("✅ Deposited successfully");
  });
});