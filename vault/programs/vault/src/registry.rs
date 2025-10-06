use anchor_lang::prelude::*;

#[account]
pub struct SourceRegistry {
    pub admin: Pubkey,
    
    // Protocol program IDs
    pub jupiter_program: Pubkey,
    pub orca_whirlpool_program: Pubkey,
    pub phoenix_program: Pubkey,
    
    // Enable/disable flags
    pub allow_jupiter: bool,
    pub allow_orca: bool,
    pub allow_phoenix: bool,
}

impl SourceRegistry {
    pub const SPACE: usize = 8 + // discriminator
        32 + // admin
        32 * 3 + // program IDs
        3 + // flags
        50; // padding
}