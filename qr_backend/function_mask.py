"""Build the QR functional-module protection mask for versions 1 through 40."""

from .exceptions import QRGenerationError


# ISO/IEC 18004 alignment pattern centre coordinates, indexed by version.
ALIGNMENT_PATTERN_CENTERS: tuple[tuple[int, ...], ...] = (
    (),
    (),
    (6, 18),
    (6, 22),
    (6, 26),
    (6, 30),
    (6, 34),
    (6, 22, 38),
    (6, 24, 42),
    (6, 26, 46),
    (6, 28, 50),
    (6, 30, 54),
    (6, 32, 58),
    (6, 34, 62),
    (6, 26, 46, 66),
    (6, 26, 48, 70),
    (6, 26, 50, 74),
    (6, 30, 54, 78),
    (6, 30, 56, 82),
    (6, 30, 58, 86),
    (6, 34, 62, 90),
    (6, 28, 50, 72, 94),
    (6, 26, 50, 74, 98),
    (6, 30, 54, 78, 102),
    (6, 28, 54, 80, 106),
    (6, 32, 58, 84, 110),
    (6, 30, 58, 86, 114),
    (6, 34, 62, 90, 118),
    (6, 26, 50, 74, 98, 122),
    (6, 30, 54, 78, 102, 126),
    (6, 26, 52, 78, 104, 130),
    (6, 30, 56, 82, 108, 134),
    (6, 34, 60, 86, 112, 138),
    (6, 30, 58, 86, 114, 142),
    (6, 34, 62, 90, 118, 146),
    (6, 30, 54, 78, 102, 126, 150),
    (6, 24, 50, 76, 102, 128, 154),
    (6, 28, 54, 80, 106, 132, 158),
    (6, 32, 58, 84, 110, 136, 162),
    (6, 26, 54, 82, 110, 138, 166),
    (6, 30, 58, 86, 114, 142, 170),
)


def build_protected_mask(version: int) -> tuple[tuple[bool, ...], ...]:
    """Return a body-sized mask covering every standard functional module."""

    if not 1 <= version <= 40:
        raise QRGenerationError("QR version must be between 1 and 40.")
    size = 17 + 4 * version
    mask = [[False] * size for _ in range(size)]

    def mark_rect(left: int, top: int, width: int, height: int) -> None:
        for y in range(max(0, top), min(size, top + height)):
            for x in range(max(0, left), min(size, left + width)):
                mask[y][x] = True

    # Finder patterns plus their one-module separators.
    mark_rect(0, 0, 8, 8)
    mark_rect(size - 8, 0, 8, 8)
    mark_rect(0, size - 8, 8, 8)

    # Timing patterns; alignment patterns may supersede parts of these lines.
    mark_rect(8, 6, size - 16, 1)
    mark_rect(6, 8, 1, size - 16)

    # All alignment patterns except the three combinations occupied by finders.
    centers = ALIGNMENT_PATTERN_CENTERS[version]
    finder_centers = {(6, 6), (size - 7, 6), (6, size - 7)}
    for center_y in centers:
        for center_x in centers:
            if (center_x, center_y) not in finder_centers:
                mark_rect(center_x - 2, center_y - 2, 5, 5)

    # Two copies of format information around row / column 8.
    for i in range(15):
        if i < 6:
            vertical_y = i
        elif i < 8:
            vertical_y = i + 1
        else:
            vertical_y = size - 15 + i
        mask[vertical_y][8] = True

        if i < 8:
            horizontal_x = size - i - 1
        elif i == 8:
            horizontal_x = 7
        else:
            horizontal_x = 14 - i
        mask[8][horizontal_x] = True

    # Fixed dark module.
    mask[size - 8][8] = True

    # Version information appears in two 3 x 6 blocks from version 7 onward.
    if version >= 7:
        mark_rect(size - 11, 0, 3, 6)
        mark_rect(0, size - 11, 6, 3)

    return tuple(tuple(row) for row in mask)

