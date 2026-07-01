from themes import resolve_theme, is_united, THEMES


def test_resolve_known_theme():
    t = resolve_theme("ucl")
    assert t["key"] == "ucl"
    assert t["name"] == "UEFA Champions League"
    assert t["bg"][0].startswith("#")
    assert t["united_home"] is False


def test_resolve_unknown_falls_back_to_generic():
    t = resolve_theme("nope")
    assert t["key"] == "generic"


def test_united_home_applies_red_accent():
    t = resolve_theme("ucl", united_home=True)
    assert t["united_home"] is True
    assert t["accent"] == "#DA020E"
    assert t["frame_glow"] == "#DA020E"


def test_non_united_frame_glow_is_theme_accent():
    t = resolve_theme("ucl", united_home=False)
    assert t["frame_glow"] == t["accent"]
    assert t["accent"] != "#DA020E"


def test_resolve_does_not_mutate_module_theme():
    resolve_theme("ucl", united_home=True)
    assert THEMES["ucl"]["accent"] != "#DA020E"


def test_is_united_detects_either_side():
    def m(h, a):
        return {"fixture": {"home": {"abbr": h}, "away": {"abbr": a}}}
    assert is_united(m("MUN", "RMA")) is True
    assert is_united(m("RMA", "MUN")) is True
    assert is_united(m("LIV", "ARS")) is False
