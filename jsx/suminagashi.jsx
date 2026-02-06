import { useState, useRef, useCallback, useEffect } from "react";

/*
 * Suminagashi Simulator — based on Jaffer's Mathematical Marbling
 *
 * Core physics: Each ink drop induces an AREA-PRESERVING radial transform.
 * When a drop of radius r is placed at center C, every point P moves to:
 *   C + (P - C) · sqrt(1 + r² / ||P-C||²)
 *
 * For inverse (raster) rendering, given pixel Q and drop at C with radius r:
 *   if ||Q-C|| < r → Q is inside drop, takes drop color
 *   else → Q maps backward to: C + (Q-C) · sqrt(1 - r² / ||Q-C||²)
 *
 * Combing/blowing applies displacement fields that warp the coordinate space.
 * All transforms compose — we trace each pixel backward through the full
 * sequence of drops and strokes to find its final color.
 */

// ─── Color palettes for authentic suminagashi ───
const PALETTES = {
  traditional: {
    name: "Traditional",
    water: [245, 242, 235],
    colors: [
      [15, 15, 15],
      [45, 42, 38],
      [90, 85, 78],
    ],
  },
  indigo: {
    name: "Indigo & Ink",
    water: [240, 238, 232],
    colors: [
      [25, 35, 80],
      [50, 60, 120],
      [10, 10, 30],
    ],
  },
  autumn: {
    name: "Autumn Leaves",
    water: [248, 244, 236],
    colors: [
      [160, 50, 20],
      [180, 100, 20],
      [80, 30, 15],
    ],
  },
  ocean: {
    name: "Ocean",
    water: [235, 242, 245],
    colors: [
      [15, 60, 90],
      [30, 100, 130],
      [5, 30, 50],
    ],
  },
  sakura: {
    name: "Sakura",
    water: [250, 245, 245],
    colors: [
      [180, 80, 100],
      [200, 120, 140],
      [120, 40, 60],
    ],
  },
  monochrome: {
    name: "Sumi Ink",
    water: [248, 246, 240],
    colors: [
      [10, 10, 10],
      [60, 58, 55],
      [30, 28, 25],
    ],
  },
};

// ─── Mathematical Marbling Engine ───
class MarblingEngine {
  constructor(width, height) {
    this.width = width;
    this.height = height;
    this.operations = []; // sequence of drops and strokes
    this.waterColor = [245, 242, 235];
    this.imageData = null;
  }

  setWaterColor(rgb) {
    this.waterColor = rgb;
  }

  addDrop(cx, cy, radius, color) {
    this.operations.push({
      type: "drop",
      cx,
      cy,
      radius,
      color, // [r, g, b]
    });
  }

  addStroke(x, y, angle, strength, width) {
    // A tine stroke: displaces points along direction (cos θ, sin θ)
    // with falloff perpendicular to the stroke line
    this.operations.push({
      type: "stroke",
      x,
      y,
      angle, // radians
      strength,
      width, // falloff width
    });
  }

  addBlow(cx, cy, strength, radius) {
    // Radial blow from center - like breathing on the surface
    this.operations.push({
      type: "blow",
      cx,
      cy,
      strength,
      radius,
    });
  }

  addVortex(cx, cy, strength, radius) {
    this.operations.push({
      type: "vortex",
      cx,
      cy,
      strength,
      radius,
    });
  }

  clear() {
    this.operations = [];
  }

