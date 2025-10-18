interface PostActionsProps {
  likes: number;
}

export const PostActions = ({ likes }: PostActionsProps) => {
  return (
    <div style={{ marginTop: '1rem', paddingTop: '0.5rem', borderTop: '1px solid #eaeaea' }}>
      <button 
        style={{ 
          background: 'none', 
          border: 'none', 
          color: '#0d76fc', 
          cursor: 'pointer',
          fontSize: '0.9rem'
        }}
        onClick={() => console.log('Like clicked')}
      >
        d {likes}
      </button>
    </div>
  );
};