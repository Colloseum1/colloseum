use anchor_lang::prelude::*;
use anchor_lang::solana_program::instruction::Instruction;

/// Execute Jupiter swap via CPI by forwarding the exact instruction from Jupiter API
///
/// This function receives the complete instruction data and accounts from Jupiter API
/// and forwards them directly to Jupiter program via CPI. The vault PDA signs the transaction.
pub fn execute_jupiter_swap<'info>(
    jupiter_program: AccountInfo<'info>,
    instruction_data: Vec<u8>,  // Complete instruction data from Jupiter API
    jupiter_accounts: &[AccountInfo<'info>],  // All accounts from Jupiter API in exact order
    signer_seeds: &[&[&[u8]]],  // Vault PDA seeds for signing
) -> Result<()> {
    // Build account metas from provided accounts
    // We need to preserve the exact order and properties from Jupiter API
    let mut account_metas = Vec::new();

    for (idx, account) in jupiter_accounts.iter().enumerate() {
        // Account at index 2 should be the user_transfer_authority (vault PDA) which needs to be a signer
        let is_signer = idx == 2; // user_transfer_authority at index 2

        account_metas.push(AccountMeta {
            pubkey: *account.key,
            is_signer,
            is_writable: account.is_writable,
        });
    }

    // Build the instruction
    let ix = Instruction {
        program_id: *jupiter_program.key,
        accounts: account_metas,
        data: instruction_data,
    };

    // Execute CPI with vault PDA as signer
    anchor_lang::solana_program::program::invoke_signed(
        &ix,
        jupiter_accounts,
        signer_seeds,
    )?;

    msg!("Jupiter swap executed successfully");
    Ok(())
}

#[error_code]
pub enum ErrorCode {
    #[msg("Invalid route plan data")]
    InvalidRoutePlan,
}
