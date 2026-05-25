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
      <div class="brand">
        <!-- logo placeholder: replace with <img src="/logo.svg" alt="Beidlbredl" class="brand-logo" /> -->
        <div class="brand-logo-placeholder">🎛️</div>
        <div class="brand-name">Beidlbredl</div>
      </div>
      <p class="brand-hint">Koa App offen. Mach oan auf mit deim Handy!</p>
    </div>
  {/if}

  <!-- persistent branding watermark -->
  <div class="watermark" class:faded={$kioskState.openAppIds.length > 0}>
    <!-- logo placeholder: replace with <img src="/logo.svg" alt="" class="watermark-logo" /> -->
    <span class="watermark-icon">🎛️</span>
    <span class="watermark-name">Beidlbredl</span>
  </div>

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
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 1.5rem;
  }

  .brand {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    user-select: none;
  }

  .brand-logo-placeholder {
    font-size: clamp(4rem, 10vw, 8rem);
    opacity: 0.15;
    line-height: 1;
  }

  /* swap this out when you have a real logo: */
  /* .brand-logo { width: clamp(80px, 15vw, 180px); opacity: 0.2; } */

  .brand-name {
    font-size: clamp(2rem, 5vw, 4.5rem);
    font-weight: 700;
    letter-spacing: 0.04em;
    color: rgba(255, 255, 255, 0.12);
    text-transform: lowercase;
  }

  .brand-hint {
    font-size: clamp(0.9rem, 1.5vw, 1.25rem);
    color: rgba(255, 255, 255, 0.2);
    margin: 0;
  }

  /* ── Persistent branding watermark ── */
  .watermark {
    position: absolute;
    top: 1.1rem;
    left: 1.4rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    z-index: 10;
    pointer-events: none;
    transition: opacity 0.6s ease;
    opacity: 1;
  }

  .watermark.faded {
    opacity: 0.18;
  }

  .watermark-icon {
    font-size: 1.25rem;
    line-height: 1;
  }

  /* swap for real logo: */
  /* .watermark-logo { height: 1.5rem; width: auto; } */

  .watermark-name {
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #fff;
    text-transform: lowercase;
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
