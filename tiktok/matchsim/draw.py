"""Pillow drawing primitives for the MatchSim renderer, in the brand style of
make_video.py (Anton/Bebas fonts, gradients, glossy orbs, glass panels).
All functions return RGBA Images; the renderer composites them.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from colors import hex_to_rgb, lerp_rgb

FONTS = Path(__file__).resolve().parents[2] / "branding" / "fonts"

_font_cache = {}


def font(name, size):
    key = (name, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(FONTS / name), size)
    return _font_cache[key]


def gradient_bg(stops, w, h):
    """Vertical 3-stop gradient as an RGBA image."""
    top, mid, bot = (hex_to_rgb(s) for s in stops)
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1) if h > 1 else 0.0
        if t < 0.5:
            col = lerp_rgb(top, mid, t / 0.5)
        else:
            col = lerp_rgb(mid, bot, (t - 0.5) / 0.5)
        row = (*col, 255)
        for x in range(w):
            px[x, y] = row
    return img


def text_layer(text, fnt, fill, shadow=3):
    asc, desc = fnt.getmetrics()
    w = int(math.ceil(fnt.getlength(text)))
    h = asc + desc
    pad = max(6, shadow + 4)
    img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shadow:
        d.text((pad + shadow, pad + shadow), text, font=fnt, fill=(0, 0, 0, 150))
    d.text((pad, pad), text, font=fnt, fill=(*fill, 255) if len(fill) == 3 else fill)
    return img


_orb_cache = {}


def orb(size, color_hex, monogram, mono_font="Anton.ttf"):
    """Glossy 3-D-looking disc: radial highlight -> colour -> shadow, plus a
    rim ring and a centered monogram. Cached by (size, colour, monogram) — the
    same disc is drawn on every frame, so building it once is essential.
    Callers only composite (read) the result, so sharing the cached image is safe.
    """
    ckey = (size, color_hex, monogram, mono_font)
    if ckey in _orb_cache:
        return _orb_cache[ckey]
    base = hex_to_rgb(color_hex)
    hi = lerp_rgb(base, (255, 255, 255), 0.55)
    lo = lerp_rgb(base, (0, 0, 0), 0.45)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cx = cy = size / 2.0
    r = size / 2.0
    hx, hy = size * 0.35, size * 0.30  # highlight point
    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > r * r:
                continue
            d = math.hypot(x - hx, y - hy) / size
            t = min(1.0, d / 0.9)
            col = lerp_rgb(hi, base, t / 0.5) if t < 0.5 else lerp_rgb(base, lo, (t - 0.5) / 0.5)
            px[x, y] = (*col, 255)
    # rim ring
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, size - 2, size - 2], outline=(255, 255, 255, 90),
              width=max(2, size // 40))
    # monogram
    fsize = max(10, int(size * 0.30))
    while fsize > 8:
        f = font(mono_font, fsize)
        if f.getlength(monogram) <= size * 0.8:
            break
        fsize -= 2
    lab = text_layer(monogram, font(mono_font, fsize),
                     (255, 255, 255) if _luma(base) < 150 else (10, 14, 42))
    img.alpha_composite(lab, (int(cx - lab.width / 2), int(cy - lab.height / 2)))
    _orb_cache[ckey] = img
    return img


def _luma(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def glass_panel(w, h, radius=16, fill=(255, 255, 255, 18), outline=(245, 196, 81, 90)):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=fill,
                        outline=outline, width=2)
    return img


def winprob_bar(w, h, p_home, p_draw, p_away, c_home, c_draw, c_away):
    """Three-segment gradient bar with rounded ends."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    total = max(1e-6, p_home + p_draw + p_away)
    widths = [int(w * p_home / total), int(w * p_draw / total)]
    widths.append(w - sum(widths))
    cols = [hex_to_rgb(c_home), hex_to_rgb(c_draw), hex_to_rgb(c_away)]
    x = 0
    for seg_w, col in zip(widths, cols):
        top = lerp_rgb(col, (255, 255, 255), 0.25)
        for i in range(seg_w):
            tt = i / max(seg_w - 1, 1)
            c = lerp_rgb(top, col, tt)
            d.line([(x + i, 0), (x + i, h)], fill=(*c, 255))
        x += seg_w
    # rounded-corner mask
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1],
                                           radius=h // 2, fill=255)
    img.putalpha(mask)
    return img
