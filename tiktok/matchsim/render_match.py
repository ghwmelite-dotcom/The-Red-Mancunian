"""Compose the three acts into a PNG frame sequence driven by the timeline.

Brand-first: every act sits on the RED MANCUNIAN textured stadium background
(ink->dark-red gradient + pitch texture + ghosted watermark + crowd ring), with
the logo, a bottom brand banner, and a scrolling side ticker. The competition
only tints the neon arena ring.

The goal "wow" moment is animated: a moving goal net sweeps the ring, the ball
flies into it (ease-in), and on the score a celebration window pops "GOAL!"
(ease-out), ripples the net, flashes, and drops confetti.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import draw
import layout
import captions
from colors import hex_to_rgb

W, H = layout.W, layout.H

_bg_cache = {}


def _eo(t):  # ease-out (entrances)
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return 1 - (1 - t) ** 3


def _ei(t):  # ease-in (the shot accelerating into the net)
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return t ** 3


def _bg(theme, competition):
    """Shared brand textured stadium background, cached per (bg, competition)."""
    key = (tuple(theme["bg"]), competition)
    if key not in _bg_cache:
        img = draw.gradient_bg(theme["bg"], W, H)
        img.alpha_composite(draw.pitch_texture(W, H))
        cx, cy, r = layout.live_zones()["arena"]
        img.alpha_composite(draw.watermark(W, H, theme["watermark"], cx, cy, 760, alpha=18))
        seed = sum(ord(c) for c in competition) or 7
        img.alpha_composite(draw.crowd_ring(W, H, cx, cy, r, seed, theme["accent"]))
        v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(v).rectangle([0, H - 300, W, H], fill=(0, 0, 0, 80))
        img.alpha_composite(v.filter(ImageFilter.GaussianBlur(60)))
        _bg_cache[key] = img
    return _bg_cache[key]


def _center(img, layer, cx, y):
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(y)))


def _acc(theme):
    return hex_to_rgb(theme["accent"])


def _frame_base(bundle, fr):
    theme, fx = bundle["theme"], bundle["match"]["fixture"]
    img = _bg(theme, fx["competition"]).copy()
    offset = int(fr.get("t", 0) * 320)
    img.alpha_composite(draw.side_ticker(H, f"{theme['name'].upper()}  -  MATCHSIM  -  ",
                        muted_hex=theme["muted"], offset=offset), (W - 60, 0))
    img.alpha_composite(draw.bottom_banner(
        W, f"{theme['name'].upper()}  -  THE RED MANCUNIAN",
        base_hex=theme["bg"][0], accent_hex=theme["gold"], text_hex=theme["text"]),
        (0, H - 60))
    return img


def _pre_frame(bundle, fr):
    theme, fx = bundle["theme"], bundle["match"]["fixture"]
    img = _frame_base(bundle, fr)
    _center(img, draw.logo(96), W / 2, 40)
    _center(img, draw.text_layer(theme["name"].upper(), draw.font("BebasNeue.ttf", 44),
                                 hex_to_rgb(theme["muted"])), W / 2, 156)
    _center(img, draw.text_layer(f"KICK OFF IN  {fr['countdown']}",
                                 draw.font("BebasNeue.ttf", 56), hex_to_rgb(theme["gold"])),
            W / 2, 330)
    _center(img, draw.team_disc(300, fx["home"]), W * 0.27, 560)
    _center(img, draw.team_disc(300, fx["away"]), W * 0.73, 560)
    _center(img, draw.text_layer("VS", draw.font("Anton.ttf", 130), hex_to_rgb(theme["cream"])),
            W / 2, 620)
    _center(img, draw.text_layer(fx["home"]["name"].upper(), draw.font("Anton.ttf", 54),
                                 hex_to_rgb(theme["cream"])), W * 0.27, 900)
    _center(img, draw.text_layer(fx["away"]["name"].upper(), draw.font("Anton.ttf", 54),
                                 hex_to_rgb(theme["cream"])), W * 0.73, 900)
    _center(img, draw.text_layer(f"{theme['name'].upper()}  -  {fx['stage'].upper()}",
                                 draw.font("BebasNeue.ttf", 40),
                                 hex_to_rgb(theme["muted"])), W / 2, 1030)
    return img


def _moving_goal(img, cx, cy, r, net_angle, theme):
    """Bright goal mouth (arc) + net mesh at the current (moving) net angle."""
    d = ImageDraw.Draw(img)
    deg = -math.degrees(net_angle)          # PIL screen degrees (y flipped)
    gold = hex_to_rgb(theme["gold"])
    d.arc([cx - r, cy - r, cx + r, cy + r], deg - 24, deg + 24, fill=(255, 255, 255, 255), width=16)
    d.arc([cx - r, cy - r, cx + r, cy + r], deg - 24, deg + 24, fill=(*gold, 255), width=6)
    for off in range(-20, 21, 8):
        a2 = net_angle + math.radians(off)
        d.line([(cx + math.cos(a2) * r, cy - math.sin(a2) * r),
                (cx + math.cos(a2) * (r - 48), cy - math.sin(a2) * (r - 48))],
               fill=(255, 255, 255, 120), width=2)
    for rr in (r - 16, r - 34):
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], deg - 24, deg + 24,
              fill=(255, 255, 255, 90), width=2)


def _arena(img, bundle, motion_frame, cx, cy, r, theme, ball_norm):
    fx = bundle["match"]["fixture"]
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([cx - r, cy - r, cx + r, cy + r],
                                 outline=(*_acc(theme), 255), width=9)
    img.alpha_composite(ring.filter(ImageFilter.GaussianBlur(16)))
    img.alpha_composite(ring)

    disc_size = int(r * 0.50)
    halo_size = int(disc_size * 1.45)

    def screen(norm):
        return (cx + norm[0] * (r - disc_size / 2), cy - norm[1] * (r - disc_size / 2))

    ball = motion_frame["ball"]
    dh = (motion_frame["home"][0] - ball[0]) ** 2 + (motion_frame["home"][1] - ball[1]) ** 2
    da = (motion_frame["away"][0] - ball[0]) ** 2 + (motion_frame["away"][1] - ball[1]) ** 2
    poss = "home" if dh <= da else "away"

    for side in ("home", "away"):
        ox, oy = screen(motion_frame[side])
        if side == poss:
            hl = draw.halo(halo_size, fx[side]["color"], blur=20)
            _center(img, hl, ox, oy - halo_size / 2)
        _center(img, draw.team_disc(disc_size, fx[side]), ox, oy - disc_size / 2)

    bx, by = cx + ball_norm[0] * r, cy - ball_norm[1] * r
    ImageDraw.Draw(img).ellipse([bx - 10, by - 10, bx + 10, by + 10], fill=(255, 255, 255, 255))


def _scoreboard(img, fr, fx, theme, z, score_scale=1.0):
    d = ImageDraw.Draw(img)
    sx, sy, sw, sh = z["scoreboard"]
    home_x, score_x, away_x = z["score_anchors"]
    ct = draw.text_layer(fr["clock"], draw.font("Anton.ttf", 50), (10, 20, 14))
    d.rounded_rectangle([sx, sy + 20, sx + ct.width + 40, sy + 20 + ct.height + 18],
                        radius=12, fill=(255, 245, 240, 240))
    img.alpha_composite(ct, (sx + 20, sy + 28))
    _center(img, draw.team_disc(46, fx["home"]), home_x - 44, sy + 30)
    img.alpha_composite(draw.text_layer(fx["home"]["monogram"], draw.font("Anton.ttf", 36),
                        hex_to_rgb(theme["cream"])), (int(home_x - 18), sy + 34))
    aw = draw.text_layer(fx["away"]["monogram"], draw.font("Anton.ttf", 36), hex_to_rgb(theme["cream"]))
    img.alpha_composite(aw, (int(away_x + 18 - aw.width), sy + 34))
    _center(img, draw.team_disc(46, fx["away"]), away_x + 44, sy + 30)
    ssz = int(62 * score_scale)
    _center(img, draw.text_layer(str(fr["score"][0]), draw.font("Anton.ttf", ssz),
            hex_to_rgb(theme["cream"])), score_x - 56, sy + 24 - (ssz - 62) / 2)
    _center(img, draw.text_layer(str(fr["score"][1]), draw.font("Anton.ttf", ssz),
            hex_to_rgb(theme["cream"])), score_x + 56, sy + 24 - (ssz - 62) / 2)
    d.ellipse([score_x - 22, sy + 52, score_x + 22, sy + 96], fill=(*hex_to_rgb(theme["gold"]), 255))
    _center(img, draw.text_layer("*", draw.font("Anton.ttf", 34), (30, 12, 12)), score_x, sy + 48)
    strip = draw.text_layer(
        f"{theme['name'].upper()}  -  {fx['stage'].upper()}"
        + (f"  -  {fx['date']}" if fx.get("date") else ""),
        draw.font("BebasNeue.ttf", 26), hex_to_rgb(theme["muted"]), shadow=0)
    ss = Image.new("RGBA", (strip.width + 30, strip.height + 12), (0, 0, 0, 0))
    ImageDraw.Draw(ss).rounded_rectangle([0, 0, ss.width - 1, ss.height - 1], radius=8,
                                         fill=(255, 255, 255, 18),
                                         outline=(*hex_to_rgb(theme["gold"]), 90), width=1)
    ss.alpha_composite(strip, (15, 6))
    _center(img, ss, W / 2, sy + sh - 6)


def _live_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    z = layout.live_zones()
    img = _frame_base(bundle, fr)
    d = ImageDraw.Draw(img)

    hx, hy, hw, hh = z["header"]
    img.alpha_composite(draw.logo(52), (hx, hy - 8))
    img.alpha_composite(draw.text_layer("THE RED MANCUNIAN",
                        draw.font("BebasNeue.ttf", 34), hex_to_rgb(theme["text"])), (hx + 62, hy))
    livetxt = draw.text_layer("LIVE", draw.font("BebasNeue.ttf", 30), (255, 255, 255))
    lp = Image.new("RGBA", (livetxt.width + 46, livetxt.height + 14), (0, 0, 0, 0))
    ImageDraw.Draw(lp).rounded_rectangle([0, 0, lp.width - 1, lp.height - 1], radius=16,
                                         fill=(*hex_to_rgb(theme["red"]), 240))
    ImageDraw.Draw(lp).ellipse([12, lp.height / 2 - 5, 22, lp.height / 2 + 5], fill=(255, 255, 255, 255))
    lp.alpha_composite(livetxt, (30, 7))
    img.alpha_composite(lp, (hx + hw - lp.width, hy - 4))

    cel = fr.get("celebrate")
    score_scale = 1.0 + 0.3 * (1 - _eo(min(1.0, (cel or 0) / 0.4))) if cel is not None else 1.0
    _scoreboard(img, fr, fx, theme, z, score_scale=score_scale)

    px, py, pw, ph = z["progress"]
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph // 2, fill=(255, 255, 255, 40))
    fillw = int(pw * fr["t"])
    if fillw >= ph:
        d.rounded_rectangle([px, py, px + fillw, py + ph], radius=ph // 2,
                            fill=(*hex_to_rgb(theme["gold"]), 255))

    wx, wy, ww, wh = z["winprob"]
    img.alpha_composite(draw.text_layer("LIVE WIN PROBABILITY - DIXON-COLES",
                        draw.font("BebasNeue.ttf", 26), hex_to_rgb(theme["gold"])), (wx, wy))
    wp = fr["winprob"]
    bar_y = wy + 40
    img.alpha_composite(draw.winprob_bar(ww, 46, wp["home"], wp["draw"], wp["away"],
                        fx["home"]["color"], "#5a5a5a", fx["away"]["color"]), (wx, bar_y))
    total = max(1e-6, wp["home"] + wp["draw"] + wp["away"])
    hw_ = ww * wp["home"] / total
    aw_ = ww * wp["away"] / total
    _center(img, draw.text_layer(f"{round(wp['home'] * 100)}%", draw.font("Anton.ttf", 26),
            (255, 255, 255)), wx + hw_ / 2, bar_y + 8)
    _center(img, draw.text_layer(f"{round(wp['away'] * 100)}%", draw.font("Anton.ttf", 26),
            (10, 20, 14)), wx + ww - aw_ / 2, bar_y + 8)
    if fr.get("swing") and fr["swing"]["delta"] > 0:
        who = fx[fr["swing"]["team"]]["monogram"]
        tag = draw.text_layer(f"UP {who} +{fr['swing']['delta']}%",
                              draw.font("Anton.ttf", 30), (70, 220, 120))
        img.alpha_composite(tag, (wx + ww - tag.width, wy - 4))

    cx, cy, r = z["arena"]
    mi = fr["motion_index"]
    mfr = bundle["motion"][mi]
    # ball position: flying into the net during a shot, in the net during a goal,
    # otherwise the ambient clash-drift ball.
    if fr.get("shot_target") is not None:
        tgt = fr["shot_target"]
        sp = fr.get("shot_progress")
        if sp is not None and sp < 1.0:
            p = _ei(sp)
            ball_norm = [tgt[0] * p, tgt[1] * p]
        else:
            ball_norm = tgt
    else:
        ball_norm = mfr["ball"]

    _moving_goal(img, cx, cy, r, fr["net_angle"], theme)
    _arena(img, bundle, mfr, cx, cy, r, theme, ball_norm)

    if cel is not None:
        na = fr["net_angle"]
        nx, ny = cx + math.cos(na) * r, cy - math.sin(na) * r
        rd = ImageDraw.Draw(img)
        for k in range(3):
            rr = int(24 + cel * 170 + k * 34)
            a = max(0, int(210 * (1 - cel) - k * 45))
            if a > 0:
                rd.ellipse([nx - rr, ny - rr, nx + rr, ny + rr], outline=(255, 255, 255, a), width=4)
        fa = int(90 * (1 - cel))
        if fa > 0:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, fa)))
        img.alpha_composite(draw.confetti(W, H, seed=fx["seed"] + fr["minute"], n=150), (0, 0))
        gsize = int(60 + 82 * _eo(min(1.0, cel / 0.4)))
        _center(img, draw.text_layer("GOAL!", draw.font("Anton.ttf", gsize), (255, 255, 255)),
                W / 2, cy - gsize / 2)
    else:
        caption_text = None
        if fr.get("goal"):
            caption_text = captions.caption_for(fr["goal"], fx["seed"], sum(fr["score"]))
        elif mfr["clash"]:
            caption_text = captions.caption_for({"type": "near_miss", "flavour": "clash"},
                                                fx["seed"], mi)
        if caption_text:
            _center(img, draw.caption_pill(caption_text, theme["gold"]), W / 2, z["caption"][1])
    return img


def _post_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    an = match["analytics"]
    img = _frame_base(bundle, fr)
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _center(card, draw.wordmark(560), W / 2, 70)
    _center(card, draw.text_layer("FULL TIME", draw.font("BebasNeue.ttf", 52),
            hex_to_rgb(theme["gold"])), W / 2, 210)
    sh, sa = (int(x) for x in fx["final"].split("-"))
    _center(card, draw.team_disc(240, fx["home"]), W * 0.24, 340)
    _center(card, draw.team_disc(240, fx["away"]), W * 0.76, 340)
    _center(card, draw.text_layer(f"{sh} : {sa}", draw.font("Anton.ttf", 150),
            hex_to_rgb(theme["cream"])), W / 2, 370)
    winner = fx["home"]["name"] if sh > sa else (fx["away"]["name"] if sa > sh else None)
    if winner:
        _center(card, draw.text_layer(f"{winner.upper()} WIN", draw.font("Anton.ttf", 56),
                hex_to_rgb(theme["gold"])), W / 2, 640)
    panel = draw.glass_panel(W - 160, 500, radius=20)
    card.alpha_composite(panel, (80, 800))
    rows = [("POSSESSION", an["possession"]), ("SHOTS", an["shots"]), ("xG", an["xg"])]
    y = 856
    for label, (hv, av) in rows:
        _center(card, draw.text_layer(str(hv), draw.font("Anton.ttf", 52), hex_to_rgb(theme["cream"])), 240, y)
        _center(card, draw.text_layer(label, draw.font("BebasNeue.ttf", 34),
                hex_to_rgb(theme["muted"])), W / 2, y + 12)
        _center(card, draw.text_layer(str(av), draw.font("Anton.ttf", 52), hex_to_rgb(theme["cream"])), W - 240, y)
        y += 128
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
