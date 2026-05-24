# Beidlboard Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full beidlboard scaffold — monorepo, Docker Compose, Flask + Flask-SocketIO backend, SvelteKit SPA frontend, and a working Hello World app — so any developer can add new apps without touching the core framework.

**Architecture:** SvelteKit SPA (adapter-static, served by Nginx) talks to a single Flask backend via REST and Socket.IO. Flask owns all business logic and proxies PocketBase. Active app state is held in Flask memory and broadcast via Socket.IO to the shared kiosk display and all mobile controllers. Two Socket.IO namespaces: `/general` (carousel, open/close apps) and `/apps` (app-specific events). Open apps stay mounted in the DOM (CSS hidden), closed apps are destroyed. All app management (open, close, carousel) is done from the mobile controller page — the kiosk display is passive.

**Tech Stack:** SvelteKit + adapter-static, socket.io-client, Nginx, Flask, Flask-SocketIO, Flask-CORS, gevent, PocketBase (via Docker image), Docker Compose, pytest, vitest

---

## File Structure

```
beidlboard/
├── docker-compose.yml
├── .env.example
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.ts
│   ├── src/
│   │   ├── app.html
│   │   ├── lib/
│   │   │   ├── socket.ts                        # Socket.IO client instances + connect()
│   │   │   ├── appRegistry.ts                   # Central app list with component refs
│   │   │   └── stores/
│   │   │       └── kiosk.ts                     # Svelte store: activeAppId, openAppIds
│   │   ├── routes/
│   │   │   ├── +layout.svelte                   # Root layout (bare shell)
│   │   │   ├── +page.svelte                     # Kiosk display (carousel)
│   │   │   └── mobile/
│   │   │       └── +page.svelte                 # Mobile controller UI
│   │   └── apps/
│   │       └── hello-world/
│   │           ├── Display.svelte               # Kiosk-side app view
│   │           └── MobileControls.svelte        # Phone-side app controls
│   └── static/
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── wsgi.py                                  # Gunicorn entry point
│   ├── app.py                                   # create_app() factory
│   ├── config.py                                # Config from env vars
│   ├── extensions.py                            # Shared socketio = SocketIO() instance
│   ├── state.py                                 # In-memory KioskState dataclass
│   ├── sockets/
│   │   ├── __init__.py
│   │   ├── general.py                           # /general namespace: open/close/carousel
│   │   └── apps.py                              # /apps namespace: relay app-specific events
│   ├── apps/
│   │   ├── __init__.py                          # APP_REGISTRY list + register_apps()
│   │   └── hello_world/
│   │       ├── __init__.py
│   │       └── routes.py                        # Blueprint + socket handler for hello-world
│   └── tests/
│       ├── conftest.py
│       ├── test_general_socket.py
│       ├── test_apps_socket.py
│       └── test_hello_world.py
│
└── pocketbase/
    └── .gitkeep
```

---

## Task 1: Monorepo scaffold + Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `pocketbase/.gitkeep`

- [ ] **Step 1: Create root files**

`docker-compose.yml`:
```yaml
version: '3.9'

services:
  backend:
    build: ./backend
    env_file: .env
    ports:
      - "5000:5000"
    depends_on:
      - pocketbase

  pocketbase:
    image: ghcr.io/muchobien/pocketbase:latest
    ports:
      - "8090:8090"
    volumes:
      - pocketbase_data:/pb/pb_data

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  pocketbase_data:
```

`.env.example`:
```
FLASK_SECRET_KEY=change-me
POCKETBASE_URL=http://pocketbase:8090
```

- [ ] **Step 2: Create .env from example**

```bash
cp .env.example .env
```

- [ ] **Step 3: Create pocketbase placeholder**

```bash
mkdir -p pocketbase && touch pocketbase/.gitkeep
```

- [ ] **Step 4: Validate compose file**

