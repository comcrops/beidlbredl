<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';
</script>

<!-- full-viewport, no scrollbars — this fills the kiosk slot -->
<div class="display">
  <p>🍽️ Hagenberger Mittagessen</p>
</div>

<style>
  .display {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
