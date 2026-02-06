"""
Colour palettes for suminagashi marbling.

Each palette provides a water (background) colour and a list of ink
colours that cycle when placing successive drops.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Palette:
    """An immutable colour palette."""
    name: str
    water: Tuple[int, int, int]
    colors: Tuple[Tuple[int, int, int], ...]

    @property
    def color_list(self) -> List[Tuple[int, int, int]]:
        return list(self.colors)


# ── Built-in palettes ────────────────────────────────────────────────────

PALETTES: Dict[str, Palette] = {
    "traditional": Palette(
        name="Traditional",
        water=(245, 242, 235),
        colors=(
            (15, 15, 15),
            (50, 48, 42),
            (95, 90, 82),
        ),
    ),
    "sumi_ink": Palette(
        name="Sumi Ink",
        water=(248, 246, 240),
        colors=(
            (10, 10, 10),
            (60, 58, 55),
            (30, 28, 25),
            (80, 76, 70),
        ),
    ),
    "indigo": Palette(
        name="Indigo & Ink",
        water=(240, 238, 232),
        colors=(
            (25, 35, 80),
            (50, 60, 120),
            (10, 10, 30),
            (70, 85, 150),
        ),
    ),
    "autumn": Palette(
        name="Autumn Leaves",
        water=(248, 244, 236),
        colors=(
            (160, 50, 20),
            (180, 100, 20),
            (80, 30, 15),
            (200, 140, 40),
        ),
    ),
    "ocean": Palette(
        name="Ocean",
        water=(235, 242, 245),
        colors=(
            (15, 60, 90),
            (30, 100, 130),
            (5, 30, 50),
            (50, 140, 170),
        ),
    ),
    "sakura": Palette(
        name="Sakura",
        water=(250, 245, 245),
        colors=(
            (180, 80, 100),
            (200, 120, 140),
            (120, 40, 60),
            (220, 160, 175),
        ),
    ),
    "forest": Palette(
        name="Forest",
        water=(242, 245, 238),
        colors=(
            (30, 60, 25),
            (55, 90, 40),
            (20, 35, 15),
            (80, 120, 60),
        ),
    ),
    "twilight": Palette(
        name="Twilight",
        water=(240, 235, 245),
        colors=(
            (60, 20, 80),
            (100, 40, 120),
            (30, 10, 50),
            (140, 60, 160),
            (80, 30, 100),
        ),
    ),
    "earth": Palette(
        name="Earth Tones",
        water=(245, 240, 232),
        colors=(
            (100, 70, 40),
            (140, 100, 60),
            (60, 40, 25),
            (170, 130, 80),
        ),
    ),
    "fire": Palette(
        name="Fire",
        water=(250, 245, 238),
        colors=(
            (180, 30, 10),
            (220, 100, 15),
            (120, 15, 5),
            (240, 160, 30),
            (90, 10, 5),
        ),
    ),
}

DEFAULT_PALETTE = "traditional"


def get_palette(name: str) -> Palette:
    """Return a palette by key, raising KeyError with helpful message."""
    if name not in PALETTES:
        available = ", ".join(sorted(PALETTES.keys()))
        raise KeyError(
            f"Unknown palette '{name}'. Available: {available}"
        )
    return PALETTES[name]


def list_palettes() -> List[str]:
    """Return sorted list of available palette keys."""
    return sorted(PALETTES.keys())
