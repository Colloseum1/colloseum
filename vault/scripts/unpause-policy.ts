import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { Vault } from "../target/types/vault";
import { PublicKey } from "@solana/web3.js";

async function unpausePolicy() {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Vault as Program<Vault>;
  const admin = provider.wallet.publicKey;

  const POLICY = new PublicKey("7zPkskwDq1uzKQ6S34HZ2k9hbYvjSpQoJgVxWME5zh5o");

  console.log("Unpausing policy...");

  // Check current state
  const policyAccount = await program.account.policy.fetch(POLICY);
  console.log("Policy paused status:", policyAccount.paused);

  if (policyAccount.paused) {
    await program.methods
      .togglePause()
      .accounts({
        policy: POLICY,
      })
      .rpc();

    console.log("✅ Policy unpaused!");
  } else {
    console.log("✅ Policy is already unpaused");
  }
}

unpausePolicy().catch(console.error);
