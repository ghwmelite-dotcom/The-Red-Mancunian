"""Wrap a goal clip in a sumptuous Red Mancunian edit (intro card -> branded
footage -> celebrate end card), for TikTok + YouTube Shorts.

Usage:
    python tiktok/goaledit/render_goal.py <clip.mp4> <out_dir>

Outputs in <out_dir>: amad-winner.mp4 (TikTok), amad-winner-youtube.mp4,
intro/overlay/end PNGs, amad-winner-caption.txt, -youtube-caption.txt.

Facts are edited in the CONFIG block below.
"""
import base64
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "branding"
FONTS = BRAND / "fonts"
WHOOSH = ROOT / "tiktok" / "assets" / "whoosh.wav"
W, H, FPS = 1080, 1920, 30

CONFIG = {
    "player": "AMAD",
    "headline_sub": "90TH-MINUTE WINNER",
    "score": "IVORY COAST 1-0 ECUADOR",
    "tag": "WORLD CUP · GROUP E",
    "lower_name": "AMAD DIALLO",
    "lower_note": "90' WINNER",
    "end_top": "UP THE REDS",
    "end_mid": "AMAD WINS IT AT THE WORLD CUP",
}
PLATFORMS = {
    "tiktok": {"suffix": "", "handle": "@exclusivelymanunited"},
    "youtube": {"suffix": "-youtube", "handle": "@theredmancunianway"},
}


def b64(p): return base64.b64encode(Path(p).read_bytes()).decode()


def assets():
    return {
        "anton": b64(FONTS / "Anton.ttf"),
        "bebas": b64(FONTS / "BebasNeue.ttf"),
        "logo": b64(BRAND / "logo-avatar.png"),
        "roar": b64(BRAND / "character" / "hero-06-roar.jpg"),
        "celebrate": b64(BRAND / "character" / "hero-03-celebrate.jpg"),
    }


def css(a, transparent=False):
    bg = "transparent" if transparent else "var(--ink)"
    return f"""
    @font-face {{ font-family:'Anton'; src:url(data:font/ttf;base64,{a['anton']}); }}
    @font-face {{ font-family:'Bebas'; src:url(data:font/ttf;base64,{a['bebas']}); }}
    * {{ margin:0; padding:0; box-sizing:border-box; -webkit-font-smoothing:antialiased; }}
    :root {{ --red:#C6241E; --dred:#781414; --coral:#E86664; --ink:#16100E;
             --cream:#FFE2DE; --white:#fff; --gold:#F5C451; }}
    body {{ width:{W}px; height:{H}px; font-family:'Bebas',sans-serif; color:#fff; background:{bg}; }}
    .anton {{ font-family:'Anton',sans-serif; }}
    .splat::before {{ content:''; position:absolute; inset:0; pointer-events:none; opacity:.5;
      background:radial-gradient(circle at 16% 14%,rgba(198,36,30,.45),transparent 22%),
      radial-gradient(circle at 84% 30%,rgba(120,20,20,.5),transparent 26%),
      radial-gradient(circle at 24% 80%,rgba(198,36,30,.35),transparent 24%); }}
    """


