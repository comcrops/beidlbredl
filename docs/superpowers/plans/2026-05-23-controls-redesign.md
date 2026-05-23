# Controls Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-app independent mobile controls, a global lock, idle auto-scroll, and app-initiated focus requests to the kiosk.

**Architecture:** `locked` is added to the Flask `KioskState` singleton and broadcast in every `state` event. Two new `/general` socket events (`toggle_lock`, `focus_request`) mutate that field. The SvelteKit frontend maps `locked` into the store; the kiosk page runs a client-side 10-second idle timer that emits `carousel_next`; the mobile controller is fully rewritten to show one card per open app instead of only the active app.

**Tech Stack:** Python/Flask-SocketIO (backend), SvelteKit 5 + Svelte stores (frontend), pytest + socketio.test_client (backend tests), `npm run build` (frontend type check)

---

## File Map

| File | Change |
|------|--------|
| `backend/state.py` | Add `locked: bool = False` field + include in `to_dict` |
| `backend/sockets/general.py` | Add `on_toggle_lock`, `on_focus_request` methods |
| `backend/tests/test_general_socket.py` | Update fixture to reset `locked`; add 4 new tests |
| `frontend/src/lib/stores/kiosk.ts` | Add `locked: boolean` to interface + initial value |
| `frontend/src/lib/socket.ts` | Map `state.locked` when updating the store |
| `frontend/src/routes/+page.svelte` | Add idle auto-scroll timer |
| `frontend/src/routes/mobile/+page.svelte` | Full redesign: open-app cards, lock button, filtered launcher |

---

## Task 1: Add `locked` to backend KioskState

**Files:**
- Modify: `backend/state.py`
- Modify: `backend/tests/test_general_socket.py`

- [ ] **Step 1: Write the failing test**

Add `assert data['locked'] is False` to the existing connect test, and update the `reset_state` fixture to also reset `kiosk_state.locked`. Open `backend/tests/test_general_socket.py` and replace the fixture and the connect test with:

```python
@pytest.fixture(autouse=True)
def reset_state():
    kiosk_state.active_app_id = None
    kiosk_state.open_app_ids = []
    kiosk_state.locked = False
    yield
    kiosk_state.active_app_id = None
    kiosk_state.open_app_ids = []
    kiosk_state.locked = False


def test_connect_receives_initial_state(socket_client):
    received = socket_client.get_received('/general')
    assert len(received) == 1
    assert received[0]['name'] == 'state'
    data = received[0]['args'][0]
    assert data['active_app_id'] is None
    assert data['open_app_ids'] == []
    assert data['locked'] is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_general_socket.py::test_connect_receives_initial_state -v
```

Expected: FAIL — `KeyError: 'locked'` (field not in `to_dict` yet)

- [ ] **Step 3: Update `backend/state.py`**

Replace the entire file with:

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KioskState:
    active_app_id: Optional[str] = None
    open_app_ids: list[str] = field(default_factory=list)
    locked: bool = False

    def to_dict(self) -> dict:
        return {
            'active_app_id': self.active_app_id,
            'open_app_ids': self.open_app_ids,
            'locked': self.locked,
        }


kiosk_state = KioskState()
```

- [ ] **Step 4: Run all backend tests to verify they pass**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/state.py backend/tests/test_general_socket.py
git commit -m "feat: add locked field to KioskState"
```

---

## Task 2: Add `toggle_lock` and `focus_request` socket events

**Files:**
- Modify: `backend/sockets/general.py`
- Modify: `backend/tests/test_general_socket.py`

- [ ] **Step 1: Write the failing tests**

Append these four tests to `backend/tests/test_general_socket.py`:

