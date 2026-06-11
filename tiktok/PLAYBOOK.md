# The Red Mancunian — TikTok News Playbook

The format: Daily Mail Sport-style news cards, Red Mancunian skin.
One story per video. Hook → 2–4 beats → follow card. 15–25 seconds.

## Copy rules
- **Hook:** ≤ 8 words, present tense, ONE highlighted phrase. No clickbait lies —
  the video must deliver what the hook promises.
- **Beats:** ≤ 12 words each. Every beat advances the story. Cut padding.
- **Highlights:** the highlight must match WHOLE WORDS of the text, verbatim.
  Highlight the number, the name, or the stake — the thing eyes should catch.
- **Rumours:** never presented as fact. status RUMOUR/REPORTED requires a source,
  which renders in-frame ("RUMOUR - PER SKY SPORTS") and should be echoed in caption.
- **Caption:** 1–2 sentences + an engagement question + hashtags. The renderer
  appends the disclaimer line automatically.

## Status ladder
| Status | Use when | Frame tag |
|---|---|---|
| OFFICIAL | Club statement / announcement | none |
| CONFIRMED | Multiple tier-1 outlets report as done | none |
| REPORTED | One tier-1/2 outlet reports | shown |
| RUMOUR | Tabloid / aggregator / speculation | shown |

## Hashtag base set
`#mufc #manutd #premierleague #football` + per category:
- TRANSFER: `#transfernews #transferwindow`
- MATCHDAY: `#matchday` + opponent tag (e.g. `#manchesterderby`)
- CLUB: story-specific
- ACADEMY: `#mufcacademy #wonderkid`

## Cadence
- Baseline: 1 post/day.
- Surge (2–3/day): matchdays, transfer deadline period, genuine breaking news.
- Slow day: ACADEMY/nostalgia evergreen, or post nothing. Never force a non-story.

## Posting workflow (per video)
Every render writes a `<id>-post-notes.txt` next to the video with the exact plan
(platform window, sound rules, suggested title) — follow that file. The general flow:
1. Watch the MP4 in `tiktok/output/<date>/` start to finish.
2. Open TikTok → upload the MP4.
3. Add a trending sound, volume LOW (~20%) under the video. This is why we don't
   bake music in — trending sounds boost reach.
4. Paste the caption from `<id>-caption.txt`.
5. Post times (UK): 12:00–14:00 or 19:00–21:00. Breaking news: post immediately.
   For deadline/countdown stories prefer the lunchtime window — it buys a full day
   of tension and leaves room for an evening follow-up.
6. First hour: reply to early comments — it feeds the algorithm.

## YouTube Shorts (same story, second platform)
Every story also renders a `-youtube` MP4 (end card: "SUBSCRIBE..." +
@theredmancunianway). Posting rules differ from TikTok:
1. Upload the ORIGINAL `<id>-youtube.mp4` from `tiktok/output/<date>/` — never a
   TikTok download (watermarked Shorts get suppressed).
2. Do NOT reuse the TikTok trending sound — licences don't transfer. Post as-is
   (the whoosh SFX carries it) or add audio from YouTube's own Shorts sound picker.
3. Title: the hook + one emoji + `#mufc` (e.g. "Barcelona have 4 DAYS to sign
   Rashford 😳 #mufc"). Description: paste the caption file (disclaimer included).
4. Channel: The Red Mancunian (@theredmancunianway). Shorts and the FM26 long-form
   feeds are recommended separately by YouTube — news Shorts won't hurt episode reach.

## Automation (cloud pipeline)
The cloud pipeline (see `automation/SETUP.md` and
`docs/superpowers/specs/2026-06-11-breaking-news-automation-design.md`) replaces
the local scheduled tasks:
- **Watcher** (GitHub Actions, every 30 min, 07:00–22:00 UK) fingerprints feed
  headlines and wakes the editor for genuinely new stories — max 3 wakes/day.
- **Editor** (GitHub Actions) runs `/mufc-update` headlessly: daily 09:00 UK
  baseline + watcher-triggered breaking runs. Renders BOTH platform videos.
- **Delivery**: each video lands in Telegram with the caption and
  ✅ Post to YouTube / ❌ Reject buttons.
- **YouTube**: approving uploads the `-youtube` MP4 automatically and replies
  with the link. TikTok stays manual from the Telegram message — save the
  video, add a trending sound at ~20%, paste the caption.
- Slow days: the editor posts nothing and says why in the run log. Evergreen
  is still interactive-only.
- Breaking news you spot yourself: Actions → editor → Run workflow, or run
  `/mufc-update` locally (still works).
- Failures arrive as Telegram alerts with a link to the run log.

## Maintenance
- Feeds live in `sources.json` — disable dead ones, add new ones with a tier.
- Template changes: edit `frames.py`, run `python -m pytest tiktok/tests`,
  visually review `tiktok/output/_preview` frames before the next live run.
