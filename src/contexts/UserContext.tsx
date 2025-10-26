import React, { createContext, useContext, useEffect, useState } from 'react';
import { useAccount } from 'wagmi';
import { ensureUser } from '../services/api';

interface User {
  username: string;
  wallet_address: string;
  is_new: boolean;
}

interface UserContextType {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { address, isConnected } = useAccount();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = async () => {
    if (!address || !isConnected) {
      setUser(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const userData = await ensureUser(address);
      setUser(userData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create user';
      setError(errorMessage);
      console.error('Error ensuring user:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isConnected || !address) {
      setUser(null);
      setError(null);
      return;
    }

    refetch();
  }, [address, isConnected]);

  return (
    <UserContext.Provider value={{ user, isLoading, error, refetch }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};