  // Inverse-map a single pixel through all operations
  // Returns the color at pixel (px, py)
  tracePixel(px, py) {
    let qx = px;
    let qy = py;

    // Walk backward through operations
    for (let i = this.operations.length - 1; i >= 0; i--) {
      const op = this.operations[i];

      if (op.type === "drop") {
        const dx = qx - op.cx;
        const dy = qy - op.cy;
        const dist2 = dx * dx + dy * dy;
        const r2 = op.radius * op.radius;

        if (dist2 < r2) {
          // Point is inside drop — it takes this drop's color
          return op.color;
        }
        // Inverse transform: map backward
        // Q_new = C + (Q - C) * sqrt(1 - r²/||Q-C||²)
        const factor = Math.sqrt(1 - r2 / dist2);
        qx = op.cx + dx * factor;
        qy = op.cy + dy * factor;
      } else if (op.type === "stroke") {
        // Inverse of a tine stroke displacement
        const cosA = Math.cos(op.angle);
        const sinA = Math.sin(op.angle);
        // Perpendicular distance from stroke line through (op.x, op.y)
        const perpDist =
          -(qx - op.x) * sinA + (qy - op.y) * cosA;
        // Displacement decays exponentially with perpendicular distance
        const disp =
          op.strength * Math.exp((-perpDist * perpDist) / (2 * op.width * op.width));
        // Inverse: subtract the displacement
        qx -= disp * cosA;
        qy -= disp * sinA;
      } else if (op.type === "blow") {
        const dx = qx - op.cx;
        const dy = qy - op.cy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > 0.1 && dist < op.radius * 3) {
          // Radial displacement that decays with distance
          const falloff = Math.exp(
            (-dist * dist) / (2 * op.radius * op.radius)
          );
          const disp = op.strength * falloff;
          const nx = dx / dist;
          const ny = dy / dist;
          // Inverse: subtract the displacement
          qx -= disp * nx;
          qy -= disp * ny;
        }
      } else if (op.type === "vortex") {
        const dx = qx - op.cx;
        const dy = qy - op.cy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > 0.1 && dist < op.radius * 3) {
          const falloff = Math.exp(
            (-dist * dist) / (2 * op.radius * op.radius)
          );
          const angle = op.strength * falloff;
          // Inverse rotation
          const cosR = Math.cos(-angle);
          const sinR = Math.sin(-angle);
          const rx = dx * cosR - dy * sinR;
          const ry = dx * sinR + dy * cosR;
          qx = op.cx + rx;
          qy = op.cy + ry;
        }
      }
    }

    return null; // water color
  }

  // Render the full image
  render(ctx) {
    const w = this.width;
    const h = this.height;
    const imgData = ctx.createImageData(w, h);
    const data = imgData.data;

    for (let py = 0; py < h; py++) {
      for (let px = 0; px < w; px++) {
        const color = this.tracePixel(px, py);
        const idx = (py * w + px) * 4;
        if (color) {
          data[idx] = color[0];
          data[idx + 1] = color[1];
          data[idx + 2] = color[2];
        } else {
          data[idx] = this.waterColor[0];
          data[idx + 1] = this.waterColor[1];
          data[idx + 2] = this.waterColor[2];
        }
        data[idx + 3] = 255;
      }
    }

    ctx.putImageData(imgData, 0, 0);
  }

  // Render only a region (for progressive updates)
  renderRegion(ctx, startY, endY) {
    const w = this.width;
    const imgData = ctx.getImageData(0, startY, w, endY - startY);
    const data = imgData.data;

    for (let py = startY; py < endY; py++) {
      for (let px = 0; px < w; px++) {
        const color = this.tracePixel(px, py);
        const idx = ((py - startY) * w + px) * 4;
        if (color) {
          data[idx] = color[0];
          data[idx + 1] = color[1];
          data[idx + 2] = color[2];
        } else {
          data[idx] = this.waterColor[0];
          data[idx + 1] = this.waterColor[1];
          data[idx + 2] = this.waterColor[2];
        }
        data[idx + 3] = 255;
      }
    }

    ctx.putImageData(imgData, 0, startY);
  }
}

