"""Compose the engine's match dict with a resolved theme and an arena motion
track into a single render-ready bundle. This is the artifact the Plan 3
renderer consumes; it has no pixel/video concerns.
"""
import arena
import themes


def prepare(match, n_frames):
    theme = themes.resolve_theme(
        match["fixture"]["competition"],
        united_home=themes.is_united(match),
    )
    motion = arena.simulate_motion(match, n_frames=n_frames)
    return {"match": match, "theme": theme, "motion": motion}
