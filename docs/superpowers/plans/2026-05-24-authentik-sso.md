# Authentik SSO Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect all beidlboard routes with Authentik SSO; users pick a username on first login stored in PocketBase; authenticated identity flows through socket sessions into app data.

**Architecture:** Frontend does OIDC PKCE manually (no library), gets a JWT, passes it via Socket.IO `auth` dict and HTTP `Authorization` header. Backend validates JWTs against Authentik's JWKS endpoint using PyJWT. Kiosk Pi connects via `KIOSK_SECRET` env var — no OIDC. User profiles stored in PocketBase `users` collection.

**Tech Stack:** PyJWT + cryptography (backend JWT validation), Web Crypto API + fetch (frontend PKCE), PocketBase REST API (user storage), Flask Blueprint (users API).

---

## File Map

**New backend files:**
- `backend/pocketbase.py` — shared admin token + collection setup (extracted from hello_world)
- `backend/auth.py` — JWT decode, `require_auth` decorator
- `backend/users.py` — PocketBase user CRUD
- `backend/routes/__init__.py` — empty
- `backend/routes/users.py` — `GET/POST /api/users/me`
- `backend/sockets/middleware.py` — `authenticate_socket`, per-sid session store
- `backend/tests/test_pocketbase.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_users_api.py`

**Modified backend files:**
- `backend/requirements.txt` — add PyJWT, cryptography
- `backend/config.py` — add Authentik + Kiosk config keys
- `backend/app.py` — register users blueprint
- `backend/sockets/general.py` — wire auth middleware into on_connect/on_disconnect
- `backend/sockets/apps.py` — same
- `backend/apps/hello_world/routes.py` — use pocketbase.py, add sender field
- `backend/tests/conftest.py` — set KIOSK_SECRET env var
- `backend/tests/test_general_socket.py` — pass auth to socket clients
- `backend/tests/test_hello_world.py` — mock pocketbase.ensure_collection, pass auth

**New frontend files:**
- `frontend/src/lib/auth.ts` — PKCE flow, token storage
- `frontend/src/lib/stores/user.ts` — userStore, fetchUser, createUser
- `frontend/src/routes/callback/+page.svelte`
- `frontend/src/routes/setup/+page.svelte`

**Modified frontend files:**
- `frontend/src/lib/socket.ts` — `connectSockets(auth)` param
- `frontend/src/routes/+page.svelte` — auth check on mount
- `frontend/src/routes/mobile/+page.svelte` — auth check + show username
- `frontend/src/apps/hello-world/Display.svelte` — bubbles show sender
- `frontend/Dockerfile` — pass VITE_ build args
- `docker-compose.yml` — add env vars + build args

---

### Task 1: Shared PocketBase utility

Extract admin token and collection setup out of `hello_world/routes.py` into a shared module so the users module (Task 4) can reuse it.

**Files:**
- Create: `backend/pocketbase.py`
- Modify: `backend/apps/hello_world/routes.py`
- Create: `backend/tests/test_pocketbase.py`

- [ ] **Step 1: Write failing test for `admin_token`**

