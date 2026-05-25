# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

beidlboard is a kiosk dashboard that runs on a Raspberry Pi with a monitor. A single shared display shows the active app; users control it from their phones via a mobile web UI. UI text is in Upper-Austrian dialect.

## Commands

### Run everything
```bash
sudo docker compose up -d          # start all services
sudo docker compose up --build -d  # rebuild images and start
sudo docker compose down           # stop
```

### Backend (run from `backend/`)
```bash
source .venv/bin/activate
pip install -r requirements.txt

pytest tests/ -v                           # all tests
pytest tests/test_general_socket.py -v    # single file
pytest tests/ -k test_open_app -v         # single test by name
```

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev      # dev server on :5173
npm run build    # production build → build/
npm test         # vitest
```

## Architecture

### Request flow
Phone browser → Nginx (`:8080`) → serves static SvelteKit SPA  
Phone/kiosk → Nginx `/socket.io/` proxy → Flask-SocketIO  
Phone/kiosk → Nginx `/api/` proxy → Flask REST  

### Two Socket.IO namespaces
- `/general` — carousel navigation, open/close apps. Every event broadcasts a `state` update (`{ active_app_id, open_app_ids }`) to all connected clients.
- `/apps` — app-specific events. Convention: `appid:event_name` (e.g. `hello_world:update_message`).

### Kiosk state
`backend/state.py` holds a module-level `kiosk_state` singleton (which app is active, which are open). It lives in Flask memory — it does not survive restarts. All changes are broadcast via `/general`.

### Adding an app
**Backend:** create `backend/apps/your_app/routes.py` with a `Blueprint` and any `@socketio.on` handlers. Add entry to `APP_REGISTRY` in `backend/apps/__init__.py` and register the blueprint in `register_apps()`.

**Frontend:** create `frontend/src/apps/your-app/Display.svelte` (kiosk view) and optionally `MobileControls.svelte` (phone controls — receives `socket: Socket` prop). Add entry to the `apps` array in `frontend/src/lib/appRegistry.ts`.

Open apps stay mounted in the DOM (CSS `display:none`) — only the active one is visible. Closed apps are destroyed.

### Frontend state
`frontend/src/lib/socket.ts` owns both socket instances. The `/general` `state` event handler directly updates the `kioskState` Svelte store (`frontend/src/lib/stores/kiosk.ts`). Components read the store reactively — no manual socket wiring needed for carousel/open/close state.

### Testing notes
Flask-SocketIO tests use `async_mode='threading'` (set in `conftest.py`) — gevent hangs in test environments. Socket.IO test clients from `socketio.test_client(app, namespace='/general')` are the standard pattern; see existing tests for reference.

### Authentication (Authentik OIDC)
Authorize/token URLs are global — no app slug in path: `{AUTHENTIK_URL}/application/o/authorize/` and `.../token/`. Authentik signs JWTs with ES256 (not RS256) — `auth.py` accepts both. `crypto.subtle` (needed for PKCE S256) requires HTTPS; `auth.ts` falls back to `plain` method on HTTP.

### PocketBase
The built-in `users` auth collection conflicts with custom collections — project uses `bb_users`. File uploads require an admin token + multipart PATCH. Schema migrations use `pocketbase.ensure_field(collection, field)` — checks existing schema and PATCHes only if the field is missing. Avatar URLs are proxied via nginx at `/pb-files/{collection}/{record_id}/{filename}`.

### Flask-SocketIO
`on_disconnect` handlers must accept `reason=None` — newer versions pass a reason argument.

### Frontend (Svelte 5 runes)
All components use Svelte 5 runes mode: `$state()`, `$derived()`, `onclick=` (not `on:click`). No `$:` reactive statements.
