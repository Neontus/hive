import { Post, CreatePostRequest } from '../types/post';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function createPost(data: CreatePostRequest): Promise<Post> {
  const response = await fetch(`${API_URL}/api/posts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create post');
  }

  return response.json();
}

export async function fetchPosts(
  sort: 'recent' | 'pnl' = 'recent',
  limit: number = 20,
  offset: number = 0
): Promise<{ posts: Post[]; total: number }> {
  const params = new URLSearchParams({
    sort,
    limit: limit.toString(),
    offset: offset.toString()
  });

  const response = await fetch(`${API_URL}/api/posts?${params}`);

  if (!response.ok) {
    throw new Error('Failed to fetch posts');
  }

  return response.json();
}
