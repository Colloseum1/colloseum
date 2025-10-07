import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { Vault } from "../target/types/vault";
import { PublicKey, LAMPORTS_PER_SOL } from "@solana/web3.js";
import {
  TOKEN_PROGRAM_ID,
  createMint,
  createAccount,
  mintTo,
  getAssociatedTokenAddressSync,
  createAssociatedTokenAccountInstruction,
  getAccount,
} from "@solana/spl-token";
import { assert } from "chai";

describe("vault - operations (existing vault)", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Vault as Program<Vault>;
  const admin = provider.wallet.publicKey;

  // Use existing vault and accounts from initial setup
  const VAULT_PDA = new PublicKey("8Q5zu1DJAWQJ69zyWPtk7i4JLTp3PGU4hN7Hnw5aoGPA");
  const POLICY = new PublicKey("7zPkskwDq1uzKQ6S34HZ2k9hbYvjSpQoJgVxWME5zh5o");
  const TEST_TOKEN = new PublicKey("A3W8y2aEeLN589AnK4G8HfMGZeqNMcyCgtGoPyGeFo9Z");

  let userTokenAccount: PublicKey;
  let vaultTokenAccount: PublicKey;

  before(async () => {
    console.log("Admin:", admin.toString());
    console.log("Vault:", VAULT_PDA.toString());
    console.log("Policy:", POLICY.toString());

    const balance = await provider.connection.getBalance(admin);
    console.log("Balance:", balance / LAMPORTS_PER_SOL, "SOL");

    if (balance < 0.1 * LAMPORTS_PER_SOL) {
      throw new Error("Need at least 0.1 SOL");
    }

    // Get or create token accounts
    vaultTokenAccount = getAssociatedTokenAddressSync(TEST_TOKEN, VAULT_PDA, true);

    try {
      await getAccount(provider.connection, vaultTokenAccount);
      console.log("Vault token account exists");
    } catch {
      console.log("Creating vault token account...");
      const createAtaIx = createAssociatedTokenAccountInstruction(
        admin,
        vaultTokenAccount,
        VAULT_PDA,
        TEST_TOKEN
      );
      await provider.sendAndConfirm(new anchor.web3.Transaction().add(createAtaIx));
    }

    try {
      // Try to find existing user account
      const accounts = await provider.connection.getTokenAccountsByOwner(admin, {
        mint: TEST_TOKEN,
      });
      if (accounts.value.length > 0) {
        userTokenAccount = accounts.value[0].pubkey;
        console.log("Using existing user token account");
      } else {
        throw new Error("Create new");
      }
    } catch {
      console.log("Creating user token account...");
      userTokenAccount = await createAccount(
        provider.connection,
        provider.wallet.payer,
        TEST_TOKEN,
        admin
      );

      await mintTo(
        provider.connection,
        provider.wallet.payer,
        TEST_TOKEN,
        userTokenAccount,
        admin,
        10_000_000_000
      );
    }

    console.log("User token account:", userTokenAccount.toString());
    console.log("Vault token account:", vaultTokenAccount.toString());
  });

  it("Deposits tokens", async () => {
    const depositAmount = new anchor.BN(1_000_000); // 1 token

    const userBefore = await getAccount(provider.connection, userTokenAccount);
    console.log("User balance before:", Number(userBefore.amount) / 1_000_000);

    await program.methods
      .deposit(depositAmount)
      .accounts({
        vault: VAULT_PDA,
        user: admin,
        userTokenAccount: userTokenAccount,
        vaultTokenAccount: vaultTokenAccount,
        policy: POLICY,
        admin: admin,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    const vaultAfter = await getAccount(provider.connection, vaultTokenAccount);
    console.log("Vault balance after:", Number(vaultAfter.amount) / 1_000_000);

    assert.isTrue(Number(vaultAfter.amount) >= Number(depositAmount.toString()));
    console.log("✅ Deposit successful");
  });

  it("Withdraws tokens", async () => {
    const vaultBefore = await getAccount(provider.connection, vaultTokenAccount);
    const withdrawAmount = new anchor.BN(500_000); // 0.5 tokens

    if (Number(vaultBefore.amount) < Number(withdrawAmount.toString())) {
      console.log("Insufficient vault balance, skipping");
      this.skip();
    }

    await program.methods
      .withdraw(withdrawAmount)
      .accounts({
        vault: VAULT_PDA,
        user: admin,
        userTokenAccount: userTokenAccount,
        vaultTokenAccount: vaultTokenAccount,
        policy: POLICY,
        admin: admin,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc();

    const vaultAfter = await getAccount(provider.connection, vaultTokenAccount);
    console.log("Vault balance after:", Number(vaultAfter.amount) / 1_000_000);

    assert.isTrue(
      Number(vaultAfter.amount) === Number(vaultBefore.amount) - Number(withdrawAmount.toString())
    );
    console.log("✅ Withdrawal successful");
  });

  it("Checks vault state", async () => {
    const vaultAccount = await program.account.vault.fetch(VAULT_PDA);

    console.log("Vault admin:", vaultAccount.admin.toString());
    console.log("Vault policy:", vaultAccount.policy.toString());
    console.log("Vault base mint:", vaultAccount.baseMint.toString());

    assert.equal(vaultAccount.admin.toString(), admin.toString());
    assert.equal(vaultAccount.policy.toString(), POLICY.toString());
    console.log("✅ Vault state correct");
  });
});
