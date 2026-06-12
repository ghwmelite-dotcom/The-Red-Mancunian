// Telegram approval relay + command bot: webhook -> verify -> act.
// Secrets (wrangler secret put): TELEGRAM_WEBHOOK_SECRET, TELEGRAM_BOT_TOKEN,
// GH_DISPATCH_PAT (fine-grained, this repo only, Contents: read+write;
// add Actions: read to enable /status).
// Vars (wrangler.toml): GH_REPO, ALLOWED_CHAT_ID (only this chat may command).

async function tg(env, method, body) {
  return fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function gh(env, path, init = {}) {
  return fetch(`https://api.github.com/repos/${env.GH_REPO}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${env.GH_DISPATCH_PAT}`,
      accept: 'application/vnd.github+json',
      'user-agent': 'red-mancunian-approval',
      'x-github-api-version': '2022-11-28',
    },
  });
}

async function handleCommand(env, msg) {
  const reply = (text) => tg(env, 'sendMessage', { chat_id: msg.chat.id, text });
  const cmd = msg.text.trim().split(/[\s@]/)[0];

  if (cmd === '/run') {
    const r = await gh(env, '/dispatches', {
      method: 'POST',
      body: JSON.stringify({
        event_type: 'editor-run',
        client_payload: {
          headlines: 'manual /run from Telegram - no specific tip, sweep all sources for the latest stories',
        },
      }),
    });
    await reply(r.status === 204
      ? '🎬 Editor dispatched - if there is a story, the video lands here in ~10 minutes.'
      : `Dispatch failed (${r.status})`);
  } else if (cmd === '/status') {
    const r = await gh(env, '/actions/runs?per_page=8');
    if (!r.ok) {
      await reply(`Status failed (${r.status})${r.status === 403
        ? ' - the PAT needs "Actions: Read" permission for /status' : ''}`);
      return;
    }
    const data = await r.json();
    const lines = data.workflow_runs.map((w) => {
      const icon = w.status !== 'completed' ? '🔄'
        : w.conclusion === 'success' ? '✅' : '❌';
      return `${icon} ${w.name} · ${w.conclusion || w.status} · ${w.created_at.replace('T', ' ').slice(5, 16)}`;
    });
    await reply(lines.length ? lines.join('\n') : 'No runs yet.');
  } else {
    await reply('Commands:\n/run - fire the editor now (breaking news you spotted)\n/status - recent pipeline runs');
  }
}

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return new Response('ok');
    if (request.headers.get('x-telegram-bot-api-secret-token') !==
        env.TELEGRAM_WEBHOOK_SECRET) {
      return new Response('forbidden', { status: 403 });
    }

    const update = await request.json();

    const msg = update.message;
    if (msg && msg.text && String(msg.chat.id) === env.ALLOWED_CHAT_ID) {
      await handleCommand(env, msg);
      return new Response('ok');
    }

    const cb = update.callback_query;
    if (!cb || !cb.data) return new Response('ok');

    // callback_data = "<action>:<run_id>:<story_id>"
    const [action, runId, ...rest] = cb.data.split(':');
    const storyId = rest.join(':');

    if (action === 'ok') {
      const r = await gh(env, '/dispatches', {
        method: 'POST',
        body: JSON.stringify({
          event_type: 'publish-youtube',
          client_payload: {
            run_id: runId,
            story_id: storyId,
            chat_id: cb.message.chat.id,
            message_id: cb.message.message_id,
          },
        }),
      });
      await tg(env, 'answerCallbackQuery', {
        callback_query_id: cb.id,
        text: r.status === 204 ? 'Queued for YouTube ✅' : `Dispatch failed (${r.status})`,
      });
      if (r.status === 204) {
        // editing without reply_markup strips the buttons, so a double-tap
        // can't dispatch a duplicate upload (reject path relies on this too)
        await tg(env, 'editMessageCaption', {
          chat_id: cb.message.chat.id,
          message_id: cb.message.message_id,
          caption: `${cb.message.caption || ''}\n\n✅ QUEUED FOR YOUTUBE`,
        });
      }
    } else if (action === 'no') {
      await tg(env, 'answerCallbackQuery', { callback_query_id: cb.id, text: 'Rejected' });
      await tg(env, 'editMessageCaption', {
        chat_id: cb.message.chat.id,
        message_id: cb.message.message_id,
        caption: `${cb.message.caption || ''}\n\n❌ REJECTED`,
      });
    }
    return new Response('ok');
  },
};
