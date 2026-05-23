<script lang="ts">
  import type { Socket } from 'socket.io-client';

  export let socket: Socket;

  let newMessage = '';

  function sendMessage() {
    const trimmed = newMessage.trim();
    if (trimmed) {
      socket.emit('hello_world:update_message', { message: trimmed });
      newMessage = '';
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') sendMessage();
  }
</script>

<div class="hello-world-controls">
  <p>Gedanken schicken</p>
  <div class="input-row">
    <input
      bind:value={newMessage}
      on:keydown={handleKeydown}
      placeholder="Was denkst du...?"
    />
    <button on:click={sendMessage} disabled={!newMessage.trim()}>Schicken</button>
  </div>
</div>

<style>
  p {
    margin: 0 0 0.5rem;
    font-size: 0.85rem;
    color: #aaa;
  }

  .input-row {
    display: flex;
    gap: 0.5rem;
  }

  input {
    flex: 1;
    padding: 0.5rem;
    background: #333;
    color: #fff;
    border: 1px solid #555;
    border-radius: 6px;
    font-size: 1rem;
  }

  button {
    padding: 0.5rem 1rem;
    background: #2d6a4f;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 1rem;
  }

  button:disabled {
    opacity: 0.4;
    cursor: default;
  }
</style>