```python
# backend/tests/test_pocketbase.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock
import pocketbase


@pytest.fixture(autouse=True)
def clear_token_cache():
    pocketbase._token_cache = None
    pocketbase._token_fetched_at = 0
    yield
    pocketbase._token_cache = None
    pocketbase._token_fetched_at = 0


def _ok_auth():
    m = MagicMock()
    m.ok = True
    m.json.return_value = {'token': 'tok123'}
    return m


def _fail_auth():
    m = MagicMock()
    m.ok = False
    m.status_code = 401
    return m


def test_admin_token_returns_token_on_success():
    with patch('pocketbase.requests.post', return_value=_ok_auth()):
        assert pocketbase.admin_token() == 'tok123'


def test_admin_token_caches_token():
    with patch('pocketbase.requests.post', return_value=_ok_auth()) as mock_post:
        pocketbase.admin_token()
        pocketbase.admin_token()
    assert mock_post.call_count == 1


def test_admin_token_returns_none_without_credentials(monkeypatch):
    monkeypatch.delenv('PB_ADMIN_EMAIL', raising=False)
    monkeypatch.delenv('PB_ADMIN_PASSWORD', raising=False)
    assert pocketbase.admin_token() is None


def test_admin_token_bootstraps_on_auth_failure():
    responses = [_fail_auth(), MagicMock(ok=True), _ok_auth()]
    with patch('pocketbase.requests.post', side_effect=responses):
        token = pocketbase.admin_token()
    assert token == 'tok123'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_pocketbase.py -v
```
Expected: ImportError or AttributeError (module doesn't exist yet).

- [ ] **Step 3: Create `backend/pocketbase.py`**

```python
import os
import time
import logging
import requests

log = logging.getLogger(__name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')

_token_cache: str | None = None
_token_fetched_at: float = 0
_TOKEN_TTL = 3600

_collection_ready: set[str] = set()


def admin_token() -> str | None:
    global _token_cache, _token_fetched_at
    if _token_cache and time.time() - _token_fetched_at < _TOKEN_TTL:
        return _token_cache

    email = os.environ.get('PB_ADMIN_EMAIL', '')
    password = os.environ.get('PB_ADMIN_PASSWORD', '')
    if not email or not password:
        return None

    resp = requests.post(
        f'{PB_URL}/api/collections/_superusers/auth-with-password',
        json={'identity': email, 'password': password},
        timeout=5,
    )
    if resp.ok:
        _token_cache = resp.json().get('token')
        _token_fetched_at = time.time()
        log.warning('PocketBase superuser auth OK')
        return _token_cache

    log.warning('PocketBase superuser auth failed (%s), trying bootstrap', resp.status_code)
    requests.post(
        f'{PB_URL}/api/collections/_superusers/records',
        json={'email': email, 'password': password, 'passwordConfirm': password},
        timeout=5,
    )
    resp = requests.post(
        f'{PB_URL}/api/collections/_superusers/auth-with-password',
        json={'identity': email, 'password': password},
        timeout=5,
    )
    if resp.ok:
        _token_cache = resp.json().get('token')
        _token_fetched_at = time.time()
        log.warning('PocketBase bootstrap + auth OK')
        return _token_cache

    log.error('PocketBase auth failed after bootstrap: %s %s', resp.status_code, resp.text)
    return None


def ensure_collection(
    name: str,
    fields: list[dict],
    rules: dict | None = None,
) -> None:
    if name in _collection_ready:
        return

    default_rules = {
        'listRule': '',
        'viewRule': '',
        'createRule': '',
        'updateRule': None,
        'deleteRule': None,
    }

    for attempt in range(6):
        try:
            token = admin_token()
            if not token:
                log.error('No PocketBase admin token for collection %s', name)
                _collection_ready.add(name)
                return
            headers = {'Authorization': f'Bearer {token}'}
            check = requests.get(
                f'{PB_URL}/api/collections/{name}', headers=headers, timeout=5
            )
            if check.status_code == 404:
                log.warning('Collection %s not found, creating...', name)
                r = requests.post(
                    f'{PB_URL}/api/collections',
                    headers=headers,
                    timeout=5,
                    json={
                        'name': name,
                        'type': 'base',
                        'fields': fields,
                        **(rules or default_rules),
                    },
                )
                log.warning('Collection %s create: %s %s', name, r.status_code, r.text)
            else:
                log.warning('Collection %s check: %s', name, check.status_code)
            _collection_ready.add(name)
            return
        except Exception as e:
            log.warning('ensure_collection %s attempt %d: %s', name, attempt, e)
            if attempt < 5:
                time.sleep(3)

    log.error('ensure_collection %s gave up after 6 attempts', name)
    _collection_ready.add(name)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && PB_ADMIN_EMAIL=admin@test.com PB_ADMIN_PASSWORD=test python -m pytest tests/test_pocketbase.py -v
```
Expected: 4 tests PASS.

- [ ] **Step 5: Refactor `backend/apps/hello_world/routes.py` to use `pocketbase.py`**

Replace the entire file:

```python
from flask import Blueprint, request
from extensions import socketio
import requests
import os
import logging

import pocketbase

log = logging.getLogger(__name__)

bp = Blueprint('hello_world', __name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')
PB_COLLECTION = 'hello_world_messages'
_FIELDS = [
    {'name': 'text', 'type': 'text', 'required': True},
    {'name': 'sender', 'type': 'text', 'required': False},
    {'name': 'created', 'type': 'autodate', 'onCreate': True, 'onUpdate': False},
]


def _ensure():
    pocketbase.ensure_collection(PB_COLLECTION, _FIELDS)


def _recent_messages(limit: int = 20) -> list[dict]:
    _ensure()
    try:
        resp = requests.get(
            f'{PB_URL}/api/collections/{PB_COLLECTION}/records',
            params={'sort': '-created', 'perPage': limit, 'skipTotal': 1},
            timeout=5,
        )
        if resp.ok:
            return [
                {'text': item['text'], 'sender': item.get('sender', '')}
                for item in resp.json().get('items', [])
            ]
        log.warning('_recent_messages failed: %s %s', resp.status_code, resp.text)
    except Exception as e:
        log.error('_recent_messages exception: %s', e)
    return []


def _save_message(text: str, sender: str = ''):
    _ensure()
    try:
        r = requests.post(
            f'{PB_URL}/api/collections/{PB_COLLECTION}/records',
            json={'text': text, 'sender': sender},
            timeout=5,
        )
        if not r.ok:
            log.warning('_save_message failed: %s %s', r.status_code, r.text)
    except Exception as e:
        log.error('_save_message exception: %s', e)


@socketio.on('hello_world:update_message', namespace='/apps')
def handle_update_message(data):
    message = data.get('message', '').strip()
    if not message:
        return
    _save_message(message)
    msgs = _recent_messages()
    socketio.emit(
        'hello_world:messages_updated',
        {'messages': [{'text': m['text'], 'sender': m['sender']} for m in msgs]},
        namespace='/apps',
    )


@socketio.on('hello_world:request_messages', namespace='/apps')
def handle_request_messages():
    msgs = _recent_messages()
    socketio.emit(
        'hello_world:messages_updated',
        {'messages': [{'text': m['text'], 'sender': m['sender']} for m in msgs]},
        namespace='/apps',
    )
```

- [ ] **Step 6: Update `backend/tests/test_hello_world.py` to match new message format**

Replace the entire file:

```python
import pytest
from unittest.mock import patch, MagicMock
from extensions import socketio
import apps.hello_world.routes as hw_routes


def _pb_list(messages):
    m = MagicMock()
    m.ok = True
    m.json.return_value = {'items': [{'text': t, 'sender': ''} for t in messages]}
    return m


def _pb_ok():
    m = MagicMock()
    m.ok = True
    m.status_code = 200
    return m


@pytest.fixture(autouse=True)
def skip_pb_setup():
    with patch('pocketbase.ensure_collection'):
        yield


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps')


def test_update_message_broadcasts_messages_list(socket_client):
    with patch('apps.hello_world.routes.requests.post', return_value=_pb_ok()), \
         patch('apps.hello_world.routes.requests.get', return_value=_pb_list(['Oida!'])):
        socket_client.emit('hello_world:update_message', {'message': 'Oida!'}, namespace='/apps')
        received = socket_client.get_received('/apps')
    event = next((e for e in received if e['name'] == 'hello_world:messages_updated'), None)
    assert event is not None
    assert any(m['text'] == 'Oida!' for m in event['args'][0]['messages'])


def test_empty_message_ignored(socket_client):
    with patch('apps.hello_world.routes.requests.post'), \
         patch('apps.hello_world.routes.requests.get'):
        socket_client.emit('hello_world:update_message', {'message': '   '}, namespace='/apps')
        received = socket_client.get_received('/apps')
    assert not any(e['name'] == 'hello_world:messages_updated' for e in received)


def test_request_messages_returns_list(socket_client):
    with patch('apps.hello_world.routes.requests.get', return_value=_pb_list(['Hawedere!', 'Servas!'])):
        socket_client.emit('hello_world:request_messages', namespace='/apps')
        received = socket_client.get_received('/apps')
    event = next(e for e in received if e['name'] == 'hello_world:messages_updated')
    texts = [m['text'] for m in event['args'][0]['messages']]
    assert texts == ['Hawedere!', 'Servas!']


def test_newest_message_first_in_response(socket_client):
    messages = ['Neu', 'Alt']
    with patch('apps.hello_world.routes.requests.post', return_value=_pb_ok()), \
         patch('apps.hello_world.routes.requests.get', return_value=_pb_list(messages)):
        socket_client.emit('hello_world:update_message', {'message': 'Neu'}, namespace='/apps')
        received = socket_client.get_received('/apps')
    event = next(e for e in received if e['name'] == 'hello_world:messages_updated')
    assert event['args'][0]['messages'][0]['text'] == 'Neu'
```

- [ ] **Step 7: Run all backend tests to verify nothing broke**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/pocketbase.py backend/apps/hello_world/routes.py backend/tests/test_pocketbase.py backend/tests/test_hello_world.py
git commit -m "refactor: extract shared pocketbase module, add sender field to hello_world"
```

---

### Task 2: Config, dependencies, and environment

Add PyJWT/cryptography to backend. Add AUTHENTIK_* and KIOSK_SECRET env vars. Wire frontend VITE_ vars into Docker build.

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config.py`
- Modify: `.env`
- Modify: `docker-compose.yml`
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: Add Python dependencies**

In `backend/requirements.txt`, add two lines:
```
PyJWT==2.10.1
cryptography==44.0.2
```

Full file:
```
flask==3.1.0
requests==2.32.3
flask-socketio==5.4.1
flask-cors==4.0.1
python-dotenv==1.0.1
gevent==24.11.1
gevent-websocket==0.10.1
gunicorn==23.0.0
pytest==8.3.5
pytest-flask==1.3.0
PyJWT==2.10.1
cryptography==44.0.2
```

- [ ] **Step 2: Install dependencies**

```bash
cd backend && pip install PyJWT==2.10.1 cryptography==44.0.2
```
Expected: Successfully installed PyJWT-2.10.1 cryptography-44.0.2

- [ ] **Step 3: Update `backend/config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')
    POCKETBASE_URL = os.environ.get('POCKETBASE_URL', 'http://localhost:8090')
    AUTHENTIK_URL = os.environ.get('AUTHENTIK_URL', '')
    AUTHENTIK_APP_SLUG = os.environ.get('AUTHENTIK_APP_SLUG', '')
    AUTHENTIK_CLIENT_ID = os.environ.get('AUTHENTIK_CLIENT_ID', '')
    KIOSK_SECRET = os.environ.get('KIOSK_SECRET', '')
    TESTING = False

class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'
```

- [ ] **Step 4: Update `.env` with new vars**

Append to `.env`:
```
AUTHENTIK_URL=https://auth.yourdomain.com
AUTHENTIK_APP_SLUG=beidlboard
AUTHENTIK_CLIENT_ID=your-client-id-here
KIOSK_SECRET=change-this-to-a-long-random-string
```

- [ ] **Step 5: Update `frontend/Dockerfile` to accept build args**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .

ARG VITE_AUTHENTIK_URL=""
ARG VITE_AUTHENTIK_APP_SLUG=""
ARG VITE_AUTHENTIK_CLIENT_ID=""
ARG VITE_KIOSK_SECRET=""
ENV VITE_AUTHENTIK_URL=$VITE_AUTHENTIK_URL
ENV VITE_AUTHENTIK_APP_SLUG=$VITE_AUTHENTIK_APP_SLUG
ENV VITE_AUTHENTIK_CLIENT_ID=$VITE_AUTHENTIK_CLIENT_ID
ENV VITE_KIOSK_SECRET=$VITE_KIOSK_SECRET

RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 6: Update `docker-compose.yml` to pass build args**

Replace the `frontend` service section:
```yaml
  frontend:
    build:
      context: ./frontend
      args:
        VITE_AUTHENTIK_URL: ${AUTHENTIK_URL}
        VITE_AUTHENTIK_APP_SLUG: ${AUTHENTIK_APP_SLUG}
        VITE_AUTHENTIK_CLIENT_ID: ${AUTHENTIK_CLIENT_ID}
        VITE_KIOSK_SECRET: ${KIOSK_SECRET:-}
    ports:
      - "0.0.0.0:8080:80"
    depends_on:
      - backend
```

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/config.py .env docker-compose.yml frontend/Dockerfile
git commit -m "feat: add Authentik SSO config and build vars"
```

---

### Task 3: JWT auth module

Backend module that validates Authentik JWTs and provides a `require_auth` decorator for Flask routes.

**Files:**
- Create: `backend/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_auth.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import jwt
from unittest.mock import patch, MagicMock
from flask import Flask, g
import auth


@pytest.fixture
def app():
    a = Flask(__name__)
    a.config['TESTING'] = True
    return a


def _make_signing_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    return private_key


def _make_token(private_key, sub='user-123', audience='test-client', expired=False):
    import datetime
    now = datetime.datetime.utcnow()
    exp = now - datetime.timedelta(hours=1) if expired else now + datetime.timedelta(hours=1)
    return jwt.encode(
        {'sub': sub, 'aud': audience, 'iat': now, 'exp': exp},
        private_key,
        algorithm='RS256',
    )


def test_decode_token_valid():
    private_key = _make_signing_key()
    token = _make_token(private_key, audience='my-client')
    mock_key = MagicMock()
    mock_key.key = private_key.public_key()
    with patch.dict(os.environ, {'AUTHENTIK_CLIENT_ID': 'my-client'}), \
         patch('auth._get_jwks_client') as mock_client_fn:
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key
        mock_client_fn.return_value = mock_client
        auth._jwks_client = None
        claims = auth.decode_token(token)
    assert claims['sub'] == 'user-123'


def test_decode_token_expired():
    private_key = _make_signing_key()
    token = _make_token(private_key, expired=True, audience='my-client')
    mock_key = MagicMock()
    mock_key.key = private_key.public_key()
    with patch.dict(os.environ, {'AUTHENTIK_CLIENT_ID': 'my-client'}), \
         patch('auth._get_jwks_client') as mock_client_fn:
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key
        mock_client_fn.return_value = mock_client
        auth._jwks_client = None
        with pytest.raises(jwt.ExpiredSignatureError):
            auth.decode_token(token)


def test_require_auth_missing_header(app):
    @app.route('/test')
    @auth.require_auth
    def view():
        return 'ok'
    with app.test_client() as c:
        resp = c.get('/test')
    assert resp.status_code == 401


def test_require_auth_invalid_token(app):
    @app.route('/test')
    @auth.require_auth
    def view():
        return 'ok'
    with patch('auth.decode_token', side_effect=jwt.InvalidTokenError('bad')):
        with app.test_client() as c:
            resp = c.get('/test', headers={'Authorization': 'Bearer badtoken'})
    assert resp.status_code == 401


def test_require_auth_valid_token(app):
    @app.route('/test')
    @auth.require_auth
    def view():
        return g.user_sub
    with patch('auth.decode_token', return_value={'sub': 'user-abc'}):
        with app.test_client() as c:
            resp = c.get('/test', headers={'Authorization': 'Bearer validtoken'})
    assert resp.status_code == 200
    assert resp.data == b'user-abc'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```
Expected: ImportError (auth module doesn't exist).

- [ ] **Step 3: Create `backend/auth.py`**

```python
import os
import logging
from functools import wraps

import jwt
from jwt import PyJWKClient
from flask import request, g, jsonify

log = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        url = os.environ.get('AUTHENTIK_URL', '')
        slug = os.environ.get('AUTHENTIK_APP_SLUG', '')
        _jwks_client = PyJWKClient(f'{url}/application/o/{slug}/jwks/')
    return _jwks_client


def decode_token(token: str) -> dict:
    """Validate JWT against Authentik JWKS. Raises jwt.InvalidTokenError on failure."""
    client = _get_jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except jwt.exceptions.PyJWKClientConnectionError as e:
        log.error('JWKS fetch failed: %s', e)
        raise jwt.InvalidTokenError('JWKS unavailable') from e

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=['RS256'],
        audience=os.environ.get('AUTHENTIK_CLIENT_ID', ''),
    )


