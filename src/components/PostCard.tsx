import styles from '../styles/Home.module.css';
import { Post } from '../types/post';
import { formatPnL, calculateVolumes } from '../utils/tokens';

interface PostCardProps {
  post: Post;
}

export const PostCard = ({ post }: PostCardProps) => {
  // PnL calculation with N/A fallback
  const pnlData = post.pnl !== null && post.pnl !== undefined && isFinite(post.pnl)
    ? formatPnL(post.pnl)
    : null;

  const volumes = calculateVolumes(post.amount_in, post.amount_out, post.entry_price, post.exit_price);
  const createdDate = new Date(post.created_at).toLocaleString();

  // Status badge: placeholder for unrealized/realized gains
  const gainStatus = post.exited ? 'Realized Gains' : 'Unrealized Gains';

  const handleTip = () => {
    // TODO: Implement tipping functionality
    console.log('Tip button clicked for post:', post.id);
  };

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.userInfo}>
          <span className={styles.username}>@{post.username}</span>
          <span className={styles.timestamp}>{createdDate}</span>
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
              padding: '2px 6px',
              borderRadius: '3px',
              fontSize: '11px',
              fontWeight: 'bold'
            }}
          >
            PnL: {pnlData ? pnlData.text : 'N/A'}
          </div>
        </div>
        <button
          className={styles.tipButton}
          onClick={handleTip}
          title="Tip this trader"
        >
          Tip
        </button>
      </div>
    </div>
  );
};