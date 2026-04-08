# Suminagashi Marbling Simulator -- Interface Map

## Package: `suminagashi/`
| File | Purpose | Key Classes/Functions |
|---|---|---|
| `__init__.py` | Package metadata (`__version__`) | |
| `__main__.py` | `python -m suminagashi` entry | |
| `app.py` | CLI argument parsing & Qt launch | `main()`, `_parse_args()` |
| `engine.py` | Numpy-vectorised marbling physics | `MarblingEngine`, `Operation`, `OpType` |
| `canvas.py` | Qt render thread & display widget | |
| `controls.py` | Control panel (tools, palette, presets) | |
| `main_window.py` | Top-level Qt window composition | `MainWindow` |
| `palettes.py` | Colour palette definitions (10 palettes) | `PALETTES`, `get_palette()`, `list_palettes()` |
| `presets.py` | Preset patterns (6 presets) | `PRESETS`, `apply_preset()`, `list_presets()` |

## Entry Points
| File | Purpose |
|---|---|
| `run_suminagashi.py` | Simple launch script |
| `suminagashi/app.py` | Full CLI with argparse |

## Tests
| File | Purpose |
|---|---|
| `tests/test_engine.py` | Engine unit tests (drop transform, stroke, blow, vortex, render) |

## Archive
| File | Purpose |
|---|---|
| `_archive/suminagashi_marbling.py` | Original monolith (superseded) |
| `_archive/suminagashi.jsx` | Abandoned JavaScript port |

## Module Dependencies
```
app.py  -->  main_window.py  -->  canvas.py   -->  engine.py
                              -->  controls.py -->  palettes.py
                                                -->  presets.py --> engine.py
```