def require_auth(f):
    """Decorator for Flask routes: validates Bearer token, injects g.user_sub."""
    @wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        try:
            g.user_claims = decode_token(header[7:])
            g.user_sub = g.user_claims['sub']
        except Exception as e:
            log.warning('Auth rejected: %s', e)
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py backend/tests/test_auth.py
git commit -m "feat: JWT validation module with require_auth decorator"
```

---

### Task 4: Users module and API

PocketBase CRUD for users + REST endpoints `GET /api/users/me` and `POST /api/users/me`.

**Files:**
- Create: `backend/users.py`
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/users.py`
- Modify: `backend/app.py`
- Create: `backend/tests/test_users_api.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_users_api.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch
from app import create_app


@pytest.fixture
def flask_app():
    return create_app({'TESTING': True, 'SECRET_KEY': 'test', 'SOCKETIO_ASYNC_MODE': 'threading'})


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def _auth_header():
    return {'Authorization': 'Bearer validtoken'}


def test_get_me_returns_user(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}), \
         patch('users.get_user', return_value={'username': 'TestUser'}):
        resp = client.get('/api/users/me', headers=_auth_header())
    assert resp.status_code == 200
    assert resp.get_json() == {'username': 'TestUser'}


def test_get_me_returns_404_for_new_user(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-new'}), \
         patch('users.get_user', return_value=None):
        resp = client.get('/api/users/me', headers=_auth_header())
    assert resp.status_code == 404


def test_get_me_requires_auth(client):
    resp = client.get('/api/users/me')
    assert resp.status_code == 401


def test_post_me_creates_user(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}), \
         patch('users.get_user', return_value=None), \
         patch('users.create_user', return_value={'username': 'Oida'}) as mock_create:
        resp = client.post('/api/users/me', json={'username': 'Oida'}, headers=_auth_header())
    assert resp.status_code == 201
    mock_create.assert_called_once_with('sub-123', 'Oida')


def test_post_me_rejects_short_username(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}):
        resp = client.post('/api/users/me', json={'username': 'ab'}, headers=_auth_header())
    assert resp.status_code == 400


def test_post_me_rejects_long_username(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}):
        resp = client.post('/api/users/me', json={'username': 'a' * 21}, headers=_auth_header())
    assert resp.status_code == 400


def test_post_me_conflict_if_already_exists(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}), \
         patch('users.get_user', return_value={'username': 'existing'}):
        resp = client.post('/api/users/me', json={'username': 'NewName'}, headers=_auth_header())
    assert resp.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_users_api.py -v
```
Expected: ImportError or 404 errors (modules don't exist).

- [ ] **Step 3: Create `backend/users.py`**

```python
import os
import logging
import requests as http

import pocketbase

log = logging.getLogger(__name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')
_COLLECTION = 'users'
_FIELDS = [
    {'name': 'authentik_sub', 'type': 'text', 'required': True},
    {'name': 'username', 'type': 'text', 'required': True},
]


def _ensure():
    pocketbase.ensure_collection(_COLLECTION, _FIELDS)


def get_user(sub: str) -> dict | None:
    _ensure()
    try:
        resp = http.get(
            f'{PB_URL}/api/collections/{_COLLECTION}/records',
            params={'filter': f'authentik_sub="{sub}"', 'perPage': 1, 'skipTotal': 1},
            timeout=5,
        )
        if resp.ok:
            items = resp.json().get('items', [])
            return items[0] if items else None
        log.warning('get_user failed: %s %s', resp.status_code, resp.text)
    except Exception as e:
        log.error('get_user exception: %s', e)
    return None


def create_user(sub: str, username: str) -> dict:
    _ensure()
    resp = http.post(
        f'{PB_URL}/api/collections/{_COLLECTION}/records',
        json={'authentik_sub': sub, 'username': username},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 4: Create `backend/routes/__init__.py`** (empty file)

```bash
touch backend/routes/__init__.py
```

- [ ] **Step 5: Create `backend/routes/users.py`**

```python
from flask import Blueprint, g, jsonify, request
from auth import require_auth
import users

bp = Blueprint('users', __name__)


@bp.route('/api/users/me', methods=['GET'])
@require_auth
def get_me():
    user = users.get_user(g.user_sub)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'username': user['username']})


