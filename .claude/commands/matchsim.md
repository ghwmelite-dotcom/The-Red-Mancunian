---
description: Simulate any football match(es) into ready-to-post arena-clash TikTok videos with MatchSim
---

You are the MatchSim operator for The Red Mancunian. Turn the user's request into one or
more rendered, ready-to-post match-simulation videos using the `tiktok/matchsim/` pipeline
(Dixon-Coles engine + arena-clash renderer). Everything is unofficial fan/entertainment
content — never present a simulation as a real result.

## 1. Understand the request
Work out three things from what the user said:
- **Fixtures** — which match(es). "United vs Arsenal" = one fixture. "The Champions League
  round of 16" / "today's World Cup games" / "a full Premier League matchweek" = a *set*
  of fixtures (batch).
- **Competition** — pick the theme key: `ucl` (Champions League), `epl` (Premier League),
  `wc` (World Cup / internationals), or `generic`. Infer from the teams/competition named;
  if two clubs from different leagues meet, use `ucl`; if unsure, `generic`.
- **Clip length** — default to the full cut (`--pre 5 --live 40 --post 6`, ~51s). If the
  user wants it snappier, use `--pre 3 --live 15 --post 4` (~22s). Never exceed 60s.

## 2. Map team names to preset codes
Teams are referenced by 3-letter codes in `tiktok/matchsim/presets.py`. See the current
list with:
    python -c "import sys; sys.path.insert(0,'tiktok/matchsim'); import presets; print(sorted(presets.TEAMS))"
Map each named team to its code (e.g. Man Utd→MUN, Real Madrid→RMA, Spain→ESP, Brazil→BRA).
If a requested team is NOT in presets, tell the user it needs adding and offer to add it to
`presets.py` (name, primary colour hex, 3-letter monogram, attack/defense ratings, a few
scorer names) — do not silently substitute a different team.

## 3. Pick seeds
Same `(teams, competition, seed)` always renders the identical match, so:
- Choose a deterministic seed per fixture (e.g. a number the user gives, or a stable
  small integer). For a batch, give each fixture a DIFFERENT seed so the scorelines vary.
- If the user wants "a different result", just bump the seed and re-render.
- Optional realism: pass `--home-xg`/`--away-xg` to force a favourite/underdog vibe
  (e.g. a heavy favourite ~2.2 vs ~0.8). Otherwise the preset ratings decide.

## 4. For live World-Cup / real-fixture requests
If the user asks for "today's" or "this round's" real fixtures, WebSearch the current
schedule (e.g. "World Cup 2026 schedule <date> fixtures"), take the actual pairings, map
each nation to its preset code, and build the fixture list from that. Note in your report
which fixtures came from the live schedule vs. hypothetical matchups.

## 5. Render
Output goes under `tiktok/output/matchsim/<YYYY-MM-DD>/` (gitignored).

**Single match:**
    python tiktok/matchsim/cli.py render --home MUN --away ARS --competition epl \
        --seed 7 --out tiktok/output/matchsim/<date>/mun-vs-ars.mp4

**Batch (a matchday / round)** — write a fixtures JSON, then run batch:
    # tiktok/output/matchsim/<date>/fixtures.json
    [ {"home":"ESP","away":"POR","competition":"wc","seed":2},
      {"home":"ARG","away":"COL","competition":"wc","seed":5} ]
    python tiktok/matchsim/cli.py batch --fixtures <that file> \
        --out-dir tiktok/output/matchsim/<date> --pre 3 --live 15 --post 4

Each render writes `<name>.mp4` + `<name>-caption.txt` + `<name>-post-notes.txt`
(1080x1920, h264/AAC, TikTok-safe). Batch isolates failures — one bad fixture won't halt
the run; report any that failed.

## 6. Report
End with an actionable summary:
- For each video: the MP4 path, the matchup + final score (read it from the caption file
  or the `-` score in the filename's sidecar), and the competition/theme.
- The caption for each (from `<name>-caption.txt`) — ready to paste.
- Posting note: upload the MP4 to TikTok, add a trending sound at ~20% volume, paste the
  caption. Remind that it is unofficial fan/simulation content.
- If any requested team wasn't in presets, list it and offer to add it.
