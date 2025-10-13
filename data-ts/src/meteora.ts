// const url = 'https://dammv2-api.devnet.meteora.ag/pools?token_a_symbol=USDC&token_b_symbol=SOL';
// const url= 'https://dammv2-api.devnet.meteora.ag/pools';
// const options = {method: 'GET', body: undefined};

// try {
//   const response = await fetch(url, options);
//   const data = await response.json();
//   console.log(data);
// } catch (error) {
//   console.error(error);
// }


const getMeteoraPools = async (tokenASymbol?: string, tokenBSymbol?: string, token_a_mint?: string, token_b_mint?: string) => {
    let queryParams = [];
    if (tokenASymbol) queryParams.push(`token_a_symbol=${tokenASymbol}`);
    if (tokenBSymbol) queryParams.push(`token_b_symbol=${tokenBSymbol}`);
    if (token_a_mint) queryParams.push(`token_a_mint=${token_a_mint}`);
    if (token_b_mint) queryParams.push(`token_b_mint=${token_b_mint}`);
    
    const queryString = queryParams.length ? `?${queryParams.join('&')}` : '';
    const url = `https://dammv2-api.devnet.meteora.ag/pools${queryString}`;
    
    try {
        const options = { method: 'GET', body: undefined };
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching Meteora pools:', error);
        throw error;
    }
}

// getMeteoraPools("USDC", "SOL")
//     .then(pools => console.log("Fetched pools:", pools))
//     .catch(error => console.error(error));