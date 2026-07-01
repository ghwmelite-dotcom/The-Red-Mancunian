---
name: matchsim
description: Procedural football match simulation video generator — turns any two teams into a retention-optimized, premium "arena-clash" TikTok/Shorts match clip driven by the Dixon-Coles model, themeable across competitions
status: approved
created: 2026-07-01
owner: Ozzy / Hodges & Co. Limited
supersedes: the draft PRD's Remotion/React approach AND the tactical top-down-pitch renderer
reference: "Smash Goal" arena-clash format (studied from @smashgoal0 sample) — adopted structurally, re-skinned and improved
---

# MatchSim — Design Spec (v2, arena-clash)

## 1. Summary

MatchSim turns a single input (Team A vs Team B + strength + competition) into a
fully rendered vertical (9:16) match-simulation video in a premium **"arena-clash"**
style: a glowing circular stadium arena where each team is a glossy disc that drifts
and clashes, over a live scoreboard, arcade collision captions, goal replays, and — the
differentiator no competitor has — a **live win-probability bar driven by the existing
Dixon-Coles model**. It runs on demand or in batch, with zero manual animation, and
**themes per competition** so it serves United-first content plus EPL, Champions League,
European leagues, and internationals from the 2026/27 season onward.

Supersedes both the draft PRD's Remotion recommendation (§3) and the earlier
tactical-pitch renderer concept (replaced by arena-clash, §7).

## 2. Decisions locked in brainstorming

| Decision | Choice | Rationale |
|---|---|---|
| **Stack** | Python + Pillow + ffmpeg | Whole repo is Python; the Dixon-Coles model and a proven motion-graphics renderer already exist in Python. |
| **Visual metaphor** | **Arena-clash** (circular neon arena, each team = one clashing disc + ball + goal) | The format the owner selected; distinctive, "glued"-friendly, simpler than 22-dot tactical movement. |
| **Team identity** | Colour + monogram discs (default), real **national flags** for countries, **optional crest drop-in** per team | Safest for the unofficial fan channel; works for every team; crests are trademarked so opt-in only. |
| **Theming** | **Per-competition theme system**; United matches get a RED MANCUNIAN red-accent treatment | Serves the multi-competition scope authentically and scalably. |
| **Visual quality bar** | Premium: brand display fonts (Anton/Bebas), glossy 3D orbs, stadium arena w/ spotlight+depth, glassmorphism panels, gradient win-prob & two-sided stat bars, motion trails, gold-laurel winner | Approved from the v3 mockup. All effects map to Pillow techniques in `make_video.py`. |
| **Structure** | Three acts: pre-match hype → live sim → full-time analytics | Matches the reference and gives a complete hook→payoff arc. |
| **v1 retention mechanics** | Live Dixon-Coles win-prob bar, accelerated match clock, ball trail + shot tracers, kinetic goal moment (replay + slow-mo + confetti), pre-match hook + full-time end-card | High impact, low–medium cost. |
| **v2 mechanics** | Commentary ticker, momentum/pressure meter, upset detector, "mystery ball" chaos mechanic | Deferred; leverage the same engine. |
| **Input mode** | xG per team + preset table (manual xG fallback) | Matches `match_model.py`'s interface; no new data infra. |
| **Video length** | Fixed ~50s target; accelerated clock, dwell on goals | Predictable for batch; matches reference (~50s). |
| **Audio** | Baked SFX (whoosh, clash thuds, crowd roar on goals), no music | Consistent with the news/betslip pipeline; trending sound added in-app. |
| **Analytics** | Credible stats (possession, shots, xG) + goal timeline | Beats the reference's gimmicky "wall bounces"; grounded in the model. |

## 3. Why not Remotion (the PRD's pick)

The draft PRD assumed an "existing React/TypeScript stack" and recommended Remotion. The
repo has **no** React/TS (`package.json` absent); the whole channel — news cards
(`tiktok/render.py`, `frames.py`, `video.py`) and betslips (`tiktok/bets/`) — is Python +
Pillow → ffmpeg, and the Dixon-Coles model (`match-analyst/scripts/match_model.py`) is
Python. Remotion would require a new Node/React toolchain, re-creating the branding
tokens in React, and bridging to Python for the stats — fighting the PRD's own reuse and
no-new-dependency goals. Python-native satisfies every goal (G1–G5, NFR1–NFR5). The
event-timeline JSON contract is kept — it is language-agnostic.

