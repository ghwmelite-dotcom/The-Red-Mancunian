"""Pillow drawing primitives for the MatchSim renderer, in the brand style of
make_video.py (Anton/Bebas fonts, gradients, glossy orbs, glass panels).
All functions return RGBA Images; the renderer composites them.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

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


def halo(size, color_hex, blur=20):
    """A soft circular glow (for the possessing disc / accents)."""
    base = hex_to_rgb(color_hex)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, size // 10)
    d.ellipse([pad, pad, size - pad, size - pad], fill=(*base, 200))
    return img.filter(ImageFilter.GaussianBlur(blur))


def confetti(w, h, seed, n=80, colors=None):
    """Deterministic scatter of small confetti rectangles (goal celebration)."""
    if colors is None:
        colors = [(255, 255, 255), (245, 196, 81), (218, 2, 14), (57, 230, 230)]
    rng = random.Random(seed * 2654435761 + 1)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        sw = rng.randint(4, 10)
        sh = rng.randint(6, 14)
        col = colors[rng.randrange(len(colors))]
        d.rectangle([x, y, x + sw, y + sh], fill=(*col, 235))
    return img


# ---- visual-overhaul primitives (Plan 5) ----
_flag_cache = {}


def flag_disc(size, bands, orient="v"):
    """A national-flag disc: colour stripe bands clipped to a circle, with a
    gloss highlight and rim ring. Cached by (size, bands, orient)."""
    ckey = (size, tuple(bands), orient)
    if ckey in _flag_cache:
        return _flag_cache[ckey]
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    n = len(bands)
    for i, c in enumerate(bands):
        col = hex_to_rgb(c)
        if orient == "v":
            d.rectangle([int(size * i / n), 0, int(size * (i + 1) / n), size], fill=(*col, 255))
        else:
            d.rectangle([0, int(size * i / n), size, int(size * (i + 1) / n)], fill=(*col, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    img.putalpha(mask)
    hi = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(hi).ellipse([size * 0.14, size * 0.10, size * 0.62, size * 0.46],
                               fill=(255, 255, 255, 70))
    img.alpha_composite(hi.filter(ImageFilter.GaussianBlur(max(3, size // 16))))
    img.putalpha(mask)  # re-clip so the gloss never bleeds past the circle
    ImageDraw.Draw(img).ellipse([1, 1, size - 2, size - 2],
                                outline=(255, 255, 255, 150), width=max(3, size // 32))
    _flag_cache[ckey] = img
    return img


def team_disc(size, team):
    """Flag disc for national teams (team['flag'] set), else colour+monogram orb."""
    if team.get("flag"):
        bands, orient = team["flag"]
        return flag_disc(size, bands, orient)
    return orb(size, team["color"], team["monogram"])


def pitch_texture(w, h, stripe_alpha=9, dot_alpha=12, band=150, dot_gap=26):
    """Overlay of mowing stripes + a dot grid to composite over the gradient bg."""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, y in enumerate(range(0, h, band)):
        if i % 2 == 0:
            d.rectangle([0, y, w, y + band], fill=(255, 255, 255, stripe_alpha))
    for y in range(0, h, dot_gap):
        for x in range(0, w, dot_gap):
            d.ellipse([x, y, x + 2, y + 2], fill=(255, 255, 255, dot_alpha))
    return lay


def watermark(w, h, text, cx, cy, size, alpha=16):
    """A large ghosted text layer (e.g. the competition year) behind the arena."""
    f = font("Anton.ttf", size)
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    tw = d.textlength(text, font=f)
    d.text((cx - tw / 2, cy - size * 0.62), text, font=f, fill=(255, 255, 255, alpha))
    return lay


def crowd_ring(w, h, cx, cy, r, seed, accent_hex, n=2200):
    """A stadium-in-the-round: dense crowd specks + scattered corner flags in the
    annulus outside the arena ring. Seeded/deterministic."""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = random.Random(seed)
    acc = hex_to_rgb(accent_hex)
    for _ in range(n):
        ang = rng.uniform(0, 2 * math.pi)
        rr = r + rng.uniform(10, 300)
        x, y = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
        if 0 <= x < w and 130 <= y < h - 120:
            s = rng.randint(2, 5)
            sh = rng.randint(25, 80)
            d.rectangle([x, y, x + s, y + s], fill=(sh, sh, sh, rng.randint(60, 150)))
    for _ in range(26):
        ang = rng.uniform(0, 2 * math.pi)
        rr = r + rng.uniform(24, 300)
        x, y = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
        if 0 <= x < w - 14 and 130 <= y < h - 130:
            d.polygon([(x, y), (x + 13, y + 4), (x, y + 10)], fill=(*acc, 150))
    return lay


def goal_net(width=150, height=60):
    """A small goal-net tile; caller places it so the crossbar sits on the ring."""
    pad = 8
    img = Image.new("RGBA", (width + pad * 2, height + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0 = pad, height + pad
    for i in range(0, width + 1, 13):
        d.line([(x0 + i, y0), (x0 + i + 22, y0 - height)], fill=(255, 255, 255, 110))
    for j in range(0, height + 1, 13):
        d.line([(x0 + j * 0.36, y0 - j), (x0 + width + j * 0.36, y0 - j)], fill=(255, 255, 255, 110))
    d.line([(x0, y0), (x0 + width, y0)], fill=(255, 255, 255, 230), width=5)
    return img


def caption_pill(text, accent_hex, fontsize=46):
    """An arcade caption pill with a drawn lightning glyph + text."""
    f = font("Anton.ttf", fontsize)
    tw = int(f.getlength(text))
    acc = hex_to_rgb(accent_hex)
    pill = Image.new("RGBA", (tw + 96, fontsize + 28), (0, 0, 0, 0))
    d = ImageDraw.Draw(pill)
    d.rounded_rectangle([0, 0, pill.width - 1, pill.height - 1], radius=16,
                        fill=(6, 20, 14, 200), outline=(*acc, 230), width=2)
    gx, gy = 28, pill.height // 2
    d.polygon([(gx, gy - 18), (gx + 16, gy - 18), (gx + 6, gy), (gx + 20, gy),
               (gx - 2, gy + 22), (gx + 6, gy + 2), (gx - 6, gy + 2)], fill=(*acc, 255))
    pill.alpha_composite(text_layer(text, f, (255, 255, 255)), (58, 8))
    return pill


def bottom_banner(w, text, base_hex="#0a2a14", accent_hex="#F5C451",
                  text_hex="#e6fff0", h=60):
    """A branded bottom bar with an accent top-edge."""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle([0, 4, w, h], fill=(*hex_to_rgb(base_hex), 235))
    d.rectangle([0, 0, w, 4], fill=(*hex_to_rgb(accent_hex), 255))
    lab = text_layer(text, font("BebasNeue.ttf", 30), hex_to_rgb(text_hex), shadow=0)
    lay.alpha_composite(lab, (int(w / 2 - lab.width / 2), int(h / 2 - lab.height / 2) + 2))
    return lay


def side_ticker(h, text, muted_hex="#8fd6b8", width=60, offset=0):
    """A vertical edge ticker; pass a per-frame `offset` to scroll it."""
    lay = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rectangle([0, 0, width, h], fill=(255, 255, 255, 16))
    unit = text_layer(text, font("BebasNeue.ttf", 26), hex_to_rgb(muted_hex),
                      shadow=0).rotate(90, expand=True)
    step = unit.height + 40
    y = -(offset % step)
    while y < h:
        lay.alpha_composite(unit, (int(width / 2 - unit.width / 2), int(y)))
        y += step
    return lay
