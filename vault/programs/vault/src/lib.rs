use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};

mod errors;
mod policy;
mod registry;
mod events;
mod price;
mod cpi;

use errors::*;
use policy::*;
use registry::*;
use events::*;

declare_id!("AqcprGtfYzZJHSPcukQrRYonvhqCkernvo7PosdS9bme"); // Replace after first build

#[program]
pub mod vault {
    use super::*;

    pub fn initialize_vault(
        ctx: Context<InitializeVault>,
        base_mint: Pubkey,
    ) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        vault.admin = ctx.accounts.admin.key();
        vault.policy = ctx.accounts.policy.key();
        vault.registry = ctx.accounts.registry.key();
        vault.base_mint = base_mint;
        vault.bump = ctx.bumps.vault;
        
        msg!("Vault initialized with admin: {}", vault.admin);
        Ok(())
    }

    pub fn initialize_policy(
        ctx: Context<InitializePolicy>,
        params: PolicyParams,
    ) -> Result<()> {
        let policy = &mut ctx.accounts.policy;
        policy.admin = ctx.accounts.admin.key();
        policy.paused = false;
        policy.allowed_programs = Vec::new();
        policy.allowed_mints = Vec::new();
        policy.denied_mints = Vec::new();
        policy.max_slippage_bps = params.max_slippage_bps;
        policy.max_oracle_delta_bps = params.max_oracle_delta_bps;
        policy.max_oracle_age_slots = params.max_oracle_age_slots;
        policy.max_confidence_bps = params.max_confidence_bps;
        policy.per_order_notional_usd_cents = params.per_order_notional_usd_cents;
        policy.daily_notional_usd_cents = params.daily_notional_usd_cents;
        policy.spent_today_usd_cents = 0;
        policy.day_epoch = 0;
        policy.max_compute_units = params.max_compute_units;
        policy.max_priority_fee_lamports = params.max_priority_fee_lamports;
        
        msg!("Policy initialized");
        Ok(())
    }

    pub fn initialize_registry(
        ctx: Context<InitializeRegistry>,
        jupiter_program: Pubkey,
    ) -> Result<()> {
        let registry = &mut ctx.accounts.registry;
        registry.admin = ctx.accounts.admin.key();
        registry.jupiter_program = jupiter_program;
        registry.orca_whirlpool_program = Pubkey::default();
        registry.phoenix_program = Pubkey::default();
        registry.allow_jupiter = true;
        registry.allow_orca = false;
        registry.allow_phoenix = false;
        
        msg!("Registry initialized");
        Ok(())
    }

    pub fn deposit(
        ctx: Context<Deposit>,
        amount: u64,
    ) -> Result<()> {
        // Transfer tokens from user to vault
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.user_token_account.to_account_info(),
                    to: ctx.accounts.vault_token_account.to_account_info(),
                    authority: ctx.accounts.user.to_account_info(),
                },
            ),
            amount,
        )?;

        emit!(DepositEvent {
            vault: ctx.accounts.vault.key(),
            user: ctx.accounts.user.key(),
            amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!("Deposited {} tokens", amount);
        Ok(())
    }
}

// Account structs
#[account]
pub struct Vault {
    pub admin: Pubkey,
    pub policy: Pubkey,
    pub registry: Pubkey,
    pub base_mint: Pubkey,
    pub bump: u8,
}

impl Vault {
    pub const SPACE: usize = 8 + 32 * 4 + 1 + 50;
}

// Context structs
#[derive(Accounts)]
pub struct InitializeVault<'info> {
    #[account(
        init,
        payer = admin,
        space = Vault::SPACE,
        seeds = [b"vault", admin.key().as_ref()],
        bump
    )]
    pub vault: Account<'info, Vault>,
    
    #[account(mut)]
    pub admin: Signer<'info>,
    
    /// CHECK: Just storing the reference
    pub policy: AccountInfo<'info>,
    
    /// CHECK: Just storing the reference
    pub registry: AccountInfo<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct InitializePolicy<'info> {
    #[account(
        init,
        payer = admin,
        space = Policy::SPACE
    )]
    pub policy: Account<'info, Policy>,
    
    #[account(mut)]
    pub admin: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct InitializeRegistry<'info> {
    #[account(
        init,
        payer = admin,
        space = SourceRegistry::SPACE
    )]
    pub registry: Account<'info, SourceRegistry>,
    
    #[account(mut)]
    pub admin: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(
        mut,
        has_one = admin
    )]
    pub vault: Account<'info, Vault>,
    
    #[account(mut)]
    pub user: Signer<'info>,
    
    #[account(mut)]
    pub user_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub vault_token_account: Account<'info, TokenAccount>,
    
    /// CHECK: Vault admin
    pub admin: AccountInfo<'info>,
    
    pub token_program: Program<'info, Token>,
}

// Parameter structs
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct PolicyParams {
    pub max_slippage_bps: u16,
    pub max_oracle_delta_bps: u16,
    pub max_oracle_age_slots: u64,
    pub max_confidence_bps: u32,
    pub per_order_notional_usd_cents: u64,
    pub daily_notional_usd_cents: u64,
    pub max_compute_units: u32,
    pub max_priority_fee_lamports: u64,
}