import { useState } from 'react';
import styles from '../styles/Home.module.css';
import { Post } from '../types/post';
import { formatPnL, calculateVolumes } from '../utils/tokens';
import { TipModal } from './TipModal';
import { useUser } from '../contexts/UserContext';

interface PostCardProps {
  post: Post;
  onTipSuccess?: () => void;
}

export const PostCard = ({ post, onTipSuccess }: PostCardProps) => {
  const [isTipModalOpen, setIsTipModalOpen] = useState(false);
  const { user } = useUser();
  const isOwnPost = user?.username === post.username;

  // PnL calculation with N/A fallback
  const pnlData = post.pnl !== null && post.pnl !== undefined && isFinite(post.pnl)
    ? formatPnL(post.pnl)
    : null;

  const volumes = calculateVolumes(post.amount_in, post.amount_out, post.entry_price, post.exit_price);
  const createdDate = new Date(post.created_at).toLocaleString();

  // Status badge: placeholder for unrealized/realized gains
  const gainStatus = post.exited ? 'Realized Gains' : 'Unrealized Gains';

  const handleTip = () => {
    setIsTipModalOpen(true);
  };

  return (
    <>
      <div className={styles.card}>
        <div className={styles.cardTop}>
          <div className={styles.header}>
            <div className={styles.userInfo}>
              <span className={styles.username}>@{post.username}</span>
              <span className={styles.timestamp}>{createdDate}</span>
            </div>
          </div>
          <div className={styles.cardTopRight}>
            <div className={styles.tipsBadgeContainer}>
              <div className={styles.tipsBadge}>
                {post.tip_count ?? 0} {(post.tip_count ?? 0) === 1 ? 'tip' : 'tips'} • ${post.total_tips?.toFixed(2) || '0.00'}
              </div>
            </div>
            {!isOwnPost && (
              <button
                className={styles.tipButton}
                onClick={handleTip}
                title="Tip this trader"
                style={{ marginTop: '0.5rem', width: '100%' }}
              >
                Tip
              </button>
            )}
          </div>
        </div>

        <div className={styles.content}>
          <p>{post.content}</p>
        </div>

        <div className={styles.footer}>
          <div className={styles.footerLeft}>
            <span className={styles.statusBadge}>
              {gainStatus}
            </span>
            <span className={styles.volumeInfo}>
              Entry: {volumes.entryVolume}
            </span>
            <span className={styles.volumeInfo}>
              Exit: {post.exited ? volumes.exitVolume : 'Not Exited'}
            </span>
            <div
              className={styles.pnlBadge}
              style={{
                backgroundColor: pnlData ? pnlData.color : '#ccc',
                color: '#fff',
                padding: '3px 8px',
                borderRadius: '3px',
                fontSize: '12px',
                fontWeight: 'bold'
              }}
            >
              PnL: {pnlData ? pnlData.text : 'N/A'}
            </div>
          </div>
        </div>

      </div>

      <TipModal
        post={post}
        isOpen={isTipModalOpen}
        onClose={() => setIsTipModalOpen(false)}
        onSuccess={() => {
          setIsTipModalOpen(false);
          onTipSuccess?.();
        }}
      />
    </>
  );
};