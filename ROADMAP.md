# Suminagashi Marbling Simulator -- Roadmap

## Current State
A well-structured PyQt5 application with clean package layout: `suminagashi/`
contains `engine.py` (numpy-vectorized marbling physics), `canvas.py` (Qt render
thread), `controls.py` (control panel), `main_window.py`, `palettes.py` (10
palettes), `presets.py` (6 presets), `app.py` (CLI), and proper `__init__.py` /
`__main__.py`. Implements Jaffer's area-preserving drop transform with comb,
blow, and vortex operations. Inverse raster mapping produces crisp boundaries.
The `original/` directory holds a previous monolith version. No tests, no CI.

## Short-term Improvements
- [x] Add unit tests for `engine.py`: verify drop transform preserves area,
      test comb/blow/vortex displacement formulas against known values
- [x] Add a `pyproject.toml` for proper packaging (currently pip-install is
      manual)
- [ ] Add type hints to `canvas.py` and `controls.py` (engine already has them)
- [ ] Add error handling for edge cases: zero-radius drops, drops outside canvas
      bounds, empty operation history for undo
- [ ] Profile rendering performance for large canvases (1000x1000+) and identify
      bottlenecks in the inverse raster loop
- [ ] Add a `--size` alias for `-W`/`-H` CLI flags for convenience

## Feature Enhancements
- [ ] Add a tine/rake tool with configurable spacing and curvature (beyond the
      single comb stroke)
- [ ] Implement multi-layer marbling: overlay multiple marble sessions with
      transparency blending
- [ ] Add animation export: record the operation sequence and render as GIF or
      MP4 showing the marbling process step by step
- [ ] Support custom palette creation via a color picker dialog in the controls
- [ ] Add paper texture overlay: simulate the texture of washi paper on the
      final print
- [ ] Implement batch rendering: apply the same operation sequence to multiple
      palette variations
- [ ] Add a gallery/history panel showing thumbnails of previous artworks from
      the session

## Long-term Vision
- [ ] GPU-accelerated rendering via OpenCL or CUDA for real-time 4K marbling
- [ ] Physical simulation mode: model actual fluid dynamics (Navier-Stokes)
      instead of purely geometric transforms for more realistic results
- [ ] Tablet pressure sensitivity: map pen pressure to drop radius/stroke width
      for Wacom/Apple Pencil users
- [ ] Web version via WebAssembly (compile engine with Emscripten) or a
      JavaScript port of the numpy-vectorized engine
- [ ] 3D marbling: wrap the 2D marble pattern onto 3D surfaces (vases, bowls)
      using UV mapping
- [ ] Print integration: direct output to art printers at correct DPI/color
      profile

## Technical Debt
- [x] The `original/suminagashi_marbling.py` monolith should be removed now that
      the package version exists -- or archived to a `legacy/` branch
- [x] The `jsx/` directory suggests an abandoned JavaScript port -- remove or
      document its purpose
- [ ] Render thread in `canvas.py` may not handle Qt shutdown gracefully --
      ensure clean thread termination on window close
- [x] No `.gitignore` -- saved PNG artworks and `__pycache__` may be tracked
- [ ] Operation history (`engine.operations`) grows unboundedly -- add a
      configurable max history size or implement undo with bounded memory
