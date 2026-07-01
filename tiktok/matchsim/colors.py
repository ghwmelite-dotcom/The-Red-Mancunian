"""Small colour helpers for the renderer: hex<->rgb and linear interpolation."""


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % (rgb[0], rgb[1], rgb[2])


def lerp_rgb(a, b, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
