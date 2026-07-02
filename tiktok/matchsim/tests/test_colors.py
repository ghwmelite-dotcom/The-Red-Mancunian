import pytest
from colors import hex_to_rgb, rgb_to_hex, lerp_rgb


def test_hex_to_rgb():
    assert hex_to_rgb("#DA020E") == (218, 2, 14)
    assert hex_to_rgb("39e6e6") == (57, 230, 230)


def test_rgb_to_hex_roundtrip():
    assert rgb_to_hex((218, 2, 14)) == "#DA020E"
    assert hex_to_rgb(rgb_to_hex((1, 2, 3))) == (1, 2, 3)


def test_lerp_endpoints_and_mid():
    a, b = (0, 0, 0), (100, 200, 50)
    assert lerp_rgb(a, b, 0.0) == (0, 0, 0)
    assert lerp_rgb(a, b, 1.0) == (100, 200, 50)
    assert lerp_rgb(a, b, 0.5) == (50, 100, 25)


def test_lerp_clamps_out_of_range():
    a, b = (0, 0, 0), (100, 100, 100)
    assert lerp_rgb(a, b, -1.0) == (0, 0, 0)
    assert lerp_rgb(a, b, 2.0) == (100, 100, 100)