```python
def test_toggle_lock_sets_locked_true(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('toggle_lock', namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['locked'] is True


def test_toggle_lock_flips_back_to_false(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('toggle_lock', namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('toggle_lock', namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['locked'] is False


def test_focus_request_sets_active_app_and_opens_it(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('focus_request', {'app_id': 'rot-app'}, namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['active_app_id'] == 'rot-app'
    assert 'rot-app' in state_event['args'][0]['open_app_ids']


def test_focus_request_no_op_when_locked(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('toggle_lock', namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('focus_request', {'app_id': 'rot-app'}, namespace='/general')
    received = socket_client.get_received('/general')
    assert not any(e['name'] == 'state' for e in received)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_general_socket.py::test_toggle_lock_sets_locked_true tests/test_general_socket.py::test_focus_request_sets_active_app_and_opens_it -v
```

Expected: FAIL — `AttributeError` (methods don't exist yet)

- [ ] **Step 3: Add the two handlers to `backend/sockets/general.py`**

Add these two methods to `GeneralNamespace` (before `_carousel_step`):

```python
def on_toggle_lock(self):
    kiosk_state.locked = not kiosk_state.locked
    self._broadcast_state()

def on_focus_request(self, data):
    if kiosk_state.locked:
        return
    app_id = data.get('app_id')
    if app_id and app_id not in kiosk_state.open_app_ids:
        kiosk_state.open_app_ids.append(app_id)
    kiosk_state.active_app_id = app_id
    self._broadcast_state()
```

The full file should now look like:

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

    def on_toggle_lock(self):
        kiosk_state.locked = not kiosk_state.locked
        self._broadcast_state()

    def on_focus_request(self, data):
        if kiosk_state.locked:
            return
        app_id = data.get('app_id')
        if app_id and app_id not in kiosk_state.open_app_ids:
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

- [ ] **Step 4: Run all backend tests**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sockets/general.py backend/tests/test_general_socket.py
git commit -m "feat: add toggle_lock and focus_request socket events"
```

---

## Task 3: Add `locked` to frontend store and socket mapping

**Files:**
- Modify: `frontend/src/lib/stores/kiosk.ts`
- Modify: `frontend/src/lib/socket.ts`

- [ ] **Step 1: Update `frontend/src/lib/stores/kiosk.ts`**

Replace the entire file with:

```ts
import { writable } from 'svelte/store';

export interface KioskState {
  activeAppId: string | null;
  openAppIds: string[];
  locked: boolean;
}

export const kioskState = writable<KioskState>({
  activeAppId: null,
  openAppIds: [],
  locked: false,
});
```

- [ ] **Step 2: Update `frontend/src/lib/socket.ts`**

Replace the entire file with:

```ts
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

export function connectSockets(): void {
  generalSocket.connect();
  appsSocket.connect();
}
```

- [ ] **Step 3: Verify no type errors**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/stores/kiosk.ts frontend/src/lib/socket.ts
git commit -m "feat: add locked field to frontend KioskState store"
```

---

## Task 4: Add idle auto-scroll timer to kiosk page

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Update the `<script>` block in `frontend/src/routes/+page.svelte`**

Replace only the `<script>` block (lines 1–10). The template and `<style>` sections stay unchanged:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { kioskState } from '$lib/stores/kiosk';
  import { connectSockets, generalSocket } from '$lib/socket';
  import { getApp } from '$lib/appRegistry';

  let idleTimer: ReturnType<typeof setTimeout>;

  function resetIdleTimer() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(onIdle, 10_000);
  }

  function onIdle() {
    if (!$kioskState.locked && $kioskState.openAppIds.length >= 2) {
      generalSocket.emit('carousel_next');
    }
    resetIdleTimer();
  }

  onMount(() => {
    connectSockets();
    generalSocket.on('state', resetIdleTimer);
    resetIdleTimer();
    return () => clearTimeout(idleTimer);
  });
