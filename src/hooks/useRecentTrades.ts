import { useState, useEffect } from 'react';
import { useAccount } from 'wagmi';
import { Trade } from '../types/trade';

const mockTrades: Trade[] = [
  {
    id: '1',
    tokenIn: 'ETH',
    tokenOut: 'USDC',
    amountIn: '1.5',
    amountOut: '3,750',
    timestamp: '2 hours ago',
    txHash: '0x1234567890abcdef',
    type: 'sell'
  },
  {
    id: '2',
    tokenIn: 'USDC',
    tokenOut: 'DEGEN',
    amountIn: '500',
    amountOut: '45,000',
    timestamp: '6 hours ago',
    txHash: '0xabcdef1234567890',
    type: 'buy'
  },
  {
    id: '3',
    tokenIn: 'WETH',
    tokenOut: 'BASE',
    amountIn: '0.8',
    amountOut: '120',
    timestamp: '1 day ago',
    txHash: '0x567890abcdef1234',
    type: 'buy'
  },
  {
    id: '4',
    tokenIn: 'USDC',
    tokenOut: 'ETH',
    amountIn: '2,500',
    amountOut: '1.0',
    timestamp: '2 days ago',
    txHash: '0xdef1234567890abc',
    type: 'buy'
  }
];

export const useRecentTrades = () => {
  const { address, isConnected } = useAccount();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isConnected || !address) {
      setTrades([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    // Simulate API call delay
    const timer = setTimeout(() => {
      setTrades(mockTrades);
      setIsLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, [address, isConnected]);

  return {
    trades,
    isLoading,
    error,
    refetch: () => {
      if (isConnected && address) {
        setIsLoading(true);
        setTimeout(() => {
          setTrades(mockTrades);
          setIsLoading(false);
        }, 500);
      }
    }
  };
};