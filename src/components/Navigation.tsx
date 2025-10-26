import { useState } from 'react';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import Image from 'next/image';
import { CreatePostModal } from './CreatePostModal';
import { CreatePostData } from '../types/trade';
import { useUser } from '../contexts/UserContext';
import { useUserTips } from '../hooks/useUserTips';
import styles from '../styles/Navigation.module.css';

export const Navigation = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { user } = useUser();
  const { totalReceived } = useUserTips(user?.username ?? null);

  const handlePostTrade = (data: CreatePostData) => {
    console.log('Posting trade with data:', data);
    // TODO: Implement actual post creation logic
    return Promise.resolve();
  };

  return (
    <>
      <nav className={styles.navigation}>
        <div className={styles.container}>
          <div className={styles.brand}>
            <Image
              src="/Hive_Logo.png"
              alt="Hive Logo"
              width={120}
              height={120}
              className={styles.logo}
            />
          </div>
          
          <div className={styles.actions}>
            {user && (
              <div className={styles.earnedBadge}>
                ${totalReceived.toFixed(2)} earned
              </div>
            )}
            <button
              className={styles.createPostButton}
              onClick={() => setIsModalOpen(true)}
            >
              Post Trade
            </button>
            <ConnectButton />
          </div>
        </div>
      </nav>

      <CreatePostModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handlePostTrade}
      />
    </>
  );
};