</script>
```

The full file after this change (template + style unchanged):

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { kioskState } from '$lib/stores/kiosk';
  import { connectSockets, generalSocket } from '$lib/socket';
  import { getApp } from '$lib/appRegistry';

  let idleTimer: ReturnType<typeof setTimeout>;

  function resetIdleTimer() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(onIdle, 10_000);
  }

  function onIdle() {
    if (!$kioskState.locked && $kioskState.openAppIds.length >= 2) {
      generalSocket.emit('carousel_next');
    }
    resetIdleTimer();
  }

  onMount(() => {
    connectSockets();
    generalSocket.on('state', resetIdleTimer);
    resetIdleTimer();
    return () => clearTimeout(idleTimer);
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

  {#if $kioskState.openAppIds.length > 0}
    <div class="carousel-bar">
      {#each $kioskState.openAppIds as appId (appId)}
        {@const app = getApp(appId)}
        {#if app}
          <div class="carousel-pill" class:active={appId === $kioskState.activeAppId}>
            <span class="pill-icon">{app.icon}</span>
            <span class="pill-name">{app.name}</span>
          </div>
        {/if}
      {/each}
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
    display: flex;
    flex-direction: column;
  }

  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-size: 1.5rem;
    color: #666;
  }

  .carousel-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.6rem 1rem;
    background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 100%);
    z-index: 5;
    pointer-events: none;
  }

  .carousel-pill {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.15);
    font-size: 0.8rem;
    color: rgba(255,255,255,0.5);
    transition: background 0.2s, color 0.2s, border-color 0.2s;
  }

  .carousel-pill.active {
    background: rgba(255,255,255,0.2);
    border-color: rgba(255,255,255,0.5);
    color: #fff;
  }

  .pill-icon {
    font-size: 0.9rem;
    line-height: 1;
  }

  .pill-name {
    font-size: 0.75rem;
    letter-spacing: 0.02em;
  }
</style>
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/+page.svelte
git commit -m "feat: add idle auto-scroll timer to kiosk page"
```

---

## Task 5: Redesign mobile controller

**Files:**
- Modify: `frontend/src/routes/mobile/+page.svelte` (full rewrite)

