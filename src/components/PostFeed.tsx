import { useState, useEffect } from 'react';
import styles from '../styles/Home.module.css';
import { PostCard } from './PostCard';
import { useFeedPosts } from '../hooks/useFeedPosts';

export const PostFeed = () => {
  const [sort, setSort] = useState<'recent' | 'pnl' | 'tipped'>('recent');
  const { posts, isLoading, error, total, hasMore, loadMore, refetch } = useFeedPosts(sort, 20);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(refetch, 30000);
    return () => clearInterval(interval);
  }, [refetch]);

  const sortOptions = [
    { value: 'recent' as const, label: 'Recent' },
    { value: 'pnl' as const, label: 'Top PnL' },
    { value: 'tipped' as const, label: 'Most Tipped' }
  ];

  return (
    <div className={styles.feedContainer}>
      <div className={styles.sortToggle}>
        {sortOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => setSort(option.value)}
            className={`${styles.sortOption} ${sort === option.value ? styles.active : ''}`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {isLoading && posts.length === 0 && (
        <div className={styles.loading}>Loading posts...</div>
      )}

      {error && posts.length === 0 && (
        <div className={styles.error}>Error: {error}</div>
      )}

      {posts.length === 0 && !isLoading && !error && (
        <div className={styles.empty}>
          No posts yet. Share your first trade!
        </div>
      )}

      {posts.length > 0 && (
        <>
          <div className={styles.grid}>
            {posts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>

          {hasMore && (
            <button
              onClick={loadMore}
              disabled={isLoading}
              className={styles.loadMoreButton}
            >
              {isLoading ? 'Loading...' : 'Load More'}
            </button>
          )}

          <div className={styles.totalCount}>
            Showing {posts.length} of {total} posts
          </div>
        </>
      )}
    </div>
  );
};