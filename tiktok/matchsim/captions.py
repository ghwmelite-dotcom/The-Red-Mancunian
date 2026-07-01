"""Arcade collision-caption bank, keyed to event type / near-miss flavour.

ASCII-only on purpose: the renderer draws captions with the Anton/Bebas brand
fonts, which have no colour-emoji glyphs. Selection is deterministic given
(seed, index) so a rendered match is reproducible.
"""

POOLS = {
    "goal": ["GOAL!!!", "SCREAMER!", "GET IN!", "SMASHED IT!"],
    "woodwork": ["OFF THE BAR!", "RATTLED THE POST!", "SO CLOSE!"],
    "big_chance": ["INCHES AWAY!", "NEARLY!", "WHAT A CHANCE!"],
    "clash": ["CLASH!", "SMASH CONTACT!", "CRUNCHING!"],
    "mystery_ball": ["MYSTERY BALL!", "CHAOS!"],
}

_FALLBACK = "clash"


def _pool_key(event):
    if event["type"] == "near_miss":
        return event.get("flavour", _FALLBACK)
    return event["type"]


def caption_for(event, seed, index):
    """Deterministically pick an arcade caption for an event."""
    key = _pool_key(event)
    pool = POOLS.get(key, POOLS[_FALLBACK])
    return pool[(seed + index) % len(pool)]
