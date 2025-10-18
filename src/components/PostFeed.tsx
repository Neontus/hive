import styles from '../styles/Home.module.css';
import { PostCard, Post } from './PostCard';

const mockPosts: Post[] = [
  {
    id: '1',
    author: 'alice.eth',
    content: 'Just deployed my first smart contract on Base! 🚀',
    timestamp: '2 hours ago',
    likes: 12
  },
  {
    id: '2',
    author: 'bob.eth',
    content: 'Building the future of decentralized social media, one post at a time.',
    timestamp: '4 hours ago',
    likes: 8
  },
  {
    id: '3',
    author: 'charlie.eth',
    content: 'Web3 is amazing! Love how easy RainbowKit makes wallet connections.',
    timestamp: '6 hours ago',
    likes: 15
  },
  {
    id: '4',
    author: 'diana.eth',
    content: 'GM everyone! Another beautiful day in the decentralized world 🌟',
    timestamp: '8 hours ago',
    likes: 23
  }
];

export const PostFeed = () => {
  return (
    <div className={styles.grid}>
      {mockPosts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
    </div>
  );
};