import { useState, useEffect } from 'react';
import { useAccount } from 'wagmi';
import { Trade } from '../types/trade';
import { decodeAbiParameters } from 'viem';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const TOKEN_INFO: Record<string, { symbol: string; decimals: number }> = {
  '0x7b79995e5f793a07bc00c21412e50ecae098e7f9': { symbol: 'WETH', decimals: 18 },
  '0x1c7d4b196cb0c7b01d743fbc6116a902379c7238': { symbol: 'USDC', decimals: 6 },
  '0x68194a729c2450ad26072b3d33adacbcef39d574': { symbol: 'DAI', decimals: 18 },
  '0x94a9d9ac8a22534e3faca9f4e7f2e2cf85d5e4c8': { symbol: 'USDT', decimals: 6 },
  '0x0000000000000000000000000000000000000000': { symbol: 'ETH', decimals: 18 },
};

function getTokenInfo(address: string): { symbol: string; decimals: number } {
  const normalized = address.toLowerCase();
  return TOKEN_INFO[normalized] || {
    symbol: `${address.slice(0, 6)}...${address.slice(-4)}`,
    decimals: 18
  };
}
interface SwapLog {
  block_number: number;
  log_index: number;
  transaction_index: number;
  data: string;
  address: string;
  topics: (string | null)[];
  // Pyth price enrichment fields from backend
  token0_address?: string;
  token1_address?: string;
  token0_symbol?: string;
  token1_symbol?: string;
  entry_price_token0_usd?: number | null;
  entry_price_token1_usd?: number | null;
  block_timestamp?: number;
}

interface SwapBlock {
  number: number;
  timestamp?: string;
  hash?: string;
}

interface SwapTransaction {
  block_number: number;
  transaction_index: number;
  hash?: string;
  from_?: string;
  to?: string;
  value?: string;
}

interface SwapsResponse {
  success: boolean;
  swaps: SwapLog[];  // Changed from 'logs' to match backend response
  blocks: SwapBlock[];
  transactions: SwapTransaction[];
  error?: string;
}
interface SwapEventData {
  amount0: bigint;
  amount1: bigint;
  sqrtPriceX96: bigint;
  liquidity: bigint;
  tick: number;
  fee: number;
}

function parseSwapEventData(data: string): SwapEventData | null {
  try {
    // Uniswap V3 Swap event: (int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)
    const decoded = decodeAbiParameters(
      [
        { name: 'amount0', type: 'int256' },
        { name: 'amount1', type: 'int256' },
        { name: 'sqrtPriceX96', type: 'uint160' },
        { name: 'liquidity', type: 'uint128' },
        { name: 'tick', type: 'int24' },
      ],
      data as `0x${string}`
    );

    return {
      amount0: decoded[0] as bigint,
      amount1: decoded[1] as bigint,
      sqrtPriceX96: decoded[2] as bigint,
      liquidity: decoded[3] as bigint,
      tick: Number(decoded[4]),
      fee: 0, // Fee is in topics, not in data
    };
  } catch (error) {
    console.error('Error parsing swap event data:', error);
    return null;
  }
}

const KNOWN_POOLS: Record<string, { currency0: string; currency1: string }> = {
  // Pool: 0x3289680dd4d6c10bb19b899729cda5eef58aeff1 (WETH/USDC)
  '0x3289680dd4d6c10bb19b899729cda5eef58aeff1': {
    currency0: '0x7b79995e5f793a07bc00c21412e50ecae098e7f9', // WETH
    currency1: '0x1c7d4b196cb0c7b01d743fbc6116a902379c7238', // USDC
  },
  '0x357d9a61623f0c9209fa971ad0a6f7fbc4330ed1f0185eb3116bbbe0346ee0ca': {
    currency0: '0x7b79995e5f793a07bc00c21412e50ecae098e7f9',
    currency1: '0x1c7d4b196cb0c7b01d743fbc6116a902379c7238',
  },
  '0xf572afd57744cf4d48a53251eca56fa30a1914091f5095af97494e9b3f66ef48': {
    currency0: '0x0000000000000000000000000000000000000000',
    currency1: '0x1c7d4b196cb0c7b01d743fbc6116a902379c7238',
  },
};

