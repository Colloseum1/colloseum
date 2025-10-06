use anchor_lang::prelude::*;

declare_id!("AqcprGtfYzZJHSPcukQrRYonvhqCkernvo7PosdS9bme");

#[program]
pub mod vault {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        msg!("Greetings from: {:?}", ctx.program_id);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize {}
