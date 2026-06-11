# Breaking-News Video Pipeline — Design

**Date:** 2026-06-11
**Status:** Approved by user (pending spec review)
**Replaces:** Local Task Scheduler runs of `/mufc-update` (09:30 / 17:30 via `tiktok/run-daily.ps1`)

## Goal

Continuously watch for breaking Manchester United news, generate the TikTok and
YouTube Shorts videos in the cloud, deliver them to the editor's phone for
approval, and auto-post to YouTube on approval — with no dependency on the
local PC being awake.

## Decisions made (with user)

| Decision | Choice |
|---|---|
| Scope | Breaking-news latency + no PC dependency + phone review + posting |
| Approval model | Approve-first, then auto-post (no unreviewed content goes live) |
| Posting | YouTube Data API auto-upload on approval; TikTok assisted-manual from the Telegram message (preserves the in-app trending-sound step, which no posting API supports) |
| Infrastructure | GitHub Actions (private repo — repo must first be pushed to GitHub) |
| Phone surface | Telegram bot (inline MP4, copyable caption, approve/reject buttons) |
| Approval relay | Cloudflare Worker (free tier) receiving the Telegram webhook, firing `repository_dispatch` |

## Architecture

```
                       GitHub (private repo)
┌──────────────────────────────────────────────────────────────────────┐
│  WATCHER (cron, every 30 min, 07:00–22:00 UK)                        │
│  Python, no LLM — fetch feeds, fingerprint headlines, diff vs seen   │
│      │ new story cluster detected                                    │
│      ▼                                                               │
│  EDITOR (repository_dispatch; plus daily 09:00 baseline run)         │
│  claude -p with ANTHROPIC_API_KEY — /mufc-update editorial logic,    │
│  writes story JSON, renders both MP4s (render.py, ffmpeg, fonts)     │
│      │                                                               │
│      ▼                                                               │
│  DELIVERY — Telegram message: TikTok MP4 + caption + score           │
│             + [✅ Post to YouTube] [❌ Reject] buttons                │
└──────────────────────────────────────────────────────────────────────┘
            │ button tap                          ▲
            ▼                                     │ repository_dispatch
      Cloudflare Worker (webhook, verify, dispatch)
            
PUBLISH (triggered job) — downloads -youtube.mp4 artifact, uploads via
YouTube Data API, replies in the Telegram thread with the live link
```

The phone is the control room. The local Task Scheduler jobs are retired after
cutover; `/mufc-update` remains available for manual terminal runs.

## Components

### Watcher — `automation/watcher.py`

- Deterministic Python on a GitHub Actions cron (`*/30`, 07:00–22:00 UK only).
  Zero LLM cost.
- Fetches the RSS feeds from `tiktok/sources.json` plus the r/reddevils Atom
  feed (curl with browser User-Agent, as the sources notes prescribe).
- Normalizes each headline to a fingerprint (lowercased significant-token set)
  and clusters near-duplicates, so "Rashford returns to United" and
  "Marcus Rashford set for United return" count as one story.
- Diffs against seen-state; a genuinely new cluster triggers the editor via
  `repository_dispatch` with the candidate headlines as payload.
- Guardrails:
  - Max **3 editor wakes per day** (rate-limit counter in state). This is the
    primary API-cost throttle.
  - On state-cache miss: mark everything seen, trigger nothing (no false
    stampede after cache eviction).
  - Feeds that block datacenter IPs are skipped silently (Google News
    aggregation is the standing backstop, per `sources.json` notes).

### Editor — existing `/mufc-update` logic on the runner

- Runs `claude -p` with `ANTHROPIC_API_KEY` (Sonnet) and the same allowed-tools
  set as `run-daily.ps1` uses today.
- Two entry modes passed in the prompt:
  - `baseline` — daily 09:00 UK scheduled run (replaces the local morning run).
  - `breaking` — watcher-triggered; the prompt includes the tripping headlines
    and applies the playbook surge bar (score ≥ 6; ≥ 8 posts regardless of
    cadence).
- Same editorial duties as today: verify publication dates, score, dedupe
  against `tiktok/stories/` (in the repo checkout), write story JSON, render
  BOTH platform MP4s.
- May conclude "no post" and exit quietly — that is a success, not a failure.
- Commits the story JSON back to `master` so repo state stays the single
  source of truth for what has been covered.

### Delivery — final step of the editor job

- Uploads both MP4s + caption files as one workflow artifact (7-day retention).
- Sends the Telegram message: TikTok MP4 inline (~3.5 MB, far under the 50 MB
  bot limit), caption as copyable text, a hook/category/status/score/source
  line, and inline buttons with `callback_data = <story-id>:<run-id>:<action>`.

