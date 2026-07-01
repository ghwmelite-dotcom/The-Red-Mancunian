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

import engine
import schema


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
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
