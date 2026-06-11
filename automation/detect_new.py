"""Diff the day's output dir against a pre-run snapshot; emit new story ids.

Usage (editor workflow):
    ls <day_dir>/*.mp4 > /tmp/before.txt   (before the editor runs; missing dir ok)
    python automation/detect_new.py /tmp/before.txt <day_dir>

Writes meta.json (run_id, story_ids, rendered_at) into the day dir for the
publisher's staleness check, and appends new_ids=<space separated> to
$GITHUB_OUTPUT.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def new_ids(day_dir: Path, before: set) -> list:
    after = {p.name for p in Path(day_dir).glob("*.mp4")}
    fresh = sorted(after - before)
    return [n[:-4] for n in fresh if not n.endswith("-youtube.mp4")]


def write_meta(day_dir: Path, run_id: str, ids: list, rendered_at: str) -> None:
    (Path(day_dir) / "meta.json").write_text(
        json.dumps({"run_id": run_id, "story_ids": ids,
                    "rendered_at": rendered_at}), encoding="utf-8")


if __name__ == "__main__":
    before_file, day_dir = sys.argv[1], Path(sys.argv[2])
    before = {Path(line).name for line in
              Path(before_file).read_text().splitlines() if line.strip()}
    day_dir.mkdir(parents=True, exist_ok=True)
    ids = new_ids(day_dir, before)
    write_meta(day_dir, os.environ.get("GITHUB_RUN_ID", "local"), ids,
               datetime.now(ZoneInfo("Europe/London")).isoformat())
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"new_ids={' '.join(ids)}\n")
    print(f"new story ids: {ids or 'none'}")
