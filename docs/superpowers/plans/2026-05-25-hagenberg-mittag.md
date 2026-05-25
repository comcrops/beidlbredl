# Hagenberg Mittag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a kiosk app that shows today's lunch menus for 5 Hagenberg restaurants using the mittag.io embed widget, with a phone-triggered 15-second focus spotlight and today/week toggle.

**Architecture:** Frontend grid of 5 restaurant cards. A minimal backend `routes.py` (no REST endpoints, just two socket relay handlers) broadcasts focus and week-mode events to all clients. mittag.io JS SDK renders each restaurant's menu inside `<a class="mittagio">` anchors. No PocketBase, no persistent state.

**Tech Stack:** Svelte 5 runes mode, Flask-SocketIO, mittag.io embed SDK (`https://www.mittag.io/e/js`), CSS transitions

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/apps/hagenberg-mittag/restaurants.ts` | Create | Restaurant config — ids, names, mittag.at URLs |
| `frontend/src/apps/hagenberg-mittag/Display.svelte` | Create | Kiosk grid, mittag.io SDK init, focus spotlight, week mode |
| `frontend/src/apps/hagenberg-mittag/MobileControls.svelte` | Create | Phone UI — restaurant picker, today/week toggle |
| `frontend/src/lib/appRegistry.ts` | Modify | Register hagenberg-mittag entry |
| `backend/apps/hagenberg_mittag/__init__.py` | Create | Empty (package marker) |
| `backend/apps/hagenberg_mittag/routes.py` | Create | Two socket relay handlers |
| `backend/apps/__init__.py` | Modify | Add to APP_REGISTRY, import routes in register_apps() |
| `backend/tests/test_hagenberg_mittag.py` | Create | Backend socket relay tests |

---

## Task 1: Scaffold with create-beidlboard-app skill

**Files:** All of the above (created by the skill, then modified per subsequent tasks)

- [ ] **Step 1: Invoke the create-beidlboard-app skill**

  Run the skill with these parameters:
  - App id: `hagenberg-mittag`
  - App name: `Hagenberger Mittagessen`
  - Icon: `🍽️`
  - Has mobile controls: yes

  The skill creates the boilerplate `Display.svelte`, `MobileControls.svelte`, `routes.py`, `__init__.py`, and registers the app in both registries. All subsequent tasks build on top of what the skill produces.

- [ ] **Step 2: Verify scaffolding**

  ```bash
  ls frontend/src/apps/hagenberg-mittag/
  ls backend/apps/hagenberg_mittag/
  grep 'hagenberg-mittag' frontend/src/lib/appRegistry.ts
  grep 'hagenberg-mittag' backend/apps/__init__.py
  ```

  Expected: both directories exist with their files, both registries contain the app entry.

- [ ] **Step 3: Commit scaffold**

  ```bash
  git add frontend/src/apps/hagenberg-mittag/ backend/apps/hagenberg_mittag/ frontend/src/lib/appRegistry.ts backend/apps/__init__.py
  git commit -m "feat: scaffold hagenberg-mittag app"
  ```

---

## Task 2: Restaurant config

**Files:**
- Create: `frontend/src/apps/hagenberg-mittag/restaurants.ts`

- [ ] **Step 1: Create the config file**

  ```typescript
  // frontend/src/apps/hagenberg-mittag/restaurants.ts
  export interface Restaurant {
    id: string;
    name: string;
    mittagUrl: string;
  }

  export const RESTAURANTS: Restaurant[] = [
    { id: 'schlossrestaurant', name: 'Schlossrestaurant', mittagUrl: 'https://www.mittag.at/w/schlossrestaurant-hagenberg' },
    { id: 'caravento',         name: 'Caravento',         mittagUrl: 'https://www.mittag.at/r/caravento' },
    { id: 'salz-pfeffer',      name: 'Salz & Pfeffer',    mittagUrl: 'https://www.mittag.at/w/salz-pfeffer' },
    { id: 'vorstadt-wirt',     name: 'Vorstadt Wirt Chili', mittagUrl: 'https://www.mittag.at/w/vorstadt-wirt-chili' },
    { id: 'fleischerei-fuerst', name: 'Fleischerei Fürst', mittagUrl: 'https://www.mittag.at/w/fleischerei-fuerst' },
  ];
  ```

- [ ] **Step 2: Run frontend type check**

  ```bash
  cd frontend && npm run check
  ```

  Expected: no errors.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/apps/hagenberg-mittag/restaurants.ts
  git commit -m "feat: add hagenberg-mittag restaurant config"
  ```

---