### Approval relay — Cloudflare Worker (~50 lines)

- Registered as the Telegram bot webhook; verifies
  `X-Telegram-Bot-Api-Secret-Token`.
- **Approve** → `repository_dispatch` (event `publish-youtube`, payload
  story-id + run-id) using a fine-grained PAT scoped to this repo with
  `actions: write` only; answers the callback instantly ("Queued ✅").
- **Reject** → edits the message (strikethrough) and does not dispatch.

### Publisher — `publish-youtube` workflow

- Downloads the artifact by run-id, refreshes the Google OAuth access token
  from the stored refresh token, resumable-uploads `-youtube.mp4`.
- Title: hook + one emoji + `#mufc` (playbook format). Description: the
  caption file (disclaimer included).
- Staleness guard: refuses uploads where the artifact is older than **12 h**,
  replying with a warning instead (news goes stale).
- Replies in the Telegram thread with the live YouTube URL.

### TikTok path (manual, by design)

The Telegram delivery message *is* the TikTok workflow: save the inline MP4 to
camera roll, upload in the TikTok app, add a trending sound at ~20 % volume,
paste the caption, post. This keeps the trending-sound reach mechanism that no
posting API can replicate.

## Data flow & state

- **Seen-state:** `automation/state/seen.json` in GitHub Actions cache —
  append-only, pruned after 7 days. Not committed (avoids ~45 bot commits/day).
- **Videos:** workflow artifacts, 7-day retention. Telegram holds the phone
  copy; YouTube receives the original artifact bytes.
- **Story JSONs:** committed to `master` by the editor job.
- **Secrets — GitHub repo:** `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
  `GOOGLE_REFRESH_TOKEN`.
- **Secrets — Worker:** `TELEGRAM_WEBHOOK_SECRET`, `GH_DISPATCH_PAT`.
- **Runner deps:** ffmpeg via apt; Python deps pinned in a requirements file.
  Fonts must be vendored into the repo if `render.py` currently resolves
  system fonts (verify during implementation — expected to be the one real
  porting task).

## Error handling

| Failure | Behaviour |
|---|---|
| Editor or render fails | Telegram alert with a link to the failing run's log |
| YouTube upload fails | Telegram alert with a [🔁 Retry] button (re-fires the same dispatch) |
| Watcher run fails | Logged silently; **3 consecutive** failures → one Telegram alert |
| Artifact older than 12 h at publish time | Upload refused, warning reply in thread |
| Seen-state cache evicted | Mark-all-seen, no triggers that run |
| YouTube quota | Default 10,000 units/day ÷ 1,600 per upload = 6 uploads/day ceiling — comfortably above the 1–3 cadence |

## Costs

| Item | Estimate |
|---|---|
| GitHub Actions | ~1,900 min/mo at the 30-min daytime cadence — inside the 2,000-min free tier for private repos |
| Anthropic API | Editor on Sonnet, capped at 3 wakes + 1 baseline/day: **$30–90/mo** depending on news volume. The wake cap is the throttle; tunable to 2 wakes or a wider cadence. |
| Cloudflare Worker, Telegram bot | Free |
| YouTube Data API | Free |

## Testing & rollout

1. **Unit tests** for watcher fingerprinting/clustering and rate-limit logic
   (pytest, alongside `tiktok/tests`).
2. **Dry-run input** on the editor workflow (`workflow_dispatch` with
   `dry_run: true`) — full pipeline minus Telegram/YouTube; artifact inspected
   manually.
3. **Shakedown week** — YouTube uploads land as `unlisted`; the editor flips
   them public manually until trust is earned, then one config switch makes
   uploads public.
4. **Cutover** — disable the two local Task Scheduler jobs only after one
   clean end-to-end breaking-news cycle (watch → render → phone → approve →
   live link).

## Prerequisites / one-time setup

1. Push this repo to a **private** GitHub repository.
2. Create the Telegram bot (@BotFather), capture token + chat id.
3. Google Cloud project + OAuth consent + refresh token for the
   @theredmancunianway channel.
4. Deploy the approval-relay Worker; register it as the bot webhook.
5. Fine-grained PAT (this repo only, `actions: write`) stored in the Worker.
6. Repo secrets as listed above.

## Out of scope (explicitly)

- TikTok API posting (Blotato or official) — rejected to preserve the
  trending-sound step.
- Overnight watching (22:00–07:00 UK) — posting windows make it pointless;
  manual `/mufc-update` covers genuine 3 am bombshells.
- Evergreen/ACADEMY auto-rendering on slow days — stays interactive-only, per
  the playbook's unattended-run rule.
