import { Connection } from "@solana/web3.js";
import { MarginfiClient, getConfig } from '@mrgnlabs/marginfi-client-v2';
import { NodeWallet } from "@mrgnlabs/mrgn-common";
import { Keypair } from "@solana/web3.js";
const CLUSTER_CONNECTION ="https://api.devnet.solana.com" ;

const main = async () => {
	const connection = new Connection(CLUSTER_CONNECTION, "confirmed");
    const keypair = Keypair.generate();
    const wallet = NodeWallet.local();

	const config = getConfig("dev");
	const client = await MarginfiClient.fetch(config, wallet, connection); 
	const marginfiAccount = await client.createMarginfiAccount(); 
	const bankLabel = "SOL";
	// console.log(client.banks.keys())
	let bankCount=1;
	for ( const key of client.banks.keys()){
		const bank =client.getBankByPk(key)
		console.log(`bank ${bankCount}'s address`,bank?.address.toBase58());
		bankCount++;
		
	}
};

main();
