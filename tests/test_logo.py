from PIL import Image

from qr_backend.compositor import apply_logo_cutout, composite_logo
from qr_backend.function_mask import build_protected_mask
from qr_backend.layout import solve_layout
from qr_backend.logo import check_logo_overlap, solve_logo_layout
from qr_backend.models import LogoLayout, LogoRequest, QRCoreRequest, QRRequest

from conftest import make_analysis


def _layout():
    analysis = make_analysis(version=1)
    request = QRRequest(
        core=QRCoreRequest("x", "M"),
        size_mode="fixed_module",
        pixels_per_module=10,
    )
    return analysis, solve_layout(request, analysis)


def test_center_logo_and_padding_layout() -> None:
    _, qr_layout = _layout()
    layout = solve_logo_layout(
        LogoRequest(enabled=True, width=20, height=30, padding=5), qr_layout
    )
    assert (layout.logo_x, layout.logo_y) == (135, 130)
    assert (layout.cutout_x, layout.cutout_y) == (130, 125)
    assert (layout.cutout_width, layout.cutout_height) == (30, 40)


def test_explicit_logo_canvas_is_centered_around_logo() -> None:
    _, qr_layout = _layout()
    layout = solve_logo_layout(
        LogoRequest(
            enabled=True,
            width=20,
            height=10,
            canvas_width=60,
            canvas_height=40,
        ),
        qr_layout,
    )
    assert (layout.logo_x, layout.logo_y) == (135, 140)
    assert (layout.cutout_x, layout.cutout_y) == (115, 125)
    assert (layout.cutout_width, layout.cutout_height) == (60, 40)


def test_safe_center_and_unsafe_finder_overlap() -> None:
    analysis, qr_layout = _layout()
    protected = build_protected_mask(1)
    center = solve_logo_layout(
        LogoRequest(enabled=True, width=10, height=10, shape="circle"), qr_layout
    )
    assert check_logo_overlap(center, analysis, qr_layout, protected).safe

    finder = solve_logo_layout(
        LogoRequest(enabled=True, width=20, height=20, x=40, y=40), qr_layout
    )
    result = check_logo_overlap(finder, analysis, qr_layout, protected)
    assert not result.safe
    assert result.protected_module_count > 0


def test_all_cutout_shapes_clear_alpha() -> None:
    source = Image.new("RGBA", (20, 20), (0, 0, 0, 255))
    for shape, radius in (("square", 0), ("rounded_square", 3), ("circle", 0)):
        layout = LogoLayout(7, 7, 6, 6, 5, 5, 10, 10, shape, radius)
        result = apply_logo_cutout(source, layout)
        assert result.getpixel((10, 10))[3] == 0
        if shape == "circle":
            assert result.getpixel((5, 5))[3] == 255


def test_transparent_logo_is_preserved_during_composition() -> None:
    qr = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    logo = Image.new("RGBA", (4, 4), (255, 0, 0, 128))
    layout = LogoLayout(8, 8, 4, 4, 8, 8, 4, 4, "square", 0)
    result = composite_logo(qr, logo, layout)
    assert result.getpixel((9, 9)) == (255, 0, 0, 128)
