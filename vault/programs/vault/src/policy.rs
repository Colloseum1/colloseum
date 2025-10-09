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

    /// Check if program is allowed
    pub fn is_program_allowed(&self, program_id: &Pubkey) -> bool {
        self.allowed_programs.contains(program_id)
    }

    /// Check if mint is allowed
    pub fn is_mint_allowed(&self, mint: &Pubkey) -> Result<()> {
        // Fail if explicitly denied
        require!(
            !self.denied_mints.contains(mint),
            crate::errors::VaultError::MintDenied
        );
        
        // Pass if allowlist is empty (allow all) or mint is in allowlist
        if self.allowed_mints.is_empty() || self.allowed_mints.contains(mint) {
            Ok(())
        } else {
            Err(crate::errors::VaultError::MintNotAllowed.into())
        }
    }

    /// Check and update daily notional cap
    pub fn check_and_update_daily_cap(
        &mut self,
        amount_usd_cents: u64,
    ) -> Result<()> {
        // Roll over to new day if needed
        let clock = Clock::get()?;
        let current_day = clock.unix_timestamp / 86_400;

        if current_day != self.day_epoch {
            self.day_epoch = current_day;
            self.spent_today_usd_cents = 0;
        }

        // Check per-order cap
        require!(
            amount_usd_cents <= self.per_order_notional_usd_cents,
            crate::errors::VaultError::PerOrderCapExceeded
        );

        // Check daily cap
        let new_spent = self.spent_today_usd_cents
            .checked_add(amount_usd_cents)
            .ok_or(crate::errors::VaultError::DailyCapExceeded)?;

        require!(
            new_spent <= self.daily_notional_usd_cents,
            crate::errors::VaultError::DailyCapExceeded
        );

        // Update spent amount
        self.spent_today_usd_cents = new_spent;
        Ok(())
    }

    /// Validate compute limits
    ///
    /// Note: Not currently enforced in swap_tokens. This is available for future use
    /// if compute budget instructions need to be validated against policy limits.
    /// The policy stores these limits for configuration purposes.
    #[allow(dead_code)]
    pub fn validate_compute_limits(
        &self,
        compute_units: u32,
        priority_fee: u64,
    ) -> Result<()> {
        require!(
            compute_units <= self.max_compute_units,
            crate::errors::VaultError::ComputeUnitExceeded
        );

        require!(
            priority_fee <= self.max_priority_fee_lamports,
            crate::errors::VaultError::PriorityFeeExceeded
        );

        Ok(())
    }
}