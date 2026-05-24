# Controls Redesign Spec

## Goal

Redesign the mobile controller so each user can control any open app independently of what's showing on the kiosk. Add global lock, idle auto-scroll, and app-initiated focus requests.

---

## 1. State changes

### `backend/state.py`

Add `locked: bool = False` to `KioskState`:

```python
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
```

### `frontend/src/lib/stores/kiosk.ts`

Add `locked: boolean` to `KioskState`:

```ts
export interface KioskState {
  activeAppId: string | null;
  openAppIds: string[];
  locked: boolean;
}
// initialise with locked: false
```

### `frontend/src/lib/socket.ts`

Map `locked` from server state to store:
```ts
kioskState.set({
  activeAppId: state.active_app_id,
  openAppIds: state.open_app_ids,
  locked: state.locked,
});
```

---

## 2. New `/general` socket events

### `toggle_lock` (mobile → server)

Flips `kiosk_state.locked`, broadcasts full state to all clients.

```python
def on_toggle_lock(self):
    kiosk_state.locked = not kiosk_state.locked
    self._broadcast_state()
```

### `focus_request(data: { app_id })` (app backend → server → all clients)

If not locked: sets `active_app_id` and ensures app is in `open_app_ids`, broadcasts state. If locked: no-op.

```python
def on_focus_request(self, data):
    if kiosk_state.locked:
        return
    app_id = data.get('app_id')
    if app_id and app_id not in kiosk_state.open_app_ids:
        kiosk_state.open_app_ids.append(app_id)
    kiosk_state.active_app_id = app_id
    self._broadcast_state()
```

App blueprints fire this from within their own socket handlers:

```python
# e.g. in dave_counter/routes.py
@socketio.on('dave_counter:increment', namespace='/apps')
def handle_increment(data):
    _state['count'] += 1
    socketio.emit('dave_counter:updated', {'count': _state['count']}, namespace='/apps')
    socketio.emit('focus_request', {'app_id': 'dave-counter'}, namespace='/general')
```

---

## 3. Idle auto-scroll

### Location: `frontend/src/routes/+page.svelte`

- On mount: start a 10s countdown timer
- Reset the timer on every incoming `state` event from `generalSocket`
- When timer fires:
  - If `$kioskState.locked` → do nothing, reset timer
  - If `$kioskState.openAppIds.length < 2` → do nothing, reset timer
  - Otherwise: emit `carousel_next` on `generalSocket`, reset timer

```ts
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
```

---

## 4. Mobile controller redesign

### Layout

```
Header:  [Beidlboard]           [🔓 / 🔒]  [⊞]
─────────────────────────────────────────────────
(one card per open app)
─────────────────────────────────────────────────
Card:
  [icon] [App Name]     [Open in Kiosk]
  ┌──────────────────────────────────────┐
  │  MobileControls component (if any)  │
  └──────────────────────────────────────┘
                              [Schließen]
─────────────────────────────────────────────────
(empty state when no apps are open)
```

### Launcher overlay (⊞ button)

Shows only apps **not** in `$kioskState.openAppIds`. If all apps are open, shows "Alle Apps offen". Tapping an app emits `open_app` and closes the overlay.

### Lock toggle button

- Shows 🔓 when `$kioskState.locked === false`, 🔒 when true
- Emits `toggle_lock` on `generalSocket`

### "Open in Kiosk" button

- Emits `open_app { app_id }` on `generalSocket`
- The existing `on_open_app` handler already handles the "already open, just bring to front" case

### MobileControls prop

No change — still receives `socket={appsSocket}` as a prop.

---

## 5. Files changed

| File | Change |
|------|--------|
| `backend/state.py` | Add `locked` field |
| `backend/sockets/general.py` | Add `on_toggle_lock`, `on_focus_request` |
| `backend/tests/test_general_socket.py` | Tests for new events |
| `frontend/src/lib/stores/kiosk.ts` | Add `locked` field |
| `frontend/src/lib/socket.ts` | Map `locked` from server state |
| `frontend/src/routes/+page.svelte` | Add idle auto-scroll timer |
| `frontend/src/routes/mobile/+page.svelte` | Full redesign |

No new files. No changes to app registry, app components, or `/apps` namespace.
