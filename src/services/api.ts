import { Post, CreatePostRequest } from '../types/post';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  username: string;
  wallet_address: string;
  is_new: boolean;
}

export async function ensureUser(walletAddress: string): Promise<User> {
  const response = await fetch(`${API_URL}/api/users/ensure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet_address: walletAddress })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to ensure user');
  }

  return response.json();
}

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

export async function fetchPostedHashes(): Promise<string[]> {
  const response = await fetch(`${API_URL}/api/posts/posted-hashes`);

  if (!response.ok) {
    throw new Error('Failed to fetch posted hashes');
  }

  const data = await response.json();
  return data.posted_hashes || [];
}

export async function fetchPosts(
  sort: 'recent' | 'pnl' | 'tipped' = 'recent',
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

export interface CreateTipRequest {
  tipper_address: string;
  tx_hash: string;
}

export interface TipResponse {
  id: string;
  post_id: string;
  tipper_address: string;
  amount: number;
  tx_hash: string;
  status: string;
  created_at: string;
}

export async function createTip(postId: string, data: CreateTipRequest): Promise<TipResponse> {
  const response = await fetch(`${API_URL}/api/posts/${postId}/tips`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create tip');
  }

  return response.json();
}

export async function fetchPostTips(postId: string) {
  const response = await fetch(`${API_URL}/api/posts/${postId}/tips`);

  if (!response.ok) {
    throw new Error('Failed to fetch post tips');
  }

  return response.json();
}

export async function fetchUserTips(username: string) {
  const response = await fetch(`${API_URL}/api/users/${username}/tips`);

  if (!response.ok) {
    throw new Error('Failed to fetch user tips');
  }

  return response.json();
}

export const api = {
  ensureUser,
  createPost,
  fetchPostedHashes,
  fetchPosts,
  createTip,
  fetchPostTips,
  fetchUserTips
};