// ─── Main Component ───
export default function SuminagashiSimulator() {
  const canvasRef = useRef(null);
  const engineRef = useRef(null);
  const renderRAF = useRef(null);
  const [canvasSize, setCanvasSize] = useState({ w: 600, h: 600 });
  const [palette, setPalette] = useState("traditional");
  const [tool, setTool] = useState("drop"); // drop, ring, blow, vortex, comb
  const [dropRadius, setDropRadius] = useState(30);
  const [blowStrength, setBlowStrength] = useState(40);
  const [combStrength, setCombStrength] = useState(60);
  const [ringCount, setRingCount] = useState(8);
  const [ringSpacing, setRingSpacing] = useState(12);
  const [isRendering, setIsRendering] = useState(false);
  const [opCount, setOpCount] = useState(0);
  const [showHelp, setShowHelp] = useState(false);
  const isDragging = useRef(false);
  const lastDragPos = useRef(null);
  const colorIndexRef = useRef(0);

  // Initialize engine
  useEffect(() => {
    const w = canvasSize.w;
    const h = canvasSize.h;
    engineRef.current = new MarblingEngine(w, h);
    engineRef.current.setWaterColor(PALETTES[palette].water);
    renderFull();
  }, [canvasSize]);

  useEffect(() => {
    if (engineRef.current) {
      engineRef.current.setWaterColor(PALETTES[palette].water);
      renderFull();
    }
  }, [palette]);

  const renderFull = useCallback(() => {
    const canvas = canvasRef.current;
    const engine = engineRef.current;
    if (!canvas || !engine) return;
    const ctx = canvas.getContext("2d");

    if (engine.operations.length === 0) {
      // Just fill with water color
      const [r, g, b] = engine.waterColor;
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      setIsRendering(false);
      return;
    }

    setIsRendering(true);

    // Progressive rendering in horizontal bands
    const bandHeight = 8;
    let currentY = 0;

    const renderBand = () => {
      const endY = Math.min(currentY + bandHeight, engine.height);
      engine.renderRegion(ctx, currentY, endY);
      currentY = endY;

      if (currentY < engine.height) {
        renderRAF.current = requestAnimationFrame(renderBand);
      } else {
        setIsRendering(false);
      }
    };

    if (renderRAF.current) cancelAnimationFrame(renderRAF.current);
    renderRAF.current = requestAnimationFrame(renderBand);
  }, []);

  const getCanvasPos = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  }, []);

  const getNextColor = useCallback(() => {
    const colors = PALETTES[palette].colors;
    const c = colors[colorIndexRef.current % colors.length];
    colorIndexRef.current++;
    return c;
  }, [palette]);

  const handlePointerDown = useCallback(
    (e) => {
      e.preventDefault();
      const pos = getCanvasPos(e);
      const engine = engineRef.current;
      if (!engine) return;

      if (tool === "drop") {
        const color = getNextColor();
        engine.addDrop(pos.x, pos.y, dropRadius, color);
        setOpCount(engine.operations.length);
        renderFull();
      } else if (tool === "ring") {
        // Classic suminagashi: alternating ink and surfactant at same center
        // Creates concentric rings that thin as each pushes the others outward
        const colors = PALETTES[palette].colors;
        for (let i = 0; i < ringCount; i++) {
          const color = colors[i % colors.length];
          const r = ringSpacing + (Math.random() - 0.5) * 4;
          engine.addDrop(
            pos.x + (Math.random() - 0.5) * 2,
            pos.y + (Math.random() - 0.5) * 2,
            r,
            color
          );
        }
        setOpCount(engine.operations.length);
        renderFull();
      } else if (tool === "blow" || tool === "vortex") {
        isDragging.current = true;
        lastDragPos.current = pos;
      } else if (tool === "comb") {
        isDragging.current = true;
        lastDragPos.current = pos;
      }
    },
    [tool, dropRadius, ringCount, ringSpacing, palette, getCanvasPos, getNextColor, renderFull]
  );

  const handlePointerMove = useCallback(
    (e) => {
      e.preventDefault();
      if (!isDragging.current || !lastDragPos.current) return;

      const pos = getCanvasPos(e);
      const engine = engineRef.current;
      if (!engine) return;

      const dx = pos.x - lastDragPos.current.x;
      const dy = pos.y - lastDragPos.current.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < 3) return; // minimum movement threshold

      if (tool === "blow") {
        engine.addBlow(
          lastDragPos.current.x,
          lastDragPos.current.y,
          blowStrength * 0.7,
          blowStrength * 2
        );
      } else if (tool === "vortex") {
        const sign = dx * (pos.y - canvasSize.h / 2) - dy * (pos.x - canvasSize.w / 2) > 0 ? 1 : -1;
        engine.addVortex(
          pos.x,
          pos.y,
          sign * 0.3 * (blowStrength / 40),
          blowStrength * 2.5
        );
      } else if (tool === "comb") {
        const angle = Math.atan2(dy, dx);
        engine.addStroke(
          lastDragPos.current.x,
          lastDragPos.current.y,
          angle,
          combStrength * 0.8,
          combStrength * 0.6
        );
      }

      lastDragPos.current = pos;
      setOpCount(engine.operations.length);
      renderFull();
    },
    [tool, blowStrength, combStrength, canvasSize, getCanvasPos, renderFull]
  );

  const handlePointerUp = useCallback((e) => {
    e.preventDefault();
    isDragging.current = false;
    lastDragPos.current = null;
  }, []);

  const handleClear = useCallback(() => {
    if (engineRef.current) {
      engineRef.current.clear();
      colorIndexRef.current = 0;
      setOpCount(0);
      renderFull();
    }
  }, [renderFull]);

  const handleUndo = useCallback(() => {
    if (engineRef.current && engineRef.current.operations.length > 0) {
      engineRef.current.operations.pop();
      setOpCount(engineRef.current.operations.length);
      renderFull();
    }
  }, [renderFull]);

  const handleSave = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = "suminagashi.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
  }, []);

  // ─── Preset patterns ───
  const handlePreset = useCallback(
    (type) => {
      const engine = engineRef.current;
      if (!engine) return;
      engine.clear();
      colorIndexRef.current = 0;
      const colors = PALETTES[palette].colors;
      const cx = canvasSize.w / 2;
      const cy = canvasSize.h / 2;

      if (type === "concentric") {
        // Classic suminagashi concentric rings
        for (let i = 0; i < 25; i++) {
          const c = colors[i % colors.length];
          engine.addDrop(
            cx + (Math.random() - 0.5) * 3,
            cy + (Math.random() - 0.5) * 3,
            10 + Math.random() * 6,
            c
          );
        }
      } else if (type === "scattered") {
        // Multiple ring centers
        const centers = [
          [cx - 120, cy - 80],
          [cx + 100, cy - 60],
          [cx - 40, cy + 100],
          [cx + 80, cy + 80],
          [cx, cy],
        ];
        for (const [x, y] of centers) {
          for (let i = 0; i < 10; i++) {
            const c = colors[i % colors.length];
            engine.addDrop(
              x + (Math.random() - 0.5) * 4,
              y + (Math.random() - 0.5) * 4,
              8 + Math.random() * 8,
              c
            );
          }
        }
      } else if (type === "blown") {
        // Concentric rings with gentle blow
        for (let i = 0; i < 20; i++) {
          const c = colors[i % colors.length];
          engine.addDrop(cx, cy, 12 + Math.random() * 4, c);
        }
        // Add some gentle blows
        for (let i = 0; i < 6; i++) {
          const angle = (i / 6) * Math.PI * 2 + Math.random() * 0.3;
          const bx = cx + Math.cos(angle) * 60;
          const by = cy + Math.sin(angle) * 60;
          engine.addBlow(bx, by, 25 + Math.random() * 15, 80);
        }
      } else if (type === "combed") {
        // Scattered drops then combed
        for (let j = 0; j < 4; j++) {
          const sx = cx - 150 + j * 100;
          for (let i = 0; i < 8; i++) {
            const c = colors[i % colors.length];
            engine.addDrop(
              sx + (Math.random() - 0.5) * 6,
              cy + (Math.random() - 0.5) * 6,
              10 + Math.random() * 5,
              c
            );
          }
        }
        // Vertical comb strokes
        for (let x = 50; x < canvasSize.w - 50; x += 40) {
          engine.addStroke(x, cy, Math.PI / 2, 50, 30);
        }
        // Then horizontal strokes
        for (let y = 80; y < canvasSize.h - 80; y += 60) {
          const dir = y % 120 === 0 ? 0 : Math.PI;
          engine.addStroke(cx, y, dir, 40, 25);
        }
      }

      setOpCount(engine.operations.length);
      renderFull();
    },
    [palette, canvasSize, renderFull]
  );

  // Slider component
  const Slider = ({ label, value, onChange, min, max, step = 1 }) => (
    <div style={{ marginBottom: 10 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 11,
          color: "#8a8578",
          marginBottom: 3,
          fontFamily: "'Noto Serif', Georgia, serif",
        }}
      >
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%", accentColor: "#8a7e6b" }}
      />
    </div>
  );

  const toolBtnStyle = (active) => ({
    padding: "7px 12px",
    fontSize: 12,
    border: active ? "2px solid #5a5347" : "1px solid #c8c0b4",
    borderRadius: 6,
    background: active ? "#eae4d8" : "#faf8f4",
    color: "#3a3630",
    cursor: "pointer",
    fontFamily: "'Noto Serif', Georgia, serif",
    transition: "all 0.2s",
    whiteSpace: "nowrap",
  });

  const smallBtnStyle = {
    padding: "5px 10px",
    fontSize: 11,
    border: "1px solid #c8c0b4",
    borderRadius: 5,
    background: "#faf8f4",
    color: "#5a5347",
    cursor: "pointer",
    fontFamily: "'Noto Serif', Georgia, serif",
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(160deg, #f5f2ec 0%, #ede8df 50%, #e8e3d8 100%)",
        fontFamily: "'Noto Serif', Georgia, serif",
        color: "#3a3630",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "16px 12px",
      }}
    >
      <link
        href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;500&family=Noto+Serif:ital,wght@0,300;0,400;1,300&display=swap"
        rel="stylesheet"
      />

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 16 }}>
        <h1
          style={{
            fontSize: 28,
            fontWeight: 300,
            letterSpacing: 6,
            margin: 0,
            fontFamily: "'Noto Serif JP', 'Noto Serif', serif",
            color: "#4a4540",
          }}
        >
          墨流し
        </h1>
        <div
          style={{
            fontSize: 11,
            letterSpacing: 4,
            color: "#9a9488",
            marginTop: 2,
            textTransform: "uppercase",
          }}
        >
          Suminagashi — Floating Ink
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: 20,
          flexWrap: "wrap",
          justifyContent: "center",
          maxWidth: 1100,
          width: "100%",
        }}
      >
        {/* Canvas */}
        <div style={{ position: "relative" }}>
          <canvas
            ref={canvasRef}
            width={canvasSize.w}
            height={canvasSize.h}
            onMouseDown={handlePointerDown}
            onMouseMove={handlePointerMove}
            onMouseUp={handlePointerUp}
            onMouseLeave={handlePointerUp}
            onTouchStart={handlePointerDown}
            onTouchMove={handlePointerMove}
            onTouchEnd={handlePointerUp}
            style={{
              width: Math.min(canvasSize.w, 560),
              height: Math.min(canvasSize.h, 560),
              borderRadius: 4,
              boxShadow: "0 4px 24px rgba(60, 50, 40, 0.15), 0 1px 4px rgba(60,50,40,0.08)",
              cursor:
                tool === "drop" || tool === "ring"
                  ? "crosshair"
                  : tool === "comb"
                  ? "col-resize"
                  : "grab",
              touchAction: "none",
              display: "block",
            }}
          />
          {isRendering && (
            <div
              style={{
                position: "absolute",
                top: 8,
                right: 8,
                fontSize: 10,
                color: "#8a7e6b",
                background: "rgba(250,248,244,0.85)",
                padding: "3px 8px",
                borderRadius: 4,
              }}
            >
              rendering…
            </div>
          )}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 6,
              fontSize: 10,
              color: "#9a9488",
            }}
          >
            <span>{opCount} operations</span>
            <span>{canvasSize.w}×{canvasSize.h}</span>
          </div>
        </div>

        {/* Controls */}
        <div
          style={{
            width: 260,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          {/* Palette */}
          <div>
            <div
              style={{
                fontSize: 10,
                textTransform: "uppercase",
                letterSpacing: 2,
                color: "#8a8578",
                marginBottom: 6,
              }}
            >
              Palette
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {Object.entries(PALETTES).map(([key, p]) => (
                <button
                  key={key}
                  onClick={() => setPalette(key)}
                  style={{
                    ...smallBtnStyle,
                    border:
                      palette === key
                        ? "2px solid #5a5347"
                        : "1px solid #c8c0b4",
                    background: palette === key ? "#eae4d8" : "#faf8f4",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <span
                    style={{
                      display: "flex",
                      gap: 1,
                    }}
                  >
                    {p.colors.map((c, i) => (
                      <span
                        key={i}
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: `rgb(${c[0]},${c[1]},${c[2]})`,
                          display: "inline-block",
                        }}
                      />
                    ))}
                  </span>
                  <span style={{ fontSize: 10 }}>{p.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Tools */}
          <div>
            <div
              style={{
                fontSize: 10,
                textTransform: "uppercase",
                letterSpacing: 2,
                color: "#8a8578",
                marginBottom: 6,
              }}
            >
              Tool
            </div>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 4,
              }}
            >
              {[
                ["drop", "Drop"],
                ["ring", "Rings"],
                ["blow", "Blow"],
                ["vortex", "Swirl"],
                ["comb", "Comb"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setTool(key)}
                  style={toolBtnStyle(tool === key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Tool-specific controls */}
          {(tool === "drop" || tool === "ring") && (
            <div>
              <Slider
                label="Drop Radius"
                value={dropRadius}
                onChange={setDropRadius}
                min={5}
                max={80}
              />
              {tool === "ring" && (
                <>
                  <Slider
                    label="Ring Count"
                    value={ringCount}
                    onChange={setRingCount}
                    min={3}
                    max={30}
                  />
                  <Slider
                    label="Ring Spacing"
                    value={ringSpacing}
                    onChange={setRingSpacing}
                    min={4}
                    max={30}
                  />
                </>
              )}
            </div>
          )}

          {(tool === "blow" || tool === "vortex") && (
            <Slider
              label="Strength"
              value={blowStrength}
              onChange={setBlowStrength}
              min={10}
              max={100}
            />
          )}

          {tool === "comb" && (
            <Slider
              label="Comb Width"
              value={combStrength}
              onChange={setCombStrength}
              min={10}
              max={120}
            />
          )}

          {/* Presets */}
          <div>
            <div
              style={{
                fontSize: 10,
                textTransform: "uppercase",
                letterSpacing: 2,
                color: "#8a8578",
                marginBottom: 6,
              }}
            >
              Presets
            </div>
            <div
              style={{ display: "flex", flexWrap: "wrap", gap: 4 }}
            >
              {[
                ["concentric", "Concentric"],
                ["scattered", "Scattered"],
                ["blown", "Wind-Blown"],
                ["combed", "Combed"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => handlePreset(key)}
                  style={smallBtnStyle}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button onClick={handleUndo} style={smallBtnStyle}>
              ↩ Undo
            </button>
            <button onClick={handleClear} style={smallBtnStyle}>
              ✕ Clear
            </button>
            <button onClick={handleSave} style={smallBtnStyle}>
              ↓ Save PNG
            </button>
            <button
              onClick={() => setShowHelp(!showHelp)}
              style={smallBtnStyle}
            >
              ? Help
            </button>
          </div>

          {/* Canvas size */}
          <div>
            <div
              style={{
                fontSize: 10,
                textTransform: "uppercase",
                letterSpacing: 2,
                color: "#8a8578",
                marginBottom: 6,
              }}
            >
              Canvas Size
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              {[
                [400, 400, "S"],
                [600, 600, "M"],
                [800, 800, "L"],
              ].map(([w, h, label]) => (
                <button
                  key={label}
                  onClick={() => {
                    setCanvasSize({ w, h });
                    if (engineRef.current) {
                      engineRef.current.clear();
                      colorIndexRef.current = 0;
                      setOpCount(0);
                    }
                  }}
                  style={{
                    ...smallBtnStyle,
                    border:
                      canvasSize.w === w
                        ? "2px solid #5a5347"
                        : "1px solid #c8c0b4",
                  }}
                >
                  {label} ({w})
                </button>
              ))}
            </div>
          </div>

          {/* Help panel */}
          {showHelp && (
            <div
              style={{
                fontSize: 11,
                lineHeight: 1.6,
                color: "#6a6458",
                background: "#faf8f4",
                padding: 12,
                borderRadius: 6,
                border: "1px solid #ddd8ce",
              }}
            >
              <strong>How to use:</strong>
              <br />
              <strong>Drop</strong> — Click to place an ink drop. Each
              drop pushes existing ink outward (area-preserving).
              <br />
              <strong>Rings</strong> — Click to place many concentric
              drops at once, creating classic suminagashi rings.
              <br />
              <strong>Blow</strong> — Click & drag to blow on the
              surface, like breathing gently across water.
              <br />
              <strong>Swirl</strong> — Click & drag to create vortex
              currents in the ink.
              <br />
              <strong>Comb</strong> — Click & drag to rake through the
              ink, creating traditional marbling patterns.
              <br />
              <br />
              <em>
                Based on Jaffer's Mathematical Marbling — each
                operation is an area-preserving transform on the fluid
                surface.
              </em>
            </div>
          )}

          {/* Physics note */}
          <div
            style={{
              fontSize: 10,
              color: "#a09888",
              lineHeight: 1.5,
              fontStyle: "italic",
              marginTop: 4,
            }}
          >
            Each ink drop induces an area-preserving radial
            displacement, thinning earlier rings as it pushes them
            outward — just as real ink spreads on water via surface
            tension and Marangoni forces.
          </div>
        </div>
      </div>
    </div>
  );
}
