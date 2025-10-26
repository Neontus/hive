export interface Trade {
  id: string;
  tokenIn: string;
  tokenOut: string;
  amountIn: string;
  amountOut: string;
  timestamp: string;
  txHash: string;
  type: 'buy' | 'sell';
  // Pyth price data
  entryPriceUsd?: number | null;
  entryPriceTokenIn?: number | null;
  entryPriceTokenOut?: number | null;
}

export interface CreatePostData {
  selectedTrade: Trade;
  reasoning: string;
}