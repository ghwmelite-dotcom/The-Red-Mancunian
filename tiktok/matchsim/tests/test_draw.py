from PIL import Image
import draw


def test_font_loads():
    f = draw.font("Anton.ttf", 48)
    assert f.size == 48


def test_gradient_bg_size():
    img = draw.gradient_bg(["#0b1030", "#131a48", "#080b24"], 1080, 1920)
    assert img.size == (1080, 1920)
    assert img.mode == "RGBA"


def test_orb_is_square_rgba_and_has_opaque_center():
    orb = draw.orb(120, "#DA020E", "MUN")
    assert orb.size == (120, 120)
    assert orb.mode == "RGBA"
    assert orb.getpixel((60, 60))[3] == 255
    assert orb.getpixel((2, 2))[3] == 0


def test_text_layer_nonempty():
    layer = draw.text_layer("GOAL", draw.font("Anton.ttf", 60), (255, 255, 255))
    assert layer.mode == "RGBA"
    assert layer.size[0] > 0 and layer.size[1] > 0


def test_winprob_bar_size_and_opaque():
    bar = draw.winprob_bar(600, 40, 0.5, 0.3, 0.2,
                           "#DA020E", "#5a5a5a", "#cccccc")
    assert bar.size == (600, 40)
    assert bar.getpixel((10, 20))[3] == 255


def test_glass_panel_size():
    p = draw.glass_panel(400, 200, radius=16)
    assert p.size == (400, 200)
    assert p.mode == "RGBA"
