"""Brand-first theming. Every video wears the RED MANCUNIAN identity — the
ink->dark-red gradient, RED/GOLD accents, brand fonts and logo. The competition
contributes ONLY a neon arena-ring tint, a display name, and a ghosted watermark;
it never repaints the whole frame.
"""

# RED MANCUNIAN brand palette (matches the news/betslip pipeline tokens).
BRAND_BG = ["#1C1310", "#2A0F0E", "#781414"]  # ink -> dark red
GOLD = "#F5C451"
RED = "#C6241E"
CREAM = "#FFE2DE"
MUTED = "#E8A0A0"

# Competition = ring tint + label + watermark only (not the base palette).
COMPETITIONS = {
    "ucl": {"name": "UEFA Champions League", "ring": "#39E6E6", "watermark": "UCL",
            "default_stage": "League Phase"},
    "epl": {"name": "Premier League", "ring": "#00FF87", "watermark": "EPL",
            "default_stage": "Matchweek 1"},
    "wc": {"name": "FIFA World Cup", "ring": "#39E6A0", "watermark": "26",
           "default_stage": "Group Stage"},
    "generic": {"name": "Football", "ring": "#F5C451", "watermark": "RM",
                "default_stage": "Friendly"},
}


def resolve_theme(competition_key, united_home=False):
    """Return the brand palette + the competition's ring tint / label / watermark.
    `united_home` is kept for callers but no longer changes the palette — the
    brand IS red for everyone now."""
    ck = (competition_key or "").lower()
    if ck not in COMPETITIONS:
        ck = "generic"
    comp = COMPETITIONS[ck]
    return {
        "key": ck,
        "name": comp["name"],
        "bg": list(BRAND_BG),          # brand background, always
        "accent": comp["ring"],        # neon arena ring = competition tint
        "gold": GOLD, "red": RED, "cream": CREAM,
        "text": CREAM, "muted": MUTED,
        "watermark": comp["watermark"],
        "united_home": bool(united_home),
        "frame_glow": RED,
    }


def is_united(match):
    fx = match["fixture"]
    return fx["home"]["abbr"] == "MUN" or fx["away"]["abbr"] == "MUN"
