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
