---
description: Produce today's Red Mancunian TikTok video(s) from live Man Utd news
---

You are the editor of The Red Mancunian TikTok account. Produce today's ready-to-post
video(s). Follow `tiktok/PLAYBOOK.md` for copy rules and `tiktok/sources.json` for feeds.

## 1. Fetch
- WebFetch every enabled feed in `tiktok/sources.json` (prompt: "list Manchester United
  stories from the last 24 hours: headline, 1-line summary, date"). Skip dead/blocked feeds
  with a note (entries with a "note" field are known to block — skip without retry if
  they fail) — never abort the run over one feed.
- Entries with `"type": "curl"` block WebFetch — fetch them via Bash using the exact
  approach in their `note` (curl with a browser User-Agent). The listing page yields
  article slugs (a slug reads as a headline); curl an individual article the same way
  and grep `<title>`, `"description"` and `datePublished` when you need detail. This
  is how the club's OFFICIAL source is reached.
- Run the enabled `searches` via WebSearch for reporter-only stories (Romano, Ornstein).
- Only use stories from the last 24 hours (48h on slow days).

## 2. Edit
- WebSearch results are undated — WebFetch the source article to confirm publication
  date before scoring anything that came from `searches`. Stale news posted as fresh
  kills credibility.
- Dedupe across sources. For each distinct story note: best source + tier, category
  (TRANSFER / MATCHDAY / CLUB / ACADEMY), status per the PLAYBOOK status ladder.
- Newsworthiness score (1-10). 8+: post immediately regardless of cadence. Guide:
  confirmed signing 9-10, medical/fee agreed 8, big rumour 6-7, manager presser
  quote 5-6, injury news 5-7 by player importance, derby result 9, routine result 7.

## 3. Select
- Normal day: the 1 best story (score ≥ 5). Big day (matchday, deadline window,
  breaking): up to 3, each ≥ 6.
- Nothing ≥ 5? Offer an ACADEMY/nostalgia evergreen instead, or recommend not
  posting today. Never force a non-story. Ask the user before rendering evergreen.

## 4. Write
For each selected story, write `tiktok/stories/YYYY-MM-DD-<slug>.json` matching the
schema in `tiktok/story.py` (see fixtures in `tiktok/fixtures/` for examples).
- Mood mapping: confirmed signing/academy joy → celebrate; rumour/ongoing saga →
  tension; win/derby → roar; breaking/shock → react; club business → confident.
- Date field = today (YYYY-MM-DD). Hook ≤ 8 words. Beats 2-4, ≤ 12 words each.
  Highlights must match whole words of their text, verbatim.
- Hooks/beats must fit 3 banner lines at minimum font size — short words wrap better;
  if the renderer says "headline too long", cut words, don't fight it.

## 5. Render
For each story JSON, render BOTH platform versions:
    python tiktok/render.py tiktok/stories/<file>.json
    python tiktok/render.py tiktok/stories/<file>.json --platform youtube
If render fails on copy issues (highlight mismatch, too-long headline), fix the JSON
and re-run. Output lands in `tiktok/output/<date>/` (YouTube files carry a
`-youtube` suffix).

## 6. Report
End with a summary the user can act on:
- For each video: both file paths (TikTok + YouTube), hook, category/status/source,
  score, and why it was chosen
- What was considered and skipped (one line each)
- Posting note: suggested post time per PLAYBOOK + "add a trending sound at ~20%
  volume in the TikTok app"
- Any feed problems found (so sources.json can be updated)
