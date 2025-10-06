use anchor_lang::prelude::*;
use anchor_lang::solana_program::instruction::Instruction;

/// Execute Jupiter swap via CPI
/// Jupiter uses a flat account list - all accounts for the swap route are passed as remaining_accounts
pub fn execute_jupiter_swap<'info>(
    jupiter_program: &AccountInfo<'info>,
    swap_accounts: &[AccountInfo<'info>],
    amount_in: u64,
    quoted_out_amount: u64,
    slippage_bps: u64,
    vault_authority_bump: u8,
    vault_authority_seeds: &[&[u8]],
) -> Result<()> {
    // Jupiter V6 uses a specific instruction format
    // The exact discriminator and data format should match Jupiter's current version
    // This is a simplified version - you may need to adjust based on Jupiter's exact format
    
    let mut instruction_data = Vec::new();
    
    // Add instruction discriminator (this is Jupiter-specific)
    // You'll need to get the exact discriminator from Jupiter's IDL or documentation
    instruction_data.extend_from_slice(&[0xf8, 0xc6, 0x9e, 0x91, 0xe1, 0x75, 0x87, 0xc8]);
    
    // Add swap parameters
    instruction_data.extend_from_slice(&amount_in.to_le_bytes());
    instruction_data.extend_from_slice(&quoted_out_amount.to_le_bytes());
    instruction_data.extend_from_slice(&slippage_bps.to_le_bytes());

    // Build account metas from all swap accounts
    let account_metas: Vec<_> = swap_accounts
        .iter()
        .map(|acc| {
            if acc.is_writable {
                AccountMeta::new(*acc.key, acc.is_signer)
            } else {
                AccountMeta::new_readonly(*acc.key, acc.is_signer)
            }
        })
        .collect();

    let ix = Instruction {
        program_id: *jupiter_program.key,
        accounts: account_metas,
        data: instruction_data,
    };

    // Create signer seeds for vault PDA
    let signer_seeds = &[vault_authority_seeds, &[vault_authority_bump]];
    let signer = &[&signer_seeds[..]];

    // Execute CPI
    anchor_lang::solana_program::program::invoke_signed(
        &ix,
        swap_accounts,
        signer,
    )?;

    Ok(())
}