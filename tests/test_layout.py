from qr_backend.layout import solve_layout
from qr_backend.models import QRCoreRequest, QRRequest

from conftest import make_analysis


def test_fixed_size_is_exact_and_centered() -> None:
    analysis = make_analysis(version=3)
    request = QRRequest(
        core=QRCoreRequest("x", "M"),
        size_mode="fixed_size",
        qr_width=300,
        qr_height=300,
        canvas_width=350,
        canvas_height=350,
    )
    layout = solve_layout(request, analysis)
    assert (layout.qr_width, layout.qr_height) == (300, 300)
    assert (layout.qr_x, layout.qr_y) == (25, 25)
    assert layout.module_width == 300 / 37
    assert layout.pixels_per_module is None


def test_fixed_module_uses_exact_integer_scale() -> None:
    analysis = make_analysis(version=3)
    request = QRRequest(
        core=QRCoreRequest("x", "M"),
        size_mode="fixed_module",
        pixels_per_module=10,
        canvas_width=500,
        canvas_height=500,
    )
    layout = solve_layout(request, analysis)
    assert (layout.qr_width, layout.qr_height) == (370, 370)
    assert layout.module_width == layout.module_height == 10
    assert (layout.qr_x, layout.qr_y) == (65, 65)


def test_explicit_position_is_preserved() -> None:
    analysis = make_analysis()
    request = QRRequest(
        core=QRCoreRequest("x", "M"),
        size_mode="fixed_size",
        qr_width=100,
        qr_height=90,
        canvas_width=200,
        canvas_height=200,
        qr_position_x=-3,
        qr_position_y=17,
    )
    layout = solve_layout(request, analysis)
    assert (layout.qr_x, layout.qr_y) == (-3, 17)

