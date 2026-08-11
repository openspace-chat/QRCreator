from qr_backend.renderer import render_fixed_module_qr, render_fixed_size_qr


BLACK = (0, 0, 0, 255)
TRANSPARENT = (255, 255, 255, 0)


def test_fixed_module_has_exact_integer_edges_and_no_antialiasing() -> None:
    image = render_fixed_module_qr(((True,),), 3, 1, BLACK, TRANSPARENT)
    assert image.size == (9, 9)
    assert image.getpixel((3, 3)) == BLACK
    assert image.getpixel((5, 5)) == BLACK
    assert image.getpixel((2, 3)) == TRANSPARENT
    assert set(image.getdata()) == {BLACK, TRANSPARENT}


def test_fixed_size_is_never_changed_for_non_divisible_dimensions() -> None:
    image = render_fixed_size_qr(((True,),), 10, 11, 1, BLACK, TRANSPARENT)
    assert image.size == (10, 11)
    assert set(image.getdata()) <= {BLACK, TRANSPARENT}

