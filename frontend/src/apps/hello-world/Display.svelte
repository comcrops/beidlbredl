<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appsSocket } from '$lib/socket';

  interface Message {
    text: string;
    sender: string;
    avatar_url: string | null;
  }

  interface Sender {
    username: string;
    avatar_url: string | null;
    x: number; // % from left (avatar center)
  }

  interface Bubble {
    id: number;
    text: string;
    sender: string;
    originX: number; // % — aligns tail with avatar
    dur: number;
    dx: number;
    dy: number;
    rot: number;
    scale: number;
  }

  let messages: Message[] = [];
  let bubbles: Bubble[] = [];
  let senders: Sender[] = [];
  // stable order: username → slot index, never reshuffles existing senders
  const senderSlots = new Map<string, number>();
  let nextId = 0;
  let spawnTimer: ReturnType<typeof setInterval>;
  let avatarCache: Record<string, string | null> = {};

  function rebuildSenders() {
    const count = senderSlots.size;
    senders = [...senderSlots.entries()]
      .sort((a, b) => a[1] - b[1])
      .map(([username, slot]) => ({
        username,
        avatar_url: avatarCache[username] ?? null,
        // spread evenly between 8% and 92%
        x: count === 1 ? 50 : 8 + (slot / (count - 1)) * 84,
      }));
  }

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

  function spawnBubble() {
    const msg = weightedPick();
    if (!msg || bubbles.length >= 7) return;
    const id = nextId++;
    const dur = 11 + Math.random() * 10;

    const sender = senders.find(s => s.username === msg.sender);
    // spawn x centered on avatar, ±4% jitter
    const originX = (sender?.x ?? 10 + Math.random() * 80) + (Math.random() - 0.5) * 4;

    // wide size range: 0.55 → 1.5
    const scale = 0.55 + Math.random() * 0.95;

    bubbles = [
      ...bubbles,
      {
        id,
        text: msg.text,
        sender: msg.sender,
        originX,
        dur,
        dx: (Math.random() - 0.5) * 130,
        dy: -(120 + Math.random() * 320), // float up 120–440px
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
        rebuildSenders();
      }
    } catch {}
  }

  function handleMessages(data: { messages: Message[] }) {
    const isNewMessage = data.messages[0]?.text !== messages[0]?.text;
    messages = data.messages;

    // register new senders in stable slots
    let changed = false;
    for (const m of messages) {
      if (m.sender && !senderSlots.has(m.sender)) {
        senderSlots.set(m.sender, senderSlots.size);
        changed = true;
      }
    }
    if (changed) rebuildSenders();

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
  <!-- floating thought bubbles -->
  {#each bubbles as bubble (bubble.id)}
    <div
      class="bubble"
      style="
        left: {bubble.originX}%;
        top: 78%;
        --dur: {bubble.dur}s;
        --dx: {bubble.dx}px;
        --dy: {bubble.dy}px;
        --rot: {bubble.rot}deg;
        --scale: {bubble.scale};
      "
    >
      <div class="bubble-text">{bubble.text}</div>
      {#if bubble.sender}
        <div class="bubble-sender">{bubble.sender}</div>
      {/if}
    </div>
  {/each}

  <!-- avatar strip at the bottom -->
  {#if senders.length > 0}
    <div class="avatars">
      {#each senders as s}
        <div class="avatar-pin" style="left: {s.x}%">
          {#if s.avatar_url}
            <img src="{s.avatar_url}?thumb=96x96" alt={s.username} class="avatar-img" />
          {:else}
            <div class="avatar-letter">{s.username[0]?.toUpperCase() ?? '?'}</div>
          {/if}
          <span class="avatar-name">{s.username}</span>
        </div>
      {/each}
    </div>
  {/if}

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

  /* ── Thought bubbles ── */
  .bubble {
    position: absolute;
    /* anchor at bottom-left so tail aligns with avatar center */
    transform-origin: bottom left;
    max-width: 240px;
    padding: 0.7rem 1.15rem;
    background: rgba(255, 255, 255, 0.93);
    color: #18182e;
    border-radius: 22px;
    font-size: clamp(0.75rem, 1.3vw, 1rem);
    font-weight: 500;
    box-shadow: 0 6px 28px rgba(0, 0, 0, 0.35), 0 1px 4px rgba(0, 0, 0, 0.15);
    pointer-events: none;
    /* shift left by half bubble width so it centers on originX */
    translate: -50% 0;
    animation: bubble-float var(--dur) ease-in-out forwards;
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

  /* thought-bubble tail: two dots pointing downward toward the avatar */
  .bubble::before {
    content: '';
    position: absolute;
    bottom: -13px;
    left: 50%;
    translate: -50% 0;
    width: 10px;
    height: 10px;
    background: rgba(255, 255, 255, 0.93);
    border-radius: 50%;
    box-shadow: 0 14px 0 -3px rgba(255, 255, 255, 0.85);
  }

  @keyframes bubble-float {
    0% {
      opacity: 0;
      transform: translate(0, 0) scale(calc(var(--scale) * 0.45)) rotate(var(--rot));
    }
    8% {
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

  /* ── Avatar strip ── */
  .avatars {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 18%;
    pointer-events: none;
  }

  .avatar-pin {
    position: absolute;
    bottom: 0.6rem;
    translate: -50% 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
  }

  .avatar-img,
  .avatar-letter {
    width: clamp(44px, 5.5vw, 72px);
    height: clamp(44px, 5.5vw, 72px);
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.18);
    object-fit: cover;
    flex-shrink: 0;
  }

  .avatar-letter {
    background: #2a2a4a;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: clamp(1rem, 1.8vw, 1.4rem);
    color: rgba(255, 255, 255, 0.6);
  }

  .avatar-name {
    font-size: clamp(0.6rem, 0.9vw, 0.75rem);
    color: rgba(255, 255, 255, 0.45);
    white-space: nowrap;
    letter-spacing: 0.02em;
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
