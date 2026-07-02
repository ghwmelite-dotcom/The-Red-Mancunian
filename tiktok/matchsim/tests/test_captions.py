from captions import caption_for, POOLS


def test_goal_uses_goal_pool():
    ev = {"type": "goal", "team": "home", "scorer": "Kane"}
    assert caption_for(ev, seed=1, index=0) in POOLS["goal"]


def test_near_miss_uses_flavour_pool():
    ev = {"type": "near_miss", "flavour": "woodwork"}
    assert caption_for(ev, seed=1, index=0) in POOLS["woodwork"]


def test_unknown_flavour_falls_back_to_clash_pool():
    ev = {"type": "near_miss", "flavour": "totally_unknown"}
    assert caption_for(ev, seed=1, index=0) in POOLS["clash"]


def test_deterministic_for_same_seed_and_index():
    ev = {"type": "goal"}
    a = caption_for(ev, seed=7, index=3)
    b = caption_for(ev, seed=7, index=3)
    assert a == b


def test_index_varies_selection_within_pool():
    ev = {"type": "near_miss", "flavour": "clash"}
    picks = {caption_for(ev, seed=0, index=i) for i in range(len(POOLS["clash"]) * 2)}
    assert len(picks) > 1


def test_captions_are_ascii_no_emoji():
    for pool in POOLS.values():
        for text in pool:
            assert text.isascii(), f"non-ascii caption: {text!r}"
