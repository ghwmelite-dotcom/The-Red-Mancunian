"""Compose the three acts into a PNG frame sequence driven by the timeline.

Act 1 pre-match: competition lockup, KICK OFF IN countdown, team discs + VS.
Act 2 live: header, rich scoreboard, clock progress, win-prob bar, arena
            (team discs + ball + goal net), arcade caption, goal flash.
Act 3 full-time: FULL TIME, big score, winner, analytics panel.

Every act sits on a shared textured "stadium" background (pitch stripes + dot
grid + ghosted watermark + crowd ring), cached per (theme, competition). A
bottom brand banner and a scrolling side ticker frame every screen.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import draw
import layout
import captions
from colors import hex_to_rgb

W, H = layout.W, layout.H

_bg_cache = {}
_WATERMARK = {"wc": "26", "ucl": "UCL", "epl": "EPL"}


def _bg(theme, competition):
    """Shared textured stadium background, cached per (theme bg, competition):
    gradient + pitch texture + ghosted watermark + crowd ring + vignette."""
    key = (tuple(theme["bg"]), competition)
    if key not in _bg_cache:
        img = draw.gradient_bg(theme["bg"], W, H)
        img.alpha_composite(draw.pitch_texture(W, H))
        cx, cy, r = layout.live_zones()["arena"]
        wm = _WATERMARK.get(competition, "26")
        img.alpha_composite(draw.watermark(W, H, wm, cx, cy, 760, alpha=15))
        seed = sum(ord(c) for c in competition) or 7  # stable, deterministic
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
    """Background copy + bottom banner + scrolling side ticker (all acts)."""
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
    _center(img, draw.text_layer(theme["name"].upper(), draw.font("BebasNeue.ttf", 46),
                                 hex_to_rgb(theme["muted"])), W / 2, 130)
    _center(img, draw.text_layer(f"KICK OFF IN  {fr['countdown']}",
                                 draw.font("BebasNeue.ttf", 56), _acc(theme)), W / 2, 320)
    _center(img, draw.team_disc(300, fx["home"]), W * 0.27, 560)
    _center(img, draw.team_disc(300, fx["away"]), W * 0.73, 560)
    _center(img, draw.text_layer("VS", draw.font("Anton.ttf", 130),
                                 (255, 255, 255)), W / 2, 620)
    _center(img, draw.text_layer(fx["home"]["name"].upper(), draw.font("Anton.ttf", 54),
                                 (255, 255, 255)), W * 0.27, 900)
    _center(img, draw.text_layer(fx["away"]["name"].upper(), draw.font("Anton.ttf", 54),
                                 (255, 255, 255)), W * 0.73, 900)
    _center(img, draw.text_layer(f"{theme['name'].upper()}  -  {fx['stage'].upper()}",
                                 draw.font("BebasNeue.ttf", 40),
                                 hex_to_rgb(theme["muted"])), W / 2, 1030)
    return img


def _arena(img, bundle, motion_frame, cx, cy, r, theme):
    fx = bundle["match"]["fixture"]
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([cx - r, cy - r, cx + r, cy + r],
                                 outline=(*_acc(theme), 255), width=9)
    img.alpha_composite(ring.filter(ImageFilter.GaussianBlur(16)))
    img.alpha_composite(ring)
    net = draw.goal_net()
    img.alpha_composite(net, (int(cx - net.width / 2), int(cy - r - net.height + 12)))

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

    bx, by = cx + ball[0] * r, cy - ball[1] * r
    ImageDraw.Draw(img).ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=(255, 255, 255, 255))


def _scoreboard(img, fr, fx, theme, z):
    d = ImageDraw.Draw(img)
    sx, sy, sw, sh = z["scoreboard"]
    home_x, score_x, away_x = z["score_anchors"]
    # clock tile
    ct = draw.text_layer(fr["clock"], draw.font("Anton.ttf", 50), (10, 20, 14))
    d.rounded_rectangle([sx, sy + 20, sx + ct.width + 40, sy + 20 + ct.height + 18],
                        radius=12, fill=(255, 255, 255, 235))
    img.alpha_composite(ct, (sx + 20, sy + 28))
    # team chips + codes
    _center(img, draw.team_disc(46, fx["home"]), home_x - 44, sy + 30)
    img.alpha_composite(draw.text_layer(fx["home"]["monogram"], draw.font("Anton.ttf", 36),
                        (255, 255, 255)), (int(home_x - 18), sy + 34))
    aw = draw.text_layer(fx["away"]["monogram"], draw.font("Anton.ttf", 36), (255, 255, 255))
    img.alpha_composite(aw, (int(away_x + 18 - aw.width), sy + 34))
    _center(img, draw.team_disc(46, fx["away"]), away_x + 44, sy + 30)
    # scores + gold trophy divider
    _center(img, draw.text_layer(str(fr["score"][0]), draw.font("Anton.ttf", 62),
            (255, 255, 255)), score_x - 56, sy + 24)
    _center(img, draw.text_layer(str(fr["score"][1]), draw.font("Anton.ttf", 62),
            (255, 255, 255)), score_x + 56, sy + 24)
    d.ellipse([score_x - 22, sy + 52, score_x + 22, sy + 96], fill=(*hex_to_rgb(theme["gold"]), 255))
    _center(img, draw.text_layer("*", draw.font("Anton.ttf", 34), (10, 20, 14)),
            score_x, sy + 48)
    # competition sub-strip
    strip = draw.text_layer(
        f"{theme['name'].upper()}  -  {fx['stage'].upper()}"
        + (f"  -  {fx['date']}" if fx.get("date") else ""),
        draw.font("BebasNeue.ttf", 26), hex_to_rgb(theme["muted"]), shadow=0)
    ss = Image.new("RGBA", (strip.width + 30, strip.height + 12), (0, 0, 0, 0))
    ImageDraw.Draw(ss).rounded_rectangle([0, 0, ss.width - 1, ss.height - 1], radius=8,
                                         fill=(255, 255, 255, 20),
                                         outline=(*hex_to_rgb(theme["muted"]), 70), width=1)
    ss.alpha_composite(strip, (15, 6))
    _center(img, ss, W / 2, sy + sh - 6)


def _live_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    z = layout.live_zones()
    img = _frame_base(bundle, fr)
    d = ImageDraw.Draw(img)

    hx, hy, hw, hh = z["header"]
    img.alpha_composite(draw.text_layer("THE RED MANCUNIAN",
                        draw.font("BebasNeue.ttf", 34), hex_to_rgb(theme["text"])), (hx, hy))
    live = draw.text_layer("LIVE", draw.font("BebasNeue.ttf", 30), (255, 255, 255))
    lp = Image.new("RGBA", (live.width + 46, live.height + 14), (0, 0, 0, 0))
    ImageDraw.Draw(lp).rounded_rectangle([0, 0, lp.width - 1, lp.height - 1], radius=16,
                                         fill=(200, 20, 20, 235))
    ImageDraw.Draw(lp).ellipse([12, lp.height / 2 - 5, 22, lp.height / 2 + 5], fill=(255, 255, 255, 255))
    lp.alpha_composite(live, (30, 7))
    img.alpha_composite(lp, (hx + hw - lp.width, hy - 4))

    _scoreboard(img, fr, fx, theme, z)

    px, py, pw, ph = z["progress"]
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph // 2, fill=(255, 255, 255, 40))
    fillw = int(pw * fr["t"])
    if fillw >= ph:
        d.rounded_rectangle([px, py, px + fillw, py + ph], radius=ph // 2, fill=(*_acc(theme), 255))

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
    _arena(img, bundle, bundle["motion"][mi], cx, cy, r, theme)

    caption_text = None
    if fr.get("goal"):
        caption_text = captions.caption_for(fr["goal"], fx["seed"], sum(fr["score"]))
    elif bundle["motion"][mi]["clash"]:
        caption_text = captions.caption_for({"type": "near_miss", "flavour": "clash"},
                                            fx["seed"], mi)
    if caption_text:
        _center(img, draw.caption_pill(caption_text, theme["gold"]), W / 2, z["caption"][1])

    if fr.get("goal"):
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 60)))
        img.alpha_composite(draw.confetti(W, H, seed=fx["seed"] + fr["minute"], n=140), (0, 0))
        _center(img, draw.text_layer("GOAL!", draw.font("Anton.ttf", 120), (255, 255, 255)),
                W / 2, cy - 40)
    return img


def _post_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    an = match["analytics"]
    img = _frame_base(bundle, fr)
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _center(card, draw.text_layer("FULL TIME", draw.font("BebasNeue.ttf", 52),
            _acc(theme)), W / 2, 150)
    sh, sa = (int(x) for x in fx["final"].split("-"))
    _center(card, draw.team_disc(240, fx["home"]), W * 0.24, 300)
    _center(card, draw.team_disc(240, fx["away"]), W * 0.76, 300)
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
        _center(card, draw.text_layer(str(hv), draw.font("Anton.ttf", 52), (255, 255, 255)), 240, y)
        _center(card, draw.text_layer(label, draw.font("BebasNeue.ttf", 34),
                hex_to_rgb(theme["muted"])), W / 2, y + 12)
        _center(card, draw.text_layer(str(av), draw.font("Anton.ttf", 52), (255, 255, 255)), W - 240, y)
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