```bash
docker-compose config
```
Expected: YAML dump of the config with no errors.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example pocketbase/.gitkeep
git commit -m "feat: add monorepo scaffold and Docker Compose"
```

---

## Task 2: Flask app scaffold

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/extensions.py`
- Create: `backend/wsgi.py`
- Create: `backend/app.py`
- Create: `backend/Dockerfile`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: Write failing health test**

`backend/tests/test_health.py`:
```python
def test_health_returns_ok(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok'}
```

- [ ] **Step 2: Create supporting files needed to run the test**

`backend/requirements.txt`:
```
flask==3.1.0
flask-socketio==5.4.1
flask-cors==4.0.1
python-dotenv==1.0.1
gevent==24.11.1
gevent-websocket==0.10.1
gunicorn==23.0.0
pytest==8.3.5
pytest-flask==1.3.0
```

`backend/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')
    POCKETBASE_URL = os.environ.get('POCKETBASE_URL', 'http://localhost:8090')
    TESTING = False

class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'
```

`backend/extensions.py`:
```python
from flask_socketio import SocketIO

socketio = SocketIO()
```

`backend/app.py`:
```python
from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import socketio


def create_app(config=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    CORS(app)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='gevent')

    from apps import register_apps
    register_apps(app)

    from sockets.general import GeneralNamespace
    from sockets.apps import AppsNamespace
    socketio.on_namespace(GeneralNamespace('/general'))
    socketio.on_namespace(AppsNamespace('/apps'))

    @app.route('/api/health')
    def health():
        return {'status': 'ok'}

    return app
```

`backend/wsgi.py`:
```python
from app import create_app

app = create_app()
```

`backend/tests/conftest.py`:
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app import create_app
from config import TestConfig


@pytest.fixture
def flask_app():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test'})
    yield app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()
```

- [ ] **Step 3: Create stub files so imports resolve (apps and sockets not built yet)**

`backend/apps/__init__.py`:
```python
from flask import Flask

APP_REGISTRY = []


def register_apps(flask_app: Flask) -> None:
    pass
```

`backend/sockets/__init__.py`:
```python
```

`backend/sockets/general.py`:
```python
from flask_socketio import Namespace


class GeneralNamespace(Namespace):
    pass
```

`backend/sockets/apps.py`:
```python
from flask_socketio import Namespace


class AppsNamespace(Namespace):
    pass
```

- [ ] **Step 4: Run the failing test**

```bash
cd backend && pip install -r requirements.txt && pytest tests/test_health.py -v
```
Expected: FAIL — `ModuleNotFoundError` or similar (stubs may not exist yet).

- [ ] **Step 5: Run test again — should pass now that all files exist**

```bash
pytest tests/test_health.py -v
```
Expected: PASS — `test_health_returns_ok PASSED`

- [ ] **Step 6: Create Dockerfile**

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
CMD ["gunicorn", "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
     "-w", "1", "--bind", "0.0.0.0:5000", "wsgi:app"]
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: add Flask app scaffold with health endpoint"
```

---

## Task 3: SvelteKit scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/svelte.config.js`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/app.html`
- Create: `frontend/src/routes/+layout.svelte`
- Create: `frontend/nginx.conf`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Create SvelteKit project files**

`frontend/package.json`:
```json
{
  "name": "beidlboard-frontend",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json"
  },
  "devDependencies": {
    "@sveltejs/adapter-static": "^3.0.8",
    "@sveltejs/kit": "^2.16.0",
    "@sveltejs/vite-plugin-svelte": "^5.0.0",
    "@testing-library/svelte": "^5.2.7",
    "svelte": "^5.0.0",
    "svelte-check": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^6.0.0",
    "vitest": "^3.0.0"
  },
  "dependencies": {
    "socket.io-client": "^4.8.1"
  }
}
```

`frontend/svelte.config.js`:
```js
import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    adapter: adapter({
      fallback: '200.html',
    }),
  },
};

export default config;
```

`frontend/vite.config.ts`:
```ts
import { sveltekit } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  test: {
    include: ['src/**/*.{test,spec}.{js,ts}'],
    environment: 'jsdom',
  },
});
```

