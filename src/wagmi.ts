import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import {
  arbitrum,
  base,
  mainnet,
  optimism,
  polygon,
  sepolia,
  baseSepolia
} from 'wagmi/chains';

export const config = getDefaultConfig({
  appName: 'RainbowKit App',
  projectId: '6fa964a1b3c213017a5e8e1fed80ea5f',
  chains: [
    sepolia
    // Note: Using Ethereum Sepolia to match backend HyperSync configuration
    // Backend is configured for https://sepolia.hypersync.xyz (Ethereum Sepolia)
  ],
  ssr: true,
});
