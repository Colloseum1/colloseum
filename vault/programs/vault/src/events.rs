use anchor_lang::prelude::*;

#[event]
pub struct DepositEvent {
    pub vault: Pubkey,
    pub user: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[event]
pub struct WithdrawEvent {
    pub vault: Pubkey,
    pub user: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[event]
pub struct SwapEvent {
    pub vault: Pubkey,
    pub user: Pubkey,
    pub input_mint: Pubkey,
    pub output_mint: Pubkey,
    pub amount_in: u64,
    pub amount_out: u64,
    pub oracle_price: i64,
    pub slippage_bps: u16,
    pub timestamp: i64,
    pub slot: u64,
}