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
  let avatarCache: Record<string, string | null> = {};

  function weightedPick(): Message | null {
    if (!messages.length) return null;
    const weights = messages.map((_, i) => 1 / (i + 1));
    const total = weights.reduce((a, b) => a + b, 0);
    let r = Math.random() * total;
    for (let i = 0; i < messages.length; i++) {
      r -= weights[i];
      if (r <= 0) return messages[i];
    }
    return messages[messages.length - 1];
  }

  function resolveAvatar(msg: Message): string | null {
    if (msg.avatar_url) return msg.avatar_url;
    if (msg.sender in avatarCache) return avatarCache[msg.sender];
    return null;
  }

  function spawnBubble() {
    const msg = weightedPick();
    if (!msg || bubbles.length >= 7) return;
    const id = nextId++;
    const dur = 11 + Math.random() * 10;
    const scale = 0.55 + Math.random() * 0.95; // 0.55 → 1.5

    bubbles = [
      ...bubbles,
      {
        id,
        text: msg.text,
        sender: msg.sender,
        avatar_url: resolveAvatar(msg),
        left: 5 + Math.random() * 72,
        top: 8 + Math.random() * 58,
        dur,
        dx: (Math.random() - 0.5) * 120,
        dy: -(40 + Math.random() * 110),
        rot: (Math.random() - 0.5) * 14,
        scale,
      },
    ];
    setTimeout(() => {
      bubbles = bubbles.filter(b => b.id !== id);
    }, dur * 1000);
  }

  async function fetchAvatars(msgs: Message[]) {
    const unknown = [...new Set(msgs.map(m => m.sender).filter(s => s && !(s in avatarCache)))];
    if (!unknown.length) return;
    try {
      const resp = await fetch(`/api/users/avatars?usernames=${unknown.map(encodeURIComponent).join(',')}`);
      if (resp.ok) {
        const data = await resp.json();
        avatarCache = { ...avatarCache, ...data };
      }
    } catch {}
  }

  function handleMessages(data: { messages: Message[] }) {
    const isNewMessage = data.messages[0]?.text !== messages[0]?.text;
    messages = data.messages;
    fetchAvatars(messages);
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
      class="thinker"
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
      <div class="bubble">
        <div class="bubble-text">{bubble.text}</div>
        {#if bubble.sender}
          <div class="bubble-sender">{bubble.sender}</div>
        {/if}
      </div>

      {#if bubble.sender}
        <div class="thinker-avatar">
          {#if bubble.avatar_url}
            <img src="{bubble.avatar_url}?thumb=96x96" alt={bubble.sender} class="avatar-img" />
          {:else}
            <div class="avatar-letter">{bubble.sender[0]?.toUpperCase() ?? '?'}</div>
          {/if}
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

  /* wrapper that floats as one unit: bubble + tail dots + avatar */
  .thinker {
    position: absolute;
    display: flex;
    flex-direction: column;
    align-items: center;
    pointer-events: none;
    animation: bubble-float var(--dur) ease-in-out forwards;
  }

  /* ── Thought bubble ── */
  .bubble {
    max-width: 220px;
    padding: 0.65rem 1.1rem;
    background: rgba(255, 255, 255, 0.93);
    color: #18182e;
    border-radius: 20px;
    font-size: clamp(0.75rem, 1.3vw, 1rem);
    font-weight: 500;
    box-shadow: 0 6px 28px rgba(0, 0, 0, 0.32), 0 1px 4px rgba(0, 0, 0, 0.15);
    position: relative;
  }

  .bubble-text {
    line-height: 1.45;
  }

  .bubble-sender {
    font-size: 0.72em;
    color: #666;
    text-align: right;
    margin-top: 0.25rem;
  }

  /* two thought-bubble dots between bubble and avatar */
  .bubble::after {
    content: '';
    position: absolute;
    bottom: -10px;
    left: 50%;
    translate: -50% 0;
    width: 9px;
    height: 9px;
    background: rgba(255, 255, 255, 0.93);
    border-radius: 50%;
    box-shadow: 0 16px 0 -3px rgba(255, 255, 255, 0.8);
  }

  /* ── Avatar beneath ── */
  .thinker-avatar {
    margin-top: 22px; /* clears the two tail dots */
  }

  .avatar-img,
  .avatar-letter {
    width: clamp(36px, 4.5vw, 60px);
    height: clamp(36px, 4.5vw, 60px);
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid rgba(255, 255, 255, 0.2);
    display: block;
  }

  .avatar-letter {
    background: #2a2a4a;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: clamp(0.9rem, 1.5vw, 1.25rem);
    color: rgba(255, 255, 255, 0.6);
  }

  /* ── Float animation (applied to .thinker wrapper) ── */
  @keyframes bubble-float {
    0% {
      opacity: 0;
      transform: translate(0, 0) scale(calc(var(--scale) * 0.45)) rotate(var(--rot));
    }
    9% {
      opacity: 1;
      transform: translate(calc(var(--dx) * 0.03), calc(var(--dy) * 0.03))
        scale(var(--scale)) rotate(calc(var(--rot) * 0.5));
    }
    80% {
      opacity: 1;
    }
    100% {
      opacity: 0;
      transform: translate(var(--dx), var(--dy))
        scale(calc(var(--scale) * 0.85)) rotate(calc(var(--rot) * -0.4));
    }
  }

  /* ── Empty state ── */
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
