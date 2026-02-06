"""
Main application window — assembles canvas, controls, and menu bar.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStatusBar,
    QWidget,
)

from . import __version__
from .canvas import MarblingCanvas
from .controls import ControlPanel
from .engine import MarblingEngine

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 600


class MainWindow(QMainWindow):
    """Top-level window for the Suminagashi Simulator.

    Parameters:
        canvas_w: Engine canvas width in pixels.
        canvas_h: Engine canvas height in pixels.
    """

    def __init__(
        self,
        canvas_w: int = DEFAULT_WIDTH,
        canvas_h: int = DEFAULT_HEIGHT,
    ) -> None:
        super().__init__()
        self.setWindowTitle(f"墨流し  Suminagashi Simulator  v{__version__}")
        self.setMinimumSize(780, 520)

        # ── Core objects ──────────────────────────────────────────────────
        self.engine = MarblingEngine(canvas_w, canvas_h)
        self.canvas = MarblingCanvas(self.engine)
        self.controls = ControlPanel(self.canvas)

        # ── Layout ────────────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(8, 8, 8, 8)
        h_layout.setSpacing(12)

        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        h_layout.addWidget(self.canvas, stretch=1)
        h_layout.addWidget(self.controls)

        # ── Menu bar ──────────────────────────────────────────────────────
        self._build_menu()

        # ── Status bar ────────────────────────────────────────────────────
        self.statusBar().showMessage("Ready — click on the canvas to begin")

        # Wire signals
        self.controls.save_requested.connect(self._save_artwork)
        self.canvas.render_time_changed.connect(self._on_render_time)
        self.canvas.op_count_changed.connect(self._on_op_count)

    # ── menu ──────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu = self.menuBar()

        # File menu
        file_menu = menu.addMenu("&File")

        save_action = QAction("&Save Artwork…", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_artwork)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menu.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.canvas.undo)
        edit_menu.addAction(undo_action)

        clear_action = QAction("&Clear Canvas", self)
        clear_action.setShortcut(QKeySequence("Ctrl+Shift+X"))
        clear_action.triggered.connect(self.canvas.clear)
        edit_menu.addAction(clear_action)

        # Canvas size menu
        canvas_menu = menu.addMenu("&Canvas")
        for label, w, h in [
            ("Small (400×400)", 400, 400),
            ("Medium (600×600)", 600, 600),
            ("Large (800×800)", 800, 800),
            ("Wide (900×600)", 900, 600),
            ("Tall (600×900)", 600, 900),
        ]:
            action = QAction(label, self)
            action.setData((w, h))
            action.triggered.connect(self._on_canvas_resize)
            canvas_menu.addAction(action)

        # Help menu
        help_menu = menu.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ── slots ─────────────────────────────────────────────────────────────

    def _save_artwork(self) -> None:
        """Save current artwork to PNG."""
        img = self.canvas.get_image()
        if img is None:
            QMessageBox.warning(self, "Save Error",
                                "No image to save. Try adding some ink first!")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Suminagashi Artwork", "suminagashi.png",
            "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)",
        )
        if not path:
            return

        if img.save(path):
            self.statusBar().showMessage(f"Saved to {path}")
            logger.info("Artwork saved to %s", path)
        else:
            QMessageBox.critical(self, "Save Error",
                                 f"Failed to save image to:\n{path}")
            logger.error("Failed to save to %s", path)

    def _on_canvas_resize(self) -> None:
        action = self.sender()
        w, h = action.data()
        logger.info("Resizing canvas to %d×%d", w, h)

        self.engine = MarblingEngine(w, h)
        pal = self.controls.current_palette()
        self.engine.set_water_color(pal.water)

        self.canvas.engine = self.engine
        self.canvas.set_ink_colors(list(pal.colors))
        self.canvas.reset_color_index()
        self.canvas._emit_count()
        self.canvas.request_render()

        self.statusBar().showMessage(f"Canvas resized to {w}×{h}")

    def _on_render_time(self, dt: float) -> None:
        self.statusBar().showMessage(
            f"{self.engine.op_count} ops  •  rendered in {dt:.2f}s"
        )

    def _on_op_count(self, count: int) -> None:
        self.statusBar().showMessage(f"{count} operations")

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Suminagashi Simulator",
            f"<h3>墨流し  Suminagashi Simulator  v{__version__}</h3>"
            "<p>Physics-based Japanese ink marbling simulator.</p>"
            "<p>Based on Jaffer's Mathematical Marbling — each ink drop "
            "applies an area-preserving radial transform, naturally creating "
            "thinning concentric rings as successive drops push earlier ink "
            "outward.</p>"
            "<p><b>References:</b></p>"
            "<ul>"
            "<li>Lu, Jaffer et al., <i>Mathematical Marbling</i>, "
            "IEEE CG&amp;A 2012</li>"
            "<li>Jaffer, <i>Dropping Paint</i>, "
            "people.csail.mit.edu/jaffer/Marbling/</li>"
            "<li>Sun et al., <i>Hydrodynamics of marbling art</i>, "
            "Phys Rev Fluids 2024</li>"
            "</ul>",
        )
