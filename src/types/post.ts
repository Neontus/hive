export interface Post {
  id: string;
  username: string;
  token_in_address: string;
  token_out_address: string;
  amount_in: number;
  amount_out: number;
  tx_hash: string;
  content: string;
  created_at: string;
  trade_timestamp: string;
  exited: boolean;
  exit_timestamp?: string;
  // Calculated fields from GET endpoint
  entry_price?: number;
  current_price?: number;
  exit_price?: number;
  pnl?: number;
  // Tips
  total_tips?: number;
  tip_count?: number;
  // Internal: trader wallet (not displayed)
  trader_wallet_address?: string;
}

export interface CreatePostRequest {
  username: string;
  tx_hash: string;
  content: string;
}
