"""
Control panel widget — tool selection, parameters, presets, and actions.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .canvas import MarblingCanvas
from .palettes import PALETTES, Palette, get_palette, list_palettes
from .presets import PRESETS, apply_preset, list_presets

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: labelled slider
# ---------------------------------------------------------------------------

class LabelledSlider(QWidget):
    """Horizontal slider with label and current-value readout."""

    valueChanged = pyqtSignal(int)

    def __init__(
        self,
        label: str,
        min_val: int,
        max_val: int,
        initial: int,
        suffix: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self._label = QLabel(label)
        self._label.setFixedWidth(110)
        layout.addWidget(self._label)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(min_val, max_val)
        self._slider.setValue(initial)
        layout.addWidget(self._slider, stretch=1)

        self._suffix = suffix
        self._readout = QLabel(f"{initial}{suffix}")
        self._readout.setFixedWidth(50)
        self._readout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self._readout)

        self._slider.valueChanged.connect(self._on_changed)

    def _on_changed(self, val: int) -> None:
        self._readout.setText(f"{val}{self._suffix}")
        self.valueChanged.emit(val)

    def value(self) -> int:
        return self._slider.value()

    def setValue(self, v: int) -> None:
        self._slider.setValue(v)


# ---------------------------------------------------------------------------
# Control panel
# ---------------------------------------------------------------------------

class ControlPanel(QWidget):
    """Side panel with all marbling controls.

    Signals:
        save_requested: user clicked Save.
    """

    save_requested = pyqtSignal()

    def __init__(
        self,
        canvas: MarblingCanvas,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.setFixedWidth(320)

        # Outer scroll area for small screens
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        inner = QWidget()
        scroll.setWidget(inner)
        layout = QVBoxLayout(inner)
        layout.setSpacing(10)

        # ── Palette ───────────────────────────────────────────────────────
        palette_group = QGroupBox("Palette")
        pg_layout = QVBoxLayout(palette_group)

        self._palette_combo = QComboBox()
        for key in list_palettes():
            self._palette_combo.addItem(PALETTES[key].name, key)
        self._palette_combo.setCurrentIndex(0)
        self._palette_combo.currentIndexChanged.connect(self._on_palette_changed)
        pg_layout.addWidget(self._palette_combo)

        # Colour swatches preview
        self._swatch_layout = QHBoxLayout()
        pg_layout.addLayout(self._swatch_layout)
        self._update_swatches()

        layout.addWidget(palette_group)

        # ── Tool selection ────────────────────────────────────────────────
        tool_group = QGroupBox("Tool")
        tg_layout = QVBoxLayout(tool_group)

        self._tool_group = QButtonGroup(self)
        tools = [
            (MarblingCanvas.TOOL_DROP, "Drop — single ink drop"),
            (MarblingCanvas.TOOL_RING, "Rings — concentric drops"),
            (MarblingCanvas.TOOL_BLOW, "Blow — radial push (drag)"),
            (MarblingCanvas.TOOL_VORTEX, "Swirl — vortex (drag)"),
            (MarblingCanvas.TOOL_COMB, "Comb — tine stroke (drag)"),
        ]
        for i, (key, desc) in enumerate(tools):
            rb = QRadioButton(desc)
            rb.setProperty("tool_key", key)
            self._tool_group.addButton(rb, i)
            tg_layout.addWidget(rb)
            if i == 0:
                rb.setChecked(True)

        self._tool_group.buttonClicked.connect(self._on_tool_changed)
        layout.addWidget(tool_group)

        # ── Tool parameters ───────────────────────────────────────────────
        param_group = QGroupBox("Parameters")
        self._param_layout = QVBoxLayout(param_group)

        self._drop_radius = LabelledSlider("Drop Radius", 3, 80, 30, " px")
        self._drop_radius.valueChanged.connect(
            lambda v: setattr(self.canvas, "drop_radius", float(v))
        )
        self._param_layout.addWidget(self._drop_radius)

        self._ring_count = LabelledSlider("Ring Count", 3, 40, 10)
        self._ring_count.valueChanged.connect(
            lambda v: setattr(self.canvas, "ring_count", v)
        )
        self._param_layout.addWidget(self._ring_count)
        self._ring_count.hide()

        self._ring_spacing = LabelledSlider("Ring Spacing", 3, 40, 12, " px")
        self._ring_spacing.valueChanged.connect(
            lambda v: setattr(self.canvas, "ring_spacing", float(v))
        )
        self._param_layout.addWidget(self._ring_spacing)
        self._ring_spacing.hide()

        self._blow_strength = LabelledSlider("Strength", 5, 120, 40)
        self._blow_strength.valueChanged.connect(
            lambda v: setattr(self.canvas, "blow_strength", float(v))
        )
        self._param_layout.addWidget(self._blow_strength)
        self._blow_strength.hide()

        self._comb_strength = LabelledSlider("Comb Width", 10, 150, 60, " px")
        self._comb_strength.valueChanged.connect(
            lambda v: setattr(self.canvas, "comb_strength", float(v))
        )
        self._param_layout.addWidget(self._comb_strength)
        self._comb_strength.hide()

        layout.addWidget(param_group)

        # ── Presets ───────────────────────────────────────────────────────
        preset_group = QGroupBox("Presets")
        preset_layout = QGridLayout(preset_group)
        preset_names = {
            "concentric": "Concentric",
            "scattered": "Scattered",
            "blown": "Wind-Blown",
            "combed": "Combed",
            "vortex_rings": "Vortex Rings",
            "stone": "Stone",
        }
        col = 0
        row = 0
        for key in list_presets():
            label = preset_names.get(key, key.title())
            btn = QPushButton(label)
            btn.setProperty("preset_key", key)
            btn.clicked.connect(self._on_preset_clicked)
            preset_layout.addWidget(btn, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
        layout.addWidget(preset_group)

        # ── Actions ───────────────────────────────────────────────────────
        action_group = QGroupBox("Actions")
        ag_layout = QGridLayout(action_group)

        undo_btn = QPushButton("↩  Undo")
        undo_btn.clicked.connect(self.canvas.undo)
        ag_layout.addWidget(undo_btn, 0, 0)

        clear_btn = QPushButton("✕  Clear")
        clear_btn.clicked.connect(self._on_clear)
        ag_layout.addWidget(clear_btn, 0, 1)

        save_btn = QPushButton("↓  Save PNG")
        save_btn.clicked.connect(self.save_requested.emit)
        ag_layout.addWidget(save_btn, 1, 0, 1, 2)

        layout.addWidget(action_group)

        # ── Status ────────────────────────────────────────────────────────
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(
            "QLabel { color: #888; font-size: 11px; font-style: italic; }"
        )
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # ── Help text ─────────────────────────────────────────────────────
        help_label = QLabel(
            "<b>How to use:</b><br>"
            "• <b>Drop</b> — click to place a single ink drop<br>"
            "• <b>Rings</b> — click to place concentric drops<br>"
            "• <b>Blow</b> — click and drag to push ink outward<br>"
            "• <b>Swirl</b> — drag to create vortex currents<br>"
            "• <b>Comb</b> — drag to rake through the ink<br>"
            "<br>"
            "<i>Each drop applies an area-preserving radial transform, "
            "thinning earlier rings as it pushes them outward — "
            "just as real sumi ink spreads on water.</i>"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet(
            "QLabel { color: #666; font-size: 11px; padding: 8px; "
            "background: #f5f3ef; border-radius: 4px; }"
        )
        layout.addWidget(help_label)

        layout.addStretch()

        # Wire up canvas signals
        self.canvas.op_count_changed.connect(self._on_op_count)
        self.canvas.render_time_changed.connect(self._on_render_time)

        # Apply initial palette
        self._apply_palette()

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_palette_changed(self, index: int) -> None:
        self._apply_palette()
        self._update_swatches()

    def _apply_palette(self) -> None:
        key = self._palette_combo.currentData()
        try:
            pal = get_palette(key)
        except KeyError as e:
            logger.error("Palette error: %s", e)
            return
        self.canvas.engine.set_water_color(pal.water)
        self.canvas.set_ink_colors(list(pal.colors))
        self.canvas.request_render()
        self._current_palette = pal

    def _update_swatches(self) -> None:
        # Clear existing
        while self._swatch_layout.count():
            item = self._swatch_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        key = self._palette_combo.currentData()
        try:
            pal = get_palette(key)
        except KeyError:
            return

        for c in pal.colors:
            swatch = QWidget()
            swatch.setFixedSize(20, 20)
            swatch.setStyleSheet(
                f"background: rgb({c[0]},{c[1]},{c[2]}); "
                f"border-radius: 10px; border: 1px solid #bbb;"
            )
            self._swatch_layout.addWidget(swatch)
        self._swatch_layout.addStretch()

    def _on_tool_changed(self, button) -> None:
        key = button.property("tool_key")
        self.canvas.tool = key

        # Show/hide relevant parameter sliders
        self._drop_radius.setVisible(key in (MarblingCanvas.TOOL_DROP, MarblingCanvas.TOOL_RING))
        self._ring_count.setVisible(key == MarblingCanvas.TOOL_RING)
        self._ring_spacing.setVisible(key == MarblingCanvas.TOOL_RING)
        self._blow_strength.setVisible(key in (MarblingCanvas.TOOL_BLOW, MarblingCanvas.TOOL_VORTEX))
        self._comb_strength.setVisible(key == MarblingCanvas.TOOL_COMB)

    def _on_preset_clicked(self) -> None:
        btn = self.sender()
        key = btn.property("preset_key")
        try:
            pal_key = self._palette_combo.currentData()
            pal = get_palette(pal_key)
            apply_preset(key, self.canvas.engine, pal)
            self.canvas.reset_color_index()
            self.canvas.op_count_changed.emit(self.canvas.engine.op_count)
            self.canvas.request_render()
        except Exception as e:
            logger.error("Preset error: %s", e, exc_info=True)
            self._status_label.setText(f"Error: {e}")

    def _on_clear(self) -> None:
        self.canvas.clear()

    def _on_op_count(self, count: int) -> None:
        self._status_label.setText(f"{count} operations")

    def _on_render_time(self, dt: float) -> None:
        ops = self.canvas.engine.op_count
        current = self._status_label.text()
        self._status_label.setText(f"{ops} operations  •  rendered in {dt:.2f}s")

    def current_palette(self) -> Palette:
        """Return the currently selected palette."""
        key = self._palette_combo.currentData()
        return get_palette(key)
