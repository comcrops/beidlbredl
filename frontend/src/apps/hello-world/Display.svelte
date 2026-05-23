<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';

  let message = 'Servus Welt!';

  function handleMessageUpdated(data: { message: string }) {
    message = data.message;
  }

  onMount(() => {
    appsSocket.on('hello_world:message_updated', handleMessageUpdated);
  });

  onDestroy(() => {
    appsSocket.off('hello_world:message_updated', handleMessageUpdated);
  });
</script>

<div class="hello-world-display">
  <h1>{message}</h1>
</div>

<style>
  .hello-world-display {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    background: #111;
  }

  h1 {
    font-size: clamp(3rem, 8vw, 8rem);
    color: #fff;
    text-align: center;
    padding: 2rem;
  }
</style>
