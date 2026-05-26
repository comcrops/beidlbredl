<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { handleCallback, login } from '$lib/auth';
  import { fetchUser, userStore } from '$lib/stores/user';

  let error = '';
  let retryReturn = '/';

  onMount(async () => {
    retryReturn = sessionStorage.getItem('pkce_return_to') ?? '/';
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
      // Clean up any partially-stored token so the user isn't stuck
      localStorage.removeItem('bb_token');
      localStorage.removeItem('bb_token_exp');
      error = e instanceof Error ? e.message : 'Login fehlgeschlagen';
    }
  });
</script>

{#if error}
  <div class="error-page">
    <p>Fehler beim Login: {error}</p>
    <button onclick={() => login(retryReturn)}>Nochmal probieren</button>
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
