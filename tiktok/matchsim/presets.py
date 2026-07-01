"""Team + competition presets, and xG derivation from strength ratings.

`attack` ~ goals a side tends to score vs average; `defense` ~ goals it tends
to concede (1.0 = average, <1.0 = solid, >1.0 = leaky). xG derivation applies
a home-advantage multiplier.
"""

HOME_ADV = 1.15

GENERIC_SCORERS = ["No. 9", "No. 10", "No. 7", "No. 11", "No. 8"]

TEAMS = {
    "MUN": {"name": "Man Utd", "color": "#DA020E", "monogram": "MUN",
            "attack": 1.75, "defense": 0.95,
            "scorers": ["Hojlund", "Garnacho", "Fernandes", "Mount", "Zirkzee"]},
    "MCI": {"name": "Man City", "color": "#6CABDD", "monogram": "MCI",
            "attack": 2.05, "defense": 0.80,
            "scorers": ["Haaland", "Foden", "Doku", "Alvarez"]},
    "LIV": {"name": "Liverpool", "color": "#C8102E", "monogram": "LIV",
            "attack": 1.95, "defense": 0.85,
            "scorers": ["Salah", "Nunez", "Diaz", "Gakpo"]},
    "ARS": {"name": "Arsenal", "color": "#EF0107", "monogram": "ARS",
            "attack": 1.90, "defense": 0.82,
            "scorers": ["Saka", "Jesus", "Odegaard", "Havertz"]},
    "RMA": {"name": "Real Madrid", "color": "#FEBE10", "monogram": "RMA",
            "attack": 2.00, "defense": 0.85,
            "scorers": ["Mbappe", "Vinicius", "Bellingham", "Rodrygo"]},
    "BAR": {"name": "Barcelona", "color": "#A50044", "monogram": "BAR",
            "attack": 1.95, "defense": 0.90,
            "scorers": ["Lewandowski", "Yamal", "Raphinha", "Pedri"]},
    "BAY": {"name": "Bayern", "color": "#DC052D", "monogram": "BAY",
            "attack": 2.00, "defense": 0.88,
            "scorers": ["Kane", "Musiala", "Sane", "Olise"]},
    "ENG": {"name": "England", "color": "#FFFFFF", "monogram": "ENG",
            "attack": 1.80, "defense": 0.85,
            "scorers": ["Kane", "Bellingham", "Foden", "Saka"]},
    "FRA": {"name": "France", "color": "#0055A4", "monogram": "FRA",
            "attack": 1.90, "defense": 0.85,
            "scorers": ["Mbappe", "Griezmann", "Dembele", "Kolo Muani"]},
}

COMPETITIONS = {
    "ucl": {"key": "ucl", "name": "UEFA Champions League",
            "default_stage": "League Phase"},
    "epl": {"key": "epl", "name": "Premier League",
            "default_stage": "Matchweek 1"},
    "wc": {"key": "wc", "name": "FIFA World Cup",
           "default_stage": "Group Stage"},
    "generic": {"key": "generic", "name": "Football",
                "default_stage": "Friendly"},
}


def resolve_team(x):
    """Accept an abbr key (str) or a dict of overrides. Returns a full record."""
    if isinstance(x, str):
        key = x.upper()
        if key not in TEAMS:
            raise ValueError(f"unknown team abbr {x!r}; pass a dict to override")
        base = {"abbr": key, **TEAMS[key]}
    elif isinstance(x, dict):
        if not x.get("name") or not x.get("abbr") or not x.get("color"):
            raise ValueError("team dict needs at least name, abbr, color")
        base = dict(x)
    else:
        raise ValueError(f"team must be str or dict, got {type(x)}")
    base.setdefault("monogram", base["abbr"][:3].upper())
    base.setdefault("attack", 1.3)
    base.setdefault("defense", 1.0)
    base.setdefault("scorers", list(GENERIC_SCORERS))
    base.setdefault("crest", None)
    return base


def resolve_competition(key):
    return COMPETITIONS.get((key or "").lower(), COMPETITIONS["generic"])


def compute_xg(home, away):
    lam_h = home["attack"] * away["defense"] * HOME_ADV
    lam_a = away["attack"] * home["defense"]
    return lam_h, lam_a
