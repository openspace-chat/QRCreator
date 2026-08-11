from io import BytesIO

import pytest
from PIL import Image

from generate_from_json import (
    DEFAULT_REQUEST_FILE,
    build_request,
    generate_from_payload,
    parse_rgba,
)


def _payload() -> dict[str, object]:
    return {
        "core": {"text": "前端数据/123", "error_level": "H"},
        "size_mode": "fixed_size",
        "qr_width": 201,
        "qr_height": 199,
        "canvas_width": 221,
        "canvas_height": 219,
        "foreground_color": [1, 2, 3, 255],
        "background_color": [255, 255, 255, 0],
        "canvas_color": [255, 255, 255, 255],
        "logo": None,
        "output_format": "png",
        "output_path": "generated/result.png",
    }


def test_frontend_json_values_are_translated(tmp_path) -> None:
    request = build_request(_payload(), tmp_path)
    assert request.core.text == "前端数据/123"
    assert request.core.error_level == "H"
    assert request.foreground_color == (1, 2, 3, 255)
    assert request.qr_width == 201
    assert request.size_mode == "fixed_size"


def test_logo_canvas_values_are_translated(tmp_path) -> None:
    payload = _payload()
    payload["logo"] = {
        "enabled": False,
        "file_path": None,
        "width": 51,
        "height": 52,
        "canvas_width": 61,
        "canvas_height": 62,
        "shape": "rounded_square",
        "corner_radius": 9,
        "padding": 0,
        "x": None,
        "y": None,
        "transparent_background": False,
        "background_color": [10, 20, 30, 255],
    }

    request = build_request(payload, tmp_path)

    assert request.logo is not None
    assert request.logo.canvas_width == 61
    assert request.logo.canvas_height == 62
    assert request.logo.transparent_background is False
    assert request.logo.background_color == (10, 20, 30, 255)


def test_size_mode_selects_fixed_module(tmp_path) -> None:
    payload = _payload()
    payload["size_mode"] = "fixed_module"
    payload["pixels_per_module"] = 7
    result, output_path = generate_from_payload(payload, tmp_path)
    assert result.size_mode == "fixed_module"
    assert result.pixels_per_module == 7
    assert result.qr_width == result.total_modules * 7
    assert output_path.is_file()


def test_json_core_can_lock_a_higher_version(tmp_path) -> None:
    payload = _payload()
    payload["core"]["version"] = 8  # type: ignore[index]

    result, _ = generate_from_payload(payload, tmp_path)

    assert result.version == 8


@pytest.mark.parametrize("version", [0, 41])
def test_json_core_rejects_version_outside_standard_range(tmp_path, version: int) -> None:
    payload = _payload()
    payload["core"]["version"] = version  # type: ignore[index]

    with pytest.raises(ValueError, match="1 到 40"):
        build_request(payload, tmp_path)


def test_mode_rejects_unknown_value(tmp_path) -> None:
    payload = _payload()
    payload["size_mode"] = "size"
    try:
        build_request(payload, tmp_path)
    except ValueError as exc:
        assert "fixed_size 或 fixed_module" in str(exc)
    else:
        raise AssertionError("An unknown size mode must not be accepted.")


def test_entrypoint_generates_requested_file(tmp_path) -> None:
    result, output_path = generate_from_payload(_payload(), tmp_path)
    assert output_path == (tmp_path / "generated/result.png").resolve()
    assert output_path.read_bytes() == result.image_bytes
    with Image.open(BytesIO(result.image_bytes)) as image:
        assert image.size == (221, 219)


def test_rgb_array_gets_opaque_alpha() -> None:
    assert parse_rgba([10, 20, 30], "color") == (10, 20, 30, 255)


def test_default_request_template_is_in_examples_directory() -> None:
    assert DEFAULT_REQUEST_FILE.name == "request_template.json"
    assert DEFAULT_REQUEST_FILE.parent.name == "examples"
    assert DEFAULT_REQUEST_FILE.is_file()
