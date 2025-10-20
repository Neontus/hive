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
  logs: SwapLog[];
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
    const decoded = decodeAbiParameters(
      [
        { name: 'amount0', type: 'int128' },
        { name: 'amount1', type: 'int128' },
        { name: 'sqrtPriceX96', type: 'uint160' },
        { name: 'liquidity', type: 'uint128' },
        { name: 'tick', type: 'int24' },
        { name: 'fee', type: 'uint24' },
      ],
      data as `0x${string}`
    );

    return {
      amount0: decoded[0] as bigint,
      amount1: decoded[1] as bigint,
      sqrtPriceX96: decoded[2] as bigint,
      liquidity: decoded[3] as bigint,
      tick: Number(decoded[4]),
      fee: Number(decoded[5]),
    };
  } catch (error) {
    console.error('Error parsing swap event data:', error);
    return null;
  }
}

const KNOWN_POOLS: Record<string, { currency0: string; currency1: string }> = {
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
    const knownPool = KNOWN_POOLS[poolId.toLowerCase()];
    if (knownPool) {
      return knownPool;
    }

    return {
      currency0: `0x${'0'.repeat(40)}`,
      currency1: `0x${'1'.repeat(40)}`,
    };
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
      const response = await fetch(`${API_BASE_URL}/api/swaps?address=${address}`);

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const result = await response.json() as SwapsResponse;

      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch swap data');
      }

      const transformedTrades: Trade[] = result.logs
        .map((log) => {
          const topic1 = log.topics[1];
          const block = result.blocks.find(b => b.number === log.block_number);
          const tx = result.transactions.find(
            t => t.block_number === log.block_number && t.transaction_index === log.transaction_index
          );

          if (!log.data || !block || !tx || !topic1) return null;

          const eventData = parseSwapEventData(log.data);
          if (!eventData) return null;

          const poolTokens = parsePoolId(topic1);
          if (!poolTokens) return null;

          const token0Info = getTokenInfo(poolTokens.currency0);
          const token1Info = getTokenInfo(poolTokens.currency1);
          const receivingToken0 = eventData.amount0 < 0n;
          const timestampBigInt = block.timestamp ? BigInt(block.timestamp) : 0n;

          return {
            id: `${log.block_number}-${log.log_index}`,
            tokenIn: receivingToken0 ? token1Info.symbol : token0Info.symbol,
            tokenOut: receivingToken0 ? token0Info.symbol : token1Info.symbol,
            amountIn: formatAmount(
              receivingToken0 ? eventData.amount1 : eventData.amount0,
              receivingToken0 ? token1Info.decimals : token0Info.decimals
            ),
            amountOut: formatAmount(
              receivingToken0 ? -eventData.amount0 : -eventData.amount1,
              receivingToken0 ? token0Info.decimals : token1Info.decimals
            ),
            timestamp: timestampBigInt > 0n ? formatTimestamp(timestampBigInt) : 'Unknown',
            txHash: tx.hash || '',
            type: receivingToken0 ? 'buy' : 'sell',
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
