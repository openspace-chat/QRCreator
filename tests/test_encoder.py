import pytest

from qr_backend.models import QRCoreRequest
from qr_backend.exceptions import QRCapacityError
from qr_backend.qr_encoder import analyze_qr


@pytest.mark.parametrize("level", ["L", "M", "Q", "H"])
def test_requested_error_level_is_not_boosted(level: str) -> None:
    result = analyze_qr(QRCoreRequest("123ABC/中国", error_level=level))
    assert result.requested_error_level == level
    assert result.actual_error_level == level
    assert result.matrix_size == 17 + 4 * result.version
    assert result.total_modules == result.matrix_size + 8


@pytest.mark.parametrize(
    "text",
    ["123ABC", "中国", "123ABC/中国", "日本語", "한국어", "العربية", "😀"],
)
def test_utf8_eci_unicode_inputs(text: str) -> None:
    result = analyze_qr(QRCoreRequest(text, error_level="M"))
    assert result.text == text
    assert result.encoded_byte_count == len(text.encode("utf-8"))
    assert result.matrix


def test_capacity_error_is_translated_to_domain_exception() -> None:
    with pytest.raises(QRCapacityError):
        analyze_qr(QRCoreRequest("x" * 5000, error_level="H"))


def test_explicit_version_can_be_locked_for_batch_generation() -> None:
    result = analyze_qr(QRCoreRequest("short", error_level="M", version=8))
    assert result.version == 8
