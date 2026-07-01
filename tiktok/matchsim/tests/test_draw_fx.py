import draw


def test_halo_size_and_transparent_by_default():
    h = draw.halo(200, "#DA020E", blur=20)
    assert h.size == (200, 200)
    assert h.mode == "RGBA"
    assert h.getpixel((1, 1))[3] < 255


def test_confetti_deterministic_and_sized():
    a = draw.confetti(400, 300, seed=7, n=60)
    b = draw.confetti(400, 300, seed=7, n=60)
    assert a.size == (400, 300)
    assert a.tobytes() == b.tobytes()
    c = draw.confetti(400, 300, seed=8, n=60)
    assert c.tobytes() != a.tobytes()


def test_confetti_actually_draws_particles():
    img = draw.confetti(200, 200, seed=1, n=120)
    assert any(img.getpixel((x, y))[3] > 0
               for x in range(0, 200, 7) for y in range(0, 200, 7))
