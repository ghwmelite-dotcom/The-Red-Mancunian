# TikTok News Pipeline — Design Spec

**Date:** 2026-06-10
**Project:** The Red Mancunian
**Status:** Approved design, pending implementation plan

## Goal

A daily content pipeline that turns Manchester United news into ready-to-post TikTok
videos in the Daily Mail Sport format (bold headline banner over visuals, story told in
3–4 text beats), skinned with The Red Mancunian brand. The user runs one command,
reviews the output, and posts manually.

**Reference format:** Daily Mail Sport TikTok — vertical 9:16, all-caps headline on an
angled black banner with one phrase highlighted in brand colour, logo badge above the
banner, 15–30s story-in-beats structure, caption with summary + hashtags.

## Decisions (locked with user)

| Decision | Choice |
|---|---|
| Output | Ready-to-post 9:16 MP4s + caption/hashtag text files |
| Imagery | Branded mascot cards only — no press photos, no real player likenesses (copyright safety) |
| Scope | All Manchester United content: transfers/rumours (priority), matchday, club news & quotes, academy & nostalgia |
| Cadence | 1 post/day baseline; 2–3/day on big days (matchday, transfer windows, breaking news) |
| Sourcing | Tier-1 led (BBC, Sky, club site, Romano/Ornstein); rumours covered but always attributed and visually tagged |
| Driver | Claude Code slash command `/mufc-update` — Claude is the editor; Python renders |

## Architecture

```
The-Red-Mancunian/
├── .claude/commands/mufc-update.md   ← slash command: the editorial brief Claude follows
└── tiktok/
    ├── PLAYBOOK.md          ← format rules, copy style guide, posting workflow
    ├── sources.json         ← news feeds + reliability tiers (user-editable)
    ├── render.py            ← frames (Pillow) + MP4 assembly (ffmpeg)
    ├── assets/              ← derived template art (mascot crops, badge, banner art)
    ├── stories/             ← story JSON files written by Claude each run
    ├── fixtures/            ← test story JSON for golden-testing the renderer
    └── output/YYYY-MM-DD/   ← per-story: story.mp4 + caption.txt + story.json copy
```

Reuses existing brand assets: `branding/character/hero-0[1-6]-*.jpg` (6 mascot poses),
`branding/fonts/Anton.ttf` + `BebasNeue.ttf`, palette from `branding/build_character.py`.

**Dependencies:** Python 3 with Pillow (already used by `build_character.py`),
`feedparser` (or stdlib XML parsing) optional, **ffmpeg** (must be on PATH; setup is an
implementation step — verify installed, install via winget if not).

## Component 1: `/mufc-update` command

A project slash command containing the editorial brief. When run, Claude:

1. **Fetch** — pull current Man Utd stories from every enabled feed in `sources.json`
   (WebFetch on RSS URLs; WebSearch as fallback/supplement for reporter-only stories,
   e.g. Romano/Ornstein who have no RSS). A dead feed is skipped with a note, never fatal.
2. **Edit** — dedupe across sources, categorise each story (TRANSFER / MATCHDAY / CLUB /
   ACADEMY), assign status (OFFICIAL / CONFIRMED / REPORTED / RUMOUR) based on best
   source tier, score newsworthiness.
3. **Select** — 1 story on a normal day; up to 3 on big days. Selection priority:
   breaking transfer news > matchday content (on matchdays) > big club news > best
   remaining story. Slow-news fallback: an ACADEMY/nostalgia evergreen piece, or an
   honest "nothing worth posting today" recommendation — never forced content.
4. **Write** — one story JSON per selected story (schema below) into `tiktok/stories/`.
5. **Render** — run `python tiktok/render.py stories/<file>.json` per story.
6. **Report** — summarise to the user: what was made, why, what was skipped, and a
   posting note (suggested post time + reminder to add a trending sound in-app).

## Component 2: Story JSON schema

```json
{
  "id": "2026-06-10-striker-fee-agreed",
  "date": "2026-06-10",
  "category": "TRANSFER",
  "status": "REPORTED",
  "source": "Sky Sports",
  "mood": "tension",
  "hook":  { "text": "UNITED AGREE £55M FEE", "highlight": "£55M FEE" },
  "beats": [
    { "text": "PERSONAL TERMS EXPECTED THIS WEEK", "highlight": "THIS WEEK" },
    { "text": "MEDICAL PLANNED FOR FRIDAY", "highlight": "FRIDAY" },
    { "text": "HERE'S WHAT HE BRINGS TO OLD TRAFFORD", "highlight": "OLD TRAFFORD" }
  ],
  "caption": "United have reportedly agreed a £55m fee — personal terms next. Thoughts? 🔴",
  "hashtags": ["#mufc", "#manutd", "#transfernews", "#premierleague", "#football"]
}
```

- `category`: TRANSFER | MATCHDAY | CLUB | ACADEMY — drives the badge text/colour.
- `status`: OFFICIAL | CONFIRMED | REPORTED | RUMOUR — drives the attribution tag.
  RUMOUR/REPORTED frames must carry `source`.
