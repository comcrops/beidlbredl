---
name: create-beidlboard-app
description: Use when adding a new app to the beidlboard dashboard — creating Display/MobileControls components, Flask blueprint, socket handlers, and registering the app in both frontend and backend registries.
---

# Create a Beidlboard App

## Overview

Each app needs up to four things: a backend blueprint, socket handlers, a frontend Display component, and an optional MobileControls component. Both registries must be updated — the backend and frontend maintain separate lists.

## Checklist

- [ ] Backend: `backend/apps/<app_name>/` files
- [ ] Backend: entry in `APP_REGISTRY` + registered in `register_apps()`
- [ ] Frontend: `frontend/src/apps/<app-name>/` components
- [ ] Frontend: entry in `frontend/src/lib/appRegistry.ts`
- [ ] Tests for socket handlers

---

## Step 1 — Backend blueprint

`backend/apps/your_app/__init__.py` — empty file

`backend/apps/your_app/routes.py`:
```python
from flask import Blueprint
from extensions import socketio

bp = Blueprint('your_app', __name__)

# in-memory state (survives until Flask restarts)
_state = {}

# Socket events follow the convention: appid:event_name
@socketio.on('your_app:some_event', namespace='/apps')
def handle_some_event(data):
    # mutate _state, then broadcast result back
    socketio.emit('your_app:some_result', {...}, namespace='/apps')
```

**Socket event naming:** always `appid:event_name` using the app's `id` value from the registry (e.g. `dave-counter:increment`).

---

## Step 2 — Register in backend

`backend/apps/__init__.py` — add to `APP_REGISTRY`:
```python
{
    'id': 'your-app',        # kebab-case, matches frontend id
    'name': 'Dein App',      # display name (Upper-Austrian dialect welcome)
    'icon': '🎯',
    'has_mobile_controls': True,  # or False
}
```

Add to `register_apps()`:
```python
from apps.your_app.routes import bp as your_app_bp
flask_app.register_blueprint(your_app_bp, url_prefix='/api/apps/your-app')
```

---

## Step 3 — Backend tests

`backend/tests/test_your_app.py`:
```python
import pytest
from extensions import socketio
from apps.your_app.routes import _state

@pytest.fixture(autouse=True)
def reset():
    _state.clear()
    yield
    _state.clear()

@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps')

def test_some_event_broadcasts(socket_client):
    socket_client.emit('your_app:some_event', {...}, namespace='/apps')
    received = socket_client.get_received('/apps')
    assert any(e['name'] == 'your_app:some_result' for e in received)
```

Run: `cd backend && python -m pytest tests/test_your_app.py -v`

---

## Step 4 — Frontend Display component

`frontend/src/apps/your-app/Display.svelte`:
```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';

  // local reactive state
  let value = $state(...);

  function handleResult(data: { ... }) {
    value = data.something;
  }

  onMount(() => appsSocket.on('your_app:some_result', handleResult));
  onDestroy(() => appsSocket.off('your_app:some_result', handleResult));
</script>

<!-- full-viewport, no scrollbars — this fills the kiosk slot -->
<div class="display">...</div>

<style>
  .display { width: 100%; height: 100%; }
</style>
```

**Display rules:** fills its slot 100% width/height. No navigation, no close button — the kiosk display is passive.

---

## Step 5 — Frontend MobileControls component (optional)

`frontend/src/apps/your-app/MobileControls.svelte`:
```svelte
<script lang="ts">
  import type { Socket } from 'socket.io-client';

  let { socket }: { socket: Socket } = $props();

  function doSomething() {
    socket.emit('your_app:some_event', { ... });
  }
</script>

<div class="controls">
  <button onclick={doSomething}>Mach wos</button>
</div>
```

**Required prop:** `socket: Socket` — always receive the appsSocket as a prop, never import it directly (the parent passes it so the component is testable).

---

## Step 6 — Register in frontend

`frontend/src/lib/appRegistry.ts` — add to the `apps` array:
```ts
import YourAppDisplay from '../apps/your-app/Display.svelte';
import YourAppMobileControls from '../apps/your-app/MobileControls.svelte'; // if applicable

// inside apps array:
{
  id: 'your-app',           // must match backend APP_REGISTRY id
  name: 'Dein App',
  icon: '🎯',
  hasMobileControls: true,  // must match backend has_mobile_controls
  display: YourAppDisplay,
  mobileControls: YourAppMobileControls,  // omit if no mobile controls
},
```

---

## Verify

```bash
# backend tests
cd backend && python -m pytest tests/ -v

# frontend build
cd frontend && npm run build
```

The app appears in the mobile controller launcher automatically once it's in both registries. No routing changes needed.
