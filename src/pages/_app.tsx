import '../styles/globals.css';
import '@rainbow-me/rainbowkit/styles.css';
import type { AppProps } from 'next/app';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider } from '@rainbow-me/rainbowkit';

import { config } from '../wagmi';
import { UserProvider } from '../contexts/UserContext';

const client = new QueryClient();

// Suppress fetchPriority and other non-critical warnings from external libraries
if (typeof window !== 'undefined') {
  const originalError = console.error;
  console.error = (...args: any[]) => {
    // Check if this is a React warning
    if (args[0] === 'Warning: React does not recognize the `%s` prop on a DOM element.') {
      const propName = args[1];
      if (propName === 'fetchPriority') {
        return;
      }
    }

    const message = args[0]?.toString?.() ?? '';
    if (message.includes('fetchPriority') || message.includes('Warning: React does not recognize')) {
      return;
    }

    originalError.call(console, ...args);
  };
}

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={client}>
        <RainbowKitProvider>
          <UserProvider>
            <Component {...pageProps} />
          </UserProvider>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}

export default MyApp;
