# Test Validator Setup

This directory contains scripts to run a local Solana test validator with Jupiter, Orca, and multiple tokens cloned from mainnet.

## Quick Start

```bash
cd test-validator
./start-test-validator.sh
```

The validator will start on `http://localhost:8899`

## What Gets Cloned

### DEXes
- **Jupiter V6**: `JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4`
- **Orca Whirlpools**: `whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc`

### Tokens
- **Wrapped SOL (WSOL)**: `So11111111111111111111111111111111111111112`
- **USDC**: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- **Wrapped ETH**: `7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs`
- **Marinade SOL (mSOL)**: `mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So`
- **Lido stSOL**: `7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj`

### Oracles (Pyth - Mainnet)
- **SOL/USD**: `H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG`
- **ETH/USD**: `JBu1AL4obBcCMqKBBxhpWCNUt136ijcuMZLFvTP7iWdB`
- **USDC/USD**: `Gnt27xtC473ZT2Mw5u8wZ68Z3gULkSTb5DuxJy7eJotD`

## Running Tests

Once the validator is running, in another terminal:

```bash
# Run all tests
anchor test --skip-local-validator

# Run specific test
anchor test --skip-local-validator tests/operations.test.ts
```

## Adding More Tokens

To add more tokens, edit `start-test-validator.sh` and add:

```bash
--clone <TOKEN_MINT_ADDRESS>
```

### Popular Token Mints

```bash
# Solana ecosystem tokens
--clone Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB  # USDT
--clone 7i5KKsX2weiTkry7jA4ZwSuXGhs5eJBEjY8vVxR4pfRx  # GMT
--clone EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v  # USDC
--clone 2FPyTwcZLUg1MDrwsyoP4D6s1tM7hAkHYRjkNb5w6Pxk  # Wrapped BTC
--clone 7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs  # Wrapped ETH

# Staked SOL variants
--clone mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So   # mSOL (Marinade)
--clone 7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj  # stSOL (Lido)
--clone J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn  # jitoSOL (Jito)
```

## Adding More DEXes

```bash
# Raydium
--clone 675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8

# Phoenix
--clone PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY

# Meteora
--clone LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo
```

## Troubleshooting

### Validator fails to start
```bash
# Check if port 8899 is already in use
lsof -i :8899

# Kill existing validator
pkill solana-test-validator
```

### Out of disk space
The validator downloads accounts from mainnet which can be large. The `--reset` flag cleans up on each restart.

### Slow startup
First run downloads all accounts from mainnet. Subsequent runs are faster unless you use `--reset`.

## Notes

- `--reset` flag wipes ledger on each start (clean state)
- `--url mainnet-beta` specifies to clone from mainnet
- Cloning gets you EXACT mainnet program code and account states
- Jupiter automatically finds routes through available liquidity pools
