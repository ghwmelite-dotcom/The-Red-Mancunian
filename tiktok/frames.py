"""Render branded 1080x1920 frames for a story (pure Pillow, no network)."""
import random
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import story

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "branding"
FONTS = BRAND / "fonts"
CHARACTER = BRAND / "character"
LOGO = BRAND / "logo-avatar.png"

W, H = 1080, 1920
RED = (198, 36, 30)
DRED = (120, 20, 20)
WHITE = (255, 255, 255)
CREAM = (255, 226, 222)
INK = (22, 14, 14)

# Per-platform end-card copy (render.py exposes --platform; tiktok is the default)
PLATFORMS = {
    "tiktok": {"handle": "@exclusivelymanunited",
               "follow": "FOLLOW FOR DAILY UNITED NEWS"},
    "youtube": {"handle": "@theredmancunianway",
                "follow": "SUBSCRIBE FOR DAILY UNITED NEWS"},
}
FOLLOW_HIGHLIGHT = "UNITED NEWS"

POSES = {
    "react": "hero-01-react.jpg",
    "tension": "hero-02-tension.jpg",
    "celebrate": "hero-03-celebrate.jpg",
    "confident": "hero-04-confident.jpg",
    "point": "hero-05-point.jpg",
    "roar": "hero-06-roar.jpg",
}
BADGES = {
    "TRANSFER": "TRANSFER NEWS",
    "MATCHDAY": "MATCHDAY",
    "CLUB": "CLUB NEWS",
    "ACADEMY": "ACADEMY WATCH",
}

if BADGES.keys() != story.CATEGORIES:
    raise RuntimeError("frames.BADGES out of sync with story.CATEGORIES")
if POSES.keys() != story.MOODS:
    raise RuntimeError("frames.POSES out of sync with story.MOODS")

BANNER_ANGLE = 2          # degrees, Daily Mail-style tilt
BANNER_MAX_LINES = 3
BANNER_SIZES = (104, 92, 80, 68)

# Bottom-block layout constants — used in BOTH height computation and drawing
SAFE_BOTTOM = 56   # px gap from frame bottom to block bottom
LOGO_GAP = 20      # px between logo ring and banner top
TAG_GAP = 20       # px between banner bottom and tag text top


def check_assets():
    """Fail fast with a clear message if any brand asset is missing."""
    missing = [str(p) for p in
               [FONTS / "Anton.ttf", FONTS / "BebasNeue.ttf", LOGO,
                *(CHARACTER / f for f in POSES.values())]
               if not p.exists()]
    if missing:
        raise FileNotFoundError("missing brand assets:\n  " + "\n  ".join(missing))


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def background(seed):
    """Ink-to-dark-red vertical gradient with seeded splatter texture."""
    img = Image.new("RGB", (W, H))
    for y in range(H):
        t = y / (H - 1)
        row = tuple(round(a + (b - a) * t) for a, b in zip(INK, DRED))
        img.paste(row, (0, y, W, y + 1))
    d = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(seed)
    for _ in range(140):
        x, y = rng.randrange(W), rng.randrange(H)
        r = rng.randrange(2, 26)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*DRED, rng.randrange(20, 60)))
    return img


def paste_mascot(canvas, mood):
    """Mascot fills the upper ~62%, fading into the background at the bottom."""
    pose = Image.open(CHARACTER / POSES[mood]).convert("RGB")
    target_h = int(H * 0.62)
    scale = max(W / pose.width, target_h / pose.height)
    pose = pose.resize((round(pose.width * scale), round(pose.height * scale)), Image.LANCZOS)
    left = (pose.width - W) // 2
    pose = pose.crop((left, 0, left + W, target_h))
    mask = Image.new("L", (W, target_h), 255)
    md = ImageDraw.Draw(mask)
    fade_start = int(target_h * 0.72)
    for y in range(fade_start, target_h):
        alpha = round(255 * (1 - (y - fade_start) / (target_h - fade_start)))
        md.line([(0, y), (W, y)], fill=alpha)
    canvas.paste(pose, (0, 0), mask)


def _mark_highlight(text, highlight):
    """[(word, is_highlight)] — highlight must match whole words; all occurrences marked."""
    words = text.split()
    if not highlight:
        return [(w, False) for w in words]
    hwords = highlight.split()
    flags = [False] * len(words)
    n = len(hwords)
    found = False
    for i in range(len(words) - n + 1):
        if words[i:i + n] == hwords:
            flags[i:i + n] = [True] * n
            found = True
    if not found:
        raise ValueError(f"highlight {highlight!r} does not align to whole words in {text!r}")
    return list(zip(words, flags))


def _wrap(words, fnt, max_width, probe):
    lines, line = [], []
    for item in words:
        trial = " ".join(w for w, _ in line + [item])
        if line and probe.textlength(trial, font=fnt) > max_width:
            lines.append(line)
            line = [item]
        else:
            line.append(item)
    if line:
        lines.append(line)
    return lines


