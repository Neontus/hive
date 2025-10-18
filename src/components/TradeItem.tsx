import { Trade } from '../types/trade';
import styles from '../styles/CreatePostModal.module.css';

interface TradeItemProps {
  trade: Trade;
  isSelected: boolean;
  onSelect: () => void;
}

export const TradeItem = ({ trade, isSelected, onSelect }: TradeItemProps) => {
  return (
    <div 
      className={`${styles.tradeItem} ${isSelected ? styles.tradeItemSelected : ''}`}
      onClick={onSelect}
    >
      <div className={styles.tradeHeader}>
        <span className={`${styles.tradeType} ${styles[trade.type]}`}>
          {trade.type.toUpperCase()}
        </span>
        <span className={styles.tradeTimestamp}>{trade.timestamp}</span>
      </div>
      
      <div className={styles.tradeDetails}>
        <div className={styles.tradeTokens}>
          {trade.amountIn} {trade.tokenIn} → {trade.amountOut} {trade.tokenOut}
        </div>
      </div>
    </div>
  );
};