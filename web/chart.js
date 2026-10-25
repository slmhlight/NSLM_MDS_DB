// The vendor comparison chart: mds_dialog._BarCanvas.paintEvent, drawn as
// SVG with the same geometry, colours and number formats.
import { T } from "./util.js";
import { pyFixed, pyLen, pyRound } from "./py.js";

const NS = "http://www.w3.org/2000/svg";
export const FAMILY = '"Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif';
const px = (pt) => pt * 96 / 72;        // Qt point sizes at 96 dpi

const UNIT = { uts: "MPa", uts_z: "MPa", ys: "MPa", ys_z: "MPa",
               elong_xy: "%", elong_z: "%", hardness_HV: "HV", surface_ra_hi: "μm" };
// saturated, well-separated hues; every one readable on white
const COLORS = ["#2f6fd0", "#e07b1f", "#1f8a4c", "#a4308f", "#c9a400", "#6a4ac8",
                "#c0392b", "#0f8f8f", "#4a90e2", "#d35400", "#27ae60", "#c2379b"];

let measureCtx = null;
let chartCount = 0;
function textWidth(text, font) {
  measureCtx ??= document.createElement("canvas").getContext("2d");
  measureCtx.font = font;
  return measureCtx.measureText(text).width;
}

// A 1/2/5·10^n step that yields roughly `target` gridlines.
function niceStep(rng, target = 5) {
  if (rng <= 0) return 1.0;
  const raw = rng / Math.max(1, target);
  const mag = 10 ** Math.floor(Math.log10(raw));
  for (const mult of [1, 2, 2.5, 5, 10]) if (raw <= mult * mag) return mult * mag;
  return 10 * mag;
}

function fmtTick(v) {
  if (v >= 10) return pyFixed(v, 0);
  if (v >= 1) return pyFixed(v, 1);
  return pyFixed(v, 2);
}

// QColor.lighter / .darker work on the HSV value channel.
function hsv(hex) {
  const n = parseInt(hex.slice(1), 16);
  const r = ((n >> 16) & 255) / 255, g = ((n >> 8) & 255) / 255, b = (n & 255) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  let hue = 0;
  if (d) {
    if (max === r) hue = ((g - b) / d) % 6;
    else if (max === g) hue = (b - r) / d + 2;
    else hue = (r - g) / d + 4;
    hue *= 60;
    if (hue < 0) hue += 360;
  }
  return [hue, max ? d / max : 0, max];
}

function rgbHex(hue, s, v) {
  const c = v * s, x = c * (1 - Math.abs(((hue / 60) % 2) - 1)), m = v - c;
  const [r, g, b] = hue < 60 ? [c, x, 0] : hue < 120 ? [x, c, 0] : hue < 180 ? [0, c, x]
    : hue < 240 ? [0, x, c] : hue < 300 ? [x, 0, c] : [c, 0, x];
  return "#" + [r, g, b].map((u) => Math.round((u + m) * 255).toString(16).padStart(2, "0")).join("");
}

function lighter(hex, factor) {
  let [hue, s, v] = hsv(hex);
  v = v * factor / 100;
  if (v > 1) { s = Math.max(0, s - (v - 1)); v = 1; }
  return rgbHex(hue, s, v);
}

function darker(hex, factor) {
  const [hue, s, v] = hsv(hex);
  return rgbHex(hue, s, v * 100 / factor);
}

function el(tag, attrs, text) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
}

// Lines of text inside a box, like QPainter.drawText(rect, flags, text):
// clipped to the box, aligned horizontally (start/middle/end) and either
// from the top or centred vertically.
function textBox(parent, defs, id, x, y, w, h, lines, { font, size, weight = "normal", fill,
                                                         hAlign = "middle", vAlign = "center" }) {
  const clip = el("clipPath", { id, clipPathUnits: "userSpaceOnUse" });
  clip.append(el("rect", { x, y, width: Math.max(0, w), height: Math.max(0, h) }));
  defs.append(clip);
  const lineH = size * 1.33;
  const ax = hAlign === "start" ? x : hAlign === "end" ? x + w : x + w / 2;
  const top = vAlign === "top" ? y : y + (h - lineH * lines.length) / 2;
  const t = el("text", { "clip-path": `url(#${id})`, "font-family": font, "font-size": size,
                         "font-weight": weight, fill, "text-anchor": hAlign });
  lines.forEach((line, i) => {
    t.append(el("tspan", { x: ax, y: top + lineH * i + size * 1.02 }, line));
  });
  parent.append(t);
}

