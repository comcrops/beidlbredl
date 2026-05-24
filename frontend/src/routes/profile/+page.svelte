<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { getToken, login, logout } from '$lib/auth';
  import { fetchUser, updateUser, uploadAvatar, userStore } from '$lib/stores/user';

  let username = $state('');
  let avatarUrl = $state<string | null>(null);
  let avatarPreview = $state<string | null>(null);
  let error = $state('');
  let success = $state('');
  let saving = $state(false);
  let uploading = $state(false);
  let returnTo = '/mobile';

  onMount(async () => {
    const token = getToken();
    if (!token) { await login(returnTo); return; }
    const user = await fetchUser(token).catch(() => null);
    if (!user) { goto('/setup?return=' + returnTo); return; }
    userStore.set(user);
    username = user.username;
    avatarUrl = user.avatar_url;
  });

  async function submit(e: Event) {
    e.preventDefault();
    const token = getToken();
    if (!token) { await login(returnTo); return; }
    saving = true;
    error = '';
    success = '';
    try {
      const user = await updateUser(token, username.trim());
      userStore.set(user);
      success = 'Gspeichert ✓';
    } catch (err) {
      error = err instanceof Error ? err.message : 'Fehler';
    } finally {
      saving = false;
    }
  }

  async function onFileChange(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    avatarPreview = URL.createObjectURL(file);
    const token = getToken();
    if (!token) return;
    uploading = true;
    error = '';
    success = '';
    try {
      const user = await uploadAvatar(token, file);
      userStore.set(user);
      avatarUrl = user.avatar_url;
      success = 'Bild hochgladen ✓';
    } catch (err) {
      error = err instanceof Error ? err.message : 'Upload Fehler';
    } finally {
      uploading = false;
    }
  }
</script>

<div class="profile">
  <header>
    <button class="back-btn" onclick={() => goto(returnTo)}>← Zruck</button>
    <h1>Profil</h1>
    <button class="logout-btn" onclick={logout}>Abmelden</button>
  </header>

  <!-- Avatar section -->
  <div class="avatar-section">
    <div class="avatar-wrap">
      {#if avatarPreview || avatarUrl}
        <img src={avatarPreview ?? avatarUrl} alt="Avatar" class="avatar" />
      {:else}
        <div class="avatar-placeholder">{username[0]?.toUpperCase() ?? '?'}</div>
      {/if}
      {#if uploading}
        <div class="avatar-overlay">⏳</div>
      {/if}
    </div>
    <label class="upload-btn">
      Bild ändern
      <input type="file" accept="image/*" onchange={onFileChange} hidden />
    </label>
  </div>

  {#if error}<p class="error">{error}</p>{/if}
  {#if success}<p class="success">{success}</p>{/if}

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
    margin-bottom: 1.5rem;
  }

  h1 { font-size: 1.25rem; margin: 0; flex: 1; }

  .back-btn {
    background: none;
    border: none;
    color: #aaa;
    font-size: 0.95rem;
    cursor: pointer;
    padding: 0;
  }
  .back-btn:hover { color: #fff; }

  .logout-btn {
    background: none;
    border: 1px solid #444;
    border-radius: 6px;
    color: #f88;
    font-size: 0.85rem;
    cursor: pointer;
    padding: 0.3rem 0.75rem;
  }
  .logout-btn:hover { background: #2a1111; border-color: #f88; }

  .avatar-section {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    margin-bottom: 1.5rem;
  }

  .avatar-wrap {
    position: relative;
    width: 72px;
    height: 72px;
    flex-shrink: 0;
  }

  .avatar, .avatar-placeholder {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    object-fit: cover;
  }

  .avatar-placeholder {
    background: #333;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.75rem;
    color: #aaa;
  }

  .avatar-overlay {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
  }

  .upload-btn {
    padding: 0.5rem 1rem;
    background: #2a2a2a;
    border: 1px solid #444;
    border-radius: 8px;
    font-size: 0.9rem;
    cursor: pointer;
    color: #ccc;
    transition: background 0.15s;
  }
  .upload-btn:hover { background: #333; color: #fff; }

  form { display: flex; flex-direction: column; gap: 0.5rem; }

  label { font-size: 0.85rem; color: #aaa; }

  input {
    padding: 0.65rem 0.75rem;
    background: #242424;
    border: 1px solid #333;
    border-radius: 8px;
    color: #fff;
    font-size: 1rem;
  }
  input:focus { outline: none; border-color: #555; }

  .hint { font-size: 0.75rem; color: #555; margin: 0; }
  .error { color: #f88; font-size: 0.9rem; margin: 0 0 0.5rem; }
  .success { color: #8f8; font-size: 0.9rem; margin: 0 0 0.5rem; }

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
