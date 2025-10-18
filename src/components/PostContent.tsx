interface PostContentProps {
  content: string;
}

export const PostContent = ({ content }: PostContentProps) => {
  return (
    <p style={{ margin: '0.5rem 0', lineHeight: '1.5' }}>
      {content}
    </p>
  );
};