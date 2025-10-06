use anchor_lang::prelude::*;

#[error_code]
pub enum VaultError {
    #[msg("Policy is paused")]
    Paused,
    
    #[msg("Target program not in allowlist")]
    ProgramNotAllowed,
    
    #[msg("Token mint not allowed")]
    MintNotAllowed,
    
    #[msg("Token mint is denied")]
    MintDenied,
    
    #[msg("Per-order notional cap exceeded")]
    PerOrderCapExceeded,
    
    #[msg("Daily notional cap exceeded")]
    DailyCapExceeded,
    
    #[msg("Oracle data is stale")]
    StaleOracle,
    
    #[msg("Oracle confidence interval too wide")]
    WideConfidence,
    
    #[msg("Price deviation from oracle too high")]
    PriceDeviationTooHigh,
    
    #[msg("Slippage exceeds maximum allowed")]
    SlippageExceeded,
    
    #[msg("Compute unit limit exceeded")]
    ComputeUnitExceeded,
    
    #[msg("Priority fee exceeds cap")]
    PriorityFeeExceeded,
    
    #[msg("Missing registry entry")]
    MissingRegistryEntry,
    
    #[msg("Feature not yet implemented")]
    NotImplemented,
}