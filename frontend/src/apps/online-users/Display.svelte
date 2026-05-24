<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';

  let users = $state<string[]>([]);

  function handleUpdate(data: { users: string[] }) {
    users = data.users;
  }

  onMount(() => appsSocket.on('online_users:updated', handleUpdate));
  onDestroy(() => appsSocket.off('online_users:updated', handleUpdate));
</script>

<div class="display">
  <h2>Wer is da?</h2>
  {#if users.length === 0}
    <p class="empty">Neamand do 👻</p>
  {:else}
    <ul>
      {#each users as user}
        <li>👤 {user}</li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .display {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #111;
    color: #fff;
    font-family: sans-serif;
  }

  h2 {
    font-size: 2rem;
    margin: 0 0 2rem;
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  li {
    font-size: 1.5rem;
  }

  .empty {
    font-size: 1.5rem;
    color: #555;
  }
</style>
