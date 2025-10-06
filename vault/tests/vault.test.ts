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
  let vaultBump: number;
  let policyKeypair: Keypair;
  let registryKeypair: Keypair;

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
    [vaultPda, vaultBump] = PublicKey.findProgramAddressSync(
      [Buffer.from("vault"), admin.publicKey.toBuffer()],
      program.programId
    );
  });

  it("Initializes vault infrastructure", async () => {
    // Initialize policy
    policyKeypair = Keypair.generate();
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
    registryKeypair = Keypair.generate();
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
    assert.equal(vaultAccount.bump, vaultBump);

    console.log("✅ Vault infrastructure initialized");
  });

  it("Deposits tokens into vault", async () => {
    const depositAmount = new anchor.BN(500000000); // 500 tokens

    await program.methods
      .deposit(depositAmount)
      .accounts({
        vault: vaultPda,
        user: admin.publicKey,
        userTokenAccount: userTokenAccount,
        vaultTokenAccount: vaultTokenAccount,
        admin: admin.publicKey,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    // Verify balance
    const vaultTokenInfo = await provider.connection.getTokenAccountBalance(vaultTokenAccount);
    assert.equal(vaultTokenInfo.value.amount, depositAmount.toString());

    const userTokenInfo = await provider.connection.getTokenAccountBalance(userTokenAccount);
    assert.equal(userTokenInfo.value.amount, "500000000"); // 1000 - 500 = 500 remaining

    console.log("✅ Deposited successfully");
  });

  it("Withdraws tokens from vault", async () => {
    const withdrawAmount = new anchor.BN(200000000); // 200 tokens

    // Get balances before
    const vaultBalanceBefore = await provider.connection.getTokenAccountBalance(vaultTokenAccount);
    const userBalanceBefore = await provider.connection.getTokenAccountBalance(userTokenAccount);

    console.log("Before withdrawal:");
    console.log("  Vault:", vaultBalanceBefore.value.uiAmount);
    console.log("  User:", userBalanceBefore.value.uiAmount);

    // Withdraw
    await program.methods
      .withdraw(withdrawAmount)
      .accounts({
        vault: vaultPda,
        user: admin.publicKey,
        userTokenAccount: userTokenAccount,
        vaultTokenAccount: vaultTokenAccount,
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    // Verify balances after
    const vaultBalanceAfter = await provider.connection.getTokenAccountBalance(vaultTokenAccount);
    const userBalanceAfter = await provider.connection.getTokenAccountBalance(userTokenAccount);

    console.log("After withdrawal:");
    console.log("  Vault:", vaultBalanceAfter.value.uiAmount);
    console.log("  User:", userBalanceAfter.value.uiAmount);

    assert.equal(vaultBalanceAfter.value.amount, "300000000"); // 500 - 200 = 300
    assert.equal(userBalanceAfter.value.amount, "700000000");  // 500 + 200 = 700

    console.log("✅ Withdrawn successfully");
  });

  it("Prevents withdrawal when paused", async () => {
    // Pause the policy
    await program.methods
      .togglePause()
      .accounts({
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
      })
      .rpc();

    console.log("Policy paused");

    // Try to withdraw (should fail)
    try {
      await program.methods
        .withdraw(new anchor.BN(100000000))
        .accounts({
          vault: vaultPda,
          user: admin.publicKey,
          userTokenAccount: userTokenAccount,
          vaultTokenAccount: vaultTokenAccount,
          policy: policyKeypair.publicKey,
          admin: admin.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .rpc();
      
      assert.fail("Withdrawal should have failed when paused");
    } catch (error) {
      assert.include(error.toString(), "Paused");
      console.log("✅ Withdrawal correctly blocked when paused");
    }

    // Unpause for remaining tests
    await program.methods
      .togglePause()
      .accounts({
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
      })
      .rpc();

    console.log("Policy unpaused");
  });

  it("Prevents withdrawal exceeding vault balance", async () => {
    const vaultBalance = await provider.connection.getTokenAccountBalance(vaultTokenAccount);
    const excessiveAmount = new anchor.BN(
      Number(vaultBalance.value.amount) + 1000000
    );

    try {
      await program.methods
        .withdraw(excessiveAmount)
        .accounts({
          vault: vaultPda,
          user: admin.publicKey,
          userTokenAccount: userTokenAccount,
          vaultTokenAccount: vaultTokenAccount,
          policy: policyKeypair.publicKey,
          admin: admin.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .rpc();
      
      assert.fail("Should not allow excessive withdrawal");
    } catch (error) {
      console.log("✅ Excessive withdrawal correctly blocked");
    }
  });

  it("Completes full cycle: deposit more, then withdraw all", async () => {
    // Deposit 50 more tokens
    const depositAmount = new anchor.BN(50000000);
    await program.methods
      .deposit(depositAmount)
      .accounts({
        vault: vaultPda,
        user: admin.publicKey,
        userTokenAccount: userTokenAccount,
        vaultTokenAccount: vaultTokenAccount,
        admin: admin.publicKey,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    console.log("Deposited 50 more tokens");

    // Withdraw everything
    const vaultBalance = await provider.connection.getTokenAccountBalance(vaultTokenAccount);
    const withdrawAll = new anchor.BN(vaultBalance.value.amount);

    await program.methods
      .withdraw(withdrawAll)
      .accounts({
        vault: vaultPda,
        user: admin.publicKey,
        userTokenAccount: userTokenAccount,
        vaultTokenAccount: vaultTokenAccount,
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    console.log("Withdrew all tokens");

    // Verify vault is empty
    const finalVaultBalance = await provider.connection.getTokenAccountBalance(vaultTokenAccount);
    assert.equal(finalVaultBalance.value.amount, "0");

    // Verify user got everything back
    const finalUserBalance = await provider.connection.getTokenAccountBalance(userTokenAccount);
    assert.equal(finalUserBalance.value.amount, "1000000000"); // All 1000 tokens back
    
    console.log("✅ Full cycle complete - vault is empty, user has all tokens");
  });
});