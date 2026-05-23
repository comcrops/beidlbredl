# Authentik SSO Authentication Design

## Goal

Protect all beidlboard routes (kiosk display and mobile controller) with Authentik SSO. Users authenticate via OIDC PKCE, pick a username on first login, and their identity is attached to socket sessions and app data. The kiosk Pi connects via a pre-shared secret instead of OIDC.

## Architecture

**Frontend OIDC PKCE flow** using `@badgateway/oauth2-client`. The frontend handles the full OAuth2 PKCE dance, stores the JWT in localStorage, and passes it to the backend on every socket connection and HTTP request. The backend validates JWTs against Authentik's JWKS endpoint.

```
User opens app
  → no valid token → redirect to Authentik login
  → Authentik redirects back to /callback with code
  → frontend exchanges code for tokens (PKCE)
  → GET /api/users/me
    → 404 (new user) → /setup (pick username) → POST /api/users/me → enter app
    → 200 → enter app
  → connect sockets with { auth: { token } }
```

Kiosk Pi bypasses OIDC entirely: `KIOSK_SECRET` env var is sent as socket auth, backend recognises it as the kiosk service connection and skips JWT validation.

## Backend

### New files

**`backend/auth.py`**
- `get_jwks()` — fetches `{AUTHENTIK_URL}/application/o/{AUTHENTIK_APP_SLUG}/jwks/`, caches in memory, re-fetches on key rotation error
- `decode_token(token) -> dict` — validates JWT signature, expiry, audience; raises on failure
- `require_auth(f)` — Flask decorator: extracts `Authorization: Bearer <token>`, calls `decode_token`, injects `g.user_sub` into request context

**`backend/users.py`**
- `get_user(sub: str) -> dict | None` — PocketBase lookup by `authentik_sub`
- `create_user(sub: str, username: str) -> dict` — creates PocketBase record
- PocketBase `users` collection: fields `authentik_sub` (text, required, unique), `username` (text, required)

**`backend/sockets/middleware.py`**
- `authenticate_socket(auth: dict) -> dict | None` — called on every socket `connect` event in both namespaces
  - If `auth.get('kiosk_secret') == KIOSK_SECRET` → return `{ 'is_kiosk': True }`
  - Else: `decode_token(auth.get('token'))` → look up user in PocketBase → return `{ 'is_kiosk': False, 'user_sub': ..., 'username': ... }`
  - Returns `None` on any failure → caller disconnects the socket

### Modified files

**`backend/sockets/general.py`** and **`backend/sockets/apps.py`**
- `on_connect(auth)` calls `authenticate_socket(auth)`, stores result in `flask.g` or session; disconnects if `None`

**`backend/app.py`**
- Register `/api/users` blueprint

**`backend/apps/hello_world/routes.py`**
- `handle_update_message` reads `username` from socket session, saves it alongside `text` in PocketBase (add `sender` field to collection)

### New endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/users/me` | JWT | Return `{ username }` or 404 |
| POST | `/api/users/me` | JWT | Create user with `{ username }` body |

### New `.env` vars

```
AUTHENTIK_URL=https://auth.example.com
AUTHENTIK_APP_SLUG=beidlboard
AUTHENTIK_CLIENT_ID=<client-id>
KIOSK_SECRET=<long-random-string>
```

## Frontend

### New files

**`frontend/src/lib/auth.ts`**
- OIDC client configured with `@badgateway/oauth2-client`
- `login()` — redirects to Authentik
- `handleCallback()` — exchanges code for tokens, stores in localStorage
- `getToken()` — returns current access token, handles refresh
- `logout()` — clears localStorage, redirects to Authentik logout

**`frontend/src/lib/stores/user.ts`**
- `userStore` — writable `{ username: string } | null`
- Populated after successful `GET /api/users/me`

**`frontend/src/routes/callback/+page.svelte`**
- Calls `handleCallback()`, then `GET /api/users/me`
- On 404 → navigate to `/setup`
- On 200 → set userStore, navigate to `/` or `/mobile` based on referrer

**`frontend/src/routes/setup/+page.svelte`**
- Username input form (3–20 chars, alphanumeric + underscores)
- Calls `POST /api/users/me`, on success sets userStore, navigates to destination

### Modified files

**`frontend/src/lib/socket.ts`**
- `connectSockets()` receives token, passes `{ auth: { token } }` to both `io()` calls
- Kiosk passes `{ auth: { kiosk_secret: import.meta.env.VITE_KIOSK_SECRET } }`

**`frontend/src/routes/+page.svelte`** (kiosk)
- On mount: check `VITE_KIOSK_SECRET` env var; if set, connect as kiosk (no OIDC)
- If not set: call `getToken()`, redirect to login if missing

**`frontend/src/routes/mobile/+page.svelte`**
- On mount: call `getToken()`, redirect to login if missing; then `connectSockets(token)`

### New `.env` / build vars

```
VITE_AUTHENTIK_URL=https://auth.example.com
VITE_AUTHENTIK_CLIENT_ID=<client-id>
VITE_KIOSK_SECRET=<same-long-random-string>   # only set on kiosk Pi
```

## Authentik configuration (manual, done by user)

- Create OAuth2/OIDC provider, type: Authorization Code (PKCE)
- Redirect URI: `http://<beidlboard-host>:8080/callback`
- Scopes: `openid profile email`
- Note the Client ID and slug for `.env`

## Security notes

- JWT audience must match `AUTHENTIK_CLIENT_ID`; backend rejects tokens with wrong audience
- JWKS cache is invalidated if signature verification fails (handles key rotation)
- `KIOSK_SECRET` should be a cryptographically random 32+ byte string
- Username uniqueness enforced by PocketBase unique constraint on `username` field
- Sockets disconnect immediately on auth failure — no partial access

## Testing

- Backend: mock `decode_token` in socket/API tests; test 401 on missing token, valid user lookup, kiosk secret path
- Frontend: OIDC callback and setup flow tested via Vitest with mocked `fetch` and `localStorage`
