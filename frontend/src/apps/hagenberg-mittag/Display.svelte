<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';
  import { RESTAURANTS } from './restaurants';

  let focusedId = $state<string | null>(null);
  let weekMode = $state(false);
  let widgetKey = $state(0);
  let countdown = $state(0);
  let countdownTimer: ReturnType<typeof setInterval> | null = null;
  let emptyCards = $state(new Set<string>());

  function checkEmpty() {
    const newEmpty = new Set<string>();
    document.querySelectorAll<HTMLElement>('.widget-wrap').forEach((wrap, i) => {
      if (wrap.scrollHeight < 40) newEmpty.add(RESTAURANTS[i]?.id ?? '');
    });
    emptyCards = newEmpty;
  }

  function loadSdk() {
    const existing = document.querySelector('script[src*="mittag.io/e/js"]');
    if (existing) existing.remove();
    const s = document.createElement('script');
    s.src = 'https://www.mittag.io/e/js';
    s.onload = () => setTimeout(checkEmpty, 3000);
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
          {#if emptyCards.has(r.id)}
            <div class="empty-state">Koa Mittagessen heut 🍺</div>
          {/if}
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

  /* mittag.io widget overrides — keep readable on dark bg */
  .widget-wrap :global(body),
  .widget-wrap :global(*) {
    color-scheme: light;
  }
</style>
