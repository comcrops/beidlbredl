<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';

  interface OnlineUser { username: string; avatar_url: string | null; }

  let users = $state<OnlineUser[]>([]);

  function handleUpdate(data: { users: OnlineUser[] }) {
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
        <li>
          {#if user.avatar_url}
            <img src="{user.avatar_url}?thumb=64x64" alt="" class="avatar" />
          {:else}
            <div class="avatar placeholder">{user.username[0].toUpperCase()}</div>
          {/if}
          {user.username}
        </li>
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

  h2 { font-size: 2rem; margin: 0 0 2rem; }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  li {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 1.5rem;
  }

  .avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
  }

  .avatar.placeholder {
    background: #333;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    color: #aaa;
  }

  .empty { font-size: 1.5rem; color: #555; }
</style>
