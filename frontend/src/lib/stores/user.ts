import { writable } from 'svelte/store';

export interface User {
  username: string;
  avatar_url: string | null;
}

export const userStore = writable<User | null>(null);

export async function fetchUser(token: string): Promise<User | null> {
  const resp = await fetch('/api/users/me', {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error('Failed to fetch user profile');
  return resp.json();
}

export async function uploadAvatar(token: string, file: File): Promise<User> {
  const body = new FormData();
  body.append('avatar', file);
  const resp = await fetch('/api/users/me/avatar', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error ?? 'Upload failed');
  }
  return resp.json();
}

export async function updateUser(token: string, username: string): Promise<User> {
  const resp = await fetch('/api/users/me', {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error ?? 'Failed to update user');
  }
  return resp.json();
}

export async function createUser(token: string, username: string): Promise<User> {
  const resp = await fetch('/api/users/me', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error ?? 'Failed to create user');
  }
  return resp.json();
}
