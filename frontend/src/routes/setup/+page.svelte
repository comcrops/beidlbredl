<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getToken, login } from '$lib/auth';
  import { createUser, userStore } from '$lib/stores/user';

  let username = '';
  let error = '';
  let saving = false;
  let returnTo = '/';

  onMount(() => {
    returnTo = $page.url.searchParams.get('return') ?? '/';
    if (!getToken()) login(returnTo);
  });

  async function submit(e: Event) {
    e.preventDefault();
    const token = getToken();
    if (!token) { login(returnTo); return; }
    saving = true;
    error = '';
    try {
      const user = await createUser(token, username.trim());
      userStore.set(user);
      goto(returnTo);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Fehler';
      saving = false;
    }
  }
</script>

<div class="setup">
  <h1>Wia hast du?</h1>
  <p>Wähl an Spitznamen (3–20 Zeichen, Buchstaben, Zahlen, Unterstrich).</p>
  <form onsubmit={submit}>
    <input
      bind:value={username}
      placeholder="z.B. MaxMustermann"
      minlength="3"
      maxlength="20"
      required
      disabled={saving}
      autocomplete="off"
    />
    {#if error}<p class="error">{error}</p>{/if}
    <button type="submit" disabled={saving || username.trim().length < 3}>
      {saving ? 'Speichern...' : 'Weiter →'}
    </button>
  </form>
</div>

<style>
  :global(body) { margin: 0; background: #111; }

  .setup {
    max-width: 400px;
    margin: 5rem auto;
    padding: 2rem;
    color: #fff;
    font-family: sans-serif;
    text-align: center;
  }
  h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
  p { color: #aaa; margin-bottom: 1.5rem; font-size: 0.95rem; }
  input {
    display: block;
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 1rem;
    border: 1px solid #444;
    border-radius: 8px;
    background: #222;
    color: #fff;
    margin-bottom: 0.75rem;
    box-sizing: border-box;
  }
  input:focus { outline: none; border-color: #1d4ed8; }
  button {
    width: 100%;
    padding: 0.75rem;
    background: #1d4ed8;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  button:disabled { opacity: 0.45; cursor: default; }
  .error { color: #f87171; font-size: 0.9rem; margin: 0.5rem 0; }
</style>
