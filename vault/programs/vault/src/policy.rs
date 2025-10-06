use anchor_lang::prelude::*;

#[account]
pub struct Policy {
    pub admin: Pubkey,
    pub paused: bool,
    
    // Allowlists
    pub allowed_programs: Vec<Pubkey>,
    pub allowed_mints: Vec<Pubkey>,
    pub denied_mints: Vec<Pubkey>,
    
    // Risk parameters (in basis points)
    pub max_slippage_bps: u16,        // e.g., 50 = 0.5%
    pub max_oracle_delta_bps: u16,    // e.g., 100 = 1%
    pub max_oracle_age_slots: u64,    // e.g., 150 slots
    pub max_confidence_bps: u32,      // e.g., 200 = 2%
    
    // Notional limits (in USD cents, e.g., 100000 = $1,000)
    pub per_order_notional_usd_cents: u64,
    pub daily_notional_usd_cents: u64,
    pub spent_today_usd_cents: u64,
    pub day_epoch: i64,               // Unix day number
    
    // Compute limits
    pub max_compute_units: u32,
    pub max_priority_fee_lamports: u64,
}

impl Policy {
    // Reserve space for 32 items in each Vec
    pub const MAX_ALLOWED_PROGRAMS: usize = 32;
    pub const MAX_ALLOWED_MINTS: usize = 32;
    pub const MAX_DENIED_MINTS: usize = 32;
    
    pub const SPACE: usize = 8 + // discriminator
        32 + // admin
        1 +  // paused
        (4 + 32 * Self::MAX_ALLOWED_PROGRAMS) + // allowed_programs
        (4 + 32 * Self::MAX_ALLOWED_MINTS) +    // allowed_mints
        (4 + 32 * Self::MAX_DENIED_MINTS) +     // denied_mints
        2 + 2 + 8 + 4 + // risk params
        8 + 8 + 8 + 8 + // notional limits
        4 + 8 + // compute limits
        100; // padding
}