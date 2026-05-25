<script lang="ts">
  import type { Socket } from 'socket.io-client';

  let { socket }: { socket: Socket } = $props();
</script>

<div class="controls">
  <!-- Mobile controls for Hagenberger Mittagessen -->
</div>

<style>
  .controls {
    width: 100%;
    padding: 1rem;
  }
</style>
