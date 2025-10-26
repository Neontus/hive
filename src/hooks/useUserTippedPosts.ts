import { useState, useEffect } from 'react';
import { fetchUserTippedPosts } from '../services/api';

export function useUserTippedPosts(walletAddress: string | undefined) {
  const [tippedPostIds, setTippedPostIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!walletAddress) {
      setTippedPostIds(new Set());
      return;
    }

    const loadTippedPosts = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const postIds = await fetchUserTippedPosts(walletAddress);
        setTippedPostIds(new Set(postIds));
      } catch (err) {
        console.error('Failed to fetch tipped posts:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch tipped posts');
      } finally {
        setIsLoading(false);
      }
    };

    loadTippedPosts();
  }, [walletAddress]);

  return {
    tippedPostIds,
    isLoading,
    error,
    hasTipped: (postId: string) => tippedPostIds.has(postId)
  };
}
