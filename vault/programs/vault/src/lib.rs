use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer, Mint};

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

declare_id!("6fMDgs8cChvnkADiS3VTJznvwxi2tbgudoAjeWjWXtVV");

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
        let policy = &ctx.accounts.policy;

        // 1. Check if policy is paused
        require!(!policy.paused, VaultError::Paused);

        // 2. Validate mint is allowed
        policy.is_mint_allowed(&ctx.accounts.user_token_account.mint)?;

        // 3. Ensure deposit is to the correct vault token account
        require_keys_eq!(
            ctx.accounts.user_token_account.mint,
            ctx.accounts.vault.base_mint,
            VaultError::MintNotAllowed
        );

        // 4. Transfer tokens from user to vault
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

    pub fn withdraw(
        ctx: Context<Withdraw>,
        amount: u64,
    ) -> Result<()> {
        let vault = &ctx.accounts.vault;
        let policy = &ctx.accounts.policy;

        // 1. Check if policy is paused
        require!(!policy.paused, VaultError::Paused);

        // 2. Verify the user is the admin (or authorized user)
        require_keys_eq!(
            ctx.accounts.user.key(),
            vault.admin,
            VaultError::Unauthorized
        );

        // 3. Check vault has sufficient balance
        let vault_balance = ctx.accounts.vault_token_account.amount;
        require!(
            vault_balance >= amount,
            VaultError::InsufficientBalance
        );

        // 4. Transfer tokens from vault to user using PDA signature
        let admin_key = vault.admin;
        let seeds = &[
            b"vault",
            admin_key.as_ref(),
            &[vault.bump],
        ];
        let signer_seeds = &[&seeds[..]];

        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.vault_token_account.to_account_info(),
                    to: ctx.accounts.user_token_account.to_account_info(),
                    authority: ctx.accounts.vault.to_account_info(),
                },
                signer_seeds,
            ),
            amount,
        )?;

        // 5. Emit withdrawal event
        emit!(WithdrawEvent {
            vault: vault.key(),
            user: ctx.accounts.user.key(),
            amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!("Withdrew {} tokens", amount);
        Ok(())
    }

    pub fn update_policy_allowlists(
        ctx: Context<UpdatePolicy>,
        allowed_programs: Option<Vec<Pubkey>>,
        allowed_mints: Option<Vec<Pubkey>>,
        denied_mints: Option<Vec<Pubkey>>,
    ) -> Result<()> {
        let policy = &mut ctx.accounts.policy;

        if let Some(programs) = allowed_programs {
            require!(
                programs.len() <= Policy::MAX_ALLOWED_PROGRAMS,
                VaultError::ProgramNotAllowed
            );
            policy.allowed_programs = programs;
        }

        if let Some(mints) = allowed_mints {
            require!(
                mints.len() <= Policy::MAX_ALLOWED_MINTS,
                VaultError::MintNotAllowed
            );
            policy.allowed_mints = mints;
        }

        if let Some(denied) = denied_mints {
            require!(
                denied.len() <= Policy::MAX_DENIED_MINTS,
                VaultError::MintDenied
            );
            policy.denied_mints = denied;
        }

        msg!("Policy allowlists updated");
        Ok(())
    }

    pub fn update_policy_risk_params(
        ctx: Context<UpdatePolicy>,
        max_slippage_bps: Option<u16>,
        max_oracle_delta_bps: Option<u16>,
        max_oracle_age_slots: Option<u64>,
        max_confidence_bps: Option<u32>,
    ) -> Result<()> {
        let policy = &mut ctx.accounts.policy;

        if let Some(slippage) = max_slippage_bps {
            policy.max_slippage_bps = slippage;
        }
        if let Some(delta) = max_oracle_delta_bps {
            policy.max_oracle_delta_bps = delta;
        }
        if let Some(age) = max_oracle_age_slots {
            policy.max_oracle_age_slots = age;
        }
        if let Some(conf) = max_confidence_bps {
            policy.max_confidence_bps = conf;
        }

        msg!("Policy risk parameters updated");
        Ok(())
    }

    pub fn toggle_pause(ctx: Context<UpdatePolicy>) -> Result<()> {
        let policy = &mut ctx.accounts.policy;
        policy.paused = !policy.paused;
        
        msg!("Policy paused status: {}", policy.paused);
        Ok(())
    }

    pub fn swap_tokens<'info>(
        ctx: Context<'_, '_, '_, 'info, SwapTokens<'info>>,
        args: SwapArgs,
    ) -> Result<()> {
        let vault = &ctx.accounts.vault;
        let policy = &mut ctx.accounts.policy;
        let registry = &ctx.accounts.registry;

        // 1. Check if paused
        require!(!policy.paused, VaultError::Paused);

        // 2. Check if Jupiter is allowed
        require!(
            registry.allow_jupiter,
            VaultError::ProgramNotAllowed
        );

        // 3. Verify Jupiter program matches registry
        require_keys_eq!(
            ctx.accounts.jupiter_program.key(),
            registry.jupiter_program,
            VaultError::ProgramNotAllowed
        );

        // 4. Verify Jupiter program is in allowlist
        require!(
            policy.is_program_allowed(&registry.jupiter_program),
            VaultError::ProgramNotAllowed
        );

        // Add oracle validation before swap (if feed ID provided)
        if let Some(ref feed_id) = args.price_feed_id {
            if let Some(oracle_account) = ctx.remaining_accounts.first() {
                let oracle_limits = price::OracleLimits {
                    max_age_slots: policy.max_oracle_age_slots,
                    max_confidence_bps: policy.max_confidence_bps,
                    max_delta_bps: policy.max_oracle_delta_bps,
                };

                let oracle_price = price::read_pyth_price(
                    oracle_account,
                    feed_id,
                    &oracle_limits,
                )?;

                price::validate_price_deviation(
                    oracle_price.price,
                    oracle_price.exponent,
                    args.route_price_fp6,
                    policy.max_oracle_delta_bps,
                )?;
            }
        }

        // 5. Verify token mints are allowed
        policy.is_mint_allowed(&ctx.accounts.vault_source_token_account.mint)?;
        policy.is_mint_allowed(&ctx.accounts.vault_dest_token_account.mint)?;

        // 6. Validate slippage against policy
        require!(
            args.slippage_bps <= policy.max_slippage_bps,
            VaultError::SlippageExceeded
        );

        // 7. Check notional caps (simplified - using quoted amount as USD proxy)
        let notional_usd_cents = (args.quoted_out_amount / 10_000) as u64; // Rough conversion
        policy.check_and_update_daily_cap(notional_usd_cents)?;

        // 8. Execute Jupiter swap via CPI
        let admin_key = vault.admin;
        let bump = &[vault.bump];
        let signer_seeds: &[&[&[u8]]] = &[&[
            b"vault",
            admin_key.as_ref(),
            bump,
        ]];

        cpi::jupiter::execute_jupiter_swap(
            ctx.accounts.jupiter_program.to_account_info(),
            ctx.accounts.token_program.to_account_info(),
            ctx.accounts.program_authority.to_account_info(),
            ctx.accounts.vault.to_account_info(), // vault PDA as user_transfer_authority
            ctx.accounts.vault_source_token_account.to_account_info(),
            ctx.accounts.program_source_token_account.to_account_info(),
            ctx.accounts.program_dest_token_account.to_account_info(),
            ctx.accounts.vault_dest_token_account.to_account_info(),
            ctx.accounts.source_mint.to_account_info(),
            ctx.accounts.dest_mint.to_account_info(),
            args.jupiter_route_id,
            args.route_plan,
            args.amount_in,
            args.quoted_out_amount,
            args.slippage_bps,
            args.platform_fee_bps,
            signer_seeds,
            ctx.remaining_accounts,
        )?;

        // 9. Emit swap event
        emit!(SwapEvent {
            vault: vault.key(),
            user: ctx.accounts.admin.key(),
            input_mint: ctx.accounts.vault_source_token_account.mint,
            output_mint: ctx.accounts.vault_dest_token_account.mint,
            amount_in: args.amount_in,
            amount_out: args.quoted_out_amount,
            oracle_price: 0, // Set this if you add oracle validation
            slippage_bps: args.slippage_bps,
            timestamp: Clock::get()?.unix_timestamp,
            slot: Clock::get()?.slot,
        });

        msg!("Swap executed: {} in, {} min out", args.amount_in, args.quoted_out_amount);
        Ok(())
    }

    /// Close vault account and return rent to admin (for testing only)
    pub fn close_vault(ctx: Context<CloseVault>) -> Result<()> {
        msg!("Closing vault and returning rent to admin");
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
        has_one = admin,
        has_one = policy
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub user: Signer<'info>,

    #[account(mut)]
    pub user_token_account: Account<'info, TokenAccount>,

    #[account(
        mut,
        constraint = vault_token_account.owner == vault.key() @ VaultError::Unauthorized
    )]
    pub vault_token_account: Account<'info, TokenAccount>,

    pub policy: Account<'info, Policy>,

    /// CHECK: Vault admin, verified by has_one constraint
    pub admin: AccountInfo<'info>,

    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(
        mut,
        has_one = admin,
        has_one = policy,
        seeds = [b"vault", admin.key().as_ref()],
        bump = vault.bump
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub user: Signer<'info>,

    #[account(mut)]
    pub user_token_account: Account<'info, TokenAccount>,

    #[account(
        mut,
        constraint = vault_token_account.owner == vault.key() @ VaultError::Unauthorized
    )]
    pub vault_token_account: Account<'info, TokenAccount>,

    pub policy: Account<'info, Policy>,

    /// CHECK: Vault admin, verified by has_one constraint
    pub admin: AccountInfo<'info>,

    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct SwapTokens<'info> {
    #[account(
        mut,
        has_one = admin,
        has_one = policy,
        has_one = registry,
        seeds = [b"vault", admin.key().as_ref()],
        bump = vault.bump
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub policy: Account<'info, Policy>,

    pub registry: Account<'info, SourceRegistry>,

    // Jupiter-specific accounts
    /// CHECK: Validated against registry
    pub jupiter_program: AccountInfo<'info>,

    /// CHECK: Jupiter's program authority PDA
    pub program_authority: AccountInfo<'info>,

    // Vault's token accounts
    #[account(mut)]
    pub vault_source_token_account: Account<'info, TokenAccount>,

    #[account(mut)]
    pub vault_dest_token_account: Account<'info, TokenAccount>,

    // Jupiter's temporary token accounts
    /// CHECK: Jupiter's temporary source token account
    #[account(mut)]
    pub program_source_token_account: AccountInfo<'info>,

    /// CHECK: Jupiter's temporary destination token account
    #[account(mut)]
    pub program_dest_token_account: AccountInfo<'info>,

    // Token mints
    pub source_mint: Account<'info, Mint>,
    pub dest_mint: Account<'info, Mint>,

    pub admin: Signer<'info>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UpdatePolicy<'info> {
    #[account(
        mut,
        has_one = admin
    )]
    pub policy: Account<'info, Policy>,

    pub admin: Signer<'info>,
}

#[derive(Accounts)]
pub struct CloseVault<'info> {
    #[account(
        mut,
        close = admin,
        has_one = admin,
        seeds = [b"vault", admin.key().as_ref()],
        bump = vault.bump
    )]
    pub vault: Account<'info, Vault>,

    #[account(mut)]
    pub admin: Signer<'info>,
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

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct SwapArgs {
    pub amount_in: u64,
    pub quoted_out_amount: u64,
    pub slippage_bps: u16,  // Changed from u64 to match Jupiter
    pub route_price_fp6: u128,  // Price from Jupiter quote (6 decimals)
    pub price_feed_id: Option<String>,  // Pyth price feed ID (optional)

    // Jupiter-specific parameters
    pub jupiter_route_id: u8,
    pub route_plan: Vec<u8>,  // Serialized RoutePlanStep[]
    pub platform_fee_bps: u8,
}