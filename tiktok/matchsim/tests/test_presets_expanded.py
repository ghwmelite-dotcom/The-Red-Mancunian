from presets import resolve_team, TEAMS


def test_new_clubs_present():
    for abbr in ["CHE", "TOT", "NEW", "AVL", "PSG", "INT", "MIL", "JUV", "NAP",
                 "ATM", "DOR"]:
        assert abbr in TEAMS, f"missing club {abbr}"


def test_world_cup_nations_present():
    # nations from the remaining WC 2026 fixtures (R32 from 2 Jul + R16 sides)
    for abbr in ["ESP", "POR", "CRO", "SUI", "ALG", "AUS", "EGY", "ARG", "CPV",
                 "COL", "GHA", "BRA", "MAR", "MEX", "NOR", "PAR", "CAN", "BEL",
                 "ENG", "FRA"]:
        assert abbr in TEAMS, f"missing nation {abbr}"


def test_every_team_record_is_well_formed():
    for abbr, t in TEAMS.items():
        rec = resolve_team(abbr)
        assert rec["abbr"] == abbr
        assert rec["color"].startswith("#") and len(rec["color"]) == 7, abbr
        assert rec["monogram"] and 1 <= len(rec["monogram"]) <= 3, abbr
        assert isinstance(rec["scorers"], list) and rec["scorers"], abbr
        assert rec["attack"] > 0 and rec["defense"] > 0, abbr


def test_roster_expanded():
    assert len(TEAMS) >= 40