// rows: [label, value, lo, hi] in tree order (lo/hi null without a range).
export function drawChart(svg, rows, metric, W, H) {
  svg.replaceChildren();
  const id = (svg.dataset.chart ??= String(++chartCount));   // ids are page-global
  svg.setAttribute("width", W);
  svg.setAttribute("height", H);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const defs = el("defs", {});
  svg.append(defs);
  // Canvas chrome is a soft neutral; the plot panel itself is pure white
  // with a hairline border, so the bars read as a distinct card.
  svg.append(el("rect", { x: 0, y: 0, width: W, height: H, fill: "#eff2f6" }));
  if (!rows.length) {
    textBox(svg, defs, `c${id}-empty`, 0, 0, W, H, [T("MD_NO_CHECKED"), T("MD_TREE_HINT")],
            { font: FAMILY, size: px(10), fill: "#888" });
    return;
  }

  const unit = UNIT[metric] || "";
  const n = rows.length;

  // ---- vertical scale on a "nice" step ----
  let vmaxRaw = Math.max(...rows.map((r) => r[1]), ...rows.filter((r) => r[3] !== null).map((r) => r[3]));
  if (vmaxRaw <= 0) vmaxRaw = 1.0;
  const step = niceStep(vmaxRaw, 5);
  let maxV = Math.ceil(vmaxRaw / step) * step;
  // headroom so value labels above the tallest bar stay inside
  if (maxV - vmaxRaw < step * 0.45) maxV += step;

  // ---- label rotation decision (drives bottom padding) ----
  const lblLines = Math.max(...rows.map((r) => r[0].split("\n").length));
  const slotW = (W - 96) / n;
  const rotate = slotW < 74;          // too narrow to read horizontally

  const padL = 62, padR = 26, padT = 34;
  let padB;
  if (rotate) {
    const longest = Math.max(...rows.map((r) => Math.max(...r[0].split("\n").map(pyLen))));
    padB = Math.min(150, 48 + Math.trunc(longest * 5.2));
  } else {
    padB = 34 + lblLines * 15;
  }
  let plotH = H - padT - padB;
  if (plotH < 40) {                   // squeezed — bail gracefully
    padB = Math.max(30, H - padT - 40);
    plotH = H - padT - padB;
  }
  const yBase = H - padB;
  const availW = W - padL - padR;

  // ---- plot panel + horizontal gridlines ----
  svg.append(el("rect", { x: padL, y: padT, width: availW, height: plotH, fill: "#ffffff",
                          stroke: "#d3dae2", "stroke-width": 1, "shape-rendering": "crispEdges" }));
  const nTicks = pyRound(maxV / step);
  for (let k = 0; k <= nTicks; k++) {
    const v = step * k;
    const y = Math.trunc(yBase - (v / maxV) * plotH);
    if (k > 0) {
      svg.append(el("line", { x1: padL + 1, y1: y, x2: W - padR, y2: y, stroke: "#dfe4ea",
                              "stroke-width": 1, "shape-rendering": "crispEdges" }));
    }
    textBox(svg, defs, `c${id}-t${k}`, 0, y - 9, padL - 8, 18, [fmtTick(v)],
            { font: FAMILY, size: px(9), fill: "#5a6472", hAlign: "end" });
  }

  // ---- axes ----
  svg.append(el("line", { x1: padL, y1: padT, x2: padL, y2: yBase, stroke: "#8b95a3", "stroke-width": 2 }));
  svg.append(el("line", { x1: padL, y1: yBase, x2: W - padR, y2: yBase, stroke: "#8b95a3", "stroke-width": 2 }));

  // unit caption (top-left of the plot)
  if (unit) {
    svg.append(el("text", { x: padL + 6, y: padT - 10, "font-family": FAMILY, "font-size": px(9),
                            "font-weight": "bold", fill: "#1a3a6a" }, `[${unit}]`));
  }

  // ---- bars ----
  const slot = availW / n;
  const barW = Math.max(6.0, Math.min(64.0, slot * 0.66));
  const valueFont = `bold ${px(9)}px ${FAMILY}`;
  rows.forEach(([lbl, val, lo, hi], i) => {
    const cx = padL + slot * (i + 0.5);
    const x = cx - barW / 2;
    const barH = Math.max(0.0, (val / maxV) * plotH);
    const y1 = yBase - barH;
    const base = COLORS[i % COLORS.length];

    // subtle vertical gradient keeps the bar readable but flat
    const grad = el("linearGradient", { id: `c${id}-g${i}`, gradientUnits: "userSpaceOnUse",
                                        x1: 0, y1, x2: 0, y2: yBase });
    grad.append(el("stop", { offset: 0, "stop-color": lighter(base, 112) }));
    grad.append(el("stop", { offset: 1, "stop-color": base }));
    defs.append(grad);
    svg.append(el("rect", { x: Math.trunc(x), y: Math.trunc(y1), width: Math.trunc(barW),
                            height: Math.trunc(barH), fill: `url(#c${id}-g${i})`,
                            stroke: darker(base, 155), "stroke-width": 1 }));

    // ---- error bar (published lo–hi range) ----
    let yTop = y1;
    if (lo !== null && hi !== null) {
      const yLo = Math.trunc(yBase - (lo / maxV) * plotH);
      const yHi = Math.trunc(yBase - (hi / maxV) * plotH);
      const icx = Math.trunc(cx);
      const cap = Math.floor(Math.max(9, Math.trunc(barW * 0.5)) / 2);
      // white halo first so the whisker reads on any fill
      svg.append(el("line", { x1: icx, y1: yLo, x2: icx, y2: yHi, stroke: "#ffffff",
                              "stroke-opacity": 210 / 255, "stroke-width": 4 }));
      svg.append(el("line", { x1: icx, y1: yLo, x2: icx, y2: yHi, stroke: "#12161c", "stroke-width": 2 }));
      for (const yy of [yLo, yHi]) {
        svg.append(el("line", { x1: icx - cap, y1: yy, x2: icx + cap, y2: yy,
                                stroke: "#12161c", "stroke-width": 2 }));
      }
      yTop = Math.min(yTop, yBase - (hi / maxV) * plotH);
    }

    // ---- value label with a light pill behind it ----
    const txt = val >= 10 ? pyFixed(val, 0) : pyFixed(val, 1);
    const tw = Math.round(textWidth(txt, valueFont)) + 10;
    const th = Math.round(px(9) * 1.33) + 2;
    const tx = Math.trunc(cx - tw / 2);
    let ty = Math.trunc(yTop) - th - 4;
    if (ty < padT - th) ty = Math.trunc(yTop) + 4;     // clamp inside the plot
    svg.append(el("rect", { x: tx, y: ty, width: tw, height: th, rx: 3, ry: 3,
                            fill: "#ffffff", "fill-opacity": 225 / 255 }));
    textBox(svg, defs, `c${id}-v${i}`, tx, ty, tw, th, [txt],
            { font: FAMILY, size: px(9), weight: "bold", fill: "#10141a" });

    // ---- x label: rotated when slots are narrow ----
    if (rotate) {
      const flat = lbl.split("\n").filter(Boolean).join(" · ");
      const g = el("g", { transform: `translate(${cx + 4} ${yBase + 6}) rotate(-52)` });
      svg.append(g);
      textBox(g, defs, `c${id}-x${i}`, -(padB + 40), -8, padB + 36, 16, [flat],
              { font: FAMILY, size: px(8), fill: "#2b3138", hAlign: "end" });
    } else {
      textBox(svg, defs, `c${id}-x${i}`, Math.trunc(cx - slot / 2), Math.trunc(yBase + 5),
              Math.trunc(slot), Math.trunc(padB - 8), lbl.split("\n"),
              { font: FAMILY, size: px(8), fill: "#2b3138", vAlign: "top" });
    }
  });
}
