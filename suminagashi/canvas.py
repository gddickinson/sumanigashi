"""
Canvas widget — displays the marbling and handles mouse interaction.

Rendering runs in a background QThread so the UI stays responsive.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

import numpy as np
from PyQt5.QtCore import (
    QPoint, QPointF, QThread, Qt, pyqtSignal, pyqtSlot, QElapsedTimer,
)
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QCursor
from PyQt5.QtWidgets import QWidget

from .engine import MarblingEngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background render thread
# ---------------------------------------------------------------------------

class RenderThread(QThread):
    """Runs engine.render() off the main thread and emits the result."""

    finished = pyqtSignal(np.ndarray)   # emits (H, W, 3) uint8

    def __init__(self, engine: MarblingEngine, parent=None):
        super().__init__(parent)
        self.engine = engine

    def run(self):
        try:
            t0 = time.perf_counter()
            img = self.engine.render()
            dt = time.perf_counter() - t0
            logger.debug("Render completed in %.3f s (%d ops)",
                         dt, self.engine.op_count)
            self.finished.emit(img)
        except Exception as e:
            logger.error("Render failed: %s", e, exc_info=True)


# ---------------------------------------------------------------------------
# Canvas widget
# ---------------------------------------------------------------------------

class MarblingCanvas(QWidget):
    """Interactive marbling canvas.

    Signals:
        op_count_changed(int): emitted whenever the operation count changes.
        render_time_changed(float): emitted with the last render duration.
    """

    op_count_changed = pyqtSignal(int)
    render_time_changed = pyqtSignal(float)

    # Tool names (matches control panel)
    TOOL_DROP = "drop"
    TOOL_RING = "ring"
    TOOL_BLOW = "blow"
    TOOL_VORTEX = "vortex"
    TOOL_COMB = "comb"

    def __init__(
        self,
        engine: MarblingEngine,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self._pixmap: Optional[QPixmap] = None
        self._render_thread: Optional[RenderThread] = None
        self._rendering = False

        # Tool state
        self.tool = self.TOOL_DROP
        self.drop_radius = 30.0
        self.ring_count = 10
        self.ring_spacing = 12.0
        self.blow_strength = 40.0
        self.comb_strength = 60.0
        self.ink_colors: list = [(0, 0, 0)]
        self._color_index = 0

        # Drag state
        self._dragging = False
        self._last_pos: Optional[QPointF] = None
        self._mouse_pos: Optional[QPointF] = None

        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        self._render_start = 0.0

        # Initial render
        self.request_render()

    # ── colour cycling ────────────────────────────────────────────────────

    def set_ink_colors(self, colors: list) -> None:
        self.ink_colors = colors if colors else [(0, 0, 0)]
        self._color_index = 0

    def _next_color(self) -> Tuple[int, int, int]:
        c = self.ink_colors[self._color_index % len(self.ink_colors)]
        self._color_index += 1
        return c

    def reset_color_index(self) -> None:
        self._color_index = 0

    # ── coordinate mapping ────────────────────────────────────────────────

    def _canvas_pos(self, widget_pos: QPointF) -> QPointF:
        """Map widget coordinates to engine (pixel) coordinates."""
        w = self.width()
        h = self.height()
        # Maintain aspect ratio
        ew, eh = self.engine.width, self.engine.height
        scale_x = ew / w
        scale_y = eh / h
        return QPointF(widget_pos.x() * scale_x, widget_pos.y() * scale_y)

    # ── mouse events ──────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = self._canvas_pos(QPointF(event.pos()))

        if self.tool == self.TOOL_DROP:
            color = self._next_color()
            self.engine.add_drop(pos.x(), pos.y(), self.drop_radius, color)
            self._emit_count()
            self.request_render()

        elif self.tool == self.TOOL_RING:
            colors = self.ink_colors
            rng = np.random.default_rng()
            for i in range(self.ring_count):
                c = colors[i % len(colors)]
                r = self.ring_spacing + rng.uniform(-2, 2)
                dx = rng.uniform(-2, 2)
                dy = rng.uniform(-2, 2)
                self.engine.add_drop(pos.x() + dx, pos.y() + dy, r, c)
            self._emit_count()
            self.request_render()

        elif self.tool in (self.TOOL_BLOW, self.TOOL_VORTEX, self.TOOL_COMB):
            self._dragging = True
            self._last_pos = pos

    def mouseMoveEvent(self, event):
        self._mouse_pos = QPointF(event.pos())
        self.update()  # redraw cursor preview

        if not self._dragging or self._last_pos is None:
            return

        pos = self._canvas_pos(QPointF(event.pos()))
        dx = pos.x() - self._last_pos.x()
        dy = pos.y() - self._last_pos.y()
        dist = (dx * dx + dy * dy) ** 0.5

        if dist < 3:
            return

        if self.tool == self.TOOL_BLOW:
            self.engine.add_blow(
                self._last_pos.x(), self._last_pos.y(),
                self.blow_strength * 0.7, self.blow_strength * 2,
            )

        elif self.tool == self.TOOL_VORTEX:
            cx = self.engine.width / 2
            cy = self.engine.height / 2
            cross = dx * (pos.y() - cy) - dy * (pos.x() - cx)
            sign = 1.0 if cross > 0 else -1.0
            self.engine.add_vortex(
                pos.x(), pos.y(),
                sign * 0.3 * (self.blow_strength / 40.0),
                self.blow_strength * 2.5,
            )

        elif self.tool == self.TOOL_COMB:
            import math
            angle = math.atan2(dy, dx)
            self.engine.add_stroke(
                self._last_pos.x(), self._last_pos.y(),
                angle, self.comb_strength * 0.8, self.comb_strength * 0.6,
            )

        self._last_pos = pos
        self._emit_count()
        self.request_render()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._last_pos = None

    # ── rendering ─────────────────────────────────────────────────────────

    def request_render(self) -> None:
        """Kick off a background render (debounces if already running)."""
        if self._rendering:
            # Will re-render after current one finishes
            return
        self._rendering = True
        self._render_start = time.perf_counter()
        thread = RenderThread(self.engine, parent=self)
        thread.finished.connect(self._on_render_done)
        thread.finished.connect(thread.deleteLater)
        self._render_thread = thread
        thread.start()

    @pyqtSlot(np.ndarray)
    def _on_render_done(self, img: np.ndarray) -> None:
        """Receive rendered image and display it."""
        self._rendering = False
        dt = time.perf_counter() - self._render_start
        self.render_time_changed.emit(dt)

        h, w, _ = img.shape
        # Convert numpy array to QImage (RGB888)
        bytes_per_line = 3 * w
        qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self._pixmap = QPixmap.fromImage(qimg)
        self.update()

    # ── painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if self._pixmap:
            painter.drawPixmap(self.rect(), self._pixmap)
        else:
            wc = self.engine.water_color
            painter.fillRect(self.rect(), QColor(wc[0], wc[1], wc[2]))

        # Cursor preview
        if self._mouse_pos and not self._dragging:
            r = self.drop_radius * self.width() / self.engine.width
            pen = QPen(QColor(100, 90, 80, 120), 1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(self._mouse_pos, r, r)

        # Rendering indicator
        if self._rendering:
            painter.setPen(QColor(120, 110, 100, 180))
            painter.drawText(self.rect().adjusted(8, 8, 0, 0),
                             Qt.AlignTop | Qt.AlignLeft, "rendering…")

        painter.end()

    # ── helpers ────────────────────────────────────────────────────────────

    def _emit_count(self) -> None:
        self.op_count_changed.emit(self.engine.op_count)

    def clear(self) -> None:
        self.engine.clear()
        self._color_index = 0
        self._emit_count()
        self.request_render()

    def undo(self) -> None:
        self.engine.undo()
        self._emit_count()
        self.request_render()

    def get_image(self) -> Optional[QImage]:
        """Return the current render as a QImage, or None."""
        if self._pixmap:
            return self._pixmap.toImage()
        return None