def intro_html(a):
    c = CONFIG
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{css(a)}
    .f {{ position:relative; width:{W}px; height:{H}px; overflow:hidden;
      background:linear-gradient(165deg,#1c1310,#2a0f0e 45%,#781414); }}
    .m {{ position:absolute; right:-110px; bottom:-30px; width:760px; opacity:.9;
      -webkit-mask-image:linear-gradient(to top,transparent 4%,#000 30%);
      mask-image:linear-gradient(to top,transparent 4%,#000 30%); }}
    .pad {{ position:relative; z-index:2; padding:80px 70px; }}
    .bar {{ display:flex; align-items:center; gap:22px; }}
    .logo {{ width:104px; height:104px; border-radius:50%; border:5px solid var(--cream); }}
    .nm {{ font-family:'Anton'; font-size:50px; letter-spacing:1px; }}
    .tag {{ display:inline-block; margin-top:80px; background:var(--red); padding:14px 30px 8px;
      font-size:40px; letter-spacing:6px; transform:rotate(-2deg); box-shadow:0 12px 26px rgba(0,0,0,.4); }}
    .big {{ font-family:'Anton'; font-size:340px; line-height:.82; margin-top:30px; color:var(--gold);
      text-shadow:0 0 50px rgba(245,196,81,.45),0 10px 0 rgba(0,0,0,.25); }}
    .sub {{ font-family:'Anton'; font-size:90px; line-height:.9; color:#fff; margin-top:6px; }}
    .sub b {{ color:var(--coral); }}
    .score {{ margin-top:34px; font-size:54px; letter-spacing:5px; color:var(--cream);
      border-top:3px solid rgba(255,226,222,.3); padding-top:26px; display:inline-block; }}
    </style></head><body>
    <div class="f splat"><img class="m" src="data:image/jpeg;base64,{a['roar']}">
      <div class="pad">
        <div class="bar"><img class="logo" src="data:image/png;base64,{a['logo']}">
          <div class="nm">THE RED MANCUNIAN</div></div>
        <div class="tag">{c['tag']}</div>
        <div class="big anton">{c['player']}!</div>
        <div class="sub anton">{c['headline_sub']}</div>
        <div class="score">{c['score']}</div>
      </div>
    </div></body></html>"""


def overlay_html(a):
    c = CONFIG
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{css(a, transparent=True)}
    .topbar {{ position:absolute; top:46px; left:46px; display:flex; align-items:center; gap:16px;
      background:rgba(22,16,14,.55); padding:12px 26px 12px 12px; border-radius:60px;
      border:1px solid rgba(255,226,222,.25); }}
    .topbar img {{ width:72px; height:72px; border-radius:50%; border:3px solid var(--cream); }}
    .topbar .t {{ font-family:'Anton'; font-size:38px; letter-spacing:.5px; }}
    .lower {{ position:absolute; left:0; right:0; bottom:300px; }}
    .band {{ background:var(--ink); transform:rotate(-2deg); margin:0 -20px; padding:26px 60px;
      box-shadow:0 16px 40px rgba(0,0,0,.5); }}
    .nm {{ font-family:'Anton'; font-size:96px; line-height:.9; }}
    .nm b {{ color:var(--coral); }}
    .note {{ font-size:46px; letter-spacing:5px; color:var(--cream); margin-top:8px; }}
    </style></head><body>
    <div class="topbar"><img src="data:image/png;base64,{a['logo']}"><div class="t">THE RED MANCUNIAN</div></div>
    <div class="lower"><div class="band">
      <div class="nm anton">{c['lower_name']} <b>{c['lower_note']}</b></div>
      <div class="note">{c['score']}</div>
    </div></div></body></html>"""


def end_html(a, handle):
    c = CONFIG
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{css(a)}
    .f {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; text-align:center;
      background:linear-gradient(165deg,#1c1310,#2a0f0e 45%,#781414);
      display:flex; flex-direction:column; align-items:center; justify-content:center; padding:80px; }}
    .m {{ position:absolute; left:50%; bottom:-40px; transform:translateX(-50%); width:780px; opacity:.9;
      -webkit-mask-image:linear-gradient(to top,transparent 4%,#000 30%);
      mask-image:linear-gradient(to top,transparent 4%,#000 30%); }}
    .z {{ position:relative; z-index:2; }}
    .logo {{ width:160px; height:160px; border-radius:50%; border:6px solid var(--cream); box-shadow:0 14px 40px rgba(0,0,0,.5); }}
    .top {{ font-family:'Anton'; font-size:140px; line-height:.86; margin-top:34px; color:var(--gold);
      text-shadow:0 0 40px rgba(245,196,81,.4); }}
    .mid {{ font-family:'Anton'; font-size:64px; line-height:.95; margin-top:18px; }}
    .mid b {{ color:var(--coral); }}
    .cta {{ font-size:46px; letter-spacing:5px; color:var(--cream); margin-top:40px; }}
    .h {{ font-family:'Anton'; font-size:56px; margin-top:8px; }}
    </style></head><body>
    <div class="f splat"><img class="m" src="data:image/jpeg;base64,{a['celebrate']}">
      <div class="z"><img class="logo" src="data:image/png;base64,{a['logo']}">
        <div class="top anton">{c['end_top']}</div>
        <div class="mid anton">{c['end_mid']}</div>
        <div class="cta">FOLLOW FOR DAILY UNITED NEWS</div>
        <div class="h anton">{handle}</div>
      </div></div></body></html>"""


def shot(pg, html, path, transparent=False):
    pg.set_content(html, wait_until="networkidle")
    pg.wait_for_timeout(250)
    pg.screenshot(path=str(path), omit_background=transparent)


def render_pngs(out):
    a = assets()
    paths = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        shot(pg, intro_html(a), out / "intro.png")
        shot(pg, overlay_html(a), out / "overlay.png", transparent=True)
        for plat, meta in PLATFORMS.items():
            shot(pg, end_html(a, meta["handle"]), out / f"end{meta['suffix']}.png")
        b.close()
    return a


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{r.stderr[-1800:]}")


def build(clip, out, transpose="2", crop_top=66):
    """transpose: ffmpeg transpose to make the footage upright (2 = 90° CCW, correct
    for this clip). crop_top: px trimmed from the upright-landscape TOP to drop the
    bookmaker watermark + broadcast scorebug before framing."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    render_pngs(out)
    intro_d, end_d = 1.9, 2.4
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        intro, main = td / "intro.mp4", td / "main.mp4"
        # intro: branded card + whoosh stinger (apad keeps audio to full length; no -shortest)
        run(["ffmpeg", "-y", "-loop", "1", "-i", out / "intro.png", "-i", WHOOSH,
             "-t", intro_d, "-vf", f"scale={W}:{H},format=yuv420p", "-af", "apad",
             "-r", FPS, "-c:v", "libx264", "-preset", "medium", "-c:a", "aac",
             "-ar", "44100", "-ac", "2", intro])
        # main: rotate upright, trim watermark, landscape clip framed on its own
        # blurred fill, then the brand overlay (top bar + lower third). Keeps audio.
        fc = (
            f"[0:v]transpose={transpose},crop=iw:ih-{crop_top}:0:{crop_top},setsar=1[up];"
            f"[up]split[fg][bg0];"
            f"[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=26:2,eq=brightness=-0.22:saturation=1.12[bg];"
            f"[fg]scale={W}:-2[fgs];"
            f"[bg][fgs]overlay=(W-w)/2:(H-h)/2-110[comp];"
            f"[comp][1:v]overlay=0:0,format=yuv420p[v]"
        )
        run(["ffmpeg", "-y", "-i", clip, "-i", out / "overlay.png", "-filter_complex", fc,
             "-map", "[v]", "-map", "0:a", "-r", FPS, "-c:v", "libx264", "-preset", "medium",
             "-c:a", "aac", "-ar", "44100", "-ac", "2", main])
        for plat, meta in PLATFORMS.items():
            end = td / f"end{meta['suffix']}.mp4"
            run(["ffmpeg", "-y", "-loop", "1", "-i", out / f"end{meta['suffix']}.png",
                 "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", end_d,
                 "-vf", f"scale={W}:{H},format=yuv420p", "-r", FPS, "-c:v", "libx264",
                 "-preset", "medium", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", end])
            lst = td / f"list{meta['suffix']}.txt"
            lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in (intro, main, end)), encoding="utf-8")
            final = out / f"amad-winner{meta['suffix']}.mp4"
            run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                 "-c:v", "libx264", "-preset", "medium", "-c:a", "aac", "-ar", "44100",
                 "-movflags", "+faststart", final])
    return out


def captions(out):
    base = ("🔴⚽ AMAD DIALLO WINS IT! Our man scores a 90th-minute winner for Ivory "
            "Coast to beat Ecuador 1-0 in their World Cup opener. A United player "
            "deciding it on the biggest stage. 🇨🇮\n\n"
            "How good is Amad?? Tell us below 👇\n\n")
    tt = base + "#mufc #manutd #amaddiallo #worldcup #ivorycoast #football #fyp"
    yt = base + "#mufc #amaddiallo #worldcup #shorts"
    disc = "\n\nUnofficial fan content. Not affiliated with Manchester United FC."
    (out / "amad-winner-caption.txt").write_text(tt + disc, encoding="utf-8")
    (out / "amad-winner-youtube-caption.txt").write_text(yt + disc, encoding="utf-8")


def main():
    clip, out = Path(sys.argv[1]), Path(sys.argv[2])
    build(clip, out)
    captions(out)
    for plat, meta in PLATFORMS.items():
        print(f"{plat}: {out / ('amad-winner' + meta['suffix'] + '.mp4')}")


if __name__ == "__main__":
    main()
