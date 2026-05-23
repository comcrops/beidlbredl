<script lang="ts">
  import { onMount } from 'svelte';
  import { kioskState } from '$lib/stores/kiosk';
  import { connectSockets, generalSocket } from '$lib/socket';
  import { getApp } from '$lib/appRegistry';

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

  onMount(() => {
    connectSockets();
    generalSocket.on('state', resetIdleTimer);
    resetIdleTimer();
    return () => {
      clearTimeout(idleTimer);
      generalSocket.off('state', resetIdleTimer);
    };
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
    <div class="carousel-bar" class:idle-active={!$kioskState.locked && $kioskState.openAppIds.length >= 2} class:locked={$kioskState.locked}>
      {#key idleKey}
        {#each $kioskState.openAppIds as appId (appId)}
          {@const app = getApp(appId)}
          {#if app}
            <div class="carousel-pill" class:active={appId === $kioskState.activeAppId}>
              <span class="pill-icon">{app.icon}</span>
              <span class="pill-name">{app.name}</span>
            </div>
          {/if}
        {/each}
      {/key}
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

  /* Carousel indicator */

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
    position: relative;
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
    border-color: rgba(255,255,255,0.3);
    color: #fff;
  }

  .carousel-bar.locked .carousel-pill.active {
    background: rgba(138, 90, 42, 0.3);
    border-color: rgba(138, 90, 42, 0.8);
    color: #f5c98a;
  }

  .carousel-bar.idle-active .carousel-pill.active::after {
    content: '';
    position: absolute;
    inset: -1px;
    border-radius: 999px;
    border: 1.5px solid rgba(255,255,255,0.9);
    clip-path: inset(0 100% 0 0 round 999px);
    animation: pill-border-fill 10s linear forwards;
  }

  @keyframes pill-border-fill {
    from { clip-path: inset(0 100% 0 0 round 999px); }
    to   { clip-path: inset(0 0% 0 0 round 999px); }
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
