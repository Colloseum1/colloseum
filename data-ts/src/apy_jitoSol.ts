export default async function handler() {
  const apiUrl = 'https://kobe.mainnet.jito.network/api/v1/stake_pool_stats'

  // Set up start and end dates
  const start = new Date('2022-10-31T00:00:00Z') 
  const end = new Date()

  const statsRequest = {
    bucket_type: 'Daily',
    range_filter: {
      start: start.toISOString(),
      end: end.toISOString(),
    },
    sort_by: {
      field: 'BlockTime',
      order: 'Asc',
    },
  }

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(statsRequest),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()

    if (data) {
      const {
        aggregated_mev_rewards: aggregatedMevRewards,
        apy,
        mev_rewards: mevRewards,
        num_validators: numValidators,
        supply,
        tvl,
      } = data

      const camelCaseData = {
        getStakePoolStats: {
          aggregatedMevRewards,
          apy,
          mevRewards,
          numValidators,
          supply,
          tvl,
        },
      }

    //   console.log('Fetched and transformed data:', camelCaseData)
    //   console.log("latest apy: ", camelCaseData.getStakePoolStats.apy[camelCaseData.getStakePoolStats.apy.length - 1])
      const latestApy = camelCaseData.getStakePoolStats.apy[camelCaseData.getStakePoolStats.apy.length - 1].data * 100
      console.log("latest apy %: ", latestApy)
      return  latestApy
    } else {
        throw new Error('No data found in response')
    }
  } catch (error) {
    console.error('Error fetching data:', error)
    
  }
}

handler()
