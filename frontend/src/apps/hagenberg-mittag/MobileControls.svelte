<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { Socket } from 'socket.io-client';
  import { RESTAURANTS } from './restaurants';

  let { socket }: { socket: Socket } = $props();

  let focusedId = $state<string | null>(null);
  let weekMode = $state(false);
  let focusTimer: ReturnType<typeof setTimeout> | null = null;

  function focus(id: string) {
    socket.emit('hagenberg_mittag:focus', { id });
  }

  function toggleWeek() {
    const next = !weekMode;
    socket.emit('hagenberg_mittag:set_week_mode', { week: next });
  }

  function handleFocus(data: { id: string }) {
    focusedId = data.id;
    if (focusTimer) clearTimeout(focusTimer);
    focusTimer = setTimeout(() => { focusedId = null; focusTimer = null; }, 15000);
  }
  function handleSetWeekMode(data: { week: boolean }) { weekMode = data.week; }

  onMount(() => {
    socket.on('hagenberg_mittag:focus', handleFocus);
    socket.on('hagenberg_mittag:set_week_mode', handleSetWeekMode);
  });

  onDestroy(() => {
    socket.off('hagenberg_mittag:focus', handleFocus);
    socket.off('hagenberg_mittag:set_week_mode', handleSetWeekMode);
    if (focusTimer) clearTimeout(focusTimer);
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
