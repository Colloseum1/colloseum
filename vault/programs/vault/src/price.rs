use anchor_lang::prelude::*;
use pyth_solana_receiver_sdk::price_update::{get_feed_id_from_hex, PriceUpdateV2};
use crate::errors::VaultError;

/// Oracle validation parameters
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Debug)]
pub struct OracleLimits {
    pub max_age_slots: u64,        // Maximum staleness in slots
    pub max_confidence_bps: u32,   // Maximum confidence interval in bps
    pub max_delta_bps: u16,        // Maximum deviation from route price in bps
}

/// Read and validate Pyth oracle price
pub fn read_pyth_price(
    price_update_account: &AccountInfo,
    feed_id: &str,
    limits: &OracleLimits,
) -> Result<PythPrice> {
    // Load Pyth price update
    let price_update = PriceUpdateV2::try_deserialize(
        &mut &price_update_account.data.borrow()[..]
    ).map_err(|_| VaultError::StaleOracle)?;

    // Get the price feed
    let feed_id_bytes = get_feed_id_from_hex(feed_id)
        .map_err(|_| VaultError::StaleOracle)?;
    
    let price_feed = price_update
        .get_price_no_older_than(
            &Clock::get()?,
            limits.max_age_slots,
            &feed_id_bytes,
        )
        .map_err(|_| VaultError::StaleOracle)?;

    // Validate confidence interval
    let price_i64 = price_feed.price;
    let confidence = price_feed.conf;
    let exponent = price_feed.exponent;

    // Calculate confidence as percentage of price
    let confidence_bps = if price_i64 != 0 {
        ((confidence as i128 * 10_000) / price_i64.abs() as i128) as u32
    } else {
        u32::MAX
    };

    require!(
        confidence_bps <= limits.max_confidence_bps,
        VaultError::WideConfidence
    );

    msg!(
        "Oracle price: {} * 10^{}, confidence: {} bps",
        price_i64,
        exponent,
        confidence_bps
    );

    Ok(PythPrice {
        price: price_i64,
        exponent,
        confidence,
        confidence_bps,
        timestamp: Clock::get()?.unix_timestamp,
    })
}

/// Validate route price against oracle price
/// route_price_fp6: Route mid price scaled to 6 decimals (e.g., 1.5 USDC = 1_500_000)
/// oracle_price: Raw Pyth price with exponent
pub fn validate_price_deviation(
    oracle_price: i64,
    oracle_exponent: i32,
    route_price_fp6: u128,
    max_delta_bps: u16,
) -> Result<()> {
    // Convert oracle price to 6 decimal fixed point
    // If oracle exponent is -8 and price is 150000000 (1.5 with -8 exponent)
    // We need to convert to 1500000 (1.5 with 6 decimals)
    
    let scale_diff = 6i32 - (-oracle_exponent);
    let oracle_fp6 = if scale_diff >= 0 {
        (oracle_price as i128) * 10_i128.pow(scale_diff as u32)
    } else {
        (oracle_price as i128) / 10_i128.pow((-scale_diff) as u32)
    };

    // Calculate deviation in basis points
    let deviation = ((route_price_fp6 as i128 - oracle_fp6).abs() * 10_000)
        / oracle_fp6.abs().max(1);

    require!(
        deviation <= max_delta_bps as i128,
        VaultError::PriceDeviationTooHigh
    );

    msg!(
        "Price validation - Oracle: {}, Route: {}, Deviation: {} bps",
        oracle_fp6,
        route_price_fp6,
        deviation
    );

    Ok(())
}

/// Calculate minimum output with slippage protection
pub fn calculate_min_output_with_slippage(
    amount_in: u64,
    route_price_fp6: u128,
    max_slippage_bps: u16,
) -> Result<u64> {
    // Calculate expected output at route price
    let expected_out = (amount_in as u128)
        .checked_mul(route_price_fp6)
        .ok_or(VaultError::SlippageExceeded)?
        / 1_000_000u128;

    // Apply slippage tolerance
    let slippage_multiplier = 10_000u128 - max_slippage_bps as u128;
    let min_out = expected_out
        .checked_mul(slippage_multiplier)
        .ok_or(VaultError::SlippageExceeded)?
        / 10_000u128;

    Ok(min_out as u64)
}

/// Pyth price data
#[derive(Debug, Clone)]
pub struct PythPrice {
    pub price: i64,
    pub exponent: i32,
    pub confidence: u64,
    pub confidence_bps: u32,
    pub timestamp: i64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_price_deviation_within_limit() {
        // Oracle: $1.50 with exponent -8 = 150000000
        // Route: $1.51 (1% deviation) = 1510000 fp6
        let result = validate_price_deviation(
            150_000_000,
            -8,
            1_510_000,
            100, // 1% tolerance
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_price_deviation_exceeds_limit() {
        // Oracle: $1.50 with exponent -8 = 150000000
        // Route: $1.60 (6.67% deviation) = 1600000 fp6
        let result = validate_price_deviation(
            150_000_000,
            -8,
            1_600_000,
            100, // 1% tolerance
        );
        assert!(result.is_err());
    }

    #[test]
    fn test_slippage_calculation() {
        // 1000 USDC in, price 1.0, slippage 50 bps (0.5%)
        let min_out = calculate_min_output_with_slippage(
            1_000_000_000, // 1000 USDC (6 decimals)
            1_000_000,     // 1.0 price
            50,            // 0.5% slippage
        ).unwrap();
        
        // Expected: 1000 * 0.995 = 995
        assert_eq!(min_out, 995_000_000);
    }
}