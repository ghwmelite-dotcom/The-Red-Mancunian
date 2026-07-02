from themes import resolve_theme, is_united, BRAND_BG, RED, GOLD


def test_resolve_known_competition():
    t = resolve_theme("ucl")
    assert t["key"] == "ucl"
    assert t["name"] == "UEFA Champions League"
    assert t["accent"] == "#39E6E6"  # competition ring tint


def test_unknown_falls_back_to_generic():
    assert resolve_theme("nope")["key"] == "generic"


def test_brand_palette_is_constant_across_competitions():
    # brand-first: the background + brand accents are identical for every comp
    for ck in ("ucl", "epl", "wc", "generic"):
        t = resolve_theme(ck)
        assert t["bg"] == BRAND_BG
        assert t["red"] == RED and t["gold"] == GOLD
        assert t["frame_glow"] == RED  # brand red glow, never a competition tint


def test_only_the_ring_tint_varies_by_competition():
    assert resolve_theme("ucl")["accent"] != resolve_theme("wc")["accent"]


def test_united_home_does_not_repaint_the_brand():
    t = resolve_theme("ucl", united_home=True)
    assert t["united_home"] is True
    assert t["accent"] == "#39E6E6"  # still the competition ring, not overridden


def test_resolve_does_not_mutate_module_bg():
    t = resolve_theme("wc")
    t["bg"].append("#000000")
    assert BRAND_BG == ["#1C1310", "#2A0F0E", "#781414"]


def test_is_united_detects_either_side():
    def m(h, a):
        return {"fixture": {"home": {"abbr": h}, "away": {"abbr": a}}}
    assert is_united(m("MUN", "RMA")) is True
    assert is_united(m("RMA", "MUN")) is True
    assert is_united(m("LIV", "ARS")) is False
