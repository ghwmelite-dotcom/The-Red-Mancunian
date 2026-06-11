# Channel Kit — The Red Mancunian

## Identity at a glance
| Element | Value |
|---|---|
| Channel name | **The Red Mancunian** (keep — already strong) |
| Series name | **The Mancunian Way** |
| Tagline | *We don't buy glory. We build it.* |
| Tone | Opinionated, honest, a real fan — celebrates highs, owns the lows |
| Palette | Red `#C6241E` · Coral `#E86664` · White `#FFFFFF` · Ink `#16100E` (cream `#FFE2DE` for sub-lines) |
| Headline font | **Anton** (heavy condensed — poster/sports) |
| Accent font | **Bebas Neue** (tall condensed — kickers, taglines) |
| Symbol | **Character mascot** — a West African Manchester United superfan (afro, red shades, red kit), bold comic/vector illustration |
| Primary mark | `logo-avatar.png` — the mascot in a circular red/white/black ring |
| Upload cadence | Pick one day, hold it (e.g. "New episodes every Sunday") |

> Why the character: a recognizable fan persona is a far stronger identity for a personality-driven channel than a generic badge. Kit is generic red/white (no Nike swoosh, no club crest) to stay clear of trademark/IP — keep it that way.

---

## Channel description (paste-ready)
```
The Red Mancunian — Football Manager 2026, the Manchester United way.

No buying our way to glory. We're rebuilding United on academy graduates and
homegrown talent and chasing the Champions League the hard way — through coaching,
scouting, and faith in youth. This is The Mancunian Way.

🔴 New episodes [DAY] — saves, tactics, wonderkids and brutal honesty.
🔔 Subscribe and follow the rebuild from the academy up.

Unofficial fan content. Not affiliated with Manchester United FC.
Football Manager 2026 © Sports Interactive / SEGA. All trademarks belong to
their respective owners.
```

## Disclaimer (short — drop in every video description)
```
Unofficial fan channel — not affiliated with Manchester United FC.
FM 2026 © Sports Interactive / SEGA.
```

---

## First 3 episodes — launch arc
Designed as **premise → first test → first payoff**.

### EP1 — "I'm Rebuilding Man United With ONLY Academy Players"
- **Thumbnail:** your reaction face (or the bee badge) left; big bold **"NO SIGNINGS"**; a young player's profile right. Red/black.
- **Job:** sell the premise, set the rules on screen, meet the youth gems, scrape or lose match one to establish stakes.

### EP2 — "My Wonderkid Is Already Better Than [Star Player]"
- **Thumbnail:** split screen — your regen's stats vs an established star, big **"VS"**, text **"17 YEARS OLD"**.
- **Job:** spotlight the first breakout academy player (the character the audience adopts) + first big tactical win.

### EP3 — "This Result Could END The Save..."
- **Thumbnail:** tense reaction, fixture/scoreline graphic, text **"MUST WIN"**.
- **Job:** first real payoff or gut-punch — a knockout tie or six-pointer. Cliffhang into EP4.

---

## Reusable formulas

**Title formula:** lead with emotion or a number → imply a stake → keep the United/homegrown identity present.
- "I Sold a £40m Star to Promote a Kid — Here's What Happened"
- "This 16-Year-Old Just Saved My United Save"
- "We're Top of the League… But I Have a Problem"

**Thumbnail rules:**
- Character on one side, big text on the other — never a cluttered scene
- ≤ 4 words of headline, huge and high-contrast (white with ink outline)
- Red/coral/white palette every time (recognizable channel row)
- Match the pose to the emotion (confident = calm, react = shock, roar = win)
- Readable at phone size — if it's not legible as a thumbnail-of-a-thumbnail, simplify

---

## Brand assets — files & how to use them
Assets live in `branding/` (logos, banner) and `thumbnails/`. They're **PNGs composited from the real character art** (`character/hero-*.jpg`) using the brand fonts in `fonts/`.

| File | Size | Use |
|---|---|---|
| `logo-avatar.png` | 1024×1024 | Channel profile picture — **mascot in a circular ring** |
| `banner.png` | 2560×1440 | Channel art (text sits in YouTube's safe zone) |
| `logo-wordmark.png` | 1500×520 | Transparent lockup for video intros/outros/overlays |
| `thumbnails/thumb-ep1–3.png` | 1280×720 | Episode thumbnails |

**Character poses** (`branding/character/`, generated free via Pollinations.ai): `confident`, `react`, `tension`, `celebrate`, `point`, `roar`. Thumbnails map a pose to each episode's emotion (EP1 confident, EP2 react, EP3 roar). The art's coral background **feathers into the brand red**, so the character looks native to every layout.

**To regenerate or edit any asset:** everything is built by one script —
```
python build_character.py     # rebuilds avatar, wordmark, banner, all 3 thumbnails (~1.5s)
```
New episode thumbnail = copy a `thumb()` call in `build_character.py`, pick a `hero-*.jpg` pose, change the number/headline/subline. New poses: add to `character/gen.py` and re-run it (free, keyless).

> Consistency note: poses are stylistically consistent but not the *exact same face* (text-to-image). For a locked, identical mascot, regenerate poses from the hero with **Gemini Nano Banana** (free API key) using the hero image as reference.

---

**Episode skeleton (reuse every video):**
1. **Cold open / hook** (15–30s) — the stake for *this* episode
2. **The decisions** — transfers, tactics, team talks; *talk through your reasoning* (the reasoning IS the content)
3. **The match(es)** — edited highlights + live reaction, not full 90-min sims
4. **Cliffhanger out** — set up next episode

**Length:** start tight (8–12 min). Stretch to 12–18 once you've found your rhythm.

---

## Pre-record reminders
1. **Audio > video.** A decent USB mic is the single highest-leverage purchase. Viewers forgive cheap video; they bounce on bad audio.
2. **Cut dead air.** Jump-cut menu navigation. On-screen text for scorelines/fees/ages = pace + signals "effort" to YouTube's content rules.
3. **Be a character.** Your takes and reactions are why people subscribe — not the save file.
