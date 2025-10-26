import styles from '../styles/Home.module.css';
import { Post } from '../types/post';
import { getTokenSymbol, formatPnL } from '../utils/tokens';

interface PostCardProps {
  post: Post;
}

export const PostCard = ({ post }: PostCardProps) => {
  const tokenInSymbol = getTokenSymbol(post.token_in_address);
  const tokenOutSymbol = getTokenSymbol(post.token_out_address);
  const pnlData = post.pnl !== null && post.pnl !== undefined ? formatPnL(post.pnl) : null;
  const etherscanUrl = `https://sepolia.etherscan.io/tx/${post.tx_hash}`;
  const createdDate = new Date(post.created_at).toLocaleString();

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.userInfo}>
          <span className={styles.username}>@{post.username}</span>
          <span className={styles.timestamp}>{createdDate}</span>
        </div>
        {pnlData && (
          <div
            className={styles.pnlBadge}
            style={{
              backgroundColor: pnlData.color,
              color: '#fff',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 'bold'
            }}
          >
            {pnlData.text}
          </div>
        )}
      </div>

      <div className={styles.tradeInfo}>
        <div className={styles.tradeAmounts}>
          <span className={styles.amount}>{post.amount_in.toFixed(2)} {tokenInSymbol}</span>
          <span className={styles.arrow}>→</span>
          <span className={styles.amount}>{post.amount_out.toFixed(4)} {tokenOutSymbol}</span>
        </div>
        <div className={styles.prices}>
          {post.entry_price && (
            <div className={styles.priceRow}>
              <span className={styles.label}>Entry:</span>
              <span className={styles.value}>${post.entry_price.toFixed(2)}</span>
            </div>
          )}
          {(post.current_price !== null && post.current_price !== undefined) && (
            <div className={styles.priceRow}>
              <span className={styles.label}>Current:</span>
              <span className={styles.value}>${post.current_price.toFixed(2)}</span>
            </div>
          )}
          {(post.exit_price !== null && post.exit_price !== undefined) && (
            <div className={styles.priceRow}>
              <span className={styles.label}>Exit:</span>
              <span className={styles.value}>${post.exit_price.toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      <div className={styles.content}>
        <p>{post.content}</p>
      </div>

      <div className={styles.footer}>
        <div className={styles.footerLeft}>
          <a href={etherscanUrl} target="_blank" rel="noopener noreferrer" className={styles.txLink}>
            {post.tx_hash.slice(0, 6)}...{post.tx_hash.slice(-4)}
          </a>
          {post.exited && <span className={styles.exitedBadge}>EXITED</span>}
        </div>
      </div>
    </div>
  );
};