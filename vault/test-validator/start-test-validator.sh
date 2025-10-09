#!/bin/bash

echo "========================================="
echo "Starting Solana Test Validator"
echo "With Jupiter, Orca, Multiple Tokens"
echo "========================================="
echo ""
echo "DEXes:"
echo "  - Jupiter V6: JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
echo "  - Orca Whirlpools: whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
echo "  - Meteora DLMM: LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"
echo ""
echo "Tokens:"
echo "  - Wrapped SOL: So11111111111111111111111111111111111111112"
echo "  - USDC: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
echo "  - Wrapped ETH: 7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"
echo "  - mSOL: mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So"
echo "  - stSOL: 7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj"
echo ""
echo "Oracles (Pyth):"
echo "  - SOL/USD: H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG"
echo "  - ETH/USD: JBu1AL4obBcCMqKBBxhpWCNUt136ijcuMZLFvTP7iWdB"
echo "  - USDC/USD: Gnt27xtC473ZT2Mw5u8wZ68Z3gULkSTb5DuxJy7eJotD"
echo ""
echo "Starting validator... (this may take a minute)"
echo "========================================="
echo ""

solana-test-validator \
    --url mainnet-beta \
    --clone JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4 \
    --clone 4Ec7ZxZS6Sbdg5UGSLHbAnM7GQHp2eFd4KYWRexAipQT \
    --clone D8cy77BBepLMngZx6ZukaTff5hCt1HrWyKk3Hnd9oitf \
    --clone whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc \
    --clone LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo \
    --clone HZcJwcJ2njPDxZtpPoKnF8v2w9QAx2rS7TdJPSRkbEhu \
    --clone 7qbRF6YsyGuLUVs6Y1q64bdVrfe4ZcUUz1JRdoVNUJnm \
    --clone 6MMM16gCNQQBgbmpNXBu4bw57EEStpRzreWQkMNNDpdW \
    --clone 4xDsmeTWPNjgSVSS1VTfzFq3iHZhp77ffPkAmkZkdu71 \
    --clone 6zAcFYmxkaH25qWZW5ek4dk4SyQNpSza3ydSoUxjTudD \
    --clone m3BrPbv2TFmZZTPpyB9NgsCXqGNujpXvzvGqj8ksars \
    --clone Gse4Z6Eb9km2BxcxCfiDtPcwf4LRabps8kLwzSMm4uEo \
    --clone So11111111111111111111111111111111111111112 \
    --clone EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
    --clone 7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs \
    --clone mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So \
    --clone 7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj \
    --clone H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG \
    --clone JBu1AL4obBcCMqKBBxhpWCNUt136ijcuMZLFvTP7iWdB \
    --clone Gnt27xtC473ZT2Mw5u8wZ68Z3gULkSTb5DuxJy7eJotD \
    --reset

# Jupiter V6 requires 3 accounts:
# - JUP6... = Program ID
# - 4Ec7... = ProgramData account (contains actual code)
# - D8cy... = Program Authority PDA

# Notes:
# - Cloning from mainnet-beta gives you real program code and account states
# - Jupiter will automatically find routes through available pools
# - You can add more tokens with: --clone <TOKEN_MINT_ADDRESS>
# - To see logs, remove --quiet flag
# - To keep ledger between runs, remove --reset flag