## Task 3: Backend socket relay handlers

**Files:**
- Modify: `backend/apps/hagenberg_mittag/routes.py`
- Create: `backend/tests/test_hagenberg_mittag.py`

The two handlers receive `hagenberg_mittag:focus` and `hagenberg_mittag:set_week_mode` and broadcast them to all `/apps` clients. No state is stored server-side.

- [ ] **Step 1: Write the failing tests**

  Create `backend/tests/test_hagenberg_mittag.py`:

  ```python
  import pytest
  from extensions import socketio


  @pytest.fixture
  def client_a(flask_app):
      return socketio.test_client(flask_app, namespace='/apps', auth={'kiosk_secret': 'test-kiosk-secret'})


  @pytest.fixture
  def client_b(flask_app):
      return socketio.test_client(flask_app, namespace='/apps', auth={'kiosk_secret': 'test-kiosk-secret'})


  def test_focus_is_broadcast_to_all_clients(client_a, client_b):
      client_a.emit('hagenberg_mittag:focus', {'id': 'caravento'}, namespace='/apps')
      received = client_b.get_received('/apps')
      focus_events = [e for e in received if e['name'] == 'hagenberg_mittag:focus']
      assert len(focus_events) == 1
      assert focus_events[0]['args'][0]['id'] == 'caravento'


  def test_set_week_mode_is_broadcast_to_all_clients(client_a, client_b):
      client_a.emit('hagenberg_mittag:set_week_mode', {'week': True}, namespace='/apps')
      received = client_b.get_received('/apps')
      events = [e for e in received if e['name'] == 'hagenberg_mittag:set_week_mode']
      assert len(events) == 1
      assert events[0]['args'][0]['week'] is True


  def test_focus_payload_preserved(client_a, client_b):
      client_a.emit('hagenberg_mittag:focus', {'id': 'schlossrestaurant'}, namespace='/apps')
      received = client_b.get_received('/apps')
      event = next(e for e in received if e['name'] == 'hagenberg_mittag:focus')
      assert event['args'][0]['id'] == 'schlossrestaurant'
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd backend && source .venv/bin/activate && pytest tests/test_hagenberg_mittag.py -v
  ```

  Expected: FAIL — handlers don't exist yet.

- [ ] **Step 3: Implement the socket handlers**

  Replace the contents of `backend/apps/hagenberg_mittag/routes.py` with:

  ```python
  from flask import Blueprint
  from extensions import socketio

  bp = Blueprint('hagenberg_mittag', __name__)


  @socketio.on('hagenberg_mittag:focus', namespace='/apps')
  def handle_focus(data):
      socketio.emit('hagenberg_mittag:focus', data, namespace='/apps')


  @socketio.on('hagenberg_mittag:set_week_mode', namespace='/apps')
  def handle_set_week_mode(data):
      socketio.emit('hagenberg_mittag:set_week_mode', data, namespace='/apps')
  ```

- [ ] **Step 4: Ensure routes are imported in register_apps()**

  Open `backend/apps/__init__.py`. Verify that `register_apps()` imports `hagenberg_mittag` (the scaffold skill should have done this). It must contain:

  ```python
  from apps.hagenberg_mittag.routes import bp as hagenberg_mittag_bp
  flask_app.register_blueprint(hagenberg_mittag_bp, url_prefix='/api/apps/hagenberg-mittag')
  ```

  If it does not exist yet, add those two lines inside `register_apps()`.

- [ ] **Step 5: Run tests to verify they pass**

  ```bash
  cd backend && pytest tests/test_hagenberg_mittag.py -v
  ```

  Expected: all 3 tests PASS.

- [ ] **Step 6: Run full test suite to check for regressions**

  ```bash
  cd backend && pytest tests/ -v
  ```

  Expected: all tests pass.

- [ ] **Step 7: Commit**

  ```bash
  git add backend/apps/hagenberg_mittag/routes.py backend/apps/__init__.py backend/tests/test_hagenberg_mittag.py
  git commit -m "feat: add hagenberg-mittag socket relay handlers"
  ```

---

## Task 4: Display.svelte — grid layout + mittag.io SDK

**Files:**
- Modify: `frontend/src/apps/hagenberg-mittag/Display.svelte`

This task wires up the restaurant grid and the mittag.io embed SDK. The SDK is loaded dynamically so it can be reloaded when week mode changes.

