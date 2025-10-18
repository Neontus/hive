import { useState, useEffect } from 'react';
import { useAccount } from 'wagmi';
import { Trade, CreatePostData } from '../types/trade';
import { TradeItem } from './TradeItem';
import { useRecentTrades } from '../hooks/useRecentTrades';
import styles from '../styles/CreatePostModal.module.css';

interface CreatePostModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreatePostData) => void;
}

export const CreatePostModal = ({ isOpen, onClose, onSubmit }: CreatePostModalProps) => {
  const { isConnected } = useAccount();
  const { trades, isLoading, error } = useRecentTrades();
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [reasoning, setReasoning] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setSelectedTrade(null);
      setReasoning('');
      setIsSubmitting(false);
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (!selectedTrade || !reasoning.trim()) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        selectedTrade,
        reasoning: reasoning.trim()
      });
      onClose();
    } catch (error) {
      console.error('Failed to submit post:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      className={styles.overlay} 
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2 id="modal-title" className={styles.title}>Create Post</h2>
          <button 
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        <div className={styles.content}>
          {!isConnected ? (
            <div className={styles.notConnected}>
              <p>Please connect your wallet to view recent trades</p>
            </div>
          ) : (
            <>
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Select a Recent Trade</h3>
                {isLoading ? (
                  <div className={styles.loading}>Loading trades...</div>
                ) : error ? (
                  <div className={styles.error}>Failed to load trades</div>
                ) : trades.length === 0 ? (
                  <div className={styles.noTrades}>No recent trades found</div>
                ) : (
                  <div className={styles.tradesList}>
                    {trades.map((trade) => (
                      <TradeItem
                        key={trade.id}
                        trade={trade}
                        isSelected={selectedTrade?.id === trade.id}
                        onSelect={() => setSelectedTrade(trade)}
                      />
                    ))}
                  </div>
                )}
              </div>

              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Add Your Reasoning</h3>
                <textarea
                  className={styles.textarea}
                  placeholder="Share your thoughts on this trade..."
                  value={reasoning}
                  onChange={(e) => setReasoning(e.target.value)}
                  maxLength={200}
                  rows={4}
                />
                <div className={styles.charCount}>
                  {reasoning.length}/200
                </div>
              </div>
            </>
          )}
        </div>

        <div className={styles.footer}>
          <button 
            className={styles.cancelButton}
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button 
            className={styles.submitButton}
            onClick={handleSubmit}
            disabled={!selectedTrade || isSubmitting || !isConnected}
          >
            {isSubmitting ? 'Creating...' : 'Post Trade'}
          </button>
        </div>
      </div>
    </div>
  );
};