@bp.route('/api/users/me', methods=['POST'])
@require_auth
def create_me():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': 'Username must be 3-20 characters'}), 400
    if not all(c.isalnum() or c == '_' for c in username):
        return jsonify({'error': 'Username: letters, numbers, underscores only'}), 400
    if users.get_user(g.user_sub):
        return jsonify({'error': 'User already exists'}), 409
    try:
        user = users.create_user(g.user_sub, username)
        return jsonify({'username': user['username']}), 201
    except Exception as e:
        log_msg = str(e)
        return jsonify({'error': log_msg}), 500
```

- [ ] **Step 6: Register blueprint in `backend/app.py`**

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
    async_mode = app.config.get('SOCKETIO_ASYNC_MODE', 'gevent')
    socketio.init_app(app, cors_allowed_origins='*', async_mode=async_mode)

    from apps import register_apps
    register_apps(app)

    from sockets.general import GeneralNamespace
    from sockets.apps import AppsNamespace
    socketio.on_namespace(GeneralNamespace('/general'))
    socketio.on_namespace(AppsNamespace('/apps'))

    from routes.users import bp as users_bp
    app.register_blueprint(users_bp)

    @app.route('/api/health')
    def health():
        return {'status': 'ok'}

    return app
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_users_api.py -v
```
Expected: 7 tests PASS.

- [ ] **Step 8: Run all backend tests**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: All tests PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/users.py backend/routes/__init__.py backend/routes/users.py backend/app.py backend/tests/test_users_api.py
git commit -m "feat: users module and GET/POST /api/users/me endpoints"
```

---

### Task 5: Socket auth middleware

Validate every socket connection. Store per-sid sessions. Reject unauthenticated connections.

**Files:**
- Create: `backend/sockets/middleware.py`
- Modify: `backend/sockets/general.py`
- Modify: `backend/sockets/apps.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_general_socket.py`
- Create: `backend/tests/test_socket_auth.py`

- [ ] **Step 1: Write failing middleware tests**

```python
# backend/tests/test_socket_auth.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch
from sockets.middleware import authenticate_socket, get_session, clear_session, _sessions


@pytest.fixture(autouse=True)
def clear_sessions():
    _sessions.clear()
    yield
    _sessions.clear()


def test_kiosk_secret_accepted():
    with patch.dict(os.environ, {'KIOSK_SECRET': 'secret123'}):
        session = authenticate_socket({'kiosk_secret': 'secret123'}, 'sid-1')
    assert session is not None
    assert session['is_kiosk'] is True


def test_kiosk_wrong_secret_rejected():
    with patch.dict(os.environ, {'KIOSK_SECRET': 'secret123'}):
        session = authenticate_socket({'kiosk_secret': 'wrong'}, 'sid-1')
    assert session is None


def test_valid_token_accepted():
    with patch('sockets.middleware.decode_token', return_value={'sub': 'u1'}), \
         patch('sockets.middleware.users.get_user', return_value={'username': 'Max'}):
        session = authenticate_socket({'token': 'validtoken'}, 'sid-2')
    assert session is not None
    assert session['username'] == 'Max'
    assert session['is_kiosk'] is False


def test_invalid_token_rejected():
    import jwt
    with patch('sockets.middleware.decode_token', side_effect=jwt.InvalidTokenError('bad')):
        session = authenticate_socket({'token': 'badtoken'}, 'sid-3')
    assert session is None


def test_unknown_user_rejected():
    with patch('sockets.middleware.decode_token', return_value={'sub': 'ghost'}), \
         patch('sockets.middleware.users.get_user', return_value=None):
        session = authenticate_socket({'token': 'tok'}, 'sid-4')
    assert session is None


def test_no_auth_rejected():
    session = authenticate_socket({}, 'sid-5')
    assert session is None


def test_session_stored_on_auth():
    with patch.dict(os.environ, {'KIOSK_SECRET': 'sec'}):
        authenticate_socket({'kiosk_secret': 'sec'}, 'sid-6')
    assert get_session('sid-6') is not None


def test_session_cleared():
    _sessions['sid-7'] = {'is_kiosk': True}
    clear_session('sid-7')
    assert get_session('sid-7') is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_socket_auth.py -v
```
Expected: ImportError (middleware doesn't exist).

- [ ] **Step 3: Create `backend/sockets/middleware.py`**

```python
import os
import logging

import jwt

import users
from auth import decode_token

log = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}


def authenticate_socket(auth: dict, sid: str) -> dict | None:
    """Returns session dict if auth valid, None to reject the connection."""
    kiosk_secret = os.environ.get('KIOSK_SECRET', '')
    if kiosk_secret and auth.get('kiosk_secret') == kiosk_secret:
        session = {'is_kiosk': True, 'username': 'Kiosk'}
        _sessions[sid] = session
        return session

    token = auth.get('token', '')
    if not token:
        log.warning('Socket rejected: no auth (sid=%s)', sid)
        return None

    try:
        claims = decode_token(token)
    except Exception as e:
        log.warning('Socket rejected: bad token: %s (sid=%s)', e, sid)
        return None

    sub = claims.get('sub')
    user = users.get_user(sub)
    if not user:
        log.warning('Socket rejected: unknown user sub=%s (sid=%s)', sub, sid)
        return None

    session = {'is_kiosk': False, 'user_sub': sub, 'username': user['username']}
    _sessions[sid] = session
    log.warning('Socket authenticated: %s (sid=%s)', user['username'], sid)
    return session


def get_session(sid: str) -> dict | None:
    return _sessions.get(sid)


def clear_session(sid: str) -> None:
    _sessions.pop(sid, None)
```

- [ ] **Step 4: Run middleware tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_socket_auth.py -v
```
Expected: 8 tests PASS.

- [ ] **Step 5: Update `backend/sockets/general.py`**

```python
from flask_socketio import Namespace, emit
from flask import request
from state import kiosk_state
from sockets.middleware import authenticate_socket, clear_session


class GeneralNamespace(Namespace):
    def on_connect(self, auth=None):
        session = authenticate_socket(auth or {}, request.sid)
        if session is None:
            return False
        emit('state', kiosk_state.to_dict())

    def on_disconnect(self):
        clear_session(request.sid)

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

    def on_toggle_lock(self):
        kiosk_state.locked = not kiosk_state.locked
        self._broadcast_state()

    def on_focus_request(self, data):
        if kiosk_state.locked:
            return
        app_id = data.get('app_id')
        if not app_id:
            return
        if app_id not in kiosk_state.open_app_ids:
            kiosk_state.open_app_ids.append(app_id)
        kiosk_state.active_app_id = app_id
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

- [ ] **Step 6: Update `backend/sockets/apps.py`**

```python
from flask_socketio import Namespace
from flask import request
from sockets.middleware import authenticate_socket, clear_session


class AppsNamespace(Namespace):
    def on_connect(self, auth=None):
        session = authenticate_socket(auth or {}, request.sid)
        if session is None:
            return False

    def on_disconnect(self):
        clear_session(request.sid)
```

- [ ] **Step 7: Update `backend/tests/conftest.py` to set KIOSK_SECRET**

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('KIOSK_SECRET', 'test-kiosk-secret')

import pytest
from app import create_app
from config import TestConfig


@pytest.fixture
def flask_app():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'SOCKETIO_ASYNC_MODE': 'threading'})
    yield app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()
```

