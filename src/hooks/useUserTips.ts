import { useState, useEffect } from 'react';
import { fetchUserTips } from '../services/api';

export interface UserTipsData {
  username: string;
  total_received: number;
  tip_count: number;
  recent_tips: Array<{
    tipper_address: string;
    tipper_username: string | null;
    amount: number;
    created_at: string;
    status: string;
  }>;
}

export function useUserTips(username: string | null) {
  const [data, setData] = useState<UserTipsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!username) {
      setData(null);
      return;
    }

    const loadUserTips = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const tipsData = await fetchUserTips(username);
        setData(tipsData);
      } catch (err) {
        console.error('Failed to fetch user tips:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch tips');
      } finally {
        setIsLoading(false);
      }
    };

    loadUserTips();

    // Refresh every 30 seconds
    const interval = setInterval(loadUserTips, 30000);
    return () => clearInterval(interval);
  }, [username]);

  return {
    data,
    isLoading,
    error,
    totalReceived: data?.total_received || 0,
    tipCount: data?.tip_count || 0
  };
}
