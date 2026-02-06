"""
Marbling Engine — core physics and rendering.

Implements Jaffer's area-preserving drop transform and additional
stroke / blow / vortex operations, all rendered via inverse raster
mapping with full numpy vectorisation for performance.

Typical usage:
    engine = MarblingEngine(800, 600)
    engine.add_drop(400, 300, radius=30, color=(0, 0, 0))
    image = engine.render()          # numpy array (H, W, 3) uint8
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Operation types
# ---------------------------------------------------------------------------

class OpType(Enum):
    """Enumeration of supported marbling operations."""
    DROP = auto()
    STROKE = auto()
    BLOW = auto()
    VORTEX = auto()


@dataclass
class Operation:
    """A single marbling operation (drop, stroke, blow, or vortex).

    Attributes:
        op_type:   The kind of operation.
        cx, cy:    Centre / reference point.
        radius:    Effective radius (meaning varies by op_type).
        color:     RGB tuple for DROP ops; ignored otherwise.
        angle:     Direction in radians (STROKE).
        strength:  Magnitude of displacement (STROKE / BLOW / VORTEX).
        width:     Gaussian falloff width (STROKE).
    """
    op_type: OpType
    cx: float = 0.0
    cy: float = 0.0
    radius: float = 10.0
    color: Tuple[int, int, int] = (0, 0, 0)
    angle: float = 0.0
    strength: float = 0.0
    width: float = 30.0


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MarblingEngine:
    """Numpy-vectorised mathematical marbling engine.

    Parameters:
        width:  Canvas width in pixels.
        height: Canvas height in pixels.
        water_color: Background RGB tuple (default: warm off-white).

    All public ``add_*`` methods append to an internal operation list.
    Call :meth:`render` to produce the final image.
    """

    # Minimum distance to avoid division-by-zero in transforms
    _EPSILON = 0.5

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        water_color: Tuple[int, int, int] = (245, 242, 235),
    ) -> None:
        if width < 1 or height < 1:
            raise ValueError(f"Canvas dimensions must be positive, got {width}×{height}")
        self.width = width
        self.height = height
        self.water_color = np.array(water_color, dtype=np.uint8)
        self.operations: List[Operation] = []
        logger.info("MarblingEngine created (%d×%d)", width, height)

    # ── mutators ──────────────────────────────────────────────────────────

    def set_water_color(self, color: Tuple[int, int, int]) -> None:
        """Set the background water colour."""
        self.water_color = np.array(color, dtype=np.uint8)

    def add_drop(
        self, cx: float, cy: float, radius: float, color: Tuple[int, int, int]
    ) -> None:
        """Place an ink drop — area-preserving radial push.

        Args:
            cx, cy:  Centre of the drop.
            radius:  Radius of the new ink disc.
            color:   RGB colour of the ink.
        """
        if radius <= 0:
            logger.warning("Ignoring drop with non-positive radius %.2f", radius)
            return
        self.operations.append(
            Operation(OpType.DROP, cx=cx, cy=cy, radius=radius, color=color)
        )

    def add_stroke(
        self,
        cx: float,
        cy: float,
        angle: float,
        strength: float,
        width: float = 30.0,
    ) -> None:
        """Apply a tine / comb stroke.

        Displaces points in the direction *angle* (radians) with
        Gaussian falloff perpendicular to the stroke line.

        Args:
            cx, cy:    Reference point the stroke passes through.
            angle:     Direction of displacement (radians).
            strength:  Maximum displacement in pixels.
            width:     σ of the perpendicular Gaussian falloff.
        """
        if abs(strength) < 0.01:
            return
        self.operations.append(
            Operation(OpType.STROKE, cx=cx, cy=cy, angle=angle,
                      strength=strength, width=max(width, 1.0))
        )

    def add_blow(
        self, cx: float, cy: float, strength: float, radius: float
    ) -> None:
        """Radial outward blow (like breathing on the surface).

        Args:
            cx, cy:    Centre of the blow.
            strength:  Maximum displacement.
            radius:    σ of the Gaussian falloff.
        """
        if abs(strength) < 0.01 or radius <= 0:
            return
        self.operations.append(
            Operation(OpType.BLOW, cx=cx, cy=cy, strength=strength,
                      radius=max(radius, 1.0))
        )

    def add_vortex(
        self, cx: float, cy: float, strength: float, radius: float
    ) -> None:
        """Rotational vortex distortion.

        Args:
            cx, cy:    Centre of the vortex.
            strength:  Peak rotation in radians.
            radius:    σ of the Gaussian falloff.
        """
        if abs(strength) < 0.01 or radius <= 0:
            return
        self.operations.append(
            Operation(OpType.VORTEX, cx=cx, cy=cy, strength=strength,
                      radius=max(radius, 1.0))
        )

    def add_concentric_rings(
        self,
        cx: float,
        cy: float,
        colors: List[Tuple[int, int, int]],
        count: int = 10,
        ring_radius: float = 12.0,
        jitter: float = 2.0,
    ) -> None:
        """Convenience: place *count* concentric drops (classic suminagashi).

        Args:
            cx, cy:      Centre of the ring cluster.
            colors:      List of RGB colours to cycle through.
            count:       Number of drops to place.
            ring_radius: Base radius for each drop.
            jitter:      Random positional jitter in pixels.
        """
        if not colors:
            raise ValueError("Need at least one colour for concentric rings")
        rng = np.random.default_rng()
        for i in range(count):
            c = colors[i % len(colors)]
            r = ring_radius + rng.uniform(-2, 2)
            dx = rng.uniform(-jitter, jitter)
            dy = rng.uniform(-jitter, jitter)
            self.add_drop(cx + dx, cy + dy, r, c)

    def undo(self) -> Optional[Operation]:
        """Remove and return the last operation, or None if empty."""
        if self.operations:
            return self.operations.pop()
        return None

    def clear(self) -> None:
        """Remove all operations."""
        self.operations.clear()
        logger.info("Canvas cleared")

    @property
    def op_count(self) -> int:
        return len(self.operations)

    # ── rendering ─────────────────────────────────────────────────────────

    def render(self) -> np.ndarray:
        """Render the full canvas and return an (H, W, 3) uint8 array.

        Uses inverse mapping: for every pixel we trace backward through
        the operation stack to determine its colour.
        """
        h, w = self.height, self.width

        # Start with a grid of all pixel coordinates
        yy, xx = np.mgrid[0:h, 0:w]
        qx = xx.astype(np.float64).ravel()
        qy = yy.astype(np.float64).ravel()
        n = qx.size

        # Colour buffer — start as water; overwrite on DROP hits
        img = np.tile(self.water_color, (n, 1)).astype(np.uint8)  # (n, 3)

        # Track which pixels have been "claimed" by a drop
        # (earliest hit during backward walk wins)
        claimed = np.zeros(n, dtype=bool)

        eps = self._EPSILON

        for op in reversed(self.operations):
            # Only unclaimed pixels need processing
            active = ~claimed

            if op.op_type == OpType.DROP:
                self._apply_drop_inverse(qx, qy, op, active, claimed, img)

            elif op.op_type == OpType.STROKE:
                self._apply_stroke_inverse(qx, qy, op, active)

            elif op.op_type == OpType.BLOW:
                self._apply_blow_inverse(qx, qy, op, active)

            elif op.op_type == OpType.VORTEX:
                self._apply_vortex_inverse(qx, qy, op, active)

        return img.reshape(h, w, 3)

    def render_region(self, y_start: int, y_end: int) -> np.ndarray:
        """Render a horizontal band [y_start, y_end) → (band_h, W, 3).

        Useful for progressive / threaded rendering.
        """
        y_start = max(0, y_start)
        y_end = min(self.height, y_end)
        band_h = y_end - y_start
        if band_h <= 0:
            return np.empty((0, self.width, 3), dtype=np.uint8)

        yy, xx = np.mgrid[y_start:y_end, 0:self.width]
        qx = xx.astype(np.float64).ravel()
        qy = yy.astype(np.float64).ravel()
        n = qx.size

        img = np.tile(self.water_color, (n, 1)).astype(np.uint8)
        claimed = np.zeros(n, dtype=bool)

        for op in reversed(self.operations):
            active = ~claimed
            if op.op_type == OpType.DROP:
                self._apply_drop_inverse(qx, qy, op, active, claimed, img)
            elif op.op_type == OpType.STROKE:
                self._apply_stroke_inverse(qx, qy, op, active)
            elif op.op_type == OpType.BLOW:
                self._apply_blow_inverse(qx, qy, op, active)
            elif op.op_type == OpType.VORTEX:
                self._apply_vortex_inverse(qx, qy, op, active)

        return img.reshape(band_h, self.width, 3)

    # ── vectorised inverse transforms ─────────────────────────────────────

    def _apply_drop_inverse(
        self,
        qx: np.ndarray,
        qy: np.ndarray,
        op: Operation,
        active: np.ndarray,
        claimed: np.ndarray,
        img: np.ndarray,
    ) -> None:
        """Inverse drop: pixels inside → claim colour; outside → warp back."""
        idx = np.where(active)[0]
        if idx.size == 0:
            return

        dx = qx[idx] - op.cx
        dy = qy[idx] - op.cy
        dist2 = dx * dx + dy * dy
        r2 = op.radius * op.radius

        inside = dist2 < r2

        # Claim inside pixels
        claim_idx = idx[inside]
        if claim_idx.size > 0:
            img[claim_idx, 0] = op.color[0]
            img[claim_idx, 1] = op.color[1]
            img[claim_idx, 2] = op.color[2]
            claimed[claim_idx] = True

        # Inverse-warp outside pixels
        outside = ~inside
        out_idx = idx[outside]
        if out_idx.size > 0:
            d2 = dist2[outside]
            # Clamp to avoid sqrt of negative due to float precision
            ratio = np.clip(1.0 - r2 / d2, 0.0, None)
            factor = np.sqrt(ratio)
            qx[out_idx] = op.cx + dx[outside] * factor
            qy[out_idx] = op.cy + dy[outside] * factor

    def _apply_stroke_inverse(
        self,
        qx: np.ndarray,
        qy: np.ndarray,
        op: Operation,
        active: np.ndarray,
    ) -> None:
        """Inverse tine stroke with Gaussian perpendicular falloff."""
        idx = np.where(active)[0]
        if idx.size == 0:
            return

        cos_a = np.cos(op.angle)
        sin_a = np.sin(op.angle)

        # Perpendicular distance from the stroke line
        perp = -(qx[idx] - op.cx) * sin_a + (qy[idx] - op.cy) * cos_a
        disp = op.strength * np.exp(-perp * perp / (2.0 * op.width * op.width))

        qx[idx] -= disp * cos_a
        qy[idx] -= disp * sin_a

    def _apply_blow_inverse(
        self,
        qx: np.ndarray,
        qy: np.ndarray,
        op: Operation,
        active: np.ndarray,
    ) -> None:
        """Inverse radial blow with Gaussian falloff."""
        idx = np.where(active)[0]
        if idx.size == 0:
            return

        dx = qx[idx] - op.cx
        dy = qy[idx] - op.cy
        dist = np.sqrt(dx * dx + dy * dy)

        mask = dist > self._EPSILON
        m_idx = idx[mask]
        if m_idx.size == 0:
            return

        d = dist[mask]
        dx_m = dx[mask]
        dy_m = dy[mask]
        falloff = np.exp(-d * d / (2.0 * op.radius * op.radius))
        disp = op.strength * falloff

        nx = dx_m / d
        ny = dy_m / d
        qx[m_idx] -= disp * nx
        qy[m_idx] -= disp * ny

    def _apply_vortex_inverse(
        self,
        qx: np.ndarray,
        qy: np.ndarray,
        op: Operation,
        active: np.ndarray,
    ) -> None:
        """Inverse vortex rotation with Gaussian falloff."""
        idx = np.where(active)[0]
        if idx.size == 0:
            return

        dx = qx[idx] - op.cx
        dy = qy[idx] - op.cy
        dist = np.sqrt(dx * dx + dy * dy)

        mask = dist > self._EPSILON
        m_idx = idx[mask]
        if m_idx.size == 0:
            return

        d = dist[mask]
        dx_m = dx[mask]
        dy_m = dy[mask]
        falloff = np.exp(-d * d / (2.0 * op.radius * op.radius))
        angle = -op.strength * falloff  # inverse rotation

        cos_r = np.cos(angle)
        sin_r = np.sin(angle)
        rx = dx_m * cos_r - dy_m * sin_r
        ry = dx_m * sin_r + dy_m * cos_r

        qx[m_idx] = op.cx + rx
        qy[m_idx] = op.cy + ry
