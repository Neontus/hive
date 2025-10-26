import { useState, useEffect } from 'react';
import { useAccount, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseUnits } from 'viem';
import styles from '../styles/Home.module.css';
import { Post } from '../types/post';
import { api } from '../services/api';

const PYUSD_SEPOLIA_ADDRESS = '0xCaC524BcA292aaade2DF8A05cC58F0a65B1B3bB9';
const PYUSD_DECIMALS = 6;
const TIP_AMOUNT = '1.0'; // Fixed $1 PYUSD

// Minimal ERC20 ABI for transfer
const erc20Abi = [
  {
    name: 'transfer',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'to', type: 'address' },
      { name: 'value', type: 'uint256' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

interface TipModalProps {
  post: Post;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const TipModal = ({ post, isOpen, onClose, onSuccess }: TipModalProps) => {
  const { address, isConnected } = useAccount();
  const { writeContract, data: hash, isPending, error: writeError } = useWriteContract();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash });
  const [error, setError] = useState<string>('');
  const [tipRecorded, setTipRecorded] = useState(false);

  const handleSendTip = async () => {
    setError('');
    setTipRecorded(false);

    if (!isConnected || !address) {
      setError('Please connect your wallet first');
      return;
    }

    try {
      // Verify we have the trader's wallet address
      if (!post.trader_wallet_address) {
        setError('Trader wallet address not found');
        return;
      }

      // Send PYUSD transfer transaction
      const amountInUnits = parseUnits(TIP_AMOUNT, PYUSD_DECIMALS);

      writeContract({
        address: PYUSD_SEPOLIA_ADDRESS,
        abi: erc20Abi,
        functionName: 'transfer',
        args: [post.trader_wallet_address as `0x${string}`, amountInUnits],
      });
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Automatically record tip when transaction is confirmed
  useEffect(() => {
    if (isSuccess && !tipRecorded) {
      const recordTip = async () => {
        if (!hash) return;

        try {
          await api.createTip(post.id, {
            tipper_address: address!,
            tx_hash: hash,
          });
          setTipRecorded(true);
        } catch (err) {
          setError(`Failed to record tip: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
      };

      recordTip();
    }
  }, [isSuccess, tipRecorded, hash, address, post.id]);

  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h2>Tip @{post.username}</h2>
          <button
            className={styles.closeButton}
            onClick={onClose}
            disabled={isPending || isConfirming}
          >
            ✕
          </button>
        </div>

        <div className={styles.modalContent}>
          <div className={styles.tipInfo}>
            <p><strong>Tip Amount:</strong> {TIP_AMOUNT} PYUSD</p>
            <p><strong>Trader:</strong> @{post.username}</p>
            <p><strong>Trade:</strong> Swap with PnL {post.pnl !== null ? `${post.pnl > 0 ? '+' : ''}${post.pnl.toFixed(2)}%` : 'N/A'}</p>
          </div>

          {error && (
            <div className={styles.errorMessage}>
              {error}
            </div>
          )}

          {!isConnected && (
            <div className={styles.warningMessage}>
              Please connect your wallet to send a tip
            </div>
          )}

          <div className={styles.stepIndicator}>
            {/* Step 1: Send Transaction */}
            <div className={`${styles.step} ${hash ? styles.completed : isPending ? styles.active : ''}`}>
              <div className={styles.stepNumber}>1</div>
              <div className={styles.stepText}>
                <div className={styles.stepTitle}>Send PYUSD</div>
                {hash && <div className={styles.stepDesc}>Tx: {hash.slice(0, 10)}...</div>}
              </div>
            </div>

            {/* Step 2: Confirm Transaction */}
            {hash && (
              <div className={`${styles.step} ${isSuccess ? styles.completed : isConfirming ? styles.active : ''}`}>
                <div className={styles.stepNumber}>2</div>
                <div className={styles.stepText}>
                  <div className={styles.stepTitle}>Confirm on Chain</div>
                  {isSuccess && <div className={styles.stepDesc}>Confirmed!</div>}
                </div>
              </div>
            )}

            {/* Step 3: Record Tip */}
            {isSuccess && (
              <div className={`${styles.step} ${tipRecorded ? styles.completed : ''}`}>
                <div className={styles.stepNumber}>3</div>
                <div className={styles.stepText}>
                  <div className={styles.stepTitle}>Record Tip</div>
                  {tipRecorded && <div className={styles.stepDesc}>Recorded!</div>}
                </div>
              </div>
            )}
          </div>

          <div className={styles.modalActions}>
            {!hash && (
              <button
                className={`${styles.button} ${styles.primaryButton}`}
                onClick={handleSendTip}
                disabled={!isConnected || isPending}
              >
                {isPending ? 'Sending...' : 'Send $1 PYUSD Tip'}
              </button>
            )}

            {hash && !isSuccess && (
              <div className={styles.loadingMessage}>
                {isConfirming ? 'Confirming transaction...' : 'Transaction pending...'}
              </div>
            )}

            {tipRecorded && (
              <div className={styles.successMessage}>
                ✓ Tip sent successfully!
              </div>
            )}

            {tipRecorded && (
              <button
                className={`${styles.button} ${styles.secondaryButton}`}
                onClick={onClose}
              >
                Close
              </button>
            )}

            {!tipRecorded && !hash && (
              <button
                className={`${styles.button} ${styles.secondaryButton}`}
                onClick={onClose}
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
