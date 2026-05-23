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
    {#if activeApp}
      <span class="active-label">
        {activeApp.icon}
        {activeApp.name}
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
