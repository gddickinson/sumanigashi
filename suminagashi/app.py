"""
Application entry point with CLI argument parsing, logging setup,
and dependency checking.
"""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__


def _check_dependencies() -> list[str]:
    """Return list of missing dependencies."""
    missing = []
    try:
        import numpy  # noqa: F401
    except ImportError:
        missing.append("numpy")
    try:
        import PyQt5  # noqa: F401
    except ImportError:
        missing.append("PyQt5")
    return missing


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="suminagashi",
        description=(
            "Suminagashi Marbling Simulator — physics-based Japanese "
            "ink marbling using area-preserving transforms."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s                      # default 600×600 canvas\n"
            "  %(prog)s -W 800 -H 800        # 800×800 canvas\n"
            "  %(prog)s --palette indigo      # start with Indigo palette\n"
            "  %(prog)s --preset concentric   # start with concentric rings\n"
            "  %(prog)s --list-palettes       # show available palettes\n"
            "  %(prog)s --list-presets        # show available presets\n"
            "  %(prog)s -v                    # verbose logging\n"
        ),
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-W", "--width", type=int, default=600,
        help="Canvas width in pixels (default: 600)",
    )
    parser.add_argument(
        "-H", "--height", type=int, default=600,
        help="Canvas height in pixels (default: 600)",
    )
    parser.add_argument(
        "--palette", type=str, default=None,
        help="Initial colour palette (e.g. traditional, indigo, sakura)",
    )
    parser.add_argument(
        "--preset", type=str, default=None,
        help="Load a preset pattern on startup",
    )
    parser.add_argument(
        "--list-palettes", action="store_true",
        help="Print available palettes and exit",
    )
    parser.add_argument(
        "--list-presets", action="store_true",
        help="Print available presets and exit",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    """Launch the Suminagashi Simulator."""
    args = _parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("suminagashi")

    # Info-only modes
    if args.list_palettes:
        from .palettes import PALETTES, list_palettes
        print("Available palettes:")
        for key in list_palettes():
            p = PALETTES[key]
            swatches = "  ".join(
                f"rgb({c[0]},{c[1]},{c[2]})" for c in p.colors
            )
            print(f"  {key:15s}  {p.name:18s}  {swatches}")
        sys.exit(0)

    if args.list_presets:
        from .presets import list_presets
        print("Available presets:")
        for name in list_presets():
            print(f"  {name}")
        sys.exit(0)

    # Check dependencies
    missing = _check_dependencies()
    if missing:
        print(
            f"ERROR: Missing required packages: {', '.join(missing)}\n"
            f"Install them with:\n"
            f"  pip install {' '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate dimensions
    if args.width < 100 or args.height < 100:
        print("ERROR: Canvas dimensions must be at least 100×100.", file=sys.stderr)
        sys.exit(1)
    if args.width > 2000 or args.height > 2000:
        print(
            "WARNING: Very large canvases (>2000 px) may be slow to render.",
            file=sys.stderr,
        )

    # Validate palette
    if args.palette:
        from .palettes import PALETTES
        if args.palette not in PALETTES:
            from .palettes import list_palettes
            available = ", ".join(list_palettes())
            print(
                f"ERROR: Unknown palette '{args.palette}'.\n"
                f"Available: {available}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Validate preset
    if args.preset:
        from .presets import PRESETS
        if args.preset not in PRESETS:
            from .presets import list_presets
            available = ", ".join(list_presets())
            print(
                f"ERROR: Unknown preset '{args.preset}'.\n"
                f"Available: {available}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Launch Qt app
    logger.info("Starting Suminagashi Simulator v%s", __version__)
    logger.info("Canvas: %d×%d", args.width, args.height)

    from PyQt5.QtWidgets import QApplication
    from .main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Suminagashi Simulator")
    app.setApplicationVersion(__version__)

    # Apply a refined stylesheet
    app.setStyleSheet("""
        QMainWindow {
            background: #f0ede6;
        }
        QGroupBox {
            font-weight: bold;
            font-size: 12px;
            color: #4a4540;
            border: 1px solid #ccc8be;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 2px 8px;
        }
        QPushButton {
            background: #faf8f4;
            border: 1px solid #c8c0b4;
            border-radius: 4px;
            padding: 5px 12px;
            color: #4a4540;
            font-size: 12px;
        }
        QPushButton:hover {
            background: #eee8dc;
            border-color: #a09888;
        }
        QPushButton:pressed {
            background: #e0d8cc;
        }
        QRadioButton {
            font-size: 12px;
            color: #4a4540;
            spacing: 6px;
        }
        QComboBox {
            background: #faf8f4;
            border: 1px solid #c8c0b4;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            color: #4a4540;
        }
        QSlider::groove:horizontal {
            height: 4px;
            background: #d0cac0;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #8a7e6b;
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }
        QSlider::handle:horizontal:hover {
            background: #6a6050;
        }
        QStatusBar {
            color: #8a8578;
            font-size: 11px;
        }
        QMenuBar {
            background: #f0ede6;
            color: #4a4540;
        }
        QMenuBar::item:selected {
            background: #e0d8cc;
        }
    """)

    window = MainWindow(args.width, args.height)

    # Apply initial palette if specified
    if args.palette:
        combo = window.controls._palette_combo
        for i in range(combo.count()):
            if combo.itemData(i) == args.palette:
                combo.setCurrentIndex(i)
                break

    # Apply initial preset if specified
    if args.preset:
        from .palettes import get_palette
        from .presets import apply_preset
        pal_key = args.palette or "traditional"
        pal = get_palette(pal_key)
        try:
            apply_preset(args.preset, window.engine, pal)
            window.canvas.request_render()
            window.canvas.op_count_changed.emit(window.engine.op_count)
        except Exception as e:
            logger.error("Failed to apply preset '%s': %s", args.preset, e)

    window.resize(1050, 700)
    window.show()

    sys.exit(app.exec_())