- [ ] **Step 1: Replace Display.svelte with the grid + SDK implementation**

  ```svelte
  <script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { appsSocket } from '$lib/socket';
    import { RESTAURANTS } from './restaurants';

    let focusedId = $state<string | null>(null);
    let weekMode = $state(false);
    let widgetKey = $state(0);
    let countdown = $state(0);
    let countdownTimer: ReturnType<typeof setInterval> | null = null;

    function loadSdk() {
      const existing = document.querySelector('script[src*="mittag.io/e/js"]');
      if (existing) existing.remove();
      const s = document.createElement('script');
      s.src = 'https://www.mittag.io/e/js';
      document.head.appendChild(s);
    }

    $effect(() => {
      // re-runs after DOM update whenever widgetKey changes
      widgetKey;
      loadSdk();
    });

    function clearFocus() {
      focusedId = null;
      if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
    }

    function startFocus(id: string) {
      focusedId = id;
      countdown = 15;
      if (countdownTimer) clearInterval(countdownTimer);
      countdownTimer = setInterval(() => {
        countdown--;
        if (countdown <= 0) clearFocus();
      }, 1000);
    }

    function handleFocus(data: { id: string }) { startFocus(data.id); }
    function handleSetWeekMode(data: { week: boolean }) {
      weekMode = data.week;
      widgetKey++;
    }

    onMount(() => {
      appsSocket.on('hagenberg_mittag:focus', handleFocus);
      appsSocket.on('hagenberg_mittag:set_week_mode', handleSetWeekMode);
    });

    onDestroy(() => {
      appsSocket.off('hagenberg_mittag:focus', handleFocus);
      appsSocket.off('hagenberg_mittag:set_week_mode', handleSetWeekMode);
      clearFocus();
    });
  </script>

  <div class="display">
    {#if focusedId}
      <div class="backdrop" onclick={clearFocus}></div>
    {/if}

    <div class="grid">
      {#each RESTAURANTS as r (r.id)}
        <div
          class="card"
          class:focused={focusedId === r.id}
          class:dimmed={focusedId !== null && focusedId !== r.id}
        >
          <div class="card-header">
            <span class="restaurant-name">{r.name}</span>
            {#if focusedId === r.id}
              <span class="countdown">{countdown}s</span>
            {/if}
          </div>
          <div class="widget-wrap">
            {#key widgetKey}
              <a
                class="mittagio"
                href={r.mittagUrl}
                data-minimal
                data-week={weekMode ? '' : undefined}
              >{r.name} Mittagessen</a>
            {/key}
          </div>
        </div>
      {/each}
    </div>
  </div>

  <style>
    .display {
      position: relative;
      width: 100%;
      height: 100%;
      background: #111;
      color: #fff;
      font-family: sans-serif;
      overflow: hidden;
    }

    .backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.65);
      z-index: 5;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      grid-template-rows: repeat(2, 1fr);
      gap: 0.75rem;
      padding: 0.75rem;
      height: 100%;
      box-sizing: border-box;
    }

    .card {
      background: #1a1a1a;
      border-radius: 10px;
      padding: 0.6rem;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: opacity 0.3s ease, transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
      position: relative;
      z-index: 1;
    }

    .card.focused {
      position: fixed;
      inset: 5%;
      z-index: 10;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
      transition: none;
    }

    .card.dimmed {
      opacity: 0.25;
      transform: scale(0.97);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.4rem;
      flex-shrink: 0;
    }

    .restaurant-name {
      font-size: clamp(0.7rem, 1.2vw, 1rem);
      font-weight: 700;
      color: #eee;
    }

    .countdown {
      font-size: 0.75rem;
      color: #f59e0b;
      font-weight: 600;
    }

    .widget-wrap {
      flex: 1;
      overflow: auto;
      min-height: 0;
    }

    /* mittag.io widget overrides — keep readable on dark bg */
    .widget-wrap :global(body),
    .widget-wrap :global(*) {
      color-scheme: light;
    }
  </style>
  ```

- [ ] **Step 2: Run frontend type check**

  ```bash
  cd frontend && npm run check
  ```

  Expected: no errors.

- [ ] **Step 3: Add per-card empty state detection**

  The mittag.io SDK takes a moment to render. After a delay, check each card's widget height. Cards whose widget rendered nothing (SDK failed or no menu today) show a fallback message.

  Add an `emptyCards` set to the script block and a `checkEmpty` function called after SDK load:

  ```svelte
  <!-- add to <script> block, after widgetKey declaration -->
  let emptyCards = $state(new Set<string>());

  function checkEmpty() {
    const newEmpty = new Set<string>();
    document.querySelectorAll<HTMLElement>('.widget-wrap').forEach((wrap, i) => {
      if (wrap.scrollHeight < 40) newEmpty.add(RESTAURANTS[i]?.id ?? '');
    });
    emptyCards = newEmpty;
  }

  // modify loadSdk() to schedule empty check after load
  function loadSdk() {
    const existing = document.querySelector('script[src*="mittag.io/e/js"]');
    if (existing) existing.remove();
    const s = document.createElement('script');
    s.src = 'https://www.mittag.io/e/js';
    s.onload = () => setTimeout(checkEmpty, 3000);
    document.head.appendChild(s);
  }
  ```

  Add the empty-state overlay inside `.widget-wrap` in the template, after the `<a>` anchor:

  ```svelte
  <!-- inside .widget-wrap, after the {#key widgetKey} block -->
  {#if emptyCards.has(r.id)}
    <div class="empty-state">Koa Mittagessen heut 🍺</div>
  {/if}
  ```

  Add to `<style>`:

  ```css
  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-size: clamp(0.8rem, 1.5vw, 1.1rem);
    color: rgba(255, 255, 255, 0.35);
    text-align: center;
    padding: 1rem;
  }
  ```

- [ ] **Step 4: Run frontend type check**

  ```bash
  cd frontend && npm run check
  ```

  Expected: no errors.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/apps/hagenberg-mittag/Display.svelte
  git commit -m "feat: add hagenberg-mittag display grid with mittag.io SDK"
  ```

---

## Task 5: MobileControls.svelte

**Files:**
- Modify: `frontend/src/apps/hagenberg-mittag/MobileControls.svelte`

The phone UI lets users pick a restaurant to spotlight and toggle today/week view. It listens to the same socket events as Display to stay in sync across multiple phones.

- [ ] **Step 1: Replace MobileControls.svelte**

  ```svelte
  <script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import type { Socket } from 'socket.io-client';
    import { RESTAURANTS } from './restaurants';

    let { socket }: { socket: Socket } = $props();

    let focusedId = $state<string | null>(null);
    let weekMode = $state(false);

    function focus(id: string) {
      socket.emit('hagenberg_mittag:focus', { id });
    }

    function toggleWeek() {
      const next = !weekMode;
      socket.emit('hagenberg_mittag:set_week_mode', { week: next });
    }

    function handleFocus(data: { id: string }) { focusedId = data.id; setTimeout(() => { focusedId = null; }, 15000); }
    function handleSetWeekMode(data: { week: boolean }) { weekMode = data.week; }

    onMount(() => {
      socket.on('hagenberg_mittag:focus', handleFocus);
      socket.on('hagenberg_mittag:set_week_mode', handleSetWeekMode);
    });

    onDestroy(() => {
      socket.off('hagenberg_mittag:focus', handleFocus);
      socket.off('hagenberg_mittag:set_week_mode', handleSetWeekMode);
    });
  </script>

  <div class="controls">
    <div class="section-label">Restaurant fokussieren</div>
    <div class="restaurant-list">
      {#each RESTAURANTS as r (r.id)}
        <button
          class="restaurant-btn"
          class:active={focusedId === r.id}
          onclick={() => focus(r.id)}
        >
          {r.name}
        </button>
      {/each}
    </div>

    <div class="divider"></div>

    <div class="week-toggle">
      <span class="toggle-label">{weekMode ? 'Ganze Wochen' : 'Heut'}</span>
      <button class="toggle-btn" onclick={toggleWeek}>
        {weekMode ? 'Auf heut wechseln' : 'Ganze Wochn zeigen'}
      </button>
    </div>
  </div>

  <style>
    .controls {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      padding: 0.5rem;
    }

    .section-label {
      font-size: 0.8rem;
      color: #aaa;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .restaurant-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .restaurant-btn {
      padding: 0.65rem 1rem;
      background: #222;
      color: #eee;
      border: 1px solid #333;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.95rem;
      text-align: left;
      transition: background 0.15s;
    }

    .restaurant-btn.active {
      background: #2d6a4f;
      border-color: #3d8a6f;
      color: #fff;
    }

    .divider {
      height: 1px;
      background: #333;
    }

    .week-toggle {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
    }

    .toggle-label {
      font-size: 0.9rem;
      color: #ccc;
    }

    .toggle-btn {
      padding: 0.5rem 1rem;
      background: #333;
      color: #fff;
      border: 1px solid #555;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.85rem;
      white-space: nowrap;
    }
  </style>
  ```

- [ ] **Step 2: Run frontend type check**

  ```bash
  cd frontend && npm run check
  ```

  Expected: no errors. If you see "Property 'socket' does not exist" errors, ensure the `$props()` destructuring matches the `AppDefinition.mobileControls` component contract (receives `socket: Socket`).

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/apps/hagenberg-mittag/MobileControls.svelte
  git commit -m "feat: add hagenberg-mittag mobile controls"
  ```

---

## Task 6: Check and update APP_REGISTRY entry

**Files:**
- Modify: `backend/apps/__init__.py`

The scaffold skill may have created the APP_REGISTRY entry already. This task verifies it is complete and correct.

- [ ] **Step 1: Verify APP_REGISTRY entry**

  Open `backend/apps/__init__.py`. The entry should look exactly like this:

  ```python
  {
      'id': 'hagenberg-mittag',
      'name': 'Hagenberger Mittagessen',
      'icon': '🍽️',
      'has_mobile_controls': True,
  },
  ```

  Fix any discrepancies (wrong name, wrong icon, wrong id).

- [ ] **Step 2: Verify appRegistry.ts entry**

  Open `frontend/src/lib/appRegistry.ts`. The entry should look like:

  ```typescript
  {
    id: 'hagenberg-mittag',
    name: 'Hagenberger Mittagessen',
    icon: '🍽️',
    hasMobileControls: true,
    display: HagenbergMittagDisplay,
    mobileControls: HagenbergMittagMobileControls,
  },
  ```

  Verify the imports for `HagenbergMittagDisplay` and `HagenbergMittagMobileControls` are present at the top of the file.

- [ ] **Step 3: Run backend tests**

  ```bash
  cd backend && pytest tests/test_app_registry.py -v
  ```

  Expected: all pass.

- [ ] **Step 4: Commit any fixes**

  ```bash
  git add backend/apps/__init__.py frontend/src/lib/appRegistry.ts
  git commit -m "fix: ensure hagenberg-mittag registry entries are correct"
  ```

  (Skip commit if no changes were needed.)

---

## Task 7: CSP — allow mittag.io

**Files:**
- Check nginx config for Content-Security-Policy headers

The mittag.io JS SDK fetches content and renders iframes. If nginx sets a restrictive CSP, the SDK will be blocked.

- [ ] **Step 1: Find the nginx config**

  ```bash
  find . -name '*.conf' | grep -i nginx
  cat nginx/default.conf 2>/dev/null || cat nginx.conf 2>/dev/null || find . -name 'nginx.conf'
  ```

- [ ] **Step 2: Check for Content-Security-Policy header**

  Look for `Content-Security-Policy` or `add_header` lines in the nginx config. If a CSP header is set, add `https://www.mittag.io https://www.mittag.at` to:
  - `script-src` (for the SDK script)
  - `frame-src` or `child-src` (for any iframes the widget creates)
  - `connect-src` (for XHR/fetch calls the SDK makes)

  If no CSP header is set, skip this task — no action needed.

- [ ] **Step 3: Rebuild nginx if config was changed**

  ```bash
  sudo docker compose up --build -d nginx
  ```

- [ ] **Step 4: Commit CSP changes if any**

  ```bash
  git add nginx/
  git commit -m "fix: allow mittag.io in CSP for hagenberg-mittag widget"
  ```

---

## Task 8: Manual verification

- [ ] **Step 1: Start the stack**

  ```bash
  sudo docker compose up --build -d
  ```

- [ ] **Step 2: Open the kiosk view**

  Navigate to `http://localhost:8080` in a browser. Open the "Hagenberger Mittagessen" app from the carousel. Verify:
  - 5 restaurant cards appear in a grid
  - mittag.io widgets load inside each card (may take a second for the SDK JS to execute)
  - If it's a weekday, at least some menus should show content

- [ ] **Step 3: Test focus spotlight**

  Open the phone UI in another browser tab. Tap a restaurant name. Verify:
  - The selected card animates to fill most of the screen on the kiosk view
  - Other cards dim
  - A countdown timer shows (15 → 0)
  - After 15 seconds the card returns to grid
  - Tapping the backdrop dismisses it early

- [ ] **Step 4: Test week mode toggle**

  On the phone UI, press "Ganze Wochn zeigen". Verify:
  - The button label changes to "Auf heut wechseln" on the phone
  - The mittag.io widgets reload and show the full week view on the kiosk
  - Pressing again switches back to today view

- [ ] **Step 5: Test multi-phone sync**

  Open the phone UI in two tabs. Trigger focus from tab 1. Verify tab 2 also shows the focused restaurant as highlighted.

- [ ] **Step 6: Commit any fixes found during manual testing**

  ```bash
  git add -p
  git commit -m "fix: <describe what was fixed>"
  ```
