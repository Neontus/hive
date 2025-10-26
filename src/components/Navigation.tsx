import { useState } from 'react';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import Image from 'next/image';
import { CreatePostModal } from './CreatePostModal';
import { CreatePostData } from '../types/trade';
import styles from '../styles/Navigation.module.css';

export const Navigation = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleCreatePost = (data: CreatePostData) => {
    console.log('Creating post with data:', data);
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
            <button 
              className={styles.createPostButton}
              onClick={() => setIsModalOpen(true)}
            >
              Create Post
            </button>
            <ConnectButton />
          </div>
        </div>
      </nav>

      <CreatePostModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreatePost}
      />
    </>
  );
};