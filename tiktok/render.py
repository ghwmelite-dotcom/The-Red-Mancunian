"""CLI: turn a story JSON into a ready-to-post MP4 + caption file.

Usage:
    python tiktok/render.py tiktok/stories/<story>.json [--out DIR] [--frames-only]
                            [--platform tiktok|youtube]

--platform swaps the end-card handle and follow/subscribe line (default: tiktok).
YouTube outputs get a "-youtube" suffix so both versions coexist per day.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import frames
import story

DISCLAIMER = "Unofficial fan content - not affiliated with Manchester United FC."

# Per-platform posting plan written next to every rendered video.
# Daily rhythm: TikTok at lunch, Shorts in the evening — staggered so each
# platform gets full first-hour comment attention. Breaking news overrides both.
POST_NOTES = {
    "tiktok": """\
POST PLAN - TIKTOK ({handle})
When: 12:00-14:00 UK (lunch peak). BREAKING NEWS: post immediately instead.

1. Upload {mp4_name} via the TikTok MOBILE app (not desktop - better sound tools).
2. Add a trending sound at ~20% volume under the video.
3. Paste the caption from {caption_name}.
4. Stay in the comments for the first hour - early replies feed the algorithm.
""",
    "youtube": """\
POST PLAN - YOUTUBE SHORTS ({handle})
When: 19:00-21:00 UK (evening peak). BREAKING NEWS: post immediately instead.

1. Upload THIS original MP4 ({mp4_name}) - never a TikTok download
   (watermarked Shorts get suppressed).
2. Suggested title: {hook} #mufc
3. Description: paste the caption from {caption_name}.
4. Do NOT reuse TikTok trending sounds (licences don't transfer) - post as-is
   or add audio from YouTube's Shorts sound picker.
""",
}

if POST_NOTES.keys() != frames.PLATFORMS.keys():
    raise RuntimeError("render.POST_NOTES out of sync with frames.PLATFORMS")


def render_story(story_path, out_root=None, frames_only=False, platform="tiktok"):
    s = story.load(story_path)
    frames.check_assets()
    out_root = Path(out_root) if out_root else Path(__file__).resolve().parent / "output"
    day_dir = out_root / s["date"]
    # tiktok keeps unsuffixed names (the default platform); others coexist via suffix
    base = s["id"] if platform == "tiktok" else f"{s['id']}-{platform}"
    frames_dir = day_dir / "frames" / base
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frame_paths = frames.render_frames(s, frames_dir, platform=platform)
    if frames_only:
        print(f"frames written to {frames_dir}")
        return None

    import video  # deferred so --frames-only works without ffmpeg
    mp4 = video.assemble(frame_paths, day_dir / f"{base}.mp4")
    problems = video.validate_mp4(mp4)
    if problems:
        mp4.unlink(missing_ok=True)
        raise RuntimeError("output failed video validation: " + "; ".join(problems))

    caption = (s["caption"] + "\n\n" + " ".join(s["hashtags"])
               + "\n\n" + DISCLAIMER + "\n")
    (day_dir / f"{base}-caption.txt").write_text(caption, encoding="utf-8")
    notes = POST_NOTES[platform].format(
        handle=frames.PLATFORMS[platform]["handle"],
        mp4_name=mp4.name,
        caption_name=f"{base}-caption.txt",
        hook=s["hook"]["text"],
    )
    (day_dir / f"{base}-post-notes.txt").write_text(notes, encoding="utf-8")
    (day_dir / f"{base}.json").write_text(
        json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ready to post: {mp4}")
    return mp4


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("story", help="path to a story JSON file")
    ap.add_argument("--out", default=None, help="output root (default: tiktok/output)")
    ap.add_argument("--frames-only", action="store_true", help="render PNG frames, skip video")
    ap.add_argument("--platform", default="tiktok", choices=sorted(frames.PLATFORMS),
                    help="end-card variant (default: tiktok)")
    args = ap.parse_args()
    if not args.frames_only and shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found on PATH. Install it: winget install Gyan.FFmpeg "
                 "(then restart the terminal), or use --frames-only.")
    try:
        render_story(args.story, out_root=args.out, frames_only=args.frames_only,
                     platform=args.platform)
    except (story.StoryError, ValueError, RuntimeError, KeyError, OSError) as e:
        sys.exit(f"render failed: {e}")


if __name__ == "__main__":
    main()