- [ ] **Step 8: Update `backend/tests/test_general_socket.py` to pass kiosk auth**

Replace every `socketio.test_client(flask_app, namespace='/general')` with:
```python
socketio.test_client(flask_app, namespace='/general', auth={'kiosk_secret': 'test-kiosk-secret'})
```

Also update the `socket_client` fixture in that file:

```python
@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/general', auth={'kiosk_secret': 'test-kiosk-secret'})
```

And update all inline socket client creations in the same file — search for `socketio.test_client` and add `auth={'kiosk_secret': 'test-kiosk-secret'}` to each one.

- [ ] **Step 9: Update `backend/tests/test_hello_world.py` socket_client fixture**

```python
@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps', auth={'kiosk_secret': 'test-kiosk-secret'})
```

Also add to `skip_pb_setup` to also mock `users.get_user` for the middleware path:

```python
@pytest.fixture(autouse=True)
def skip_pb_setup():
    with patch('pocketbase.ensure_collection'), \
         patch('sockets.middleware.users.get_user', return_value={'username': 'Tester'}):
        yield
```

- [ ] **Step 10: Run all backend tests**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: All tests PASS.

- [ ] **Step 11: Commit**

```bash
git add backend/sockets/middleware.py backend/sockets/general.py backend/sockets/apps.py backend/tests/conftest.py backend/tests/test_general_socket.py backend/tests/test_hello_world.py backend/tests/test_socket_auth.py
git commit -m "feat: socket auth middleware - reject unauthenticated connections"
```

---

### Task 6: Frontend auth library, user store, socket update

PKCE flow, token storage, user store, and updated `connectSockets`.

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/stores/user.ts`
- Modify: `frontend/src/lib/socket.ts`

- [ ] **Step 1: Create `frontend/src/lib/auth.ts`**

```typescript
const AUTHENTIK_URL = import.meta.env.VITE_AUTHENTIK_URL as string;
const APP_SLUG = import.meta.env.VITE_AUTHENTIK_APP_SLUG as string;
const CLIENT_ID = import.meta.env.VITE_AUTHENTIK_CLIENT_ID as string;

function base64url(buffer: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

function generateVerifier(): string {
  return base64url(crypto.getRandomValues(new Uint8Array(32)).buffer as ArrayBuffer);
}

async function generateChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier);
  return base64url(await crypto.subtle.digest('SHA-256', data));
}

export async function login(returnTo = '/'): Promise<void> {
  const verifier = generateVerifier();
  const challenge = await generateChallenge(verifier);
  sessionStorage.setItem('pkce_verifier', verifier);
  sessionStorage.setItem('pkce_return_to', returnTo);
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: `${location.origin}/callback`,
    scope: 'openid profile email',
    code_challenge: challenge,
    code_challenge_method: 'S256',
  });
  location.href = `${AUTHENTIK_URL}/application/o/${APP_SLUG}/authorize/?${params}`;
}

