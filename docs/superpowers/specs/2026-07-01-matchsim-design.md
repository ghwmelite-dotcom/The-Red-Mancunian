---
name: matchsim
description: Procedural football match simulation video generator — turns any two teams into a retention-optimized TikTok/Shorts match clip driven by the Dixon-Coles model
status: approved
created: 2026-07-01
owner: Ozzy / Hodges & Co. Limited
supersedes: the draft PRD's Remotion/React technical approach
---

# MatchSim — Design Spec

## 1. Summary

MatchSim turns a single input (Team A vs Team B + strength) into a fully rendered
vertical (9:16) match-simulation video: top-down animated pitch, live scoreboard,
event captions, and — the differentiator — a **live win-probability bar driven by
the existing Dixon-Coles model** that swings on every goal. It runs on demand or in
batch, with zero manual animation.

This spec supersedes the draft PRD's central technical recommendation (Remotion /
React / TypeScript). See §3.

## 2. Decisions locked in brainstorming

| Decision | Choice | Rationale |
|---|---|---|
| **Stack** | Python + Pillow + ffmpeg | The entire repo is Python; there is no React/TS. The Dixon-Coles model and a proven motion-graphics renderer already exist in Python. |
| **Frame layout** | Layout B — horizontal pitch, top scoreboard, caption zone | Closest to the reference "Match Day Star" format; cleanest bands for overlays. |
| **v1 retention mechanics** | Win-prob bar, clock-as-progress bar, ball trail + tracers, kinetic goal moment, hook + end-card loop | High impact, low–medium cost, all buildable on the existing pipeline. |
| **v2 mechanics** | Live commentary ticker, momentum/pressure meter, upset detector | Deferred; leverage the same engine/win-prob track. |
| **Input mode** | xG per team + ~30-team preset table (manual xG fallback) | Matches `match_model.py`'s real interface; no new data infra. |
| **Video length** | Fixed ~50–60s target; compressed clock with dwell on goals | Predictable for batch posting, platform-friendly. |
| **Audio** | Baked SFX (whoosh transitions + goal roar), no music | Consistent with the news/betslip pipeline; trending sound added in-app. |
| **Team visuals** | Abstract: colour + initials + generic name pool | Avoids crest/kit/likeness IP risk (PRD non-goal). |

## 3. Why not Remotion (the PRD's pick)

The draft PRD assumed an "existing React/TypeScript stack" and recommended Remotion.
On inspection the repo has **no** React/TS (`package.json` absent); the whole channel
— news cards (`tiktok/render.py`, `frames.py`, `video.py`) and betslips
(`tiktok/bets/`) — is Python + Pillow → ffmpeg, and the Dixon-Coles model
(`match-analyst/scripts/match_model.py`) is Python. Remotion would require a new
Node/React toolchain, re-creating the branding token system in React, and bridging
to Python (or reimplementing Dixon-Coles) — directly fighting the PRD's own reuse and
no-new-dependency goals. Python-native satisfies every stated goal (G1–G5, NFR1–NFR5).
The PRD's **event-timeline JSON contract is kept unchanged** — it is language-agnostic.

## 4. Architecture & data flow

```
fixture(s) → [engine] → match JSON (event timeline + win-prob track)
           → [renderer] → PNG frames → [ffmpeg + SFX mux] → MP4 + caption + post-notes
```

The **match JSON is the single interface** between engine and renderer, enabling each
half to be developed, tested, and swapped independently (NFR4, NFR5). Batch mode wraps
the single-match flow over a fixture list; a failure in one fixture does not halt the
batch (FR14).

## 5. Module boundaries — new package `tiktok/matchsim/`

Placed as a sibling to `tiktok/bets/`, following the repo's existing structure.

- **`dixon_coles.py`** — self-contained copy of the Dixon-Coles core (`poisson_pmf`,
  `dc_tau`, `score_matrix`, `derive_markets`) refactored out of
  `match-analyst/scripts/match_model.py`. Vendored (not imported) because the skill's
  copy lives in a transient extracted directory; MatchSim must stand alone and be
  unit-testable. Pure functions, ~60 lines.
