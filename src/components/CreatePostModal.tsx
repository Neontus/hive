import { useState, useEffect } from 'react';
import { useAccount } from 'wagmi';
import { Trade, CreatePostData } from '../types/trade';
import { TradeItem } from './TradeItem';
import { useRecentTrades } from '../hooks/useRecentTrades';
import { createPost } from '../services/api';
import styles from '../styles/CreatePostModal.module.css';

interface CreatePostModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit?: (data: CreatePostData) => void;
  onPostCreated?: () => void;
}

export const CreatePostModal = ({ isOpen, onClose, onSubmit, onPostCreated }: CreatePostModalProps) => {
  const { isConnected, address } = useAccount();
  const { trades, isLoading, error } = useRecentTrades();
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [reasoning, setReasoning] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [username, setUsername] = useState('trader');

  useEffect(() => {
    if (!isOpen) {
      setSelectedTrade(null);
      setReasoning('');
      setIsSubmitting(false);
      setSubmitError(null);
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (!selectedTrade || !reasoning.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // Try new API integration first
      if (selectedTrade.txHash) {
        await createPost({
          username: username || 'trader',
          tx_hash: selectedTrade.txHash,
          content: reasoning.trim()
        });

        // Trigger parent refetch if callback provided
        onPostCreated?.();
        onClose();
      } else {
        throw new Error('Trade hash not found');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create post';

      if (errorMessage.includes('404')) {
        setSubmitError('Trade not found. Please wait a moment and try again.');
      } else if (errorMessage.includes('403')) {
        setSubmitError('This trade does not belong to your wallet.');
      } else if (errorMessage.includes('409')) {
        setSubmitError('This trade has already been posted.');
      } else {
        setSubmitError(errorMessage);
      }

      console.error('Failed to create post:', error);
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
                        onSelect={() => setSelectedTrade(selectedTrade?.id === trade.id ? null : trade)}
                      />
                    ))}
                  </div>
                )}
              </div>

              {selectedTrade && (
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Trade Details</h3>
                  <div className={styles.selectedTradeDetails}>
                    {(selectedTrade.entryPriceTokenIn || selectedTrade.entryPriceTokenOut) ? (
                      <>
                        <div className={styles.priceDetail}>
                          <div className={styles.priceDetailLabel}>Entry Prices:</div>
                          <div className={styles.priceDetailRow}>
                            <span className={styles.priceDetailItem}>
                              {selectedTrade.tokenIn}: ${selectedTrade.entryPriceTokenIn?.toFixed(2) || 'N/A'}
                            </span>
                            <span className={styles.priceDetailSeparator}>•</span>
                            <span className={styles.priceDetailItem}>
                              {selectedTrade.tokenOut}: ${selectedTrade.entryPriceTokenOut?.toFixed(2) || 'N/A'}
                            </span>
                          </div>
                        </div>

                        <div className={styles.priceDetail}>
                          <div className={styles.priceDetailLabel}>Trade Value:</div>
                          <div className={styles.priceDetailRow}>
                            {selectedTrade.entryPriceTokenIn && (
                              <span className={styles.priceDetailItem}>
                                Spent: ${(parseFloat(selectedTrade.amountIn) * selectedTrade.entryPriceTokenIn).toFixed(2)}
                              </span>
                            )}
                            {selectedTrade.entryPriceTokenOut && (
                              <>
                                {selectedTrade.entryPriceTokenIn && <span className={styles.priceDetailSeparator}>•</span>}
                                <span className={styles.priceDetailItem}>
                                  Received: ${(parseFloat(selectedTrade.amountOut) * selectedTrade.entryPriceTokenOut).toFixed(2)}
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className={styles.noPriceData}>
                        Price data not available for this trade
                      </div>
                    )}
                  </div>
                </div>
              )}

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

              {submitError && (
                <div className={styles.submitError}>
                  {submitError}
                </div>
              )}
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