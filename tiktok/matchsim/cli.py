#!/usr/bin/env python3
"""MatchSim CLI. v1 (this plan) exposes `simulate` -> match JSON.

Usage:
    python tiktok/matchsim/cli.py simulate --home MUN --away RMA \
        --competition ucl --seed 21 [--home-xg 1.9 --away-xg 1.2] \
        [--venue "Old Trafford"] [--stage "Quarter-final"] [--date 2026-09-15] \
        [--out match.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tempfile

import engine
import schema
import prepare as prepare_mod
import timeline as timeline_mod
import render_match
import encode

DISCLAIMER = "Unofficial fan content - not affiliated with any club or competition."


def _cmd_simulate(args):
    m = engine.simulate(
        args.home, args.away, competition=args.competition, seed=args.seed,
        home_xg=args.home_xg, away_xg=args.away_xg,
        venue=args.venue, stage=args.stage, date=args.date,
    )
    try:
        schema.validate(m)
    except schema.SchemaError as e:
        print(f"schema error: {e}", file=sys.stderr)
        return 1
    public = {k: v for k, v in m.items() if not k.startswith("_")}
    text = json.dumps(public, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def _cmd_prepare(args):
    m = engine.simulate(
        args.home, args.away, competition=args.competition, seed=args.seed,
        home_xg=args.home_xg, away_xg=args.away_xg,
        venue=args.venue, stage=args.stage, date=args.date,
    )
    try:
        schema.validate(m)
    except schema.SchemaError as e:
        print(f"schema error: {e}", file=sys.stderr)
        return 1
    bundle = prepare_mod.prepare(m, n_frames=args.frames)
    public = {"match": {k: v for k, v in bundle["match"].items()
                        if not k.startswith("_")},
              "theme": bundle["theme"], "motion": bundle["motion"]}
    text = json.dumps(public, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def _cmd_render(args):
    m = engine.simulate(
        args.home, args.away, competition=args.competition, seed=args.seed,
        home_xg=args.home_xg, away_xg=args.away_xg,
        venue=args.venue, stage=args.stage, date=args.date,
    )
    try:
        schema.validate(m)
    except schema.SchemaError as e:
        print(f"schema error: {e}", file=sys.stderr)
        return 1
    fps = 30
    n_frames = round((args.pre + args.live + args.post) * fps)
    bundle = prepare_mod.prepare(m, n_frames=n_frames)
    tl = timeline_mod.build_timeline(bundle, fps=fps, pre=args.pre,
                                     live=args.live, post=args.post)
    out_mp4 = Path(args.out)
    sfx = []
    live_a = tl["acts"]["live"][0]
    post_a = tl["acts"]["post"][0]
    sfx.append((live_a / fps, 0.7))
    sfx.append((post_a / fps, 0.7))
    for i, fr in enumerate(tl["frames"]):
        if fr.get("goal"):
            sfx.append((i / fps, 1.0))
    with tempfile.TemporaryDirectory() as td:
        render_match.render_frames(bundle, tl, td)
        encode.encode(td, out_mp4, fps=fps, sfx_events=sfx)
    fx = m["fixture"]
    caption = (f"{fx['home']['name']} {fx['final']} {fx['away']['name']} - "
               f"a {bundle['theme']['name']} simulation. Who wins the rematch? "
               f"Comment your scoreline. #matchsim #football\n{DISCLAIMER}")
    out_mp4.with_name(out_mp4.stem + "-caption.txt").write_text(caption, encoding="utf-8")
    notes = (f"POST PLAN - {fx['home']['name']} vs {fx['away']['name']}\n"
             f"1. Upload {out_mp4.name} to TikTok.\n"
             f"2. Add a trending sound at ~20% volume.\n"
             f"3. Paste the caption from {out_mp4.stem}-caption.txt.\n")
    out_mp4.with_name(out_mp4.stem + "-post-notes.txt").write_text(notes, encoding="utf-8")
    print(f"wrote {out_mp4}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="MatchSim")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("simulate", help="simulate a match -> JSON")
    s.add_argument("--home", required=True)
    s.add_argument("--away", required=True)
    s.add_argument("--competition", default="generic")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--home-xg", type=float, default=None, dest="home_xg")
    s.add_argument("--away-xg", type=float, default=None, dest="away_xg")
    s.add_argument("--venue", default="")
    s.add_argument("--stage", default=None)
    s.add_argument("--date", default="")
    s.add_argument("--out", default=None)
    s.set_defaults(func=_cmd_simulate)
    p = sub.add_parser("prepare", help="simulate + theme + motion -> render-ready bundle JSON")
    p.add_argument("--home", required=True)
    p.add_argument("--away", required=True)
    p.add_argument("--competition", default="generic")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--home-xg", type=float, default=None, dest="home_xg")
    p.add_argument("--away-xg", type=float, default=None, dest="away_xg")
    p.add_argument("--venue", default="")
    p.add_argument("--stage", default=None)
    p.add_argument("--date", default="")
    p.add_argument("--frames", type=int, default=1140,
                   help="arena motion frames (default 1140 = ~38s at 30fps)")
    p.add_argument("--out", default=None)
    p.set_defaults(func=_cmd_prepare)
    rp = sub.add_parser("render", help="simulate + render -> MP4 + caption + post-notes")
    rp.add_argument("--home", required=True)
    rp.add_argument("--away", required=True)
    rp.add_argument("--competition", default="generic")
    rp.add_argument("--seed", type=int, default=0)
    rp.add_argument("--home-xg", type=float, default=None, dest="home_xg")
    rp.add_argument("--away-xg", type=float, default=None, dest="away_xg")
    rp.add_argument("--venue", default="")
    rp.add_argument("--stage", default=None)
    rp.add_argument("--date", default="")
    rp.add_argument("--pre", type=float, default=5.0)
    rp.add_argument("--live", type=float, default=40.0)
    rp.add_argument("--post", type=float, default=6.0)
    rp.add_argument("--out", required=True)
    rp.set_defaults(func=_cmd_render)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
