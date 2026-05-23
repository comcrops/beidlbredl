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
    <div class="header-right">
      {#if activeApp}
        <span class="active-label">{activeApp.icon} {activeApp.name}</span>
      {/if}
      <button class="launcher-btn" on:click={() => launcherOpen = true} aria-label="Apps öffnen">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <rect x="2" y="2" width="6" height="6" rx="1.5"/>
          <rect x="12" y="2" width="6" height="6" rx="1.5"/>
          <rect x="2" y="12" width="6" height="6" rx="1.5"/>
          <rect x="12" y="12" width="6" height="6" rx="1.5"/>
        </svg>
      </button>
    </div>
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
</div>

<!-- Launcher overlay -->
{#if launcherOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="backdrop" on:click={() => launcherOpen = false}></div>
  <div class="launcher-sheet">
    <div class="sheet-handle"></div>
    <div class="sheet-header">
      <span>Apps</span>
      <button class="close-sheet-btn" on:click={() => launcherOpen = false}>✕</button>
    </div>
    <div class="app-list">
      {#each apps as app}
        <div class="app-item">
          <span class="app-label">{app.icon} {app.name}</span>
          {#if $kioskState.openAppIds.includes(app.id)}
            <button class="close-btn" on:click={() => { closeApp(app.id); }}>Schließen</button>
          {:else}
            <button class="open-btn" on:click={() => { openApp(app.id); launcherOpen = false; }}>Öffnen</button>
          {/if}
        </div>
      {/each}
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
    gap: 0.75rem;
  }

  .active-label {
    font-size: 0.85rem;
    color: #aaa;
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
    transition: background 0.15s;
  }

  .general-controls button:hover:not(:disabled) {
    background: #444;
  }

  .general-controls button:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .app-controls {
    padding: 1rem;
    background: #2a2a2a;
    border-radius: 8px;
  }

  /* Overlay */

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

  .open-btn, .close-btn {
    padding: 0.4rem 1rem;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: opacity 0.15s;
  }

  .open-btn:hover, .close-btn:hover {
    opacity: 0.85;
  }

  .open-btn { background: #2d6a4f; color: #fff; }
  .close-btn { background: #6a2d2d; color: #fff; }

  @keyframes fade-in {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  @keyframes slide-up {
    from { transform: translateY(100%); }
    to   { transform: translateY(0); }
  }
</style>