def banner(text, highlight):
    """Angled black banner with white Anton caps; highlight words in red."""
    pad_x, pad_y, gap = 56, 52, 18
    # Banner spans nearly full frame width — allow text up to W minus side padding only
    max_text_width = W - pad_x * 2
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    words = _mark_highlight(text, highlight)
    chosen = None
    for size in BANNER_SIZES:
        fnt = font("Anton.ttf", size)
        lines = _wrap(words, fnt, max_text_width, probe)
        if len(lines) <= BANNER_MAX_LINES:
            chosen = (fnt, lines, size)
            break
    if chosen is None:
        raise ValueError(f"headline too long even at minimum size: {text!r}")
    fnt, lines, size = chosen
    # Use font metrics for proper line height — Anton has tall ascenders
    ascent, descent = fnt.getmetrics()
    line_h = ascent + descent + gap
    # Banner is always full-frame width for clean edge-to-edge look
    bw = W
    bh = pad_y * 2 + line_h * len(lines) - gap
    img = Image.new("RGBA", (bw, bh), (*INK, 255))
    d = ImageDraw.Draw(img)
    y = pad_y
    for ln in lines:
        # Centre each line within the banner
        line_text_w = probe.textlength(" ".join(w for w, _ in ln), font=fnt)
        x = (bw - line_text_w) / 2
        for word, hl in ln:
            d.text((x, y), word, font=fnt, fill=RED if hl else WHITE)
            x += probe.textlength(word + " ", font=fnt)
        y += line_h
    # rotate(BANNER_ANGLE, expand=True) makes the banner wider than W so its corners crop
    # at the frame edge — pad_x provides the headroom; reduce BANNER_ANGLE or keep pad_x >= 48
    # when tweaking.
    return img.rotate(BANNER_ANGLE, expand=True, resample=Image.BICUBIC)


def build_frame(s, segment, kind, index, platform="tiktok"):
    end_card = PLATFORMS[platform]
    seed = zlib.crc32(s["id"].encode()) + index
    cv = background(seed)
    mood = "point" if kind == "end" else s["mood"]
    paste_mascot(cv, mood)
    d = ImageDraw.Draw(cv)

    # category badge, top-left — vertically centre text in the red pill
    label = BADGES[s["category"]]
    bf = font("BebasNeue.ttf", 52)
    tw = int(d.textlength(label, font=bf))
    badge_x, badge_y = 48, 64
    badge_h = 76
    badge_w = tw + 56
    d.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill=RED)
    # Vertically centre: use getbbox for precise ascent
    ascent_b, descent_b = bf.getmetrics()
    text_h = ascent_b + descent_b
    text_y = badge_y + (badge_h - text_h) // 2
    d.text((badge_x + 28, text_y), label, font=bf, fill=WHITE)

    # attribution tag / handle measurements (needed for vertical layout)
    tf = font("BebasNeue.ttf", 48)
    if kind == "end":
        tag = end_card["handle"]
    elif s["status"] in ("REPORTED", "RUMOUR"):
        tag = f'{s["status"]} - PER {s["source"].upper()}'
    else:
        tag = ""

    # headline banner, lower third
    if kind == "end":
        bn = banner(end_card["follow"], FOLLOW_HIGHLIGHT)
    else:
        bn = banner(segment["text"], segment.get("highlight", ""))

    # Logo badge above banner — 160px logo with white ring for contrast
    logo_size = 160
    logo = Image.open(LOGO).convert("RGBA").resize((logo_size, logo_size), Image.LANCZOS)
    # Ring: draw a white circle slightly larger as background for contrast
    ring_size = logo_size + 8
    ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse([0, 0, ring_size - 1, ring_size - 1], fill=(*WHITE, 220))
    ring.paste(logo, (4, 4), logo)

    # Compute tag height so we can position everything from the bottom up
    tag_h = 0
    if tag:
        ascent_t, descent_t = tf.getmetrics()
        tag_h = ascent_t + descent_t + TAG_GAP  # TAG_GAP px gap below banner

    # Total bottom block height: tag + banner + gap + logo + gap
    total_block = tag_h + bn.height + LOGO_GAP + ring_size + 16
    # Place the block starting SAFE_BOTTOM px from bottom (safe zone)
    block_bottom = H - SAFE_BOTTOM
    block_top = block_bottom - total_block

    # Stack from top of block: ring/logo, gap, banner, gap, tag
    logo_y = block_top
    logo_x = (W - ring_size) // 2
    cv.paste(ring, (logo_x, logo_y), ring)

    by = logo_y + ring_size + LOGO_GAP
    cv.paste(bn, ((W - bn.width) // 2, by), bn)

    if tag:
        ttw = d.textlength(tag, font=tf)
        tag_y = by + bn.height + TAG_GAP
        d.text(((W - ttw) / 2, tag_y), tag, font=tf, fill=CREAM)
    return cv


def render_frames(s, out_dir, platform="tiktok"):
    PLATFORMS[platform]  # fail fast on unknown platform before any rendering
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seq = ([("hook", s["hook"])]
           + [("beat", b) for b in s["beats"]]
           + [("end", None)])
    paths = []
    for i, (kind, seg) in enumerate(seq):
        p = out_dir / f"frame-{i:02d}-{kind}.png"
        build_frame(s, seg, kind, i, platform=platform).save(p)
        paths.append(p)
    return paths
