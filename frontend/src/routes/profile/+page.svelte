<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { getToken, login } from '$lib/auth';
  import { fetchUser, updateUser, userStore } from '$lib/stores/user';

  let username = $state('');
  let error = $state('');
  let success = $state(false);
  let saving = $state(false);
  let returnTo = '/mobile';

  onMount(async () => {
    const token = getToken();
    if (!token) { await login(returnTo); return; }
    const user = await fetchUser(token).catch(() => null);
    if (!user) { goto('/setup?return=' + returnTo); return; }
    userStore.set(user);
    username = user.username;
  });

  async function submit(e: Event) {
    e.preventDefault();
    const token = getToken();
    if (!token) { await login(returnTo); return; }
    saving = true;
    error = '';
    success = false;
    try {
      const user = await updateUser(token, username.trim());
      userStore.set(user);
      success = true;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Fehler';
    } finally {
      saving = false;
    }
  }
</script>

<div class="profile">
  <header>
    <button class="back-btn" onclick={() => goto(returnTo)}>← Zruck</button>
    <h1>Profil</h1>
  </header>

  <form onsubmit={submit}>
    <label for="username">Spitzname</label>
    <input
      id="username"
      bind:value={username}
      minlength={3}
      maxlength={20}
      pattern="[a-zA-Z0-9_]+"
      required
      disabled={saving}
    />
    <p class="hint">3–20 Zeichen, Buchstaben, Zahlen, Unterstrich</p>

    {#if error}
      <p class="error">{error}</p>
    {/if}
    {#if success}
      <p class="success">Gspeichert ✓</p>
    {/if}

    <button type="submit" disabled={saving}>
      {saving ? 'Speichern...' : 'Speichern'}
    </button>
  </form>
</div>

<style>
  :global(body) {
    margin: 0;
    background: #1a1a1a;
    color: #fff;
    font-family: sans-serif;
  }

  .profile {
    max-width: 480px;
    margin: 0 auto;
    padding: 1rem;
  }

  header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 2rem;
  }

  h1 {
    font-size: 1.25rem;
    margin: 0;
  }

  .back-btn {
    background: none;
    border: none;
    color: #aaa;
    font-size: 0.95rem;
    cursor: pointer;
    padding: 0;
  }

  .back-btn:hover { color: #fff; }

  form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  label {
    font-size: 0.85rem;
    color: #aaa;
  }

  input {
    padding: 0.65rem 0.75rem;
    background: #242424;
    border: 1px solid #333;
    border-radius: 8px;
    color: #fff;
    font-size: 1rem;
  }

  input:focus {
    outline: none;
    border-color: #555;
  }

  .hint {
    font-size: 0.75rem;
    color: #555;
    margin: 0;
  }

  .error { color: #f88; font-size: 0.9rem; margin: 0; }
  .success { color: #8f8; font-size: 0.9rem; margin: 0; }

  button[type="submit"] {
    margin-top: 0.5rem;
    padding: 0.65rem;
    background: #1d4ed8;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  button[type="submit"]:hover { opacity: 0.85; }
  button[type="submit"]:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
