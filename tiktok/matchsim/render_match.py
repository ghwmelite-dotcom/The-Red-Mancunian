"""Compose the three acts into a PNG frame sequence driven by the timeline.

Act 1 pre-match: competition lockup, KICK OFF IN countdown, two orbs + VS.
Act 2 live: header, scoreboard, clock progress, win-prob bar, arena (orbs+ball),
            arcade caption on clash/goal frames.
Act 3 full-time: FULL TIME, big score, winner highlight, analytics panel.

Visual polish (goal replay/tracer/confetti, SFX, ticker scroll) is Plan 4.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import draw
import layout
import captions
from colors import hex_to_rgb

W, H = layout.W, layout.H

_bg_cache = {}


def _bg(theme):
    """Gradient background + vignette, cached by the theme's bg stops. The
    O(W*H) gradient is built once, not per frame; callers must .copy() before
    drawing so the shared cached image is never mutated."""
    key = tuple(theme["bg"])
    if key not in _bg_cache:
        img = draw.gradient_bg(theme["bg"], W, H)
        v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(v).rectangle([0, H - 320, W, H], fill=(0, 0, 0, 90))
        img.alpha_composite(v.filter(ImageFilter.GaussianBlur(60)))
        _bg_cache[key] = img
    return _bg_cache[key]


def _center(img, layer, cx, y):
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(y)))


def _acc(theme):
    return hex_to_rgb(theme["accent"])


def _pre_frame(bundle, fr):
    theme, fx = bundle["theme"], bundle["match"]["fixture"]
    img = _bg(theme).copy()
    _center(img, draw.text_layer(theme["name"].upper(), draw.font("BebasNeue.ttf", 46),
                                 hex_to_rgb(theme["muted"])), W / 2, 120)
    _center(img, draw.text_layer(f"KICK OFF IN  {fr['countdown']}",
                                 draw.font("BebasNeue.ttf", 56), _acc(theme)), W / 2, 300)
    _center(img, draw.orb(300, fx["home"]["color"], fx["home"]["monogram"]),
            W * 0.27, 560)
    _center(img, draw.orb(300, fx["away"]["color"], fx["away"]["monogram"]),
            W * 0.73, 560)
    _center(img, draw.text_layer("VS", draw.font("Anton.ttf", 130),
                                 (255, 255, 255)), W / 2, 620)
    _center(img, draw.text_layer(fx["home"]["name"].upper(), draw.font("Anton.ttf", 54),
                                 (255, 255, 255)), W * 0.27, 900)
    _center(img, draw.text_layer(fx["away"]["name"].upper(), draw.font("Anton.ttf", 54),
                                 (255, 255, 255)), W * 0.73, 900)
    _center(img, draw.text_layer(f"{theme['name'].upper()}  -  {fx['stage'].upper()}",
                                 draw.font("BebasNeue.ttf", 40),
                                 hex_to_rgb(theme["muted"])), W / 2, 1040)
    return img


def _arena(img, bundle, motion_frame, cx, cy, r, theme):
    fx = bundle["match"]["fixture"]
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ring)
    acc = _acc(theme)
    dd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*acc, 255), width=8)
    glow = ring.filter(ImageFilter.GaussianBlur(18))
    img.alpha_composite(glow)
    img.alpha_composite(ring)

    disc_size = int(r * 0.46)

    def screen(norm, size):
        return (cx + norm[0] * (r - size / 2), cy - norm[1] * (r - size / 2))

    ball = motion_frame["ball"]
    dh = (motion_frame["home"][0] - ball[0]) ** 2 + (motion_frame["home"][1] - ball[1]) ** 2
    da = (motion_frame["away"][0] - ball[0]) ** 2 + (motion_frame["away"][1] - ball[1]) ** 2
    poss = "home" if dh <= da else "away"

    halo_size = int(disc_size * 1.7)
    for side in ("home", "away"):
        ox, oy = screen(motion_frame[side], disc_size)
        if side == poss:
            hl = draw.halo(halo_size, fx[side]["color"], blur=22)
            _center(img, hl, ox, oy - halo_size / 2)
        disc = draw.orb(disc_size, fx[side]["color"], fx[side]["monogram"])
        _center(img, disc, ox, oy - disc_size / 2)

    bx = cx + ball[0] * r
    by = cy - ball[1] * r
    ImageDraw.Draw(img).ellipse([bx - 9, by - 9, bx + 9, by + 9],
                                fill=(255, 255, 255, 255))


def _live_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    z = layout.live_zones()
    img = _bg(theme).copy()
    d = ImageDraw.Draw(img)

    hx, hy, hw, hh = z["header"]
    img.alpha_composite(draw.text_layer("THE RED MANCUNIAN",
                        draw.font("BebasNeue.ttf", 34), hex_to_rgb(theme["text"])), (hx, hy))
    livelbl = draw.text_layer("LIVE", draw.font("BebasNeue.ttf", 34), (255, 80, 80))
    img.alpha_composite(livelbl, (hx + hw - livelbl.width, hy))

    sx, sy, sw, sh = z["scoreboard"]
    home_x, score_x, away_x = z["score_anchors"]
    ct = draw.text_layer(fr["clock"], draw.font("Anton.ttf", 52), (10, 14, 42))
    d.rounded_rectangle([sx, sy + 24, sx + ct.width + 40, sy + 24 + ct.height + 18],
                        radius=12, fill=(255, 255, 255, 235))
    img.alpha_composite(ct, (sx + 20, sy + 32))
    _center(img, draw.text_layer(fx["home"]["monogram"], draw.font("Anton.ttf", 40),
            hex_to_rgb(fx["home"]["color"])), home_x, sy + 44)
    _center(img, draw.text_layer(f"{fr['score'][0]}  -  {fr['score'][1]}",
            draw.font("Anton.ttf", 66), (255, 255, 255)), score_x, sy + 28)
    _center(img, draw.text_layer(fx["away"]["monogram"], draw.font("Anton.ttf", 40),
            hex_to_rgb(fx["away"]["color"])), away_x, sy + 44)

    px, py, pw, ph = z["progress"]
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph // 2, fill=(255, 255, 255, 40))
    fillw = int(pw * fr["t"])
    if fillw >= ph:
        d.rounded_rectangle([px, py, px + fillw, py + ph], radius=ph // 2,
                            fill=(*_acc(theme), 255))

    wx, wy, ww, wh = z["winprob"]
    img.alpha_composite(draw.text_layer("LIVE WIN PROBABILITY - DIXON-COLES",
                        draw.font("BebasNeue.ttf", 26), hex_to_rgb(theme["gold"])), (wx, wy))
    wp = fr["winprob"]
    bar_y = wy + 40
    bar = draw.winprob_bar(ww, 46, wp["home"], wp["draw"], wp["away"],
                           fx["home"]["color"], "#5a5a5a", fx["away"]["color"])
    img.alpha_composite(bar, (wx, bar_y))
    total = max(1e-6, wp["home"] + wp["draw"] + wp["away"])
    hw_ = ww * wp["home"] / total
    aw_ = ww * wp["away"] / total
    _center(img, draw.text_layer(f"{round(wp['home'] * 100)}%",
            draw.font("Anton.ttf", 26), (255, 255, 255)), wx + hw_ / 2, bar_y + 8)
    _center(img, draw.text_layer(f"{round(wp['away'] * 100)}%",
            draw.font("Anton.ttf", 26), (10, 14, 42)), wx + ww - aw_ / 2, bar_y + 8)
    if fr.get("swing") and fr["swing"]["delta"] > 0:
        sw_ = fr["swing"]
        who = fx[sw_["team"]]["monogram"]
        tag = draw.text_layer(f"UP {who} +{sw_['delta']}%",
                              draw.font("Anton.ttf", 30), (70, 220, 120))
        img.alpha_composite(tag, (wx + ww - tag.width, wy - 4))

    cx, cy, r = z["arena"]
    mi = fr["motion_index"]
    _arena(img, bundle, bundle["motion"][mi], cx, cy, r, theme)

    caption_text = None
    if fr.get("goal"):
        caption_text = captions.caption_for(fr["goal"], fx["seed"], fr["score"][0] + fr["score"][1])
    elif bundle["motion"][mi]["clash"]:
        caption_text = captions.caption_for({"type": "near_miss", "flavour": "clash"},
                                            fx["seed"], mi)
    if caption_text:
        cxr, cyr, cwr, chr_ = z["caption"]
        pill_font = draw.font("Anton.ttf", 54)
        tw = int(pill_font.getlength(caption_text))
        pill = draw.glass_panel(tw + 60, 84, radius=18,
                                fill=(10, 14, 42, 180), outline=(245, 196, 81, 200))
        _center(img, pill, W / 2, cyr)
        _center(img, draw.text_layer(caption_text, pill_font, (255, 255, 255)),
                W / 2, cyr + 10)

    if fr.get("goal"):
        flash = Image.new("RGBA", (W, H), (255, 255, 255, 60))
        img.alpha_composite(flash)
        img.alpha_composite(draw.confetti(W, H, seed=fx["seed"] + fr["minute"], n=140),
                            (0, 0))
        _center(img, draw.text_layer("GOAL!", draw.font("Anton.ttf", 120),
                (255, 255, 255)), W / 2, cy - 40)
    return img


def _post_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    an = match["analytics"]
    img = _bg(theme).copy()
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _center(card, draw.text_layer("FULL TIME", draw.font("BebasNeue.ttf", 52),
            _acc(theme)), W / 2, 150)
    sh, sa = (int(x) for x in fx["final"].split("-"))
    _center(card, draw.orb(240, fx["home"]["color"], fx["home"]["monogram"]), W * 0.24, 300)
    _center(card, draw.orb(240, fx["away"]["color"], fx["away"]["monogram"]), W * 0.76, 300)
    _center(card, draw.text_layer(f"{sh} : {sa}", draw.font("Anton.ttf", 150),
            (255, 255, 255)), W / 2, 330)
    winner = fx["home"]["name"] if sh > sa else (fx["away"]["name"] if sa > sh else None)
    if winner:
        _center(card, draw.text_layer(f"{winner.upper()} WIN", draw.font("Anton.ttf", 56),
                hex_to_rgb(theme["gold"])), W / 2, 600)
    panel = draw.glass_panel(W - 160, 520, radius=20)
    card.alpha_composite(panel, (80, 760))
    rows = [("POSSESSION", an["possession"]), ("SHOTS", an["shots"]), ("xG", an["xg"])]
    y = 820
    for label, (hv, av) in rows:
        _center(card, draw.text_layer(str(hv), draw.font("Anton.ttf", 52), (255, 255, 255)),
                240, y)
        _center(card, draw.text_layer(label, draw.font("BebasNeue.ttf", 34),
                hex_to_rgb(theme["muted"])), W / 2, y + 12)
        _center(card, draw.text_layer(str(av), draw.font("Anton.ttf", 52), (255, 255, 255)),
                W - 240, y)
        y += 130
    alpha = min(1.0, fr["t"] / 0.35)
    if alpha < 1.0:
        r_, g_, b_, a_ = card.split()
        card = Image.merge("RGBA", (r_, g_, b_, a_.point(lambda v: int(v * alpha))))
    img.alpha_composite(card)
    return img


def render_frames(bundle, timeline, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, fr in enumerate(timeline["frames"]):
        if fr["act"] == "pre":
            img = _pre_frame(bundle, fr)
        elif fr["act"] == "live":
            img = _live_frame(bundle, fr)
        elif fr["act"] == "post":
            img = _post_frame(bundle, fr)
        else:
            raise ValueError(f"unknown act {fr['act']!r}")
        p = out_dir / f"f{i:05d}.png"
        img.convert("RGB").save(p)
        paths.append(str(p))
    return paths
