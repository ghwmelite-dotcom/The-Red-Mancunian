# The Red Mancunian — Project Hub

YouTube channel: **The Red Mancunian**
Series: **The Mancunian Way** — Football Manager 2026, Manchester United rebuilt on academy graduates and homegrown talent, chasing the Champions League the hard way.

## The concept (one line)
> We're not buying our way to glory — we're building it. This is The Mancunian Way.

**The rule of the save:** the *spine* of the team is academy graduates and homegrown players. The occasional dramatic signing is allowed (keeps deadline-day episodes alive), but the identity is youth-first. Win condition: a Champions League with a homegrown core.

## Folder contents
```
The-Red-Mancunian/
├── README.md                      ← you are here
├── branding/
│   ├── CHANNEL-KIT.md             ← name, description, disclaimer, titles, asset guide
│   ├── build_character.py         ← builds ALL assets from the character art (~1.5s)
│   ├── character/                 ← hero illustrations (hero-*.jpg) + gen.py (Pollinations)
│   ├── fonts/                     ← brand fonts (Anton, Bebas Neue)
│   ├── logo-avatar.png            ← profile picture (1024×1024, mascot in ring)
│   ├── logo-wordmark.png          ← transparent lockup (1500×520)
│   ├── banner.png                 ← channel art (2560×1440, text in safe area)
│   └── red mancunian.jpg          ← original style reference
├── scripts/
│   ├── EP1-SCRIPT.md              ← "NO SIGNINGS" — premise + first match
│   ├── EP2-SCRIPT.md              ← "BETTER THAN £100M?" — first wonderkid
│   └── EP3-SCRIPT.md              ← "MUST WIN" — first high-stakes payoff
├── thumbnails/
│   └── thumb-ep1–3.png            ← launch thumbnails, matched pose per episode (1280×720)
├── tiktok/                        ← daily TikTok news pipeline (see tiktok/PLAYBOOK.md)
│   ├── PLAYBOOK.md                ← format rules + posting workflow
│   ├── sources.json               ← news feeds + reliability tiers
│   ├── render.py                  ← story JSON → ready-to-post MP4 (run /mufc-update)
│   └── output/YYYY-MM-DD/         ← finished videos + captions
└── world-cup/                     ← 2026 World Cup growth play (time-sensitive)
    ├── FM26-RESEARCH.md           ← verified: FM26 has official licensed WC2026 mode
    ├── FLAGSHIP-SCRIPT.md         ← "I Simulated the ENTIRE 2026 World Cup in FM26"
    └── SHORTS-PLAYBOOK.md         ← Shorts template + 10-clip batch + recurring formats
```

**Identity:** character mascot — a West African Man Utd superfan, bold comic illustration. Generic red/white kit (no swoosh, no club crest) to stay clear of IP.
**Fonts:** Anton (condensed headline) + Bebas Neue (accents), in `branding/fonts/`.
**Palette:** Red `#C6241E` + Coral + White + ink. Everything is composited by `branding/build_character.py` — edit it and re-run to regenerate all assets. New character poses: add to `branding/character/gen.py` (free, keyless Pollinations.ai) and re-run.

## Quick-start checklist before first record
- [ ] Decent USB mic plugged in and levels tested (single highest-leverage thing)
- [ ] OBS set up: screen capture + mic (facecam optional)
- [ ] Logo exported to PNG, set as channel profile picture
- [ ] Banner exported to PNG, set as channel art
- [ ] Channel description pasted in (from CHANNEL-KIT.md)
- [ ] Disclaimer saved as a reusable description snippet
- [ ] EP1 script skimmed — know your 5 beats before you hit record
- [ ] Daily: run /mufc-update in Claude Code, review, post (see tiktok/PLAYBOOK.md)

## Legal note (keep it boring and safe)
Unofficial fan content. Not affiliated with Manchester United FC. Football Manager 2026 © Sports Interactive / SEGA. Branding uses the Manchester *worker bee* (a city symbol), **not** the club crest — keep it that way.
