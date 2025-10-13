import { Connection, PublicKey } from "@solana/web3.js";
import { MarginfiClient, getConfig, AccountType, Bank } from '@mrgnlabs/marginfi-client-v2';
import { NodeWallet } from "@mrgnlabs/mrgn-common";
import { Keypair } from "@solana/web3.js";

const RPC_ENDPOINT = "https://api.devnet.solana.com";

async function main() {
    const connection = new Connection(RPC_ENDPOINT, "confirmed");
    // const keypair = Keypair.generate(); 
    // await connection.requestAirdrop(keypair.publicKey, 1e9)
    const wallet =  NodeWallet.local();
    const config = getConfig("production");
    const client = await MarginfiClient.fetch(config, wallet, connection);

    // Fetch all public keys of banks owned by the mfi program
    const bankPubKeys = await client.getAllProgramAccountAddresses(AccountType.Bank);

    const banks = await Promise.all(
        bankPubKeys.map(async (bankPubKey) => {
            try {
                // Fetch account data for each bank
                const accountInfo = await connection.getAccountInfo(bankPubKey);
                if (accountInfo === null) {
                    console.error(`Failed to fetch account info for ${bankPubKey.toString()}`);
                    return null;
                }

                // Parse account data using Bank.fromBuffer
                const bank = Bank.fromBuffer(bankPubKey, accountInfo.data);
                return bank;
            } catch (error) {
                console.error(`Error processing bank ${bankPubKey.toString()}:`, error);
                return null;
            }
        })
    );

    // Filter out any null values (failed fetches/parses)
    const validBanks = banks.filter(bank => bank !== null);
    validBanks.forEach((bank, index) => {
        console.log(`Bank ${index + 1}:`, bank);
    });
}

main().catch((e) => console.log(e));
