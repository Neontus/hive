import { useState, useEffect } from 'react';
import styles from '../styles/Home.module.css';
import { PostCard } from './PostCard';
import { useFeedPosts } from '../hooks/useFeedPosts';

export const PostFeed = () => {
  const [sort, setSort] = useState<'recent' | 'pnl'>('recent');
  const { posts, isLoading, error, total, hasMore, loadMore, refetch } = useFeedPosts(sort, 20);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(refetch, 30000);
    return () => clearInterval(interval);
  }, [refetch]);

  return (
    <div className={styles.feedContainer}>
      <div className={styles.sortToggle}>
        <button
          onClick={() => setSort('recent')}
          className={sort === 'recent' ? styles.active : ''}
        >
          Recent
        </button>
        <button
          onClick={() => setSort('pnl')}
          className={sort === 'pnl' ? styles.active : ''}
        >
          Top P&L
        </button>
      </div>

      {isLoading && posts.length === 0 && (
        <div className={styles.loading}>Loading posts...</div>
      )}

      {error && (
        <div className={styles.error}>Error: {error}</div>
      )}

      {posts.length === 0 && !isLoading && (
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