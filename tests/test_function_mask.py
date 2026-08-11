import pytest
import segno
from segno import consts

from qr_backend.function_mask import build_protected_mask


@pytest.mark.parametrize("version", [1, 2, 7, 10, 25, 40])
def test_mask_matches_body_size(version: int) -> None:
    size = 17 + 4 * version
    mask = build_protected_mask(version)
    assert len(mask) == size
    assert all(len(row) == size for row in mask)


def test_version_one_core_structures_are_protected() -> None:
    mask = build_protected_mask(1)
    assert mask[0][0]  # top-left finder
    assert mask[7][7]  # finder separator
    assert mask[6][10]  # horizontal timing
    assert mask[10][6]  # vertical timing
    assert mask[0][8] and mask[8][0]  # format information
    assert mask[13][8]  # fixed dark module
    assert not mask[10][10]  # central data region remains available


def test_alignment_and_version_information_are_protected() -> None:
    version_two = build_protected_mask(2)
    assert all(version_two[y][x] for y in range(16, 21) for x in range(16, 21))

    version_seven = build_protected_mask(7)
    size = len(version_seven)
    assert all(version_seven[y][x] for y in range(6) for x in range(size - 11, size - 8))
    assert all(version_seven[y][x] for y in range(size - 11, size - 8) for x in range(6))


@pytest.mark.parametrize("version", range(1, 41))
def test_mask_matches_segnos_independent_module_classification(version: int) -> None:
    qr = segno.make_qr("mask check", version=version, error="M", boost_error=False)
    verbose_matrix = tuple(
        tuple(row) for row in qr.matrix_iter(scale=1, border=0, verbose=True)
    )
    data_types = {consts.TYPE_DATA_DARK, consts.TYPE_DATA_LIGHT}
    expected_rows = [
        [module_type not in data_types for module_type in row]
        for row in verbose_matrix
    ]
    # Segno's verbose type map reserves one extra data neighbor immediately
    # before the upper-right format copy. Its encoder's add_format_info()
    # writes only columns size-8 through size-1, as required by the standard.
    expected_rows[8][len(expected_rows) - 9] = False
    expected = tuple(tuple(row) for row in expected_rows)
    assert build_protected_mask(version) == expected
