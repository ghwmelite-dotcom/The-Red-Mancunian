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

COMP_HASHTAG = {"ucl": "#ucl #championsleague", "epl": "#premierleague",
                "wc": "#worldcup", "generic": ""}


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


def _render_one(home, away, competition, seed, out_mp4,
                home_xg=None, away_xg=None, venue="", stage=None, date="",
                pre=5.0, live=40.0, post=6.0, fps=30):
    m = engine.simulate(home, away, competition=competition, seed=seed,
                        home_xg=home_xg, away_xg=away_xg,
                        venue=venue, stage=stage, date=date)
    schema.validate(m)
    n_frames = round((pre + live + post) * fps)
    bundle = prepare_mod.prepare(m, n_frames=n_frames)
    tl = timeline_mod.build_timeline(bundle, fps=fps, pre=pre, live=live, post=post)
    out_mp4 = Path(out_mp4)
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
    tags = COMP_HASHTAG.get(competition, "")
    tag_str = f" {tags}" if tags else ""
    caption = (f"{fx['home']['name']} {fx['final']} {fx['away']['name']} - "
               f"a {bundle['theme']['name']} simulation. Who wins the rematch? "
               f"Comment your scoreline. #matchsim #football{tag_str}\n{DISCLAIMER}")
    out_mp4.with_name(out_mp4.stem + "-caption.txt").write_text(caption, encoding="utf-8")
    notes = (f"POST PLAN - {fx['home']['name']} vs {fx['away']['name']}\n"
             f"1. Upload {out_mp4.name} to TikTok.\n"
             f"2. Add a trending sound at ~20% volume.\n"
             f"3. Paste the caption from {out_mp4.stem}-caption.txt.\n")
    out_mp4.with_name(out_mp4.stem + "-post-notes.txt").write_text(notes, encoding="utf-8")
    return out_mp4


def _cmd_render(args):
    try:
        out = _render_one(args.home, args.away, args.competition, args.seed, args.out,
                          home_xg=args.home_xg, away_xg=args.away_xg,
                          venue=args.venue, stage=args.stage, date=args.date,
                          pre=args.pre, live=args.live, post=args.post)
    except schema.SchemaError as e:
        print(f"schema error: {e}", file=sys.stderr)
        return 1
    print(f"wrote {out}")
    return 0


def _cmd_batch(args):
    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, 0
    for fxt in fixtures:
        home, away = fxt["home"], fxt["away"]
        name = f"{home}-vs-{away}".lower()
        out_mp4 = out_dir / f"{name}.mp4"
        try:
            _render_one(home, away, fxt.get("competition", "generic"),
                        int(fxt.get("seed", 0)), out_mp4,
                        pre=args.pre, live=args.live, post=args.post)
            print(f"ok   {out_mp4.name}")
            ok += 1
        except Exception as e:
            print(f"FAIL {name}: {e}", file=sys.stderr)
            failed += 1
    print(f"batch done: {ok} ok, {failed} failed")
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
    bp = sub.add_parser("batch", help="render a JSON list of fixtures -> a directory of MP4s")
    bp.add_argument("--fixtures", required=True, help="JSON list of {home,away,competition?,seed?}")
    bp.add_argument("--out-dir", required=True, dest="out_dir")
    bp.add_argument("--pre", type=float, default=5.0)
    bp.add_argument("--live", type=float, default=40.0)
    bp.add_argument("--post", type=float, default=6.0)
    bp.set_defaults(func=_cmd_batch)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