`frontend/src/app.html`:
```html
<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%sveltekit.assets%/favicon.png" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    %sveltekit.head%
  </head>
  <body data-sveltekit-preload-data="hover">
    <div style="display: contents">%sveltekit.body%</div>
  </body>
</html>
```

`frontend/src/routes/+layout.svelte`:
```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  let { children }: { children: Snippet } = $props();
</script>

{@render children()}
```

- [ ] **Step 2: Install dependencies and verify build**

```bash
cd frontend && npm install && npm run build
```
Expected: `build/` directory created, `build/200.html` present.

- [ ] **Step 3: Create Nginx config and Dockerfile**

`frontend/nginx.conf`:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /200.html;
    }

    location /api/ {
        proxy_pass http://backend:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /socket.io/ {
        proxy_pass http://backend:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

`frontend/Dockerfile`:
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 4: Create static directory placeholder**

```bash
mkdir -p frontend/static && touch frontend/static/.gitkeep
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add SvelteKit scaffold with adapter-static and Nginx"
```

---

## Task 4: Backend app registry + in-memory state

**Files:**
- Modify: `backend/apps/__init__.py`
- Create: `backend/state.py`
- Create: `backend/tests/test_app_registry.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_app_registry.py`:
```python
from apps import APP_REGISTRY


def test_registry_is_list():
    assert isinstance(APP_REGISTRY, list)


def test_hello_world_in_registry():
    ids = [app['id'] for app in APP_REGISTRY]
    assert 'hello-world' in ids


def test_hello_world_has_required_fields():
    app = next(a for a in APP_REGISTRY if a['id'] == 'hello-world')
    assert 'name' in app
    assert 'icon' in app
    assert 'has_mobile_controls' in app
    assert app['has_mobile_controls'] is True
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_app_registry.py -v
```
Expected: `test_hello_world_in_registry FAILED`

- [ ] **Step 3: Implement app registry**

`backend/apps/__init__.py`:
```python
from flask import Flask

APP_REGISTRY = [
    {
        'id': 'hello-world',
        'name': 'Hallo Welt',
        'icon': '👋',
        'has_mobile_controls': True,
    }
]


def register_apps(flask_app: Flask) -> None:
    from apps.hello_world.routes import bp as hello_world_bp
    flask_app.register_blueprint(hello_world_bp, url_prefix='/api/apps/hello-world')
```

- [ ] **Step 4: Create Hello World blueprint stub (needed for import above)**

`backend/apps/hello_world/__init__.py`:
```python
```

`backend/apps/hello_world/routes.py`:
```python
from flask import Blueprint

bp = Blueprint('hello_world', __name__)
```

- [ ] **Step 5: Run tests — should pass**

```bash
pytest tests/test_app_registry.py -v
```
Expected: all 3 tests PASS.

- [ ] **Step 6: Create in-memory state**

`backend/state.py`:
```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KioskState:
    active_app_id: Optional[str] = None
    open_app_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'active_app_id': self.active_app_id,
            'open_app_ids': self.open_app_ids,
        }


kiosk_state = KioskState()
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: add backend app registry and in-memory kiosk state"
```

---

## Task 5: Flask-SocketIO /general namespace

**Files:**
- Modify: `backend/sockets/general.py`
- Create: `backend/tests/test_general_socket.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_general_socket.py`:
```python
import pytest
from app import create_app
from extensions import socketio
from state import kiosk_state


@pytest.fixture(autouse=True)
def reset_state():
    kiosk_state.active_app_id = None
    kiosk_state.open_app_ids = []
    yield
    kiosk_state.active_app_id = None
    kiosk_state.open_app_ids = []


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/general')


def test_connect_receives_initial_state(socket_client):
    received = socket_client.get_received('/general')
    assert len(received) == 1
    assert received[0]['name'] == 'state'
    data = received[0]['args'][0]
    assert data['active_app_id'] is None
    assert data['open_app_ids'] == []


def test_open_app_updates_state(socket_client):
    socket_client.get_received('/general')  # clear connect event
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    received = socket_client.get_received('/general')
    assert any(e['name'] == 'state' for e in received)
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['active_app_id'] == 'hello-world'
    assert 'hello-world' in state_event['args'][0]['open_app_ids']


def test_close_app_removes_from_state(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('close_app', {'app_id': 'hello-world'}, namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert 'hello-world' not in state_event['args'][0]['open_app_ids']
    assert state_event['args'][0]['active_app_id'] is None


def test_carousel_next_cycles_active_app(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('carousel_next', namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['active_app_id'] == 'hello-world'


def test_carousel_prev_cycles_active_app(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('carousel_prev', namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['active_app_id'] == 'hello-world'
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_general_socket.py -v
```
Expected: all tests FAIL (namespace handler does nothing yet).

- [ ] **Step 3: Implement GeneralNamespace**

`backend/sockets/general.py`:
```python
from flask_socketio import Namespace, emit
from state import kiosk_state


class GeneralNamespace(Namespace):
    def on_connect(self):
        emit('state', kiosk_state.to_dict())

    def on_open_app(self, data):
        app_id = data.get('app_id')
        if app_id and app_id not in kiosk_state.open_app_ids:
            kiosk_state.open_app_ids.append(app_id)
        kiosk_state.active_app_id = app_id
        self._broadcast_state()

    def on_close_app(self, data):
        app_id = data.get('app_id')
        if app_id in kiosk_state.open_app_ids:
            kiosk_state.open_app_ids.remove(app_id)
        if kiosk_state.active_app_id == app_id:
            kiosk_state.active_app_id = kiosk_state.open_app_ids[-1] if kiosk_state.open_app_ids else None
        self._broadcast_state()

    def on_carousel_next(self):
        self._carousel_step(1)

    def on_carousel_prev(self):
        self._carousel_step(-1)

    def _carousel_step(self, direction: int):
        if not kiosk_state.open_app_ids:
            return
        ids = kiosk_state.open_app_ids
        try:
            idx = ids.index(kiosk_state.active_app_id)
        except ValueError:
            idx = 0
        kiosk_state.active_app_id = ids[(idx + direction) % len(ids)]
        self._broadcast_state()

    def _broadcast_state(self):
        emit('state', kiosk_state.to_dict(), broadcast=True, namespace='/general')
```

- [ ] **Step 4: Run tests — should pass**

```bash
pytest tests/test_general_socket.py -v
```
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/sockets/general.py backend/tests/test_general_socket.py
git commit -m "feat: implement /general Socket.IO namespace for carousel and app management"
```

---

## Task 6: Flask-SocketIO /apps namespace + Hello World socket handler

**Files:**
- Modify: `backend/sockets/apps.py`
- Modify: `backend/apps/hello_world/routes.py`
- Create: `backend/tests/test_apps_socket.py`
- Create: `backend/tests/test_hello_world.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_apps_socket.py`:
```python
import pytest
from app import create_app
from extensions import socketio


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps')


def test_connect_succeeds(socket_client):
    assert socket_client.is_connected('/apps')
```

`backend/tests/test_hello_world.py`:
```python
import pytest
from app import create_app
from extensions import socketio
from apps.hello_world.routes import _state


@pytest.fixture(autouse=True)
def reset_hello_world_state():
    _state['message'] = 'Servus Welt!'
    yield
    _state['message'] = 'Servus Welt!'


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps')


def test_update_message_broadcasts(socket_client):
    socket_client.emit('hello_world:update_message', {'message': 'Oida!'}, namespace='/apps')
    received = socket_client.get_received('/apps')
    assert any(e['name'] == 'hello_world:message_updated' for e in received)
    event = next(e for e in received if e['name'] == 'hello_world:message_updated')
    assert event['args'][0]['message'] == 'Oida!'


def test_update_message_persists_in_state(socket_client):
    socket_client.emit('hello_world:update_message', {'message': 'Hawedere!'}, namespace='/apps')
    assert _state['message'] == 'Hawedere!'


def test_empty_message_ignored(socket_client):
    socket_client.emit('hello_world:update_message', {'message': '   '}, namespace='/apps')
    assert _state['message'] == 'Servus Welt!'
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_apps_socket.py tests/test_hello_world.py -v
```
Expected: `test_connect_succeeds` passes, hello_world tests FAIL.

- [ ] **Step 3: Implement /apps namespace and Hello World handler**

`backend/sockets/apps.py`:
```python
from flask_socketio import Namespace


class AppsNamespace(Namespace):
    def on_connect(self):
        pass
```

`backend/apps/hello_world/routes.py`:
```python
from flask import Blueprint
from extensions import socketio

bp = Blueprint('hello_world', __name__)

_state = {'message': 'Servus Welt!'}


@socketio.on('hello_world:update_message', namespace='/apps')
def handle_update_message(data):
    message = data.get('message', '').strip()
    if message:
        _state['message'] = message
        socketio.emit('hello_world:message_updated', {'message': message}, namespace='/apps')
```

- [ ] **Step 4: Run tests — should pass**

```bash
pytest tests/test_apps_socket.py tests/test_hello_world.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/sockets/apps.py backend/apps/hello_world/routes.py backend/tests/
git commit -m "feat: implement /apps namespace and Hello World socket handler"
```

---

## Task 7: Frontend app registry + kiosk store

**Files:**
- Create: `frontend/src/lib/appRegistry.ts`
- Create: `frontend/src/lib/stores/kiosk.ts`
- Create: `frontend/src/lib/__tests__/appRegistry.test.ts`
- Create: `frontend/src/lib/__tests__/kiosk.test.ts`

- [ ] **Step 1: Write failing tests**

`frontend/src/lib/__tests__/appRegistry.test.ts`:
```ts
import { describe, it, expect } from 'vitest';
import { apps, getApp } from '../appRegistry';

describe('appRegistry', () => {
  it('contains hello-world', () => {
    const ids = apps.map((a) => a.id);
    expect(ids).toContain('hello-world');
  });

  it('hello-world has required fields', () => {
    const app = getApp('hello-world');
    expect(app).toBeDefined();
    expect(app?.name).toBeTruthy();
    expect(app?.icon).toBeTruthy();
    expect(app?.hasMobileControls).toBe(true);
    expect(app?.display).toBeDefined();
    expect(app?.mobileControls).toBeDefined();
  });

  it('getApp returns undefined for unknown id', () => {
    expect(getApp('does-not-exist')).toBeUndefined();
  });
});
```

`frontend/src/lib/__tests__/kiosk.test.ts`:
```ts
import { describe, it, expect } from 'vitest';
import { get } from 'svelte/store';
import { kioskState } from '../stores/kiosk';

describe('kioskState', () => {
  it('starts with null active app and empty open list', () => {
    const state = get(kioskState);
    expect(state.activeAppId).toBeNull();
    expect(state.openAppIds).toEqual([]);
  });
});
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd frontend && npm test
```
Expected: FAIL — modules not found.

- [ ] **Step 3: Create Hello World app component stubs (needed for registry import)**

`frontend/src/apps/hello-world/Display.svelte`:
```svelte
<div class="hello-world-display">
  <h1>Servus Welt!</h1>
</div>
```

`frontend/src/apps/hello-world/MobileControls.svelte`:
```svelte
<script lang="ts">
  // props added in Task 9
</script>
<div class="hello-world-controls"></div>
```

- [ ] **Step 4: Implement app registry and kiosk store**

`frontend/src/lib/appRegistry.ts`:
```ts
import type { Component } from 'svelte';
import HelloWorldDisplay from '../apps/hello-world/Display.svelte';
import HelloWorldMobileControls from '../apps/hello-world/MobileControls.svelte';

export interface AppDefinition {
  id: string;
  name: string;
  icon: string;
  hasMobileControls: boolean;
  display: Component;
  mobileControls?: Component;
}

export const apps: AppDefinition[] = [
  {
    id: 'hello-world',
    name: 'Hallo Welt',
    icon: '👋',
    hasMobileControls: true,
    display: HelloWorldDisplay,
    mobileControls: HelloWorldMobileControls,
  },
];

export function getApp(id: string): AppDefinition | undefined {
  return apps.find((app) => app.id === id);
}
```

`frontend/src/lib/stores/kiosk.ts`:
```ts
import { writable } from 'svelte/store';

export interface KioskState {
  activeAppId: string | null;
  openAppIds: string[];
}

export const kioskState = writable<KioskState>({
  activeAppId: null,
  openAppIds: [],
});
```

- [ ] **Step 5: Run tests — should pass**

```bash
cd frontend && npm test
```
Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add frontend app registry, kiosk store, and Hello World component stubs"
```

---

## Task 8: Frontend Socket.IO client

**Files:**
- Create: `frontend/src/lib/socket.ts`

- [ ] **Step 1: Create socket client**

`frontend/src/lib/socket.ts`:
```ts
import { io } from 'socket.io-client';
import { kioskState } from './stores/kiosk';

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? '';

export const generalSocket = io(`${BASE_URL}/general`, { autoConnect: false });
export const appsSocket = io(`${BASE_URL}/apps`, { autoConnect: false });

generalSocket.on(
  'state',
  (state: { active_app_id: string | null; open_app_ids: string[] }) => {
    kioskState.set({
      activeAppId: state.active_app_id,
      openAppIds: state.open_app_ids,
    });
  }
);

export function connectSockets(): void {
  generalSocket.connect();
  appsSocket.connect();
}
```

- [ ] **Step 2: Verify build still passes**

```bash
cd frontend && npm run build
```
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/socket.ts
git commit -m "feat: add Socket.IO client connecting /general and /apps namespaces"
```

---

## Task 9: Kiosk display page

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Implement kiosk display**

`frontend/src/routes/+page.svelte`:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { kioskState } from '$lib/stores/kiosk';
  import { connectSockets } from '$lib/socket';
  import { getApp } from '$lib/appRegistry';

  onMount(() => {
    connectSockets();
  });
</script>

<div class="kiosk">
  {#each $kioskState.openAppIds as appId (appId)}
    {@const app = getApp(appId)}
    {#if app}
      <div class="app-slot" class:active={appId === $kioskState.activeAppId}>
        <svelte:component this={app.display} />
      </div>
    {/if}
  {/each}

  {#if $kioskState.openAppIds.length === 0}
    <div class="empty-state">
      <p>Koa App offen. Mach oan auf mit deim Handy!</p>
    </div>
  {/if}
</div>

<style>
  :global(body) {
    margin: 0;
    background: #111;
    color: #fff;
    font-family: sans-serif;
  }

  .kiosk {
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    position: relative;
  }

  .app-slot {
    display: none;
    width: 100%;
    height: 100%;
    position: absolute;
    inset: 0;
  }

  .app-slot.active {
    display: block;
  }

  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-size: 1.5rem;
    color: #666;
  }
</style>
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/+page.svelte
git commit -m "feat: add kiosk display page with mounted app carousel"
```

---

## Task 10: Mobile controller page

**Files:**
- Create: `frontend/src/routes/mobile/+page.svelte`

- [ ] **Step 1: Implement mobile controller**

`frontend/src/routes/mobile/+page.svelte`:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { kioskState } from '$lib/stores/kiosk';
  import { generalSocket, appsSocket, connectSockets } from '$lib/socket';
  import { apps, getApp } from '$lib/appRegistry';

  onMount(() => {
    connectSockets();
  });

  function openApp(appId: string) {
    generalSocket.emit('open_app', { app_id: appId });
  }

  function closeApp(appId: string) {
    generalSocket.emit('close_app', { app_id: appId });
  }

  function carouselPrev() {
    generalSocket.emit('carousel_prev');
  }

  function carouselNext() {
    generalSocket.emit('carousel_next');
  }

  $: activeApp = $kioskState.activeAppId ? getApp($kioskState.activeAppId) : null;
</script>

<div class="mobile-controller">
  <header>
    <h1>Beidlboard</h1>
    {#if $kioskState.activeAppId}
      <span class="active-label">
        {getApp($kioskState.activeAppId)?.icon}
        {getApp($kioskState.activeAppId)?.name}
      </span>
    {/if}
  </header>

  <div class="general-controls">
    <button on:click={carouselPrev} disabled={$kioskState.openAppIds.length < 2}>←</button>
    <button on:click={carouselNext} disabled={$kioskState.openAppIds.length < 2}>→</button>
  </div>

  {#if activeApp?.hasMobileControls && activeApp.mobileControls}
    <div class="app-controls">
      <svelte:component this={activeApp.mobileControls} socket={appsSocket} />
    </div>
  {/if}

  <div class="app-launcher">
    <h2>Apps</h2>
    {#each apps as app}
      <div class="app-item">
        <span>{app.icon} {app.name}</span>
        {#if $kioskState.openAppIds.includes(app.id)}
          <button class="close-btn" on:click={() => closeApp(app.id)}>Schließen</button>
        {:else}
          <button class="open-btn" on:click={() => openApp(app.id)}>Öffnen</button>
        {/if}
      </div>
    {/each}
  </div>
</div>

<style>
  :global(body) {
    margin: 0;
    background: #1a1a1a;
    color: #fff;
    font-family: sans-serif;
  }

  .mobile-controller {
    max-width: 480px;
    margin: 0 auto;
    padding: 1rem;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
  }

  h1 {
    font-size: 1.25rem;
    margin: 0;
  }

  .active-label {
    font-size: 0.9rem;
    color: #aaa;
  }

  .general-controls {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .general-controls button {
    flex: 1;
    padding: 0.75rem;
    font-size: 1.5rem;
    background: #333;
    color: #fff;
    border: none;
    border-radius: 8px;
    cursor: pointer;
  }

  .general-controls button:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .app-controls {
    margin-bottom: 1rem;
    padding: 1rem;
    background: #2a2a2a;
    border-radius: 8px;
  }

  .app-launcher h2 {
    font-size: 1rem;
    color: #aaa;
    margin: 0 0 0.5rem;
  }

  .app-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 0;
    border-bottom: 1px solid #333;
  }

  .open-btn, .close-btn {
    padding: 0.4rem 1rem;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
  }

  .open-btn { background: #2d6a4f; color: #fff; }
  .close-btn { background: #6a2d2d; color: #fff; }
</style>
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/mobile/
git commit -m "feat: add mobile controller page with app launcher and general controls"
```

---

## Task 11: Hello World app components

**Files:**
- Modify: `frontend/src/apps/hello-world/Display.svelte`
- Modify: `frontend/src/apps/hello-world/MobileControls.svelte`

- [ ] **Step 1: Implement Display**

`frontend/src/apps/hello-world/Display.svelte`:
```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';

  let message = $state('Servus Welt!');

  function handleMessageUpdated(data: { message: string }) {
    message = data.message;
  }

  onMount(() => {
    appsSocket.on('hello_world:message_updated', handleMessageUpdated);
  });

  onDestroy(() => {
    appsSocket.off('hello_world:message_updated', handleMessageUpdated);
  });
</script>

<div class="hello-world-display">
  <h1>{message}</h1>
</div>

<style>
  .hello-world-display {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    background: #111;
  }

  h1 {
    font-size: clamp(3rem, 8vw, 8rem);
    color: #fff;
    text-align: center;
    padding: 2rem;
  }
</style>
```

- [ ] **Step 2: Implement MobileControls**

`frontend/src/apps/hello-world/MobileControls.svelte`:
```svelte
<script lang="ts">
  import type { Socket } from 'socket.io-client';

  let { socket }: { socket: Socket } = $props();

  let newMessage = $state('');

  function sendMessage() {
    const trimmed = newMessage.trim();
    if (trimmed) {
      socket.emit('hello_world:update_message', { message: trimmed });
      newMessage = '';
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') sendMessage();
  }
</script>

<div class="hello-world-controls">
  <p style="margin: 0 0 0.5rem; font-size: 0.85rem; color: #aaa;">Nachricht ändern</p>
  <div class="input-row">
    <input
      bind:value={newMessage}
      onkeydown={handleKeydown}
      placeholder="Neue Nachricht..."
    />
    <button onclick={sendMessage} disabled={!newMessage.trim()}>Schicken</button>
  </div>
</div>

<style>
  .input-row {
    display: flex;
    gap: 0.5rem;
  }

  input {
    flex: 1;
    padding: 0.5rem;
    background: #333;
    color: #fff;
    border: 1px solid #555;
    border-radius: 6px;
    font-size: 1rem;
  }

  button {
    padding: 0.5rem 1rem;
    background: #2d6a4f;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 1rem;
  }

  button:disabled {
    opacity: 0.4;
    cursor: default;
  }
</style>
```

- [ ] **Step 3: Verify build and tests**

```bash
cd frontend && npm run build && npm test
```
Expected: build PASS, tests PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/apps/hello-world/
git commit -m "feat: implement Hello World Display and MobileControls components"
```

---

## Task 12: End-to-end Docker smoke test

**Files:** none — this task verifies the full system works together.

- [ ] **Step 1: Build and start all services**

```bash
docker-compose up --build -d
```
Expected: all three containers start (backend, pocketbase, frontend). Check with:
```bash
docker-compose ps
```
Expected output: `backend`, `pocketbase`, `frontend` all `Up`.

- [ ] **Step 2: Verify health endpoint**

```bash
curl http://localhost/api/health
```
Expected: `{"status": "ok"}`

- [ ] **Step 3: Verify kiosk display loads**

Open `http://localhost` in a browser.
Expected: dark screen with "Koa App offen. Mach oan auf mit deim Handy!"

- [ ] **Step 4: Verify mobile controller loads**

Open `http://localhost/mobile` in a browser (or a second device on the same network).
Expected: Beidlboard mobile controller with "Hallo Welt 👋" in the app list and an "Öffnen" button.

- [ ] **Step 5: Open Hello World from mobile controller**

Click "Öffnen" next to "Hallo Welt" on the mobile page.
Expected: kiosk display switches to show "Servus Welt!" in large text.

- [ ] **Step 6: Send a message from mobile controller**

Type a message in the Hello World controls input on the mobile page and click "Schicken".
Expected: kiosk display updates to show the new message in real time.

- [ ] **Step 7: Test carousel controls**

Open a second tab at `http://localhost/mobile`. Click ← or → on either mobile tab.
Expected: no visible change (only one app open), but no errors in the console.

- [ ] **Step 8: Stop containers**

```bash
docker-compose down
```

- [ ] **Step 9: Final commit**

```bash
git add .
git commit -m "feat: complete beidlboard scaffold with Hello World end-to-end"
```

---

## Adding a New App (Reference)

To add a new app after this scaffold is in place:

**Backend:**
1. Create `backend/apps/your_app/__init__.py` (empty)
2. Create `backend/apps/your_app/routes.py` with a `Blueprint` and any Socket.IO handlers
3. Add entry to `APP_REGISTRY` in `backend/apps/__init__.py`
4. Import and register the blueprint in `register_apps()`

**Frontend:**
1. Create `frontend/src/apps/your-app/Display.svelte`
2. Create `frontend/src/apps/your-app/MobileControls.svelte` (if needed)
3. Add entry to `apps` array in `frontend/src/lib/appRegistry.ts`

That's it. The carousel, mobile controller, and Socket.IO routing all work automatically.
