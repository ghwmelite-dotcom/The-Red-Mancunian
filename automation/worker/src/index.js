// Telegram approval relay: webhook -> verify -> repository_dispatch.
// Secrets (wrangler secret put): TELEGRAM_WEBHOOK_SECRET, TELEGRAM_BOT_TOKEN,
// GH_DISPATCH_PAT (fine-grained, this repo only, Contents: read+write).

async function tg(env, method, body) {
  return fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return new Response('ok');
    if (request.headers.get('x-telegram-bot-api-secret-token') !==
        env.TELEGRAM_WEBHOOK_SECRET) {
      return new Response('forbidden', { status: 403 });
    }

    const update = await request.json();
    const cb = update.callback_query;
    if (!cb || !cb.data) return new Response('ok');

    // callback_data = "<action>:<run_id>:<story_id>"
    const [action, runId, ...rest] = cb.data.split(':');
    const storyId = rest.join(':');

    if (action === 'ok') {
      const r = await fetch(`https://api.github.com/repos/${env.GH_REPO}/dispatches`, {
        method: 'POST',
        headers: {
          authorization: `Bearer ${env.GH_DISPATCH_PAT}`,
          accept: 'application/vnd.github+json',
          'user-agent': 'red-mancunian-approval',
          'x-github-api-version': '2022-11-28',
        },
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
