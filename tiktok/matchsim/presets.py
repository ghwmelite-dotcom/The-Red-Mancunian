"""Team + competition presets, and xG derivation from strength ratings.

`attack` ~ goals a side tends to score vs average; `defense` ~ goals it tends
to concede (1.0 = average, <1.0 = solid, >1.0 = leaky). xG derivation applies
a home-advantage multiplier.
"""

HOME_ADV = 1.15

GENERIC_SCORERS = ["No. 9", "No. 10", "No. 7", "No. 11", "No. 8"]

TEAMS = {
    # --- Premier League ---
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
    "CHE": {"name": "Chelsea", "color": "#034694", "monogram": "CHE",
            "attack": 1.80, "defense": 0.88,
            "scorers": ["Palmer", "Jackson", "Madueke", "Nkunku"]},
    "TOT": {"name": "Tottenham", "color": "#132257", "monogram": "TOT",
            "attack": 1.85, "defense": 0.98,
            "scorers": ["Son", "Richarlison", "Kulusevski", "Johnson"]},
    "NEW": {"name": "Newcastle", "color": "#241F20", "monogram": "NEW",
            "attack": 1.70, "defense": 0.92,
            "scorers": ["Isak", "Gordon", "Barnes", "Wilson"]},
    "AVL": {"name": "Aston Villa", "color": "#95BFE5", "monogram": "AVL",
            "attack": 1.65, "defense": 0.95,
            "scorers": ["Watkins", "Bailey", "Rogers", "Duran"]},
    # --- European clubs ---
    "RMA": {"name": "Real Madrid", "color": "#FEBE10", "monogram": "RMA",
            "attack": 2.00, "defense": 0.85,
            "scorers": ["Mbappe", "Vinicius", "Bellingham", "Rodrygo"]},
    "BAR": {"name": "Barcelona", "color": "#A50044", "monogram": "BAR",
            "attack": 1.95, "defense": 0.90,
            "scorers": ["Lewandowski", "Yamal", "Raphinha", "Pedri"]},
    "ATM": {"name": "Atletico", "color": "#CB3524", "monogram": "ATM",
            "attack": 1.70, "defense": 0.80,
            "scorers": ["Griezmann", "J. Alvarez", "Sorloth", "Lino"]},
    "BAY": {"name": "Bayern", "color": "#DC052D", "monogram": "BAY",
            "attack": 2.00, "defense": 0.88,
            "scorers": ["Kane", "Musiala", "Sane", "Olise"]},
    "DOR": {"name": "Dortmund", "color": "#FDE100", "monogram": "DOR",
            "attack": 1.75, "defense": 0.98,
            "scorers": ["Guirassy", "Adeyemi", "Brandt", "Gittens"]},
    "PSG": {"name": "PSG", "color": "#004170", "monogram": "PSG",
            "attack": 2.00, "defense": 0.85,
            "scorers": ["Dembele", "Barcola", "Kolo Muani", "Ramos"]},
    "INT": {"name": "Inter", "color": "#0068A8", "monogram": "INT",
            "attack": 1.90, "defense": 0.82,
            "scorers": ["Lautaro", "Thuram", "Calhanoglu", "Dumfries"]},
    "MIL": {"name": "AC Milan", "color": "#FB090B", "monogram": "MIL",
            "attack": 1.80, "defense": 0.90,
            "scorers": ["Leao", "Pulisic", "Morata", "Reijnders"]},
    "JUV": {"name": "Juventus", "color": "#3B3B3B", "monogram": "JUV",
            "attack": 1.65, "defense": 0.85,
            "scorers": ["Vlahovic", "Yildiz", "N. Gonzalez", "Koopmeiners"]},
    "NAP": {"name": "Napoli", "color": "#12A0D7", "monogram": "NAP",
            "attack": 1.80, "defense": 0.85,
            "scorers": ["Lukaku", "Kvaratskhelia", "Politano", "Raspadori"]},
    # --- National teams (FIFA codes) ---
    "ENG": {"name": "England", "color": "#F4F4F4", "monogram": "ENG",
            "attack": 1.80, "defense": 0.85,
            "scorers": ["Kane", "Bellingham", "Foden", "Saka"]},
    "FRA": {"name": "France", "color": "#1E3A8A", "monogram": "FRA",
            "attack": 1.95, "defense": 0.82,
            "scorers": ["Mbappe", "Griezmann", "Dembele", "Kolo Muani"]},
    "ESP": {"name": "Spain", "color": "#C60B1E", "monogram": "ESP",
            "attack": 1.95, "defense": 0.82,
            "scorers": ["Yamal", "Morata", "Olmo", "Oyarzabal"]},
    "POR": {"name": "Portugal", "color": "#0E6B34", "monogram": "POR",
            "attack": 1.90, "defense": 0.85,
            "scorers": ["Ronaldo", "B. Fernandes", "Leao", "Felix"]},
    "GER": {"name": "Germany", "color": "#E8E8E8", "monogram": "GER",
            "attack": 1.85, "defense": 0.85,
            "scorers": ["Havertz", "Wirtz", "Musiala", "Fullkrug"]},
    "NED": {"name": "Netherlands", "color": "#FF6A00", "monogram": "NED",
            "attack": 1.80, "defense": 0.85,
            "scorers": ["Gakpo", "Depay", "Simons", "Malen"]},
    "ITA": {"name": "Italy", "color": "#0066CC", "monogram": "ITA",
            "attack": 1.70, "defense": 0.80,
            "scorers": ["Retegui", "Chiesa", "Scamacca", "Frattesi"]},
    "BRA": {"name": "Brazil", "color": "#FFDF00", "monogram": "BRA",
            "attack": 2.00, "defense": 0.82,
            "scorers": ["Vinicius", "Rodrygo", "Raphinha", "Endrick"]},
    "ARG": {"name": "Argentina", "color": "#75AADB", "monogram": "ARG",
            "attack": 1.95, "defense": 0.80,
            "scorers": ["Messi", "L. Martinez", "J. Alvarez", "Di Maria"]},
    "BEL": {"name": "Belgium", "color": "#E30613", "monogram": "BEL",
            "attack": 1.75, "defense": 0.90,
            "scorers": ["Lukaku", "De Bruyne", "Doku", "Trossard"]},
    "CRO": {"name": "Croatia", "color": "#D01C1F", "monogram": "CRO",
            "attack": 1.55, "defense": 0.92,
            "scorers": ["Kramaric", "Budimir", "Perisic", "Sucic"]},
    "MAR": {"name": "Morocco", "color": "#C1272D", "monogram": "MAR",
            "attack": 1.55, "defense": 0.85,
            "scorers": ["En-Nesyri", "Ziyech", "Diaz", "Ounahi"]},
    "MEX": {"name": "Mexico", "color": "#006847", "monogram": "MEX",
            "attack": 1.55, "defense": 0.95,
            "scorers": ["Gimenez", "Jimenez", "Lozano", "Vega"]},
    "USA": {"name": "USA", "color": "#0A3161", "monogram": "USA",
            "attack": 1.55, "defense": 0.95,
            "scorers": ["Pulisic", "Balogun", "Weah", "Reyna"]},
    "CAN": {"name": "Canada", "color": "#D80621", "monogram": "CAN",
            "attack": 1.50, "defense": 1.00,
            "scorers": ["J. David", "Larin", "Buchanan", "A. Davies"]},
    "NOR": {"name": "Norway", "color": "#BA0C2F", "monogram": "NOR",
            "attack": 1.70, "defense": 0.95,
            "scorers": ["Haaland", "Odegaard", "Sorloth", "Nusa"]},
    "PAR": {"name": "Paraguay", "color": "#D52B1E", "monogram": "PAR",
            "attack": 1.30, "defense": 1.00,
            "scorers": ["Sanabria", "Almiron", "Enciso", "Bareiro"]},
    "AUT": {"name": "Austria", "color": "#ED2939", "monogram": "AUT",
            "attack": 1.50, "defense": 0.95,
            "scorers": ["Arnautovic", "Baumgartner", "Gregoritsch", "Sabitzer"]},
    "SUI": {"name": "Switzerland", "color": "#B31942", "monogram": "SUI",
            "attack": 1.45, "defense": 0.92,
            "scorers": ["Embolo", "Freuler", "Vargas", "Ndoye"]},
    "ALG": {"name": "Algeria", "color": "#006233", "monogram": "ALG",
            "attack": 1.45, "defense": 0.98,
            "scorers": ["Mahrez", "Bounedjah", "Amoura", "Gouiri"]},
    "AUS": {"name": "Australia", "color": "#FFCD00", "monogram": "AUS",
            "attack": 1.30, "defense": 1.05,
            "scorers": ["Duke", "Irvine", "Goodwin", "Boyle"]},
    "EGY": {"name": "Egypt", "color": "#B01C2E", "monogram": "EGY",
            "attack": 1.50, "defense": 0.95,
            "scorers": ["Salah", "Mohamed", "Marmoush", "Trezeguet"]},
    "CPV": {"name": "Cape Verde", "color": "#003893", "monogram": "CPV",
            "attack": 1.25, "defense": 1.05,
            "scorers": ["Rodrigues", "Tavares", "Andrade", "Semedo"]},
    "COL": {"name": "Colombia", "color": "#FCD116", "monogram": "COL",
            "attack": 1.70, "defense": 0.90,
            "scorers": ["J. Rodriguez", "L. Diaz", "Duran", "Cordoba"]},
    "GHA": {"name": "Ghana", "color": "#006B3F", "monogram": "GHA",
            "attack": 1.45, "defense": 1.00,
            "scorers": ["J. Ayew", "Kudus", "Semenyo", "Sulemana"]},
    "SEN": {"name": "Senegal", "color": "#00853F", "monogram": "SEN",
            "attack": 1.60, "defense": 0.90,
            "scorers": ["I. Sarr", "N. Jackson", "Dia", "Ndiaye"]},
    "JPN": {"name": "Japan", "color": "#0033A0", "monogram": "JPN",
            "attack": 1.60, "defense": 0.90,
            "scorers": ["Kubo", "Mitoma", "Kamada", "Ueda"]},
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


# Simplified, IP-safe flag stripe sets for national teams: (bands, orientation).
# Clean tricolours are exact; complex flags (stars/crests/checks) are approximated
# by their dominant colours. Clubs have no flag and render as colour+monogram orbs.
FLAGS = {
    "ENG": (["#FFFFFF", "#CE1124", "#FFFFFF"], "h"),
    "FRA": (["#0055A4", "#FFFFFF", "#EF4135"], "v"),
    "ESP": (["#C60B1E", "#FFC400", "#FFC400", "#C60B1E"], "h"),
    "POR": (["#0E6B34", "#0E6B34", "#C8102E", "#C8102E", "#C8102E"], "v"),
    "GER": (["#000000", "#DD0000", "#FFCE00"], "h"),
    "NED": (["#AE1C28", "#FFFFFF", "#21468B"], "h"),
    "ITA": (["#009246", "#FFFFFF", "#CE2B37"], "v"),
    "BRA": (["#009C3B", "#FFDF00", "#002776"], "h"),
    "ARG": (["#74ACDF", "#FFFFFF", "#74ACDF"], "h"),
    "BEL": (["#000000", "#FDDA24", "#EF3340"], "v"),
    "CRO": (["#FF0000", "#FFFFFF", "#171796"], "h"),
    "MAR": (["#C1272D", "#006233"], "h"),
    "MEX": (["#006847", "#FFFFFF", "#CE1126"], "v"),
    "USA": (["#3C3B6E", "#FFFFFF", "#B22234"], "h"),
    "CAN": (["#FF0000", "#FFFFFF", "#FF0000"], "v"),
    "NOR": (["#BA0C2F", "#FFFFFF", "#00205B"], "h"),
    "PAR": (["#D52B1E", "#FFFFFF", "#0038A8"], "h"),
    "AUT": (["#ED2939", "#FFFFFF", "#ED2939"], "h"),
    "SUI": (["#D52B1E", "#FFFFFF", "#D52B1E"], "h"),
    "ALG": (["#006233", "#FFFFFF"], "v"),
    "AUS": (["#00843D", "#FFCD00"], "h"),
    "EGY": (["#CE1126", "#FFFFFF", "#000000"], "h"),
    "CPV": (["#003893", "#FFFFFF", "#003893"], "h"),
    "COL": (["#FCD116", "#FCD116", "#003893", "#CE1126"], "h"),
    "GHA": (["#CE1126", "#FCD116", "#006B3F"], "h"),
    "SEN": (["#00853F", "#FDEF42", "#E31B23"], "v"),
    "JPN": (["#FFFFFF", "#BC002D", "#FFFFFF"], "h"),
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
    base.setdefault("flag", FLAGS.get(base["abbr"].upper()))
    return base


def resolve_competition(key):
    return COMPETITIONS.get((key or "").lower(), COMPETITIONS["generic"])


def compute_xg(home, away):
    lam_h = home["attack"] * away["defense"] * HOME_ADV
    lam_a = away["attack"] * home["defense"]
    return lam_h, lam_a
