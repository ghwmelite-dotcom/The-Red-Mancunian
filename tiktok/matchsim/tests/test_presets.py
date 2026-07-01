import pytest
from presets import resolve_team, resolve_competition, compute_xg


def test_resolve_known_team_by_abbr():
    t = resolve_team("MUN")
    assert t["name"] == "Man Utd"
    assert t["abbr"] == "MUN"
    assert t["color"].startswith("#")
    assert isinstance(t["scorers"], list) and t["scorers"]
    assert t["crest"] is None


def test_resolve_unknown_team_from_dict():
    t = resolve_team({"name": "Wrexham", "abbr": "WRX", "color": "#FF0000"})
    assert t["name"] == "Wrexham"
    assert t["monogram"] == "WRX"
    assert t["attack"] > 0 and t["defense"] > 0
    assert t["scorers"]


def test_resolve_unknown_team_missing_fields_raises():
    with pytest.raises(ValueError):
        resolve_team({"name": "NoAbbr"})


def test_resolve_competition():
    c = resolve_competition("ucl")
    assert c["key"] == "ucl"
    assert "name" in c and "default_stage" in c


def test_resolve_competition_unknown_falls_back_to_generic():
    c = resolve_competition("nope")
    assert c["key"] == "generic"


def test_compute_xg_home_advantage():
    home = resolve_team("MUN")
    away = resolve_team("MUN")
    lam_h, lam_a = compute_xg(home, away)
    assert lam_h > lam_a
