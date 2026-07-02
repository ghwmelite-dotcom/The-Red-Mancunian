# MatchSim Visual Overhaul Plan (Plan 5)

**Goal:** Close the density/texture gap with the "Smash Goal" reference — turn the flat
look into a dense, textured, branded broadcast frame. Direction validated by an approved
hero-frame prototype (`tiktok/output/_hero_prototype.py` → `_hero_upgraded.png`).

**Execution note:** implemented directly with rendered-frame visual inspection at each
step (the real QA for visual work), tests on the data/pure additions, and a final
code-review pass. On branch `feat/matchsim`.

## Decisions (from the user)
- **Nations get drawn flag discs** (IP-safe); **clubs keep colour+monogram orbs**.
- Full overhaul across all three acts.

## Tasks
1. **`presets.py`** — add a `FLAGS` table (simplified stripe sets for the 25 nations;
   clean tricolours exact, complex flags approximated by dominant colours) and have
   `resolve_team` attach `flag` (None for clubs). Test: every nation has a flag, clubs
   don't, and the render falls back to an orb when `flag` is None.
2. **`draw.py`** — new primitives (smoke-tested): `flag_disc(size, bands, orient)`,
   `team_disc(size, team)` (flag if `team['flag']` else `orb`), `pitch_texture(img)`
   (mowing stripes + dot grid), `watermark(text, cx, cy, size)`, `crowd_ring(cx, cy, r,
   seed, accent)`, `goal_net(cx, y_top)`, `caption_pill(text, accent)`,
   `bottom_banner(text, theme)`, `side_ticker(text, theme, offset)`.
3. **`render_match.py`** — overhaul: cache a full textured background per
   `(theme.bg, competition)` = gradient + stripes + dots + watermark + crowd ring;
   richer scoreboard (flag/colour chips + trophy divider + competition·stage·date
   sub-strip); goal net on the ring; bigger `team_disc`s (flags for nations); win-prob
   `%` labels retained; caption **stack** with drawn glyph pills; bottom banner; a side
   ticker that scrolls via `fr['t']`. Apply consistently to pre-match, live, full-time.
   Verify each act by rendering a preview frame and inspecting it.
4. **Re-render demos** (UCL clubs + WC nations), run the full suite, final code review.

## Deferred (unchanged from before)
Slow-mo goal replay + ball tracer, exact heraldry on complex flags (stars/crests),
crest images for clubs.