- [ ] **Step 1: Replace the entire file with the new design**

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { kioskState } from '$lib/stores/kiosk';
  import { generalSocket, appsSocket, connectSockets } from '$lib/socket';
  import { apps, getApp } from '$lib/appRegistry';

  let launcherOpen = false;

  onMount(() => {
    connectSockets();
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

<div class="mobile-controller">
  <header>
    <h1>Beidlboard</h1>
    <div class="header-right">
      <button
        class="lock-btn"
        class:locked={$kioskState.locked}
        on:click={toggleLock}
        aria-label={$kioskState.locked ? 'Entsperren' : 'Sperren'}
      >
        {$kioskState.locked ? '🔒' : '🔓'}
      </button>
      <button class="launcher-btn" on:click={() => (launcherOpen = true)} aria-label="Apps öffnen">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <rect x="2" y="2" width="6" height="6" rx="1.5" />
          <rect x="12" y="2" width="6" height="6" rx="1.5" />
          <rect x="2" y="12" width="6" height="6" rx="1.5" />
          <rect x="12" y="12" width="6" height="6" rx="1.5" />
        </svg>
      </button>
    </div>
  </header>

  <div class="app-cards">
    {#each $kioskState.openAppIds as appId (appId)}
      {@const app = getApp(appId)}
      {#if app}
        <div class="app-card">
          <div class="card-header">
            <span class="app-identity">{app.icon} {app.name}</span>
            <div class="card-actions">
              <button class="kiosk-btn" on:click={() => openInKiosk(appId)}>Am Kiosk zeigen</button>
              <button class="close-btn" on:click={() => closeApp(appId)}>Schließen</button>
            </div>
          </div>
          {#if app.hasMobileControls && app.mobileControls}
            <div class="card-controls">
              <svelte:component this={app.mobileControls} socket={appsSocket} />
            </div>
          {/if}
        </div>
      {/if}
    {/each}

    {#if $kioskState.openAppIds.length === 0}
      <div class="empty-state">
        <p>Koa App offen. Tipp ⊞ zum Aufmachen!</p>
      </div>
    {/if}
  </div>
</div>

<!-- Launcher overlay -->
{#if launcherOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="backdrop" on:click={() => (launcherOpen = false)}></div>
  <div class="launcher-sheet">
    <div class="sheet-handle"></div>
    <div class="sheet-header">
      <span>Apps</span>
      <button class="close-sheet-btn" on:click={() => (launcherOpen = false)}>✕</button>
    </div>
    <div class="app-list">
      {#if closedApps.length === 0}
        <p class="all-open">Alle Apps offen</p>
      {:else}
        {#each closedApps as app}
          <div class="app-item">
            <span class="app-label">{app.icon} {app.name}</span>
            <button class="open-btn" on:click={() => openApp(app.id)}>Öffnen</button>
          </div>
        {/each}
      {/if}
    </div>
  </div>
{/if}

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

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .lock-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.25rem;
    height: 2.25rem;
    background: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    font-size: 1.1rem;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    flex-shrink: 0;
  }

  .lock-btn.locked {
    background: #3a2a1a;
    border-color: #8a5a2a;
  }

  .lock-btn:hover {
    background: #333;
  }

  .launcher-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.25rem;
    height: 2.25rem;
    background: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    color: #ccc;
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.15s, color 0.15s;
  }

  .launcher-btn:hover {
    background: #333;
    color: #fff;
  }

  /* App cards */

  .app-cards {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .app-card {
    background: #242424;
    border: 1px solid #333;
    border-radius: 12px;
    overflow: hidden;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .app-identity {
    font-size: 1rem;
    font-weight: 600;
    color: #fff;
  }

  .card-actions {
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .kiosk-btn {
    padding: 0.35rem 0.75rem;
    background: #1d4ed8;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    transition: opacity 0.15s;
    white-space: nowrap;
  }

  .kiosk-btn:hover {
    opacity: 0.85;
  }

  .close-btn {
    padding: 0.35rem 0.75rem;
    background: #6a2d2d;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    transition: opacity 0.15s;
    white-space: nowrap;
  }

  .close-btn:hover {
    opacity: 0.85;
  }

  .card-controls {
    padding: 0 1rem 1rem;
  }

  .empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #555;
    font-size: 1rem;
  }

  /* Launcher overlay */

  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(2px);
    z-index: 10;
    animation: fade-in 0.2s ease;
  }

  .launcher-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    max-height: 70vh;
    background: #222;
    border-radius: 16px 16px 0 0;
    border-top: 1px solid #333;
    z-index: 11;
    display: flex;
    flex-direction: column;
    animation: slide-up 0.25s cubic-bezier(0.32, 0.72, 0, 1);
  }

  .sheet-handle {
    width: 36px;
    height: 4px;
    background: #444;
    border-radius: 2px;
    margin: 0.75rem auto 0;
    flex-shrink: 0;
  }

  .sheet-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.25rem 0.5rem;
    flex-shrink: 0;
  }

  .sheet-header span {
    font-size: 1rem;
    font-weight: 600;
    color: #fff;
  }

  .close-sheet-btn {
    background: none;
    border: none;
    color: #777;
    font-size: 1rem;
    cursor: pointer;
    padding: 0.25rem;
    line-height: 1;
  }

  .close-sheet-btn:hover {
    color: #fff;
  }

  .app-list {
    overflow-y: auto;
    padding: 0 1.25rem 1.5rem;
  }

  .all-open {
    text-align: center;
    color: #666;
    padding: 1.5rem 0;
    font-size: 0.95rem;
  }

  .app-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 0;
    border-bottom: 1px solid #2e2e2e;
  }

  .app-item:last-child {
    border-bottom: none;
  }

  .app-label {
    font-size: 1rem;
  }

  .open-btn {
    padding: 0.4rem 1rem;
    background: #2d6a4f;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: opacity 0.15s;
  }

  .open-btn:hover {
    opacity: 0.85;
  }

  @keyframes fade-in {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  @keyframes slide-up {
    from { transform: translateY(100%); }
    to   { transform: translateY(0); }
  }
</style>
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/mobile/+page.svelte
git commit -m "feat: redesign mobile controller with per-app cards and lock button"
```
