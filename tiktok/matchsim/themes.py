"""Per-competition visual themes. Pure data + a resolver.

The renderer reads ONLY the resolved theme (never hard-coded competition
colours), so adding a competition = adding a THEMES entry. When Man Utd are
involved, a red-accent "home" treatment is layered on top.
"""

RED_MANCUNIAN = "#DA020E"

# `bg` is a 3-stop vertical gradient; `trophy` is a glyph key the renderer maps
# to a drawn badge; `ticker` is the scrolling edge text.
THEMES = {
    "ucl": {
        "key": "ucl", "name": "UEFA Champions League",
        "bg": ["#0b1030", "#131a48", "#080b24"],
        "accent": "#39e6e6", "gold": "#F5C451",
        "text": "#dbe3ff", "muted": "#9fb0ff",
        "trophy": "star", "ticker": "UEFA CHAMPIONS LEAGUE",
    },
    "epl": {
        "key": "epl", "name": "Premier League",
        "bg": ["#1b0a2e", "#2d0b4e", "#12071f"],
        "accent": "#00ff87", "gold": "#F5C451",
        "text": "#efe6ff", "muted": "#b9a3d6",
        "trophy": "crown", "ticker": "PREMIER LEAGUE",
    },
    "wc": {
        "key": "wc", "name": "FIFA World Cup",
        "bg": ["#0a2a14", "#0f3d1d", "#071f0f"],
        "accent": "#35e0a0", "gold": "#F5C451",
        "text": "#e6fff0", "muted": "#9fd6b8",
        "trophy": "cup", "ticker": "FIFA WORLD CUP",
    },
    "generic": {
        "key": "generic", "name": "Football",
        "bg": ["#101018", "#1a1a2a", "#0a0a12"],
        "accent": "#39e6e6", "gold": "#F5C451",
        "text": "#e6e6f0", "muted": "#9f9fb0",
        "trophy": "ball", "ticker": "MATCH SIMULATION",
    },
}


def resolve_theme(competition_key, united_home=False):
    """Return a fresh theme dict (never mutate the module THEMES)."""
    base = THEMES.get((competition_key or "").lower(), THEMES["generic"])
    t = dict(base)
    t["bg"] = list(base["bg"])  # deep-copy the mutable list too
    t["united_home"] = bool(united_home)
    if united_home:
        t["accent"] = RED_MANCUNIAN
        t["frame_glow"] = RED_MANCUNIAN
    else:
        t["frame_glow"] = t["accent"]
    return t


def is_united(match):
    fx = match["fixture"]
    return fx["home"]["abbr"] == "MUN" or fx["away"]["abbr"] == "MUN"
