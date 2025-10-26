import { useState, useEffect, useCallback } from 'react';
import { fetchPosts } from '../services/api';
import { Post } from '../types/post';

export function useFeedPosts(sort: 'recent' | 'pnl' | 'tipped' = 'recent', pageSize: number = 20, viewerWallet?: string) {
  const [posts, setPosts] = useState<Post[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  const loadPosts = useCallback(
    async (reset: boolean = false) => {
      setIsLoading(true);
      setError(null);

      try {
        const currentOffset = reset ? 0 : offset;
        const result = await fetchPosts(sort, pageSize, currentOffset, viewerWallet);

        if (reset) {
          setPosts(result.posts);
          setOffset(result.posts.length);
        } else {
          setPosts((prevPosts) => [...prevPosts, ...result.posts]);
          setOffset(currentOffset + result.posts.length);
        }
        setTotal(result.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch posts');
      } finally {
        setIsLoading(false);
      }
    },
    [sort, pageSize, offset, viewerWallet]
  );

  // Refetch when viewer wallet changes
  useEffect(() => {
    setOffset(0);
    loadPosts(true);
  }, [viewerWallet]);

  // Refetch when sort changes
  useEffect(() => {
    setOffset(0);
    loadPosts(true);
  }, [sort]);

  const refetch = useCallback(() => {
    loadPosts(true);
  }, [loadPosts]);

  const loadMore = useCallback(() => {
    loadPosts(false);
  }, [loadPosts]);

  return {
    posts,
    isLoading,
    error,
    total,
    hasMore: posts.length < total,
    loadMore,
    refetch
  };
}
