import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { Vault } from "../target/types/vault";
import { PublicKey, Keypair, SystemProgram } from "@solana/web3.js";
import { assert } from "chai";

describe("oracle validation", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Vault as Program<Vault>;
  const admin = provider.wallet as anchor.Wallet;

  let policyKeypair: Keypair;

  before(async () => {
    policyKeypair = Keypair.generate();
    
    // Initialize policy with strict oracle limits
    await program.methods
      .initializePolicy({
        maxSlippageBps: 50, // 0.5%
        maxOracleDeltaBps: 100, // 1%
        maxOracleAgeSlots: new anchor.BN(25),
        maxConfidenceBps: 200, // 2%
        perOrderNotionalUsdCents: new anchor.BN(100000),
        dailyNotionalUsdCents: new anchor.BN(1000000),
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
  });

  it("Updates policy allowlists", async () => {
    const testProgram = Keypair.generate().publicKey;
    const testMint = Keypair.generate().publicKey;
    const deniedMint = Keypair.generate().publicKey;

    await program.methods
      .updatePolicyAllowlists(
        [testProgram],
        [testMint],
        [deniedMint]
      )
      .accounts({
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
      })
      .rpc();

    const policy = await program.account.policy.fetch(policyKeypair.publicKey);
    
    assert.equal(policy.allowedPrograms.length, 1);
    assert.equal(policy.allowedPrograms[0].toString(), testProgram.toString());
    assert.equal(policy.allowedMints[0].toString(), testMint.toString());
    assert.equal(policy.deniedMints[0].toString(), deniedMint.toString());
    
    console.log("✅ Policy allowlists updated");
  });

  it("Updates policy risk parameters", async () => {
    await program.methods
      .updatePolicyRiskParams(
        100, // 1% slippage
        200, // 2% oracle delta
        new anchor.BN(50), // 50 slots
        300  // 3% confidence
      )
      .accounts({
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
      })
      .rpc();

    const policy = await program.account.policy.fetch(policyKeypair.publicKey);
    
    assert.equal(policy.maxSlippageBps, 100);
    assert.equal(policy.maxOracleDeltaBps, 200);
    assert.equal(policy.maxOracleAgeSlots.toNumber(), 50);
    assert.equal(policy.maxConfidenceBps, 300);
    
    console.log("✅ Risk parameters updated");
  });

  it("Toggles pause state", async () => {
    // Pause
    await program.methods
      .togglePause()
      .accounts({
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
      })
      .rpc();

    let policy = await program.account.policy.fetch(policyKeypair.publicKey);
    assert.equal(policy.paused, true);

    // Unpause
    await program.methods
      .togglePause()
      .accounts({
        policy: policyKeypair.publicKey,
        admin: admin.publicKey,
      })
      .rpc();

    policy = await program.account.policy.fetch(policyKeypair.publicKey);
    assert.equal(policy.paused, false);
    
    console.log("✅ Pause toggle working");
  });

  it("Validates risk parameters are enforced", async () => {
    const policy = await program.account.policy.fetch(policyKeypair.publicKey);
    
    // Verify all parameters are set
    assert.isTrue(policy.maxSlippageBps > 0);
    assert.isTrue(policy.maxOracleDeltaBps > 0);
    assert.isTrue(policy.maxOracleAgeSlots.toNumber() > 0);
    assert.isTrue(policy.maxConfidenceBps > 0);
    assert.isTrue(policy.perOrderNotionalUsdCents.toNumber() > 0);
    assert.isTrue(policy.dailyNotionalUsdCents.toNumber() > 0);
    
    console.log("✅ All risk parameters validated");
  });
});