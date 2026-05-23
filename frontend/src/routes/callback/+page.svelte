<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { handleCallback } from '$lib/auth';
  import { fetchUser, userStore } from '$lib/stores/user';

  let error = '';

  onMount(async () => {
    try {
      const { token, returnTo } = await handleCallback();
      const user = await fetchUser(token);
      if (!user) {
        goto(`/setup?return=${encodeURIComponent(returnTo)}`);
        return;
      }
      userStore.set(user);
      goto(returnTo);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Login fehlgeschlagen';
    }
  });
</script>

{#if error}
  <div class="error-page">
    <p>Fehler beim Login: {error}</p>
    <button onclick={() => goto('/')}>Zurück</button>
  </div>
{:else}
  <div class="loading">Einloggen...</div>
{/if}

<style>
  .loading, .error-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    color: #fff;
    font-family: sans-serif;
    background: #111;
    gap: 1rem;
  }
  button {
    padding: 0.5rem 1.5rem;
    background: #333;
    color: #fff;
    border: 1px solid #555;
    border-radius: 6px;
    cursor: pointer;
  }
</style>
