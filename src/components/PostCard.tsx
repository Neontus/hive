import styles from '../styles/Home.module.css';
import { PostHeader } from './PostHeader';
import { PostContent } from './PostContent';
import { PostActions } from './PostActions';

export interface Post {
  id: string;
  author: string;
  content: string;
  timestamp: string;
  likes: number;
}

interface PostCardProps {
  post: Post;
}

export const PostCard = ({ post }: PostCardProps) => {
  return (
    <div className={styles.card}>
      <PostHeader author={post.author} timestamp={post.timestamp} />
      <PostContent content={post.content} />
      <PostActions likes={post.likes} />
    </div>
  );
};