- **`presets.py`** — team table `{name, abbr, color, attack, defense}` for ~30 common
  teams → `(home_xg, away_xg)`; plus a per-team generic scorer-name pool. Manual xG
  fallback for teams not in the table (FR1, addresses the "teams not in ratings DB"
  user story).
- **`engine.py`** — pure `simulate(home, away, seed) → match dict`. Samples a final
  score from the DC score-matrix, places goal minutes across 90' (+ optional stoppage),
  generates `chance` events at a rate tied to attack rating for pacing (FR2, FR3),
  stamps `half_time`/`full_time`. Deterministic per seed (FR5). No video concerns.
- **`winprob.py`** — `win_prob(score_home, score_away, minutes_remaining, home_xg,
  away_xg) → {home, draw, away}`. Scales λ by remaining fraction of the match, runs DC
  over remaining goals, folds in the current score. Produces a per-minute `winprob`
  track for the timeline. Property: the three outcomes sum to ~1.0 and shift toward the
  scoring side after a goal.
- **`motion.py`** — illustrative dot/ball positioning: 11 dots per side biased toward
  the ball and the in-possession attacking third, converging on shot/goal events.
  Seeded and deterministic; **not tactical** (per non-goals). Pure functions of
  (phase, event context) → positions.
- **`render_match.py`** — Pillow frame renderer reusing brand tokens, fonts
  (Anton/Bebas), palette (RED/GOLD/CREAM on ink→dark-red gradient), and easing helpers
  established in `make_video.py`/`frames.py`. Draws the Layout B frame and all five v1
  mechanics (§7). Emits PNG frames.
- **`matchsim.py`** — CLI orchestration. Single: `--home ENG --away BEL [--home-xg
  X --away-xg Y] [--seed N] [--out DIR] [--platform tiktok|youtube]`. Batch: `--batch
  fixtures.json`. Wires engine → renderer → ffmpeg mux; writes MP4 + `-caption.txt` +
  `-post-notes.txt`, matching `render.py` conventions and per-platform variants.
- **`assets/`** — SFX (reuse `tiktok/assets/whoosh.wav`; add a crowd-roar clip).
- **`fixtures/`** — example match JSONs + a batch fixture list (e.g. a World Cup group).
- **`tests/`** — see §9.

## 6. Data model (extends the PRD timeline)

```json
{
  "fixture": {
    "home": { "name": "England", "abbr": "ENG", "color": "#CE1124" },
    "away": { "name": "Belgium", "abbr": "BEL", "color": "#0F0F0F" },
    "seed": 12345,
    "final": "1-1"
  },
  "events": [
    { "minute": 3,  "type": "chance", "team": "home" },
    { "minute": 23, "type": "goal", "team": "home", "scorer": "Kane", "scoreAfter": "1-0" },
    { "minute": 45, "type": "half_time", "scoreAfter": "1-0" },
    { "minute": 61, "type": "chance", "team": "away" },
    { "minute": 78, "type": "goal", "team": "away", "scorer": "Doku", "scoreAfter": "1-1" },
    { "minute": 90, "type": "full_time", "scoreAfter": "1-1" }
  ],
  "winprob": [
    { "minute": 0,  "home": 0.52, "draw": 0.27, "away": 0.21 },
    { "minute": 23, "home": 0.71, "draw": 0.20, "away": 0.09 },
    { "minute": 78, "home": 0.34, "draw": 0.40, "away": 0.26 }
  ]
}
```

`event.type` ∈ {`chance`, `goal`, `half_time`, `full_time`}. `scorer` is drawn from the
preset name pool (generic if the team is unknown). `winprob` is sampled at kickoff, at
every goal, and at a fixed cadence for smooth bar interpolation.

## 7. v1 retention mechanics (renderer)

1. **Live win-probability bar** — three-segment bar (home/draw/away) fed by the
   `winprob` track; animates from the old split to the new on each goal with a swing
   callout (e.g. "▲ BEL +14%"). Labelled "LIVE WIN PROBABILITY · DIXON-COLES".
2. **Clock-as-progress bar** — thin bar under the scoreboard filling 0→100% as the
   match clock advances; reduces drop-off.
3. **Ball trail + shot tracers + speed lines** — fading trail behind the ball; a tracer
   line on shots/goals. Keeps the pitch feeling alive.
4. **Kinetic goal moment** — on each goal: full-frame flash, screen shake, ~1.5s
   slow-mo dwell, net-ripple accent, large rotated "GOAL", scorer card slides in.
5. **First-second hook + end-card loop** — cold-open stakes line ("Can Belgium cause
   the upset?"); end card with a CTA ("Comment your scoreline / who wins the rematch?")
   to drive engagement and loops.

## 8. Pacing (fixed ~55s target)

90 match-minutes map into a fixed video length. Quiet spells fast-forward; each goal
triggers a dwell beat (~1.5s slow-mo + win-prob swing). Video timeline: cold-open hook
(~2s) → match play (~45s) → full-time + end-card CTA (~6s). Length is configurable but
predictable, so a batch renders to known duration.

## 9. Audio

Frames render silent. ffmpeg muxes `whoosh.wav` at scene transitions and layers a
crowd-roar on goal minutes (same technique as `make_video.py`). No music track — a
trending sound is added at ~20% volume in the TikTok app; YouTube Shorts posts as-is.

## 10. Testing

- **Engine determinism**: same `(home, away, seed)` ⇒ byte-identical match JSON.
- **Win-prob correctness**: outcomes sum to ~1.0 at every minute; after a home goal,
  `home` probability strictly increases vs the pre-goal value.
- **Schema validation**: a `validate()` on the match dict (mirrors `story.py`),
  enforcing event types, minute ranges, `scoreAfter` format, and presence of `winprob`.
- **Golden preview frame**: render a fixed timeline's key frames to
  `tiktok/output/_preview` and eyeball before live runs (mirrors the existing habit).

## 11. Non-functional targets

- **NFR1 render time**: a ~55s video (≈1650 frames @ 30fps) renders in under ~2 min on
  standard hardware; batch of 6 under ~15 min. If frame generation is the bottleneck,
  optimize with cached static layers (the `cl()` cache pattern in `make_video.py`).
- **NFR2 cost**: no paid API in the v1 core loop.
- **NFR3 portability**: runs locally via Python; no cloud dependency to produce a video.
- **NFR4/5**: engine and renderer decoupled via the match JSON.

## 12. Milestones

| Phase | Deliverable |
|---|---|
| M1 | `dixon_coles.py` + `engine.py` + `winprob.py` + `presets.py`: fixture → match JSON (with win-prob track), unit-tested, no video. |
| M2 | `render_match.py`: render a fixed hardcoded match JSON to MP4 in Layout B with the five v1 mechanics. |
| M3 | `matchsim.py`: wire engine → renderer → ffmpeg end-to-end, single command, + caption/post-notes. |
| M4 | Batch mode: fixture list → directory of MP4s; per-fixture failure isolation. |
| M5 | Polish: goal-moment timing, tracers, SFX mix, preview-frame pass against the reference. |
| v2 | Commentary ticker, momentum meter, upset detector; optional AI voice, real Dixon-Coles ratings feed. |

## 13. Out of scope for v1

Real player likenesses/footage/licensed crests; tactical/formation realism; live
real-match syncing; in-app auto-publishing; AI voice commentary; web UI; multi-language
captions. (All per the PRD non-goals.)

## 14. Success metrics

- A generated video is indistinguishable in *format* from the reference to a casual
  viewer, and the win-prob bar makes it feel more premium than typical sim reels.
- A 6-fixture batch renders unattended in under 15 minutes.
- Zero manual animation/editing between "pick two teams" and "file ready to post."
```
