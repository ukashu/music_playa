import pytest
from PySide6.QtCore import QSize

from PySide6.QtGui import QColor

from music_playa_gui.theme import PINK
from music_playa_gui.widgets.backdrop import (
    GRID_GLOW_BOOST,
    GRID_HORIZONTAL_LINES,
    _fade,
    _passes,
    grid_pixmap,
)


@pytest.mark.parametrize("ratio", [1.0, 1.5, 2.0])
def test_size_and_ratio(ratio: float) -> None:
    pixmap = grid_pixmap(QSize(300, 90), ratio, 150, 200)
    assert (pixmap.width(), pixmap.height()) == (round(300 * ratio), round(90 * ratio))
    assert pixmap.devicePixelRatio() == ratio


def test_empty_size_gives_an_empty_transparent_pixmap() -> None:
    pixmap = grid_pixmap(QSize(0, 0), 1.0, 0, 100)
    assert pixmap.isNull() or pixmap.width() == 0


def _lit_columns(image, y: int) -> list[int]:
    return [x for x in range(image.width()) if image.pixelColor(x, y).alpha() > 0]


def test_lines_point_at_the_vanishing_point() -> None:
    # A close vanishing point: at the top the radial lines bunch up around it.
    image = grid_pixmap(QSize(600, 100), 1.0, 450, 20).toImage()
    top = [x for x in _lit_columns(image, 0)]
    assert top
    assert abs(sum(top) / len(top) - 450) < 30


def test_horizontal_lines_are_drawn() -> None:
    image = grid_pixmap(QSize(400, 100), 1.0, 200, 100).toImage()
    full_rows = [y for y in range(image.height()) if len(_lit_columns(image, y)) == image.width()]
    assert len(full_rows) >= GRID_HORIZONTAL_LINES


def test_horizon_below_one_is_treated_as_one() -> None:
    low = grid_pixmap(QSize(200, 50), 1.0, 100, -40).toImage()
    one = grid_pixmap(QSize(200, 50), 1.0, 100, 1).toImage()
    two = grid_pixmap(QSize(200, 50), 1.0, 100, 2).toImage()
    assert low == one
    assert one != two


def test_radial_lines_at_the_top_edge() -> None:
    # Horizon 100 above a 100 px tall grid: the lines are 64 px apart at the bottom
    # and half of that (32 px) at the top edge, around the vanishing x.
    image = grid_pixmap(QSize(640, 100), 1.0, 320, 100).toImage()
    for x in (320, 352, 288, 416):
        assert image.pixelColor(x, 0).alpha() > 0, x
    for x in (336, 304):
        assert image.pixelColor(x, 0).alpha() == 0, x


def test_horizontal_lines_are_evenly_spaced_in_depth() -> None:
    # With the horizon as far above the grid as it is tall, line n sits at
    # 200 / (1 + n / 6) - 100 px: about 71, 50, 33, 20 and 9.
    image = grid_pixmap(QSize(400, 100), 1.0, 200, 100).toImage()
    full = [y for y in range(image.height()) if len(_lit_columns(image, y)) == image.width()]
    groups: list[list[int]] = []
    for y in full:
        if groups and y == groups[-1][-1] + 1:
            groups[-1].append(y)
        else:
            groups.append([y])
    centres = [sum(group) / len(group) for group in groups]
    expected = [200 / (1 + step / 6) - 100 for step in range(GRID_HORIZONTAL_LINES, 0, -1)]
    assert len(centres) == GRID_HORIZONTAL_LINES
    assert centres == pytest.approx(expected, abs=1.0)


def test_lines_are_pink() -> None:
    image = grid_pixmap(QSize(400, 100), 1.0, 200, 100).toImage()
    colour = image.pixelColor(200, 50)
    assert colour.alpha() > 0
    assert colour.red() > colour.blue() > colour.green()


