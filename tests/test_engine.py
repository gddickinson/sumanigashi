"""
tests/test_engine.py
====================
Unit tests for the suminagashi marbling engine.
"""

import math
import numpy as np

from suminagashi.engine import MarblingEngine, Operation, OpType


def test_engine_creation():
    """MarblingEngine can be created with default or custom size."""
    eng = MarblingEngine(200, 150)
    assert eng.width == 200
    assert eng.height == 150
    assert eng.op_count == 0


def test_engine_invalid_dimensions():
    """Negative or zero dimensions raise ValueError."""
    try:
        MarblingEngine(0, 100)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_add_drop():
    """add_drop() records an operation."""
    eng = MarblingEngine(100, 100)
    eng.add_drop(50, 50, 10, (255, 0, 0))
    assert eng.op_count == 1


def test_add_drop_zero_radius_ignored():
    """Drops with radius <= 0 are silently ignored."""
    eng = MarblingEngine(100, 100)
    eng.add_drop(50, 50, 0, (0, 0, 0))
    assert eng.op_count == 0


def test_add_stroke():
    """add_stroke() records an operation."""
    eng = MarblingEngine(100, 100)
    eng.add_stroke(50, 50, angle=0.0, strength=20.0, width=15.0)
    assert eng.op_count == 1


def test_add_blow():
    """add_blow() records an operation."""
    eng = MarblingEngine(100, 100)
    eng.add_blow(50, 50, strength=10.0, radius=20.0)
    assert eng.op_count == 1


def test_add_vortex():
    """add_vortex() records an operation."""
    eng = MarblingEngine(100, 100)
    eng.add_vortex(50, 50, strength=0.5, radius=30.0)
    assert eng.op_count == 1


def test_undo():
    """undo() removes and returns the last operation."""
    eng = MarblingEngine(100, 100)
    eng.add_drop(50, 50, 10, (255, 0, 0))
    eng.add_drop(60, 60, 10, (0, 255, 0))
    assert eng.op_count == 2
    op = eng.undo()
    assert op is not None
    assert eng.op_count == 1
    # Undo on empty returns None
    eng.undo()
    assert eng.undo() is None


def test_clear():
    """clear() removes all operations."""
    eng = MarblingEngine(100, 100)
    eng.add_drop(50, 50, 10, (0, 0, 0))
    eng.add_stroke(50, 50, 0, 10)
    eng.clear()
    assert eng.op_count == 0


def test_render_returns_correct_shape():
    """render() returns an (H, W, 3) uint8 array."""
    eng = MarblingEngine(80, 60)
    img = eng.render()
    assert img.shape == (60, 80, 3)
    assert img.dtype == np.uint8


def test_render_empty_is_water_color():
    """An empty canvas renders as the water colour everywhere."""
    color = (200, 180, 160)
    eng = MarblingEngine(50, 50, water_color=color)
    img = eng.render()
    assert np.all(img[0, 0] == np.array(color, dtype=np.uint8))
    assert np.all(img[25, 25] == np.array(color, dtype=np.uint8))


def test_render_with_drop():
    """A drop placed at centre colours the centre pixel."""
    eng = MarblingEngine(100, 100, water_color=(255, 255, 255))
    eng.add_drop(50, 50, 20, (255, 0, 0))
    img = eng.render()
    # Centre pixel should be the drop colour
    assert img[50, 50, 0] == 255
    assert img[50, 50, 1] == 0
    assert img[50, 50, 2] == 0


def test_drop_preserves_area_approximately():
    """After a drop, the approximate area of ink pixels matches pi*r^2."""
    eng = MarblingEngine(200, 200, water_color=(255, 255, 255))
    radius = 30
    eng.add_drop(100, 100, radius, (0, 0, 0))
    img = eng.render()
    # Count black-ish pixels
    ink_pixels = np.sum(img[:, :, 0] < 128)
    expected_area = math.pi * radius * radius
    # Allow 10% tolerance
    assert abs(ink_pixels - expected_area) / expected_area < 0.10


def test_render_region():
    """render_region() returns a horizontal band of the correct height."""
    eng = MarblingEngine(100, 100)
    eng.add_drop(50, 50, 15, (0, 0, 0))
    band = eng.render_region(20, 40)
    assert band.shape == (20, 100, 3)


def test_concentric_rings():
    """add_concentric_rings() adds multiple drops."""
    eng = MarblingEngine(100, 100)
    eng.add_concentric_rings(50, 50, colors=[(0, 0, 0), (255, 0, 0)], count=6)
    assert eng.op_count == 6


if __name__ == "__main__":
    test_engine_creation()
    test_engine_invalid_dimensions()
    test_add_drop()
    test_add_drop_zero_radius_ignored()
    test_add_stroke()
    test_add_blow()
    test_add_vortex()
    test_undo()
    test_clear()
    test_render_returns_correct_shape()
    test_render_empty_is_water_color()
    test_render_with_drop()
    test_drop_preserves_area_approximately()
    test_render_region()
    test_concentric_rings()
    print("All suminagashi engine tests passed!")
