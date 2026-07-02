from presets import resolve_team, FLAGS, TEAMS


def test_nations_have_valid_flags():
    for abbr in ["ENG", "FRA", "ESP", "POR", "GER", "BRA", "ARG", "MAR", "JPN",
                 "CRO", "MEX", "USA"]:
        t = resolve_team(abbr)
        assert t["flag"] is not None, abbr
        bands, orient = t["flag"]
        assert orient in ("h", "v")
        assert len(bands) >= 2
        assert all(b.startswith("#") and len(b) == 7 for b in bands), abbr


def test_clubs_have_no_flag():
    for abbr in ["MUN", "MCI", "RMA", "BAR", "PSG", "INT"]:
        assert resolve_team(abbr)["flag"] is None, abbr


def test_every_flag_key_is_a_real_team():
    for abbr in FLAGS:
        assert abbr in TEAMS, abbr