export async function handleCallback(): Promise<{ token: string; returnTo: string }> {
  const code = new URLSearchParams(location.search).get('code');
  if (!code) throw new Error('No code in callback URL');
  const verifier = sessionStorage.getItem('pkce_verifier');
  if (!verifier) throw new Error('No PKCE verifier in session');
  const returnTo = sessionStorage.getItem('pkce_return_to') ?? '/';

  const resp = await fetch(`${AUTHENTIK_URL}/application/o/${APP_SLUG}/token/`, {
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
```

- [ ] **Step 2: Create `frontend/src/lib/stores/user.ts`**

```typescript
import { writable } from 'svelte/store';

export interface User {
  username: string;
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
```

- [ ] **Step 3: Update `frontend/src/lib/socket.ts`**

```typescript
import { io } from 'socket.io-client';
import { kioskState } from './stores/kiosk';

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? '';

export const generalSocket = io(`${BASE_URL}/general`, { autoConnect: false });
export const appsSocket = io(`${BASE_URL}/apps`, { autoConnect: false });

generalSocket.on(
  'state',
  (state: { active_app_id: string | null; open_app_ids: string[]; locked: boolean }) => {
    kioskState.set({
      activeAppId: state.active_app_id,
      openAppIds: state.open_app_ids,
      locked: state.locked,
    });
  }
);

export function connectSockets(auth: Record<string, string>): void {
  generalSocket.auth = auth;
  appsSocket.auth = auth;
  generalSocket.connect();
  appsSocket.connect();
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npm run check
```
Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/auth.ts frontend/src/lib/stores/user.ts frontend/src/lib/socket.ts
git commit -m "feat: frontend auth PKCE, user store, socket auth param"
```

---

### Task 7: Frontend callback route

Exchanges the authorization code for a token, checks user existence, redirects to setup or destination.

**Files:**
- Create: `frontend/src/routes/callback/+page.svelte`

- [ ] **Step 1: Create `frontend/src/routes/callback/+page.svelte`**

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { handleCallback } from '$lib/auth';
  import { fetchUser, userStore } from '$lib/stores/user';

  let error = '';

  onMount(async () => {
    try {
      const { token, returnTo } = await handleCallback();
      const user = await fetchUser(token);
      if (!user) {
        goto(`/setup?return=${encodeURIComponent(returnTo)}`);
        return;
      }
      userStore.set(user);
      goto(returnTo);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Login fehlgeschlagen';
    }
  });
</script>

{#if error}
  <div class="error-page">
    <p>Fehler beim Login: {error}</p>
    <button onclick={() => goto('/')}>Zurück</button>
  </div>
{:else}
  <div class="loading">Einloggen...</div>
{/if}

<style>
  .loading, .error-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    color: #fff;
    font-family: sans-serif;
    background: #111;
    gap: 1rem;
  }
  button {
    padding: 0.5rem 1.5rem;
    background: #333;
    color: #fff;
    border: 1px solid #555;
    border-radius: 6px;
    cursor: pointer;
  }
</style>
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds, `build/callback/index.html` exists.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/callback/+page.svelte
git commit -m "feat: OIDC callback route"
```

---

### Task 8: Frontend setup route

Username picker shown on first login. Validates and posts to the users API.

**Files:**
- Create: `frontend/src/routes/setup/+page.svelte`

- [ ] **Step 1: Create `frontend/src/routes/setup/+page.svelte`**

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getToken, login } from '$lib/auth';
  import { createUser, userStore } from '$lib/stores/user';

  let username = '';
  let error = '';
  let saving = false;
  let returnTo = '/';

  onMount(() => {
    returnTo = $page.url.searchParams.get('return') ?? '/';
    if (!getToken()) login(returnTo);
  });

  async function submit(e: Event) {
    e.preventDefault();
    const token = getToken();
    if (!token) { login(returnTo); return; }
    saving = true;
    error = '';
    try {
      const user = await createUser(token, username.trim());
      userStore.set(user);
      goto(returnTo);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Fehler';
      saving = false;
    }
  }
</script>

<div class="setup">
  <h1>Wia hast du?</h1>
  <p>Wähl an Spitznamen (3–20 Zeichen, Buchstaben, Zahlen, Unterstrich).</p>
  <form onsubmit={submit}>
    <input
      bind:value={username}
      placeholder="z.B. MaxMustermann"
      minlength="3"
      maxlength="20"
      required
      disabled={saving}
      autocomplete="off"
    />
    {#if error}<p class="error">{error}</p>{/if}
    <button type="submit" disabled={saving || username.trim().length < 3}>
      {saving ? 'Speichern...' : 'Weiter →'}
    </button>
  </form>
</div>

<style>
  :global(body) { margin: 0; background: #111; }

  .setup {
    max-width: 400px;
    margin: 5rem auto;
    padding: 2rem;
    color: #fff;
    font-family: sans-serif;
    text-align: center;
  }
  h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
  p { color: #aaa; margin-bottom: 1.5rem; font-size: 0.95rem; }
  input {
    display: block;
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 1rem;
    border: 1px solid #444;
    border-radius: 8px;
    background: #222;
    color: #fff;
    margin-bottom: 0.75rem;
    box-sizing: border-box;
  }
  input:focus { outline: none; border-color: #1d4ed8; }
  button {
    width: 100%;
    padding: 0.75rem;
    background: #1d4ed8;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  button:disabled { opacity: 0.45; cursor: default; }
  .error { color: #f87171; font-size: 0.9rem; margin: 0.5rem 0; }
</style>
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/setup/+page.svelte
git commit -m "feat: username setup route for first-time login"
```

---

### Task 9: Wire auth into kiosk and mobile pages

Add auth guards to both pages. Kiosk uses `VITE_KIOSK_SECRET` if set; otherwise falls back to user OIDC. Mobile always uses OIDC. Display username in mobile header.

**Files:**
- Modify: `frontend/src/routes/+page.svelte`
- Modify: `frontend/src/routes/mobile/+page.svelte`

- [ ] **Step 1: Update `frontend/src/routes/+page.svelte`**

Replace only the `<script>` section (keep all styles unchanged):

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { kioskState } from '$lib/stores/kiosk';
  import { connectSockets, generalSocket } from '$lib/socket';
  import { getApp } from '$lib/appRegistry';
  import { getToken, login } from '$lib/auth';
  import { fetchUser, userStore } from '$lib/stores/user';

  let idleTimer: ReturnType<typeof setTimeout>;
  let idleKey = 0;

  function resetIdleTimer() {
    clearTimeout(idleTimer);
    idleKey += 1;
    idleTimer = setTimeout(onIdle, 10_000);
  }

  function onIdle() {
    if (!$kioskState.locked && $kioskState.openAppIds.length >= 2) {
      generalSocket.emit('carousel_next');
    }
    resetIdleTimer();
  }

  onMount(async () => {
    const kioskSecret = import.meta.env.VITE_KIOSK_SECRET as string | undefined;

    if (kioskSecret) {
      connectSockets({ kiosk_secret: kioskSecret });
    } else {
      const token = getToken();
      if (!token) {
        login(location.pathname);
        return;
      }
      const user = await fetchUser(token).catch(() => null);
      if (!user) {
        goto(`/setup?return=${encodeURIComponent(location.pathname)}`);
        return;
      }
      userStore.set(user);
      connectSockets({ token });
    }

    generalSocket.on('state', resetIdleTimer);
    resetIdleTimer();

    return () => {
      clearTimeout(idleTimer);
      generalSocket.off('state', resetIdleTimer);
    };
  });
</script>
```

- [ ] **Step 2: Update `frontend/src/routes/mobile/+page.svelte`**

Replace only the `<script>` section (keep all styles unchanged). Also add username display in the header template.

Script:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { kioskState } from '$lib/stores/kiosk';
  import { generalSocket, appsSocket, connectSockets } from '$lib/socket';
  import { apps, getApp } from '$lib/appRegistry';
  import { getToken, login } from '$lib/auth';
  import { fetchUser, userStore } from '$lib/stores/user';
  import { goto } from '$app/navigation';

  let launcherOpen = false;

  onMount(async () => {
    const token = getToken();
    if (!token) {
      login('/mobile');
      return;
    }
    const user = await fetchUser(token).catch(() => null);
    if (!user) {
      goto('/setup?return=/mobile');
      return;
    }
    userStore.set(user);
    connectSockets({ token });
  });

  function openApp(appId: string) {
    generalSocket.emit('open_app', { app_id: appId });
    launcherOpen = false;
  }

  function closeApp(appId: string) {
    generalSocket.emit('close_app', { app_id: appId });
  }

  function openInKiosk(appId: string) {
    generalSocket.emit('open_app', { app_id: appId });
  }

  function toggleLock() {
    generalSocket.emit('toggle_lock');
  }

  $: closedApps = apps.filter(a => !$kioskState.openAppIds.includes(a.id));
</script>
```

In the `<header>` template, add the username display after `<h1>`:
```svelte
<header>
  <div class="header-left">
    <h1>Beidlboard</h1>
    {#if $userStore}
      <span class="username">{$userStore.username}</span>
    {/if}
  </div>
  <div class="header-right">
    <!-- lock-btn and launcher-btn stay unchanged -->
```

Add to `<style>`:
```css
  .header-left {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
  }

  .username {
    font-size: 0.8rem;
    color: #666;
  }
```

- [ ] **Step 3: Build frontend**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 4: Rebuild Docker and smoke-test**

```bash
sudo docker compose up --build -d
```

Open `http://localhost:8080/mobile` — should redirect to Authentik login.
Open `http://localhost:8080/` — if `VITE_KIOSK_SECRET` is not set in the build, should also redirect to login.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/+page.svelte frontend/src/routes/mobile/+page.svelte
git commit -m "feat: auth guards on kiosk and mobile pages"
```

---

### Task 10: Hello world — attach sender to messages

Pass the authenticated username with saved messages. Show sender name on thought bubbles.

**Files:**
- Modify: `backend/apps/hello_world/routes.py`
- Modify: `backend/tests/test_hello_world.py`
- Modify: `frontend/src/apps/hello-world/Display.svelte`

> **Note:** Before running the backend for the first time after this task, delete the `hello_world_messages` collection in PocketBase UI (`http://localhost:8090/_/`) so it gets recreated with the new `sender` field. The collection schema was already updated in Task 1.

- [ ] **Step 1: Update `handle_update_message` to read sender from socket session**

In `backend/apps/hello_world/routes.py`, update the `handle_update_message` handler:

```python
@socketio.on('hello_world:update_message', namespace='/apps')
def handle_update_message(data):
    message = data.get('message', '').strip()
    if not message:
        return
    from sockets.middleware import get_session
    session = get_session(request.sid)
    sender = session.get('username', '') if session else ''
    _save_message(message, sender)
    msgs = _recent_messages()
    socketio.emit(
        'hello_world:messages_updated',
        {'messages': [{'text': m['text'], 'sender': m['sender']} for m in msgs]},
        namespace='/apps',
    )
```

- [ ] **Step 2: Update tests to verify sender is passed**

In `backend/tests/test_hello_world.py`, add a test:

```python
def test_sender_attached_from_session(socket_client):
    with patch('apps.hello_world.routes.requests.post', return_value=_pb_ok()), \
         patch('apps.hello_world.routes.requests.get', return_value=_pb_list(['Hoi'])), \
         patch('sockets.middleware.users.get_user', return_value={'username': 'Tester'}):
        socket_client.emit('hello_world:update_message', {'message': 'Hoi'}, namespace='/apps')
        received = socket_client.get_received('/apps')
    event = next(e for e in received if e['name'] == 'hello_world:messages_updated')
    # sender comes from session set up by authenticate_socket in the fixture
    assert 'sender' in event['args'][0]['messages'][0]
```

- [ ] **Step 3: Run backend tests**

```bash
cd backend && python -m pytest tests/test_hello_world.py -v
```
Expected: All tests PASS.

- [ ] **Step 4: Update `frontend/src/apps/hello-world/Display.svelte`**

Update the `Bubble` interface and `handleMessages` function, and add sender display:

```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';

  interface Message {
    text: string;
    sender: string;
  }

  interface Bubble {
    id: number;
    text: string;
    sender: string;
    left: number;
    top: number;
    dur: number;
    dx: number;
    dy: number;
    rot: number;
    scale: number;
  }

  let messages: Message[] = [];
  let bubbles: Bubble[] = [];
  let nextId = 0;
  let spawnTimer: ReturnType<typeof setInterval>;

  function weightedPick(): Message | null {
    if (!messages.length) return null;
    const weights = messages.map((_, i) => 1 / (i + 1));
    const total = weights.reduce((a, b) => a + b, 0);
    let r = Math.random() * total;
    for (let i = 0; i < messages.length; i++) {
      r -= weights[i];
      if (r <= 0) return messages[i];
    }
    return messages[messages.length - 1];
  }

  function spawnBubble() {
    const msg = weightedPick();
    if (!msg || bubbles.length >= 6) return;
    const id = nextId++;
    const dur = 12 + Math.random() * 7;
    bubbles = [
      ...bubbles,
      {
        id,
        text: msg.text,
        sender: msg.sender,
        left: 4 + Math.random() * 68,
        top: 10 + Math.random() * 62,
        dur,
        dx: (Math.random() - 0.5) * 110,
        dy: -(35 + Math.random() * 90),
        rot: (Math.random() - 0.5) * 8,
        scale: 0.85 + Math.random() * 0.3,
      },
    ];
    setTimeout(() => {
      bubbles = bubbles.filter(b => b.id !== id);
    }, dur * 1000);
  }

  function handleMessages(data: { messages: Message[] }) {
    const isNewMessage = data.messages[0]?.text !== messages[0]?.text;
    messages = data.messages;
    if (isNewMessage && messages.length) spawnBubble();
  }

  onMount(() => {
    appsSocket.on('hello_world:messages_updated', handleMessages);
    appsSocket.emit('hello_world:request_messages');
    spawnTimer = setInterval(spawnBubble, 3500);
    setTimeout(spawnBubble, 700);
  });

  onDestroy(() => {
    appsSocket.off('hello_world:messages_updated', handleMessages);
    clearInterval(spawnTimer);
  });
</script>

<div class="display">
  {#each bubbles as bubble (bubble.id)}
    <div
      class="bubble"
      style="
        left: {bubble.left}%;
        top: {bubble.top}%;
        --dur: {bubble.dur}s;
        --dx: {bubble.dx}px;
        --dy: {bubble.dy}px;
        --rot: {bubble.rot}deg;
        --scale: {bubble.scale};
      "
    >
      <div class="bubble-text">{bubble.text}</div>
      {#if bubble.sender}
        <div class="bubble-sender">— {bubble.sender}</div>
      {/if}
    </div>
  {/each}

  {#if messages.length === 0}
    <div class="empty">Schreib wos auf dein Handy! 💭</div>
  {/if}
</div>
```

Add to the `<style>` section (keep all existing styles, add):
```css
  .bubble-text {
    line-height: 1.45;
  }

  .bubble-sender {
    font-size: 0.75em;
    color: #555;
    margin-top: 0.3rem;
    text-align: right;
  }
```

- [ ] **Step 5: Build frontend**

```bash
cd frontend && npm run build
```
Expected: Build succeeds.

- [ ] **Step 6: Rebuild Docker and end-to-end test**

```bash
sudo docker compose up --build -d
```

1. Open `http://localhost:8080/mobile` — redirected to Authentik login
2. Log in with Authentik credentials
3. First login: redirected to `/setup`, pick a username, click "Weiter"
4. Land on mobile page, username visible in header
5. Open Hello World app
6. Send a message — appears as a thought bubble on kiosk display with your username

- [ ] **Step 7: Commit**

```bash
git add backend/apps/hello_world/routes.py backend/tests/test_hello_world.py frontend/src/apps/hello-world/Display.svelte
git commit -m "feat: attach sender username to hello_world messages"
```
