# One-time setup — breaking-news pipeline

Work through these in order. Everything here is manual/one-time; daily
operation needs none of it.

## 1. Telegram bot
1. In Telegram, message @BotFather → `/newbot` → name it (e.g. "Red Mancunian
   Desk") → copy the **bot token**.
2. Message your new bot once (any text), then:
   `curl "https://api.telegram.org/bot<TOKEN>/getUpdates"` — your **chat id**
   is `result[0].message.chat.id`.

## 2. GitHub PAT for dispatches
GitHub → Settings → Developer settings → Fine-grained tokens → Generate:
- Repository access: ONLY this repo
- Permissions: **Contents: Read and write** (required for repository_dispatch)
- 1-year expiry; calendar a renewal reminder.

## 3. Repo secrets + variable
`gh secret set <NAME>` for each: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN,
TELEGRAM_CHAT_ID, REPO_DISPATCH_PAT, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
GOOGLE_REFRESH_TOKEN (from step 4).
`gh variable set YOUTUBE_PRIVACY --body unlisted`  (flip to `public` after the
shakedown week).

## 4. Google / YouTube OAuth
1. console.cloud.google.com → new project "red-mancunian" → enable
   **YouTube Data API v3**.
2. OAuth consent screen: External, add yourself as test user.
3. Credentials → Create → OAuth client ID → **Desktop app** → copy client
   id + secret.
4. Locally: set GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET env vars, run
   `python automation/get_refresh_token.py`, sign in as the channel owner,
   store the printed token as the GOOGLE_REFRESH_TOKEN secret.

## 5. Cloudflare Worker
```
cd automation/worker
npx wrangler deploy
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET   # invent a long random string
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put GH_DISPATCH_PAT           # same PAT as REPO_DISPATCH_PAT
```
Register the webhook (note the secret_token must match):
```
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://red-mancunian-approval.<account>.workers.dev" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

## 6. End-to-end verification (in order)
1. `python automation/telegram_bot.py alert "wiring test"` locally with the
   env vars set → message arrives on the phone.
2. Actions → editor → Run workflow with dry_run=true → artifact contains the
   MP4s (or run log explains a no-post day).
3. Actions → editor → Run workflow (dry_run=false) → video + caption + buttons
   arrive in Telegram. Tap ❌ Reject → caption gains "REJECTED".
4. Re-run, tap ✅ → publish workflow runs → reply contains an **unlisted**
   YouTube link that plays.
5. Watcher: wait for a 30-min tick or `gh workflow run news-watcher` → log
   shows "nothing new" (state already seeded).

## 7. Shakedown week, then cutover
- Keep YOUTUBE_PRIVACY=unlisted for ~a week; flip each good upload public by
  hand in YouTube Studio. When trust is earned:
  `gh variable set YOUTUBE_PRIVACY --body public`.
- Disable the local scheduled tasks ONLY after one clean breaking-news cycle:
  `schtasks /Change /TN "RedMancunian-Daily-Update" /DISABLE`
  `schtasks /Change /TN "RedMancunian-Evening-Update" /DISABLE`
- tiktok/run-daily.ps1 stays in the repo as the manual/local fallback.