def test_fades_toward_the_bottom() -> None:
    image = grid_pixmap(QSize(400, 100), 1.0, 200, 50).toImage()
    top = max(image.pixelColor(x, 1).alpha() for x in range(400))
    bottom = max(image.pixelColor(x, 98).alpha() for x in range(400))
    assert top > bottom


def _lit_pixels(image) -> int:
    return sum(
        image.pixelColor(x, y).alpha() > 0 for x in range(image.width()) for y in range(image.height())
    )


def _glow_grid(boost: float):
    return grid_pixmap(QSize(400, 100), 1.0, 200, 100, boost).toImage()


def test_a_boost_of_one_is_the_normal_grid() -> None:
    assert _glow_grid(1.0) == grid_pixmap(QSize(400, 100), 1.0, 200, 100).toImage()


def test_a_boosted_grid_has_stronger_lines() -> None:
    normal, glowing = _glow_grid(1.0), _glow_grid(GRID_GLOW_BOOST)
    assert max(glowing.pixelColor(x, 1).alpha() for x in range(400)) > 2 * max(
        normal.pixelColor(x, 1).alpha() for x in range(400)
    )
    assert max(glowing.pixelColor(x, 98).alpha() for x in range(400)) > max(
        normal.pixelColor(x, 98).alpha() for x in range(400)
    )


def test_boosted_alpha_stops_at_full_opacity() -> None:
    glowing = grid_pixmap(QSize(400, 100), 1.0, 200, 100, 10.0).toImage()
    assert max(glowing.pixelColor(x, 1).alpha() for x in range(400)) <= 255
    assert max(glowing.pixelColor(x, 1).alpha() for x in range(400)) > 240


def test_a_boosted_grid_has_thicker_lines_and_a_halo() -> None:
    normal, glowing = _glow_grid(1.0), _glow_grid(GRID_GLOW_BOOST)
    assert _lit_pixels(glowing) > 2 * _lit_pixels(normal)
    # The halo is lit where the normal grid has nothing.
    assert any(
        glowing.pixelColor(x, y).alpha() > 0 and normal.pixelColor(x, y).alpha() == 0
        for x in range(400)
        for y in range(100)
    )


def test_the_halo_starts_as_soon_as_the_boost_is_above_one() -> None:
    assert _lit_pixels(_glow_grid(1.01)) > _lit_pixels(_glow_grid(1.0))


def test_a_normal_grid_is_one_thin_stroke() -> None:
    assert _passes(1.0) == [(1.0, 1.0)]


def test_a_glowing_grid_has_a_wide_faint_halo_under_thicker_lines() -> None:
    halo, lines = _passes(3.0)
    assert halo == pytest.approx((5.0, 0.75))
    assert lines == pytest.approx((1.6, 3.0))


def test_the_halo_is_drawn_first() -> None:
    assert _passes(2.0)[0][0] > _passes(2.0)[1][0]


def _stops(gradient) -> list[tuple[float, QColor]]:
    return [(position, colour) for position, colour in gradient.stops()]


def test_the_fade_goes_from_the_top_to_the_bottom_in_pink() -> None:
    gradient = _fade(80.0, 1.0)
    assert (gradient.start().x(), gradient.start().y()) == (0.0, 0.0)
    assert (gradient.finalStop().x(), gradient.finalStop().y()) == (0.0, 80.0)
    (top_at, top), (bottom_at, bottom) = _stops(gradient)
    assert (top_at, bottom_at) == (0.0, 1.0)
    assert top.rgb() == bottom.rgb() == QColor(PINK).rgb()
    assert (top.alpha(), bottom.alpha()) == (100, 40)


def test_the_fade_scales_the_alpha_and_stops_at_full_opacity() -> None:
    (_, top), (_, bottom) = _stops(_fade(80.0, 0.5))
    assert (top.alpha(), bottom.alpha()) == (50, 20)
    (_, top), (_, bottom) = _stops(_fade(80.0, 10.0))
    assert (top.alpha(), bottom.alpha()) == (255, 255)