## 4. Scope — competitions & teams

MatchSim is **not World-Cup-only**. It serves all major football with an emphasis on
Manchester United, from the 2026/27 season:

- **Competitions (v1 presets):** UEFA Champions League, Premier League, World Cup /
  international windows, plus a generic "European league/cup" fallback. Each is a theme
  (§5) with its own accent colours, trophy/badge glyph, stage labels (e.g. "LEAGUE PHASE
  · MD 1", "ROUND OF 32", "MATCHWEEK 5"), and ticker text.
- **Teams (v1 presets):** Manchester United (first-class), the rest of the "big" EPL and
  European clubs, and major national teams — each as `{name, abbr, color, color2,
  monogram, crest?}`. Any team not in the table can be passed manually
  (`--home-name --home-color …`). National-team games use flag assets; club games use
  colour+monogram discs (crest optional).
- **United emphasis:** when either side is Man Utd, the theme applies a RED MANCUNIAN
  red-accent home treatment (frame glow, red-weighted palette) over the competition base.

## 5. Theme system

A `theme` is a small declarative record resolved from the competition (and whether United
is involved):

```
Theme = {
  key, name, stageLabelFmt,
  bg_gradient, accent, accent2, arena_ring, text, muted,
  trophy_glyph, ticker_text, united_home: bool
}
```

The renderer reads only the theme + the match JSON — never hard-coded competition colours.
Adding a competition = adding a theme record. United-red treatment = a theme modifier
applied when `united_home` is true.

## 6. Architecture, modules & data flow

```
fixture(s) → [engine] → match JSON (events + win-prob + analytics)
           → [arena]  → motion/collision track (positions per frame, clash events)
           → [renderer + theme] → PNG frames → [ffmpeg + SFX mux] → MP4 + caption + post-notes
```

The **match JSON is the contract** between the statistical engine and everything visual
(NFR4/5). New package **`tiktok/matchsim/`** (sibling to `tiktok/bets/`):

- **`dixon_coles.py`** — vendored, self-contained DC core (`poisson_pmf`, `dc_tau`,
  `score_matrix`, `derive_markets`) refactored out of `match_model.py`. Vendored because
  the skill's copy lives in a transient extracted dir. Pure, ~60 lines.
- **`presets.py`** — team table + competition presets + per-team scorer-name pools.
  Manual-override fallback for unknown teams/competitions.
- **`themes.py`** — theme records (§5) + the United-red modifier + theme resolver.
- **`engine.py`** — pure `simulate(home, away, competition, seed) → match dict`: samples
  the final score from the DC score-matrix, places goal minutes, generates chance/shot &
  near-miss events (rate tied to attack rating) for captions & pacing, computes the
  win-prob track (via `winprob.py`) and full-time analytics (possession/shots/xG from the
  model + seeded variance). Deterministic per seed (FR5). No video concerns.
- **`winprob.py`** — `win_prob(score_h, score_a, minutes_left, λ_h, λ_a)`: DC over the
  remaining match folded onto the current score → live win-prob; sums to ~1, swings on
  goals.
- **`arena.py`** — lightweight deterministic 2-D physics of the discs + ball (+ optional
  mystery third ball) inside the circle: drift, attraction toward the ball, disc–disc
  **clashes**, and ball acceleration toward the (occasionally moving) goal at the engine's
  scripted shot/goal minutes. Emits per-frame positions and a **clash/near-miss event
  track** that drives arcade captions. Seeded; does not change the outcome (the engine
  owns truth) — it produces the *visual motion and flavour events* only.
- **`captions.py`** — arcade caption template bank keyed to event types (clash, near-miss,
  woodwork, big-chance, goal, mystery-ball). Deterministic pick by seed+index.
- **`render_match.py`** — Pillow renderer implementing the premium visual system (§7) and
  the three acts, driven by the match JSON + arena track + resolved theme. Emits PNGs.
- **`matchsim.py`** (CLI) — single: `--home ENG --away BEL --competition wc [--home-xg X
  --away-xg Y] [--seed N] [--out DIR] [--platform tiktok|youtube]`; batch: `--batch
  fixtures.json`. Wires engine → arena → renderer → ffmpeg; writes MP4 + `-caption.txt`
  + `-post-notes.txt` (parity with `render.py`, TikTok + YouTube variants).
- **`assets/`** — SFX (whoosh, clash thud, crowd roar), `flags/` (national), optional
  `crests/<ABBR>.png` drop-in. **`fixtures/`** examples + a batch list. **`tests/`**.

## 7. Visual system & three acts (the premium bar)

Global visual language (from the approved v3 mockup): brand fonts **Anton** (numbers/
headlines) + **Bebas** (labels); **glossy 3-D orbs** (radial highlight → team colour →
shadow, rim ring, glow halo on the United/possessing side); **stadium arena** (radial
depth gradient, soft spotlight, glowing goal net, inner ring line, centre spot, ball
motion trail); **glassmorphism** panels (translucent + blur + gold hairline);
**gradient** win-prob segments and **two-sided** stat bars; gradient tickers; vignette +
dot-grid texture; theme-tinted frame with glow (red on United games). All reproducible in
Pillow via gradients, `GaussianBlur` glows, rounded panels, and layered shadows.

**Act 1 — Pre-match hype (~0–6s):** competition lockup (trophy + name) and stage/date;
account + location; "KICK OFF IN · 3-2-1" countdown; two team orbs with "VS"; competition
+ venue line; ghosted watermark; scrolling side + bottom tickers.

**Act 2 — Live sim (~6–44s):** zoned layout — header (account + ● LIVE) → scoreboard
(white clock tile with accelerated mm:ss + dark team pill with colour chips, score, trophy
divider) → competition strip → **live Dixon-Coles win-prob bar** (with swing callout) →
arena (clashing orbs + ball + goal + trail/tracers) → arcade caption band. Goals trigger a
**kinetic goal moment**: flash, screen shake, "🔄 REPLAY · SLOW-MO" with a **path tracer**
+ **confetti**, scoreboard + win-prob update.

**Act 3 — Full-time (~44–50s):** "FULL TIME"; big score; **gold-laurel + WIN badge** on
the winner orb (glow); **MATCH ANALYTICS** glass panel with two-sided bars (possession,
shots, xG) + a **goal timeline** (0'–90' with glowing minute-stamped dots); tickers.

## 8. v1 retention mechanics → mapped to the format

1. **Live win-probability bar (Dixon-Coles)** — Act 2, swings on every goal. Signature.
2. **Accelerated match clock** — mm:ss counting up fast; a subtle progress feel (finish
   line visible) reduces drop-off.
3. **Ball trail + shot tracers** — motion energy in the arena; tracer on shots/goals.
4. **Kinetic goal moment** — flash + shake + slow-mo replay + tracer + confetti.
5. **Pre-match hook + full-time end-card** — countdown open; end-card CTA
   ("Comment your scoreline / who wins the rematch?") for engagement + loops.

## 9. Data model (extends the PRD timeline)

```json
{
  "fixture": {
    "home": { "name": "Man Utd", "abbr": "MUN", "color": "#DA020E", "monogram": "MUN", "crest": null },
    "away": { "name": "Real Madrid", "abbr": "RMA", "color": "#F4F4F4", "monogram": "RMA", "crest": null },
    "competition": "ucl", "stage": "League Phase · MD 1", "venue": "Old Trafford",
    "date": "2026-09-15", "seed": 12345, "final": "2-1"
  },
  "events": [
    { "minute": 24, "type": "goal", "team": "home", "scorer": "Højlund", "scoreAfter": "1-0" },
    { "minute": 31, "type": "near_miss", "team": "away", "flavour": "woodwork" },
    { "minute": 52, "type": "goal", "team": "away", "scorer": "Mbappé", "scoreAfter": "1-1" },
    { "minute": 80, "type": "goal", "team": "home", "scorer": "Garnacho", "scoreAfter": "2-1" },
    { "minute": 90, "type": "full_time", "scoreAfter": "2-1" }
  ],
  "winprob": [ { "minute": 0, "home": 0.44, "draw": 0.27, "away": 0.29 }, "…per goal + cadence" ],
  "analytics": { "possession": [58, 42], "shots": [14, 9], "xg": [2.1, 1.3] }
}
```

`event.type` ∈ {`chance`, `near_miss`, `clash`, `goal`, `mystery_ball`, `half_time`,
`full_time`}; `flavour` refines caption choice. `scorer` from the preset pool (generic if
unknown — no real-likeness claims). `analytics` derived from the model + seeded variance.

## 10. Pacing & audio

90 match-minutes → fixed ~50s video; quiet spells fast-forward, each goal gets a ~1.5s
slow-mo replay dwell. Frames render silent; ffmpeg muxes whoosh at act transitions, a
clash thud on disc collisions, and a crowd roar on goals. No music — a trending sound is
added at ~20% in the TikTok app; YouTube Shorts posts as-is.

## 11. Testing

- **Engine determinism**: same `(home, away, competition, seed)` ⇒ identical match JSON.
- **Win-prob correctness**: sums to ~1.0 each minute; a home goal strictly raises `home`.
- **Analytics sanity**: possession pair sums to 100; shots/xG non-negative and correlate
  with attack ratings.
- **Arena determinism**: same seed ⇒ identical motion/clash track; discs stay inside the
  circle; clash events only fire on actual disc overlap.
- **Schema validation**: `validate()` on the match dict (mirrors `story.py`).
- **Golden preview frame**: render key frames of each act to `tiktok/output/_preview` and
  eyeball before live runs.

## 12. Non-functional targets

- **NFR1 render**: ~50s video (~1500 frames @ 30fps) in under ~2 min; batch of 6 under
  ~15 min. Use the `cl()` static-layer cache from `make_video.py` for backgrounds/panels.
- **NFR2 cost**: no paid API in the v1 core loop.
- **NFR3 portability**: runs locally via Python; no cloud dependency to produce a video.
- **NFR4/5**: statistical engine, arena motion, and renderer decoupled via the match JSON
  + arena track; themes swappable without touching engine or renderer internals.

## 13. Milestones

| Phase | Deliverable |
|---|---|
| M1 | `dixon_coles.py` + `engine.py` + `winprob.py` + analytics: fixture → match JSON, unit-tested, no video. |
| M2 | `arena.py`: deterministic disc/ball motion + clash/near-miss track from a match JSON, unit-tested. |
| M3 | `render_match.py`: render a fixed match JSON to MP4 across the three acts in the premium visual system, one theme (UCL/United). |
| M4 | `matchsim.py`: wire engine → arena → renderer → ffmpeg end-to-end, single command + caption/post-notes. |
| M5 | `themes.py` + `presets.py`: multi-competition theming + team/competition presets + flag/crest drop-in. |
| M6 | Batch mode: fixture list → directory of MP4s; per-fixture failure isolation (FR14). |
| M7 | Polish: goal replay tracer + confetti + slow-mo, arcade caption timing, SFX mix, preview pass vs reference. |
| v2 | Commentary ticker, momentum meter, upset detector, mystery-ball mechanic, AI voice, real Dixon-Coles ratings feed. |

## 14. Out of scope for v1

Real player likenesses/footage; mandatory licensed crests (crests are opt-in drop-ins,
off by default); tactical/formation realism; live real-match syncing; in-app
auto-publishing; AI voice commentary; web UI; multi-language captions.

## 15. Success metrics

- A generated video matches the reference's *format* quality and, via the win-prob bar +
  credible analytics + premium visual system, reads as **more premium** than typical sim
  reels — to a casual viewer.
- Themes make a United UCL game, a World Cup tie, and an EPL match each feel
  competition-appropriate from the same engine.
- A 6-fixture batch renders unattended in under 15 minutes.
- Zero manual animation/editing between "pick two teams" and "file ready to post."

## 16. Reference attribution

Structure and several UI ideas (arena-clash metaphor, three-act flow, scoreboard, arcade
captions, goal replay, scrolling tickers, full-time analytics + timeline) are adapted from
the "Smash Goal" sample studied during design. MatchSim re-skins these to the RED
MANCUNIAN brand, adds a per-competition theme system, uses crest-safe colour/monogram
discs, and adds the live Dixon-Coles win-probability bar and credible analytics as its
differentiators. No assets from the reference are reused.
```
