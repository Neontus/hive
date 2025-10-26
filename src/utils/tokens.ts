const TOKEN_INFO: Record<string, { symbol: string; decimals: number }> = {
  '0x7b79995e5f793a07bc00c21412e50ecae098e7f9': { symbol: 'WETH', decimals: 18 },
  '0x1c7d4b196cb0c7b01d743fbc6116a902379c7238': { symbol: 'USDC', decimals: 6 },
  '0x68194a729c2450ad26072b3d33adacbcef39d574': { symbol: 'DAI', decimals: 18 },
  '0x94a9d9ac8a22534e3faca9f4e7f2e2cf85d5e4c8': { symbol: 'USDT', decimals: 6 },
  '0x0000000000000000000000000000000000000000': { symbol: 'ETH', decimals: 18 },
};

export function getTokenSymbol(address: string): string {
  const normalized = address.toLowerCase();
  return TOKEN_INFO[normalized]?.symbol || `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function formatPnL(pnl: number): { text: string; color: string; sign: string } {
  const sign = pnl >= 0 ? '+' : '';
  const color = pnl >= 0 ? '#10b981' : '#ef4444';
  const text = `${sign}${pnl.toFixed(2)}%`;
  return { text, color, sign };
}

export function calculateVolumes(
  amountIn: number,
  amountOut: number,
  entryPrice?: number,
  exitPrice?: number
): { entryVolume: string; exitVolume: string } {
  let entryVolume = '-';
  let exitVolume = '-';

  // Calculate entry volume (amount_in * entry_price)
  if (amountIn && entryPrice) {
    const volume = amountIn * entryPrice;
    entryVolume = volume >= 1000000
      ? `$${(volume / 1000000).toFixed(2)}M`
      : volume >= 1000
      ? `$${(volume / 1000).toFixed(2)}K`
      : `$${volume.toFixed(2)}`;
  }

  // Calculate exit volume (amount_out * exit_price)
  if (amountOut && exitPrice) {
    const volume = amountOut * exitPrice;
    exitVolume = volume >= 1000000
      ? `$${(volume / 1000000).toFixed(2)}M`
      : volume >= 1000
      ? `$${(volume / 1000).toFixed(2)}K`
      : `$${volume.toFixed(2)}`;
  }

  return { entryVolume, exitVolume };
}
