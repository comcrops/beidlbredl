<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';

  interface Message {
    text: string;
    sender: string;
    avatar_url: string | null;
  }

  interface Bubble {
    id: number;
    text: string;
    sender: string;
    avatar_url: string | null;
    left: number;
    top: number;
    dur: number;
    dx: number;
    dy: number;
    rot: number;
    scale: number;
  }

  let messages: Message[] = [];
  let bubbles: Bubble[] = [];
  let nextId = 0;
  let spawnTimer: ReturnType<typeof setInterval>;

  function weightedPick(): Message | null {
    if (!messages.length) return null;
    // weight[i] = 1/(i+1): index 0 (newest) is 2x more likely than index 1, 3x more than index 2, etc.
    const weights = messages.map((_, i) => 1 / (i + 1));
    const total = weights.reduce((a, b) => a + b, 0);
    let r = Math.random() * total;
    for (let i = 0; i < messages.length; i++) {
      r -= weights[i];
      if (r <= 0) return messages[i];
    }
    return messages[messages.length - 1];
  }

  function spawnBubble() {
    const msg = weightedPick();
    if (!msg || bubbles.length >= 6) return;
    const id = nextId++;
    const dur = 12 + Math.random() * 7;
    bubbles = [
      ...bubbles,
      {
        id,
        text: msg.text,
        sender: msg.sender,
        avatar_url: msg.avatar_url ?? null,
        left: 4 + Math.random() * 68,
        top: 10 + Math.random() * 62,
        dur,
        dx: (Math.random() - 0.5) * 110,
        dy: -(35 + Math.random() * 90),
        rot: (Math.random() - 0.5) * 8,
        scale: 0.85 + Math.random() * 0.3,
      },
    ];
    setTimeout(() => {
      bubbles = bubbles.filter(b => b.id !== id);
    }, dur * 1000);
  }

  function handleMessages(data: { messages: Message[] }) {
    const isNewMessage = data.messages[0]?.text !== messages[0]?.text;
    messages = data.messages;
    if (isNewMessage && messages.length) spawnBubble();
  }

  onMount(() => {
    appsSocket.on('hello_world:messages_updated', handleMessages);
    appsSocket.emit('hello_world:request_messages');
    spawnTimer = setInterval(spawnBubble, 3500);
    setTimeout(spawnBubble, 700);
  });

  onDestroy(() => {
    appsSocket.off('hello_world:messages_updated', handleMessages);
    clearInterval(spawnTimer);
  });
</script>

<div class="display">
  {#each bubbles as bubble (bubble.id)}
    <div
      class="bubble"
      style="
        left: {bubble.left}%;
        top: {bubble.top}%;
        --dur: {bubble.dur}s;
        --dx: {bubble.dx}px;
        --dy: {bubble.dy}px;
        --rot: {bubble.rot}deg;
        --scale: {bubble.scale};
      "
    >
      <div class="bubble-text">{bubble.text}</div>
      {#if bubble.sender}
        <div class="bubble-sender">
          {#if bubble.avatar_url}
            <img src="{bubble.avatar_url}?thumb=32x32" alt="" class="bubble-avatar" />
          {/if}
          {bubble.sender}
        </div>
      {/if}
    </div>
  {/each}

  {#if messages.length === 0}
    <div class="empty">Schreib wos auf dein Handy! 💭</div>
  {/if}
</div>

<style>
  .display {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: radial-gradient(ellipse at 50% 60%, #1c1c3a 0%, #0d0d18 100%);
  }

  .bubble {
    position: absolute;
    max-width: 220px;
    padding: 0.65rem 1.1rem;
    background: rgba(255, 255, 255, 0.93);
    color: #18182e;
    border-radius: 20px;
    font-size: clamp(0.8rem, 1.4vw, 1.05rem);
    font-weight: 500;
    box-shadow: 0 6px 28px rgba(0, 0, 0, 0.3), 0 1px 4px rgba(0, 0, 0, 0.15);
    pointer-events: none;
    animation: bubble-float var(--dur) ease-in-out forwards;
  }

  .bubble-text {
    line-height: 1.45;
  }

  .bubble-sender {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.35rem;
    font-size: 0.75em;
    color: #555;
    margin-top: 0.3rem;
  }

  .bubble-avatar {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
  }

  /* thought bubble tail: two decreasing circles */
  .bubble::before {
    content: '';
    position: absolute;
    bottom: -12px;
    left: 22px;
    width: 11px;
    height: 11px;
    background: rgba(255, 255, 255, 0.93);
    border-radius: 50%;
    box-shadow: -10px 12px 0 -4px rgba(255, 255, 255, 0.93);
  }

  @keyframes bubble-float {
    0% {
      opacity: 0;
      transform: translate(0, 0) scale(calc(var(--scale) * 0.55)) rotate(var(--rot));
    }
    10% {
      opacity: 1;
      transform: translate(calc(var(--dx) * 0.04), calc(var(--dy) * 0.04))
        scale(var(--scale)) rotate(calc(var(--rot) * 0.6));
    }
    82% {
      opacity: 1;
    }
    100% {
      opacity: 0;
      transform: translate(var(--dx), var(--dy))
        scale(calc(var(--scale) * 0.88)) rotate(calc(var(--rot) * -0.35));
    }
  }

  .empty {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.2);
    font-size: clamp(1rem, 2vw, 1.5rem);
    pointer-events: none;
  }
</style>