function parsePoolId(poolId: string): { currency0: string; currency1: string } | null {
  try {
    const poolIdLower = poolId.toLowerCase();
    const knownPool = KNOWN_POOLS[poolIdLower];
    if (knownPool) {
      return knownPool;
    }

    // If not in known pools, return null so we skip this trade
    // This prevents showing trades with unknown token pairs
    return null;
  } catch (error) {
    console.error('Error parsing pool ID:', error);
    return null;
  }
}
function formatTimestamp(timestamp: bigint): string {
  const now = Date.now();
  const eventTime = Number(timestamp) * 1000;
  const diffMs = now - eventTime;
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

function formatAmount(amount: bigint, decimals: number = 18): string {
  const absAmount = amount < 0n ? -amount : amount;

  if (absAmount === 0n) {
    return '0';
  }

  const divisor = 10n ** BigInt(decimals);
  const whole = absAmount / divisor;
  const fraction = absAmount % divisor;
  const fractionStr = fraction.toString().padStart(decimals, '0');

  let significantDecimals = 0;
  let foundNonZero = false;
  let result = '';

  for (let i = 0; i < fractionStr.length && significantDecimals < 4; i++) {
    if (fractionStr[i] !== '0') {
      foundNonZero = true;
    }
    if (foundNonZero) {
      result += fractionStr[i];
      significantDecimals++;
    } else {
      result += fractionStr[i];
    }
  }

  result = result.replace(/0+$/, '');

  if (result === '') {
    return whole.toString();
  }

  return `${whole}.${result}`;
}


export const useRecentTrades = () => {
  const { address, isConnected } = useAccount();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecentSwaps = async () => {
    if (!address) {
      setTrades([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/swaps?address=${address}&debug=true`);

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const result = await response.json() as SwapsResponse;
      console.log('Swaps response:', result);

      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch swap data');
      }

      console.log('Raw swaps:', result.swaps);
      console.log('Blocks:', result.blocks);
      console.log('Transactions:', result.transactions);

      const transformedTrades: Trade[] = result.swaps
        .map((log) => {
          // Use backend-enriched data
          const block = result.blocks.find(b => b.number === log.block_number);
          const tx = result.transactions.find(
            t => t.block_number === log.block_number && t.transaction_index === log.transaction_index
          );

          // Check that we have required enriched data from backend
          if (!block || !tx || !log.token0_symbol || !log.token1_symbol) {
            return null;
          }

          // Parse the swap event data to determine direction (which token was received)
          const eventData = parseSwapEventData(log.data);
          if (!eventData) return null;

          const receivingToken0 = eventData.amount0 < 0n;
          // block_timestamp is already a Unix timestamp from backend (number, not string)
          const timestampBigInt = BigInt(log.block_timestamp || 0);

          // Extract Pyth price data (already enriched by backend)
          const entryPriceToken0 = log.entry_price_token0_usd;
          const entryPriceToken1 = log.entry_price_token1_usd;

          // Determine token info from backend data
          const token0Decimals = log.token0_symbol === 'USDC' ? 6 : 18;
          const token1Decimals = log.token1_symbol === 'USDC' ? 6 : 18;

          return {
            id: `${log.block_number}-${log.log_index}`,
            tokenIn: receivingToken0 ? log.token1_symbol : log.token0_symbol,
            tokenOut: receivingToken0 ? log.token0_symbol : log.token1_symbol,
            amountIn: formatAmount(
              receivingToken0 ? eventData.amount1 : eventData.amount0,
              receivingToken0 ? token1Decimals : token0Decimals
            ),
            amountOut: formatAmount(
              receivingToken0 ? -eventData.amount0 : -eventData.amount1,
              receivingToken0 ? token0Decimals : token1Decimals
            ),
            timestamp: timestampBigInt > 0n ? formatTimestamp(timestampBigInt) : 'Unknown',
            txHash: tx.hash || '',
            type: receivingToken0 ? 'buy' : 'sell',
            // Add Pyth entry prices
            entryPriceTokenIn: receivingToken0 ? entryPriceToken1 : entryPriceToken0,
            entryPriceTokenOut: receivingToken0 ? entryPriceToken0 : entryPriceToken1,
          } as Trade;
        })
        .filter((trade): trade is Trade => trade !== null)
        .reverse();

      setTrades(transformedTrades);
      setError(null);
    } catch (err) {
      console.error('Error fetching trades:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch trades');
      setTrades([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isConnected || !address) {
      setTrades([]);
      return;
    }

    fetchRecentSwaps();
  }, [address, isConnected]);

  return {
    trades,
    isLoading,
    error,
    refetch: fetchRecentSwaps,
  };
};