- `mood`: maps to a mascot pose — celebrate | tension | roar | react | confident | point.
- `highlight`: exact substring of `text` rendered in red; renderer errors if not found.
- `beats`: 2–4 entries.

## Component 3: `render.py` (template spec)

Standalone CLI: `python render.py <story.json> [--out DIR] [--frames-only]`.
No network access, no AI — pure deterministic rendering, testable with fixtures.

**Canvas:** 1080×1920. Palette (from `build_character.py`): RED `(198,36,30)`,
DRED `(120,20,20)`, WHITE, CREAM `(255,226,222)`, INK `(22,14,14)`, CORAL (sampled).
Fonts: Anton (headlines), Bebas Neue (badges, tags, kickers).

**Frame layout (all frames share):**
- Background: ink-to-dark-red vertical gradient + the brand splatter texture treatment
- Mascot pose (per `mood`) filling upper ~60%, masked/faded into the background
- Category badge top-left: Bebas, small red block, e.g. `TRANSFER NEWS` / `MATCHDAY` /
  `CLUB NEWS` / `ACADEMY WATCH`
- Logo badge (small circular mascot avatar from `logo-avatar.png`) bottom-centre,
  sitting above the banner — mirroring Daily Mail's badge placement
- Headline banner bottom third: slightly angled (~2°) black banner block, Anton all-caps
  white text, `highlight` substring in RED; 2–3 lines max, auto-sized to fit
- Status/attribution tag below banner for REPORTED/RUMOUR: Bebas small caps, CREAM,
  e.g. `RUMOUR — PER SKY SPORTS` (legible, not hidden)

**Frame sequence:** hook frame → one frame per beat → end frame
(end frame: mascot `point` pose + `FOLLOW FOR DAILY UNITED NEWS` + `@handle`).
The handle is a constant at the top of `render.py` — set during implementation.

**Video assembly (ffmpeg):**
- Hook 3.0s, beats 3.5s each, end 2.0s → ~15–25s total depending on beat count
- Subtle ken-burns (slow zoompan, alternating direction) per frame; hard cuts
- Quiet whoosh SFX on each cut (single bundled CC0 .wav, low volume) so the file is not
  silent; **no music bed** — user adds a trending sound in the TikTok app when posting
- Encode: h264, yuv420p, 30fps, AAC audio, faststart — TikTok-safe spec, < 60s

**Outputs per story:** `output/<date>/<id>.mp4`, `<id>-caption.txt` (caption + hashtags
+ disclaimer line), and a copy of the story JSON for the record.

## Component 4: `sources.json`

User-editable feed registry. Initial set (exact URLs verified at implementation):

- **Tier 1** (can yield CONFIRMED/REPORTED): BBC Sport Man Utd RSS; Sky Sports football
  RSS; manutd.com official news; The Guardian football RSS. Romano/Ornstein/The Athletic
  via WebSearch (no public RSS) — Tier 1 for transfer status.
- **Tier 2** (REPORTED with attribution): Manchester Evening News Man Utd RSS;
  Google News RSS query for "Manchester United".
- **Tier 3** (RUMOUR only, always attributed): talkSPORT, Mirror, Sun — surfaced via
  Google News rather than direct feeds.

Each entry: `{ "name", "url", "tier", "type": "rss|search", "enabled" }`.

## Component 5: `PLAYBOOK.md` copy rules

- Hook: ≤ 8 words, present tense, one highlighted phrase, no clickbait lies
- Beats: ≤ 12 words each; each beat advances the story (no padding)
- Rumours: always attributed in-frame and in-caption; never presented as fact
- Caption: 1–2 sentences + engagement question + hashtag set
  (`#mufc #manutd #premierleague #football` + category/story-specific tags)
- Caption footer: `Unofficial fan content — not affiliated with Manchester United FC.`
- Posting workflow: review video → post via TikTok app → add trending sound at low
  volume under the video → post times guidance (UK evening peak; immediately for
  breaking news)

## Error handling

- Dead/changed feed → skip, note in run report, continue
- No newsworthy stories → evergreen fallback or "don't post today" recommendation
- `highlight` not found in `text` → renderer exits with clear error (Claude fixes JSON)
- Text too long for banner → auto-shrink one step, then hard error (copy must be cut)
- ffmpeg missing → clear install instructions; `--frames-only` still works
- Missing font/asset paths → checked at startup with explicit error messages

## Testing

- `tiktok/fixtures/` holds one story JSON per category incl. a RUMOUR — golden tests
- `render.py` run on fixtures must produce frames + MP4 with no network; visual review
  of frames is the acceptance check for template changes
- MP4 validated: 1080×1920, h264/yuv420p, AAC, ≤ 60s (ffprobe check in a small
  `validate.py` or inline in render)
- First live `/mufc-update` run is the end-to-end test, reviewed before first post

## Out of scope (deliberately)

- Auto-posting to TikTok (API restrictions; manual posting enables trending sounds)
- Press photos / real player imagery (copyright)
- Baked-in music beds (trending sounds added in-app perform better)
- Scheduling/unattended runs (can be added later once the template is proven)
- YouTube Shorts cross-posting (same MP4s would work — future option, not built now)
