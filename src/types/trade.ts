export interface Trade {
  id: string;
  tokenIn: string;
  tokenOut: string;
  amountIn: string;
  amountOut: string;
  timestamp: string;
  txHash: string;
  type: 'buy' | 'sell';
}

export interface CreatePostData {
  selectedTrade: Trade;
  reasoning: string;
}