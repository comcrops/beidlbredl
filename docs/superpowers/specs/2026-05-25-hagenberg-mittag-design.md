# Hagenberg Mittag — Design Spec

**Date:** 2026-05-25  
**Status:** Approved

## Overview

A beidlbredl kiosk app that displays lunch menus for 5 Hagenberg restaurants using the official mittag.io embed widget. The kiosk shows all restaurants in a grid; phone users can spotlight a single restaurant for 15 seconds or toggle today/week view.

## Restaurants

| Name | mittag.at slug | URL type |
|---|---|---|
| Schlossrestaurant Hagenberg | `schlossrestaurant-hagenberg` | `/w/` |
| Caravento | `caravento` | `/r/` |
| Salz & Pfeffer | `salz-pfeffer` | `/w/` |
| Vorstadt Wirt Chili | `vorstadt-wirt-chili` | `/w/` |
| Fleischerei Fürst | `fleischerei-fuerst` | `/w/` |

## Architecture

**Frontend-only app.** No Flask Blueprint, no socket handlers in the backend. The only backend change is adding the entry to `APP_REGISTRY` in `backend/apps/__init__.py`.

Frontend files:
- `frontend/src/apps/hagenberg-mittag/Display.svelte`
- `frontend/src/apps/hagenberg-mittag/MobileControls.svelte`
- Entry added to `frontend/src/lib/appRegistry.ts`

App registry entry:
```
id: 'hagenberg-mittag'
name: 'Hagenberger Mittagessen'
icon: '🍽️'
has_mobile_controls: true
```

## Data Fetching

Uses the **mittag.io embed widget** — the official external embedding system.

- SDK loaded from `https://www.mittag.io/e/js` via `<svelte:head>` in Display.svelte
- Each restaurant rendered as `<a class="mittagio" href="https://www.mittag.at/{type}/{slug}">` with `data-minimal` attribute
- `data-week` attribute present when week mode is active
- Widget initializes itself client-side; no backend scraping needed

On week mode toggle, widgets are re-initialized by destroying and recreating the anchor elements (SDK reads attributes at init time).

## Display Layout (Kiosk)

- CSS grid: 3 columns × 2 rows (5 cards + 1 empty cell, or balanced layout)
- Each card: restaurant name header + mittag.io widget
- Default state: all 5 cards equal size, today's menu

**Focus spotlight:**
- Triggered by phone via socket event
- Targeted card animates to foreground: CSS `transform: scale()` + overlay backdrop
- Duration: 15 seconds, then auto-returns to grid with reverse animation
- Retrigger on same card resets the 15s timer
- Uses CSS transitions (not JS animation libraries)

**Empty state per card:**
- If the widget renders no menu content (weekend / restaurant closed), show a friendly message in dialect: *"Koa Mittagessen heut 🍺"*
- Detected by observing the rendered widget DOM; fallback timeout if detection is unreliable

## Mobile Controls

`MobileControls.svelte` receives `socket: Socket` prop.

UI elements:
1. **Restaurant buttons** — 5 tappable cards, one per restaurant. Tapping emits `hagenberg_mittag:focus`. Active focus is highlighted with a countdown indicator.
2. **Today/Week toggle** — switch that emits `hagenberg_mittag:set_week_mode`.
3. **Status indicator** — shows currently focused restaurant name, or "Alle" if no focus active.

## Socket Events (namespace `/apps`)

All events are on the `/apps` namespace, following the `appid:event_name` convention.

| Event | Direction | Payload | Description |
|---|---|---|---|
| `hagenberg_mittag:focus` | phone → server → all | `{ id: string }` | Spotlight a restaurant for 15s |
| `hagenberg_mittag:set_week_mode` | phone → server → all | `{ week: boolean }` | Switch today/week view |
| `hagenberg_mittag:state` | server → all | `{ focused_id: string \| null, week_mode: boolean }` | Full state sync |

Since this is frontend-only, socket relay is handled via the existing `/apps` namespace broadcast pattern. State (`focused_id`, `week_mode`) lives in the Display component's reactive state and is synced to all clients via broadcasts.

**Note:** Because there is no backend handler, the phone emits directly and Display listens. Both Display and MobileControls subscribe to `hagenberg_mittag:state` for sync. The phone emits events; Display processes them and re-broadcasts state — OR both components independently listen to the same events. The simpler model: all clients (kiosk + phones) receive the same events; Display is authoritative for countdown timing.

## State Management

In-memory only — no PocketBase, no persistence across restarts.

- `focused_id: string | null` — which restaurant is spotlit (null = grid view)
- `week_mode: boolean` — false = today, true = full week
- Countdown timer managed in Display with `setInterval`, clears on defocus or retrigger

## Implementation Notes

- Use the `create-beidlboard-app` skill when scaffolding the files
- Svelte 5 runes mode throughout: `$state()`, `$derived()`, `onclick=`
- mittag.io SDK may be blocked by CSP — check nginx/CSP headers and add `https://www.mittag.io` to `script-src` and `frame-src` if needed
- The mittag.io widget renders in an iframe internally — allow `frame-src https://www.mittag.io` in CSP
- Test on a weekday to confirm widgets render; weekend fallback relies on DOM observation
