"""
Preset marbling patterns.

Each preset function takes an engine and a palette, clears the engine,
and populates it with a pre-designed sequence of operations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Dict, List, Tuple

import numpy as np

if TYPE_CHECKING:
    from .engine import MarblingEngine
    from .palettes import Palette

logger = logging.getLogger(__name__)


def concentric(engine: "MarblingEngine", palette: "Palette", **kw) -> None:
    """Classic suminagashi — concentric rings at the centre."""
    engine.clear()
    cx, cy = engine.width / 2, engine.height / 2
    count = kw.get("count", 25)
    engine.add_concentric_rings(cx, cy, palette.color_list, count=count,
                                ring_radius=12, jitter=2.0)
    logger.info("Preset 'concentric' applied (%d drops)", count)


def scattered(engine: "MarblingEngine", palette: "Palette", **kw) -> None:
    """Multiple ring clusters scattered across the canvas."""
    engine.clear()
    w, h = engine.width, engine.height
    rng = np.random.default_rng()
    n_centers = kw.get("n_centers", 5)
    drops_per = kw.get("drops_per", 10)

    for _ in range(n_centers):
        cx = rng.uniform(w * 0.15, w * 0.85)
        cy = rng.uniform(h * 0.15, h * 0.85)
        engine.add_concentric_rings(cx, cy, palette.color_list,
                                    count=drops_per, ring_radius=10, jitter=3.0)
    logger.info("Preset 'scattered' applied (%d centres)", n_centers)


def blown(engine: "MarblingEngine", palette: "Palette", **kw) -> None:
    """Concentric rings with gentle radial blow distortions."""
    engine.clear()
    cx, cy = engine.width / 2, engine.height / 2
    rng = np.random.default_rng()

    engine.add_concentric_rings(cx, cy, palette.color_list, count=20,
                                ring_radius=14, jitter=2.0)

    n_blows = kw.get("n_blows", 6)
    for i in range(n_blows):
        angle = (i / n_blows) * np.pi * 2 + rng.uniform(-0.3, 0.3)
        bx = cx + np.cos(angle) * 60
        by = cy + np.sin(angle) * 60
        engine.add_blow(bx, by, 25 + rng.uniform(0, 15), 80)

    logger.info("Preset 'blown' applied")


def combed(engine: "MarblingEngine", palette: "Palette", **kw) -> None:
    """Scattered drops with vertical then horizontal comb strokes."""
    engine.clear()
    w, h = engine.width, engine.height
    cx, cy = w / 2, h / 2
    rng = np.random.default_rng()

    # Drop clusters in a row
    n_clusters = kw.get("n_clusters", 4)
    for j in range(n_clusters):
        sx = cx - (n_clusters - 1) * 50 + j * 100
        engine.add_concentric_rings(sx, cy, palette.color_list,
                                    count=8, ring_radius=10, jitter=3.0)

    # Vertical comb
    spacing = kw.get("comb_spacing", 40)
    for x in range(int(w * 0.08), int(w * 0.92), spacing):
        engine.add_stroke(x, cy, np.pi / 2, 50, 30)

    # Alternating horizontal
    for y in range(int(h * 0.12), int(h * 0.88), 60):
        direction = 0 if (y // 60) % 2 == 0 else np.pi
        engine.add_stroke(cx, y, direction, 40, 25)

    logger.info("Preset 'combed' applied")


def vortex_rings(engine: "MarblingEngine", palette: "Palette", **kw) -> None:
    """Concentric rings with vortex swirl distortion."""
    engine.clear()
    cx, cy = engine.width / 2, engine.height / 2
    rng = np.random.default_rng()

    engine.add_concentric_rings(cx, cy, palette.color_list, count=22,
                                ring_radius=12, jitter=2.0)

    n_vortices = kw.get("n_vortices", 4)
    for i in range(n_vortices):
        angle = (i / n_vortices) * np.pi * 2
        vx = cx + np.cos(angle) * 70
        vy = cy + np.sin(angle) * 70
        sign = 1 if i % 2 == 0 else -1
        engine.add_vortex(vx, vy, sign * 0.6, 90)

    logger.info("Preset 'vortex_rings' applied")


def stone(engine: "MarblingEngine", palette: "Palette", **kw) -> None:
    """Many small scattered drops — stone-like texture."""
    engine.clear()
    w, h = engine.width, engine.height
    rng = np.random.default_rng()
    n_drops = kw.get("n_drops", 120)

    colors = palette.color_list
    for i in range(n_drops):
        cx = rng.uniform(0, w)
        cy = rng.uniform(0, h)
        r = rng.uniform(4, 16)
        c = colors[i % len(colors)]
        engine.add_drop(cx, cy, r, c)

    logger.info("Preset 'stone' applied (%d drops)", n_drops)


# ── Registry ──────────────────────────────────────────────────────────────

PRESETS: Dict[str, Callable] = {
    "concentric": concentric,
    "scattered": scattered,
    "blown": blown,
    "combed": combed,
    "vortex_rings": vortex_rings,
    "stone": stone,
}


def apply_preset(
    name: str,
    engine: "MarblingEngine",
    palette: "Palette",
    **kw,
) -> None:
    """Apply a named preset, raising KeyError if unknown."""
    if name not in PRESETS:
        available = ", ".join(sorted(PRESETS.keys()))
        raise KeyError(f"Unknown preset '{name}'. Available: {available}")
    PRESETS[name](engine, palette, **kw)


def list_presets() -> List[str]:
    """Return sorted list of available preset names."""
    return sorted(PRESETS.keys())
