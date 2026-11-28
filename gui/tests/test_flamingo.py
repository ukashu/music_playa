import pytest
from PySide6.QtCore import QSize

from music_playa_gui.widgets import flamingo
from music_playa_gui.widgets.flamingo import BIRD_OPACITY, RIGHT_MARGIN, flamingo_pixmap, halo_padding


def _opaque_bounds(image) -> tuple[int, int, int, int]:
    xs, ys = [], []
    for y in range(0, image.height()):
        for x in range(0, image.width()):
            if image.pixelColor(x, y).alpha() > 20:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


@pytest.mark.parametrize("ratio", [1.0, 1.5, 2.0])
def test_size_and_ratio(ratio: float) -> None:
    pixmap = flamingo_pixmap(QSize(100, 120), 10, 100, ratio)
    assert (pixmap.width(), pixmap.height()) == (round(100 * ratio), round(120 * ratio))
    assert pixmap.devicePixelRatio() == ratio


def test_position_is_fixed_to_the_top_right() -> None:
    top, height = 30, 150
    image = flamingo_pixmap(QSize(340, 300), top, height).toImage()
    left, upper, right, lower = _opaque_bounds(image)
    assert right <= 340 - RIGHT_MARGIN
    assert right >= 340 - RIGHT_MARGIN - 10
    assert top <= upper <= top + 10
    assert lower <= top + height


def test_short_pixmap_cuts_the_legs() -> None:
    # The bird is taller than the space below its top, so it runs to the bottom edge.
    image = flamingo_pixmap(QSize(340, 100), 30, 300).toImage()
    assert _opaque_bounds(image)[3] > 90


def test_empty_inputs_give_a_transparent_pixmap() -> None:
    for pixmap in (flamingo_pixmap(QSize(50, 50), 0, 0), flamingo_pixmap(QSize(0, 0), 0, 100)):
        image = pixmap.toImage()
        assert all(
            image.pixelColor(x, y).alpha() == 0 for x in range(image.width()) for y in range(image.height())
        )


def test_tinted_bird_is_cached_by_size() -> None:
    first = flamingo._bird_image(40, 60)
    assert flamingo._bird_image(40, 60) is first
    assert flamingo._bird_image(41, 60) is not first


def _max_alpha(image) -> int:
    return max(image.pixelColor(x, y).alpha() for x in range(image.width()) for y in range(image.height()))


def _lit_pixels(image) -> int:
    return sum(
        image.pixelColor(x, y).alpha() > 0 for x in range(image.width()) for y in range(image.height())
    )


def test_the_bird_is_drawn_dimmed_and_the_glowing_one_at_full_opacity() -> None:
    normal = flamingo_pixmap(QSize(340, 300), 30, 200).toImage()
    glowing = flamingo_pixmap(QSize(340, 300), 30, 200, glow=True).toImage()
    assert _max_alpha(normal) <= round(255 * BIRD_OPACITY) + 2
    assert _max_alpha(glowing) > 240


def test_the_glowing_bird_has_a_halo_that_is_not_cut_off() -> None:
    normal = flamingo_pixmap(QSize(340, 300), 30, 200).toImage()
    glowing = flamingo_pixmap(QSize(340, 300), 30, 200, glow=True).toImage()
    assert _lit_pixels(glowing) > _lit_pixels(normal)
    left, upper, right, lower = _opaque_bounds(normal)
    # The halo is lit beyond the bird on every side, as far as the picture reaches.
    bounds = _opaque_bounds(glowing)
    assert bounds[1] < upper
    assert bounds[2] >= right


def test_the_halo_is_made_larger_than_the_bird_and_cached_by_size() -> None:
    pad = halo_padding(40, 60)
    assert pad == 60 // 20
    halo = flamingo._halo_image(40, 60)
    assert (halo.width(), halo.height()) == (40 + 2 * pad, 60 + 2 * pad)
    assert flamingo._halo_image(40, 60) is halo
    assert flamingo._halo_image(41, 60) is not halo


def test_the_halo_padding_follows_the_longer_side() -> None:
    assert halo_padding(400, 100) == 20
    assert halo_padding(100, 400) == 20
