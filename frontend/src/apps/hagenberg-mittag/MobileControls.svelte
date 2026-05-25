<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { Socket } from 'socket.io-client';
  import { RESTAURANTS } from './restaurants';

  let { socket }: { socket: Socket } = $props();

  let focusedId = $state<string | null>(null);
  let focusTimer: ReturnType<typeof setTimeout> | null = null;

  function focus(id: string) {
    socket.emit('hagenberg_mittag:focus', { id: focusedId === id ? null : id });
  }

  function handleFocus(data: { id: string | null }) {
    if (data.id === null) {
      focusedId = null;
      if (focusTimer) { clearTimeout(focusTimer); focusTimer = null; }
      return;
    }
    focusedId = data.id;
    if (focusTimer) clearTimeout(focusTimer);
    focusTimer = setTimeout(() => { focusedId = null; focusTimer = null; }, 15000);
  }

  onMount(() => {
    socket.on('hagenberg_mittag:focus', handleFocus);
  });

  onDestroy(() => {
    socket.off('hagenberg_mittag:focus', handleFocus);
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

</style>
