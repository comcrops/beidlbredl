<script lang="ts">
  import { onMount } from 'svelte';
  import { kioskState } from '$lib/stores/kiosk';
  import { connectSockets } from '$lib/socket';
  import { getApp } from '$lib/appRegistry';

  onMount(() => {
    connectSockets();
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
    display: block;
  }

  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-size: 1.5rem;
    color: #666;
  }
</style>
