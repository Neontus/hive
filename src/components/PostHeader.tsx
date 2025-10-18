interface PostHeaderProps {
  author: string;
  timestamp: string;
}

export const PostHeader = ({ author, timestamp }: PostHeaderProps) => {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
      <strong>{author}</strong>
      <span style={{ fontSize: '0.9rem', color: '#666' }}>{timestamp}</span>
    </div>
  );
};