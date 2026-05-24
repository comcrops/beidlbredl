const AUTHENTIK_URL = import.meta.env.VITE_AUTHENTIK_URL as string;
const APP_SLUG = import.meta.env.VITE_AUTHENTIK_APP_SLUG as string;
const CLIENT_ID = import.meta.env.VITE_AUTHENTIK_CLIENT_ID as string;

function generateVerifier(): string {
  const arr = new Uint8Array(32);
  // crypto.getRandomValues works on HTTP; crypto.subtle (S256 hashing) requires HTTPS
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(arr);
  } else {
    for (let i = 0; i < arr.length; i++) arr[i] = Math.floor(Math.random() * 256);
  }
  return btoa(String.fromCharCode(...arr)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

async function buildChallenge(verifier: string): Promise<{ challenge: string; method: string }> {
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const data = new TextEncoder().encode(verifier);
    const hash = await crypto.subtle.digest('SHA-256', data);
    const challenge = btoa(String.fromCharCode(...new Uint8Array(hash)))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
    return { challenge, method: 'S256' };
  }
  // HTTP fallback: plain method (verifier == challenge)
  return { challenge: verifier, method: 'plain' };
}

export async function login(returnTo = '/'): Promise<void> {
  const verifier = generateVerifier();
  const { challenge, method } = await buildChallenge(verifier);
  sessionStorage.setItem('pkce_verifier', verifier);
  sessionStorage.setItem('pkce_return_to', returnTo);
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: `${location.origin}/callback`,
    scope: 'openid profile email',
    code_challenge: challenge,
    code_challenge_method: method,
  });
  location.href = `${AUTHENTIK_URL}/application/o/authorize/?${params}`;
}

export async function handleCallback(): Promise<{ token: string; returnTo: string }> {
  const code = new URLSearchParams(location.search).get('code');
  if (!code) throw new Error('No code in callback URL');
  const verifier = sessionStorage.getItem('pkce_verifier');
  if (!verifier) throw new Error('No PKCE verifier in session');
  const returnTo = sessionStorage.getItem('pkce_return_to') ?? '/';

  const resp = await fetch(`${AUTHENTIK_URL}/application/o/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: `${location.origin}/callback`,
      client_id: CLIENT_ID,
      code_verifier: verifier,
    }),
  });
  if (!resp.ok) throw new Error(`Token exchange failed: ${await resp.text()}`);

  const data = await resp.json();
  localStorage.setItem('bb_token', data.access_token);
  localStorage.setItem('bb_token_exp', String(Date.now() + data.expires_in * 1000));
  sessionStorage.removeItem('pkce_verifier');
  sessionStorage.removeItem('pkce_return_to');
  return { token: data.access_token, returnTo };
}

export function getToken(): string | null {
  const token = localStorage.getItem('bb_token');
  const exp = localStorage.getItem('bb_token_exp');
  if (!token || !exp) return null;
  if (Date.now() > Number(exp) - 30_000) {
    localStorage.removeItem('bb_token');
    localStorage.removeItem('bb_token_exp');
    return null;
  }
  return token;
}

export function logout(): void {
  localStorage.removeItem('bb_token');
  localStorage.removeItem('bb_token_exp');
  login();
}
