# Test Validator Usage Guide

## Complete Setup with Jupiter, Tokens, and Pyth Oracles

This guide explains how to run your vault tests with Jupiter swaps and Pyth oracles on a **local forked validator**.

---

## ✅ What's Cloned

When you run `./start-test-validator.sh`, it clones from **mainnet**:

### Programs
- **Jupiter V6**: Full swap aggregator
- **Orca Whirlpools**: DEX for direct swaps

### Tokens
- Wrapped SOL (WSOL)
- USDC
- Wrapped ETH
- Marinade SOL (mSOL)
- Lido stSOL

### Pyth Oracles (Mainnet addresses)
- **SOL/USD**: `H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG`
- **ETH/USD**: `JBu1AL4obBcCMqKBBxhpWCNUt136ijcuMZLFvTP7iWdB`
- **USDC/USD**: `Gnt27xtC473ZT2Mw5u8wZ68Z3gULkSTb5DuxJy7eJotD`

---

## 🚀 Quick Start

### 1. Start the Validator (Terminal 1)

```bash
cd test-validator
./start-test-validator.sh
```

**First run takes 1-2 minutes** as it downloads accounts from mainnet.

You'll see:
```
========================================
Starting Solana Test Validator
With Jupiter, Orca, Multiple Tokens
========================================

Ledger location: test-ledger
Log: test-ledger/validator.log
⠒ Initializing...
```

Wait until you see it listening on port 8899.

### 2. Verify Setup (Terminal 2)

```bash
cd test-validator
./test-setup.sh
```

Expected output:
```
✅ Validator is running
✅ Jupiter V6 program loaded
✅ Orca Whirlpools program loaded
✅ WSOL loaded
✅ USDC loaded
✅ ETH loaded
✅ SOL/USD oracle loaded
✅ ETH/USD oracle loaded
✅ USDC/USD oracle loaded
```

### 3. Update Anchor.toml for Localnet

```toml
[provider]
cluster = "localnet"  # Change from "devnet" to "localnet"
wallet = "/home/r0hith/.config/solana/devnet-test.json"
```

### 4. Run Your Tests

```bash
# Run all tests
anchor test --skip-local-validator

# Run specific test
anchor test --skip-local-validator tests/oracle.test.ts
```

---

## 📝 Important Notes

### Pyth Oracle Addresses

**Your code needs to use MAINNET addresses** when running on local validator:

```typescript
// In tests/oracle.test.ts
const PYTH_SOL_USD_ACCOUNT = PYTH_SOL_USD_ACCOUNT_MAINNET; // Not DEVNET!
```

**Why?** Because we're cloning from mainnet, the oracle accounts have mainnet addresses.

### Devnet vs Localnet

| Testing On | Oracle Addresses | Anchor.toml |
|------------|------------------|-------------|
| **Devnet** (current setup) | Use `PYTH_*_DEVNET` | `cluster = "devnet"` |
| **Local Validator** (new) | Use `PYTH_*_MAINNET` | `cluster = "localnet"` |

---

## 🔧 Troubleshooting

### "Error: clone_accounts failed"

**Problem**: RPC rate limiting or network issues

**Solution 1** - Use minimal version:
```bash
./start-test-validator-minimal.sh
```

**Solution 2** - Remove problematic accounts:
Edit `start-test-validator.sh` and comment out failing `--clone` lines

### "Account not found" in tests

**Problem**: Using wrong oracle addresses

**Solution**: Check you're using MAINNET addresses:
```typescript
const PYTH_SOL_USD_ACCOUNT = PYTH_SOL_USD_ACCOUNT_MAINNET;
```

### Validator won't start (port conflict)

**Problem**: Port 8899 already in use

**Solution**:
```bash
# Kill existing validator
pkill solana-test-validator

# Or check what's using the port
lsof -i :8899
```

### Out of disk space

**Problem**: Ledger gets large over time

**Solution**: The `--reset` flag cleans up on each start. If you remove it, manually clean:
```bash
rm -rf test-ledger
```

---

## 🎯 Benefits of Local Validator

### ✅ Pros
- **Full control**: Unlimited SOL, instant finality
- **Offline testing**: No network dependency
- **Fast iteration**: No waiting for devnet
- **Real programs**: Exact mainnet code
- **Deterministic**: Same state every run with `--reset`

### ⚠️ Cons
- **First startup slow**: Downloads accounts from mainnet
- **Static data**: Oracle prices don't update (they're snapshots)
- **Limited pools**: Only has pools you explicitly clone
- **Disk usage**: Ledger can grow large

---

## 🔄 Switching Between Devnet and Localnet

### To test on Devnet (current setup):

```toml
# Anchor.toml
cluster = "devnet"
```

```bash
anchor test --skip-local-validator
```

### To test on Localnet (new setup):

1. Start validator:
```bash
cd test-validator
./start-test-validator.sh
```

2. Update config:
```toml
# Anchor.toml
cluster = "localnet"
```

3. Update test code:
```typescript
// Use MAINNET oracle addresses
const PYTH_SOL_USD_ACCOUNT = PYTH_SOL_USD_ACCOUNT_MAINNET;
```

4. Run tests:
```bash
anchor test --skip-local-validator
```

---

## 💡 Best Practices

1. **Devnet for oracle testing**: Prices update in real-time
2. **Localnet for Jupiter testing**: Faster iteration, offline
3. **Keep both configs**: Comment/uncomment in Anchor.toml
4. **Use `--reset`**: Clean state every run prevents weird bugs
5. **Add accounts as needed**: Start minimal, clone more if required

---

## 📚 Next Steps

- [ ] Run `./start-test-validator.sh` to test validator startup
- [ ] Run `./test-setup.sh` to verify all accounts loaded
- [ ] Update `Anchor.toml` to use localnet
- [ ] Update oracle test to use MAINNET addresses
- [ ] Run oracle tests: `anchor test --skip-local-validator tests/oracle.test.ts`
- [ ] Create Jupiter swap test

---

## 🆘 Still Having Issues?

Check the validator logs:
```bash
tail -f test-ledger/validator.log
```

Check which accounts failed to clone and remove them from the script.
