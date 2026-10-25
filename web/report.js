// report_generator.build_report_html for the web viewer: the same
// self-contained HTML report, character for character, built from the
// checked vendor rows. The only addition is a CSP meta tag, because a
// report opened from a blob: URL runs with this page's origin.
import { esc, isHttpUrl } from "./util.js";
import { pyFixed, pyFloat, pyOr, pySlice, pyStr, strValue, truthy } from "./py.js";

// _num: v as a float if numeric and non-zero, else null.
function num(v) {
  if (v === null || v === undefined) return null;
  const f = pyFloat(v);
  return f === null || f === 0 ? null : f;
}

function fmt(v, digits = 0) {
  const n = num(v);
  return n === null ? "-" : pyFixed(n, digits);
}

// str(a or b or c): Python's `or` yields the first truthy operand, else the last.
function firstTruthy(...vals) {
  for (const [c, k] of vals.slice(0, -1)) if (truthy(c?.[k])) return c[k];
  const [c, k] = vals[vals.length - 1];
  return c?.[k] ?? null;
}

const COLORS = ["#3a78d8", "#cc6622", "#1a8a3a", "#a82a82", "#d8a800", "#6a4ac8",
                "#aa3030", "#3a8a8a", "#5a9ad8", "#dc7632", "#2a9a4a", "#b83a92"];

const f1 = (x) => pyFixed(x, 1);
const pf = (x) => strValue(x, true);          // a Python float in an f-string

function svgBarChart(title, unit, points, width = 760, height = 320) {
  if (!points.length) {
    return `<div class="chart-empty"><strong>${esc(title)}</strong>`
      + '<br><span class="muted">No measured values</span></div>';
  }
  const [padL, padR, padT, padB] = [60, 24, 40, 100];
  const maxV = Math.max(...points.map(([, v]) => v)) * 1.18 || 1.0;
  const n = points.length;
  const availW = width - padL - padR;
  const barW = availW / n * 0.72;
  const gap = availW / n * 0.28;
  const plotH = height - padT - padB;

  const out = [
    '<div class="chart-block">',
    `<h3>${esc(title)} <span class="unit">[${esc(unit)}]</span></h3>`,
    `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" class="bar-chart">`,
    `<rect x="0" y="0" width="${width}" height="${height}" fill="#fafbfc"/>`,
    `<line x1="${padL}" y1="${padT}" x2="${padL}" y2="${height - padB}" stroke="#999"/>`,
    `<line x1="${padL}" y1="${height - padB}" x2="${width - padR}" y2="${height - padB}" stroke="#999"/>`,
    `<text x="6" y="${padT - 6}" fill="#444" font-size="11">${Math.trunc(maxV)}</text>`,
    `<text x="6" y="${height - padB + 14}" fill="#444" font-size="11">0</text>`,
    `<line x1="${padL}" y1="${pf(padT + plotH / 2)}" x2="${width - padR}" y2="${pf(padT + plotH / 2)}" `
      + 'stroke="#e0e0e0" stroke-dasharray="4 4"/>',
    `<text x="6" y="${pf(padT + plotH / 2 + 4)}" fill="#666" font-size="10">${Math.trunc(maxV / 2)}</text>`,
  ];
  points.forEach(([lbl, val], i) => {
    const x = padL + i * (barW + gap) + gap / 2;
    const barH = (val / maxV) * plotH;
    const y1 = height - padB - barH;
    const col = COLORS[i % COLORS.length];
    out.push(`<rect x="${f1(x)}" y="${f1(y1)}" width="${f1(barW)}" height="${f1(barH)}" `
      + `fill="${col}" stroke="#333" stroke-width="0.5"/>`);
    out.push(`<text x="${f1(x + barW / 2)}" y="${f1(y1 - 6)}" text-anchor="middle" fill="#111" `
      + `font-size="11" font-weight="bold">${f1(val)}</text>`);
    lbl.split(" | ").forEach((part, li) => {
      const ty = height - padB + 14 + li * 12;
      out.push(`<text x="${f1(x + barW / 2)}" y="${f1(ty)}" text-anchor="middle" fill="#222" `
        + `font-size="10">${esc(part)}</text>`);
    });
  });
  out.push("</svg></div>");
  return out.join("");
}

// (db field, unit, header)
const METRICS = [
  ["yield_MPa", "MPa", "YS XY — Yield Strength (in-plane)"],
  ["yield_z_MPa", "MPa", "YS Z — Yield Strength (build direction)"],
  ["uts_xy_MPa", "MPa", "UTS XY — Tensile Strength (in-plane)"],
  ["uts_z_MPa", "MPa", "UTS Z — Tensile Strength (build direction)"],
  ["elongation_xy_pct", "%", "Elongation XY"],
  ["elongation_z_pct", "%", "Elongation Z"],
  ["hardness_HV", "HV", "Hardness (Vickers)"],
  ["surface_ra_hi", "μm", "Surface Roughness Ra (upper bound, side wall as-built)"],
];

// Chart x-axis label; ' | ' is the line break svgBarChart splits on.
function vendorShortLabel(vd) {
  const manuf = pySlice(pyOr(vd, "manufacturer", "?"), 14);
  const machine = pySlice(pyOr(vd, "machine", ""), 14);
  const post = pyOr(vd, "post_treatment", "");
  const layer = truthy(vd.layer_thickness_um) ? ` ${pyStr(vd, "layer_thickness_um")}μm` : "";
  const line2 = (machine + layer).trim() || "-";
  const line3 = ["as-built", ""].includes(post.toLowerCase()) ? "" : pySlice(post, 14);
  const parts = [manuf, line2];
  if (line3) parts.push(`(${line3})`);
  return parts.join(" | ");
}

function compositionRows(comp) {
  if (!truthy(comp)) return '<tr><td colspan="2" class="muted">(not reported)</td></tr>';
  return comp.map((c) => {
    let el, pct;
    if (Array.isArray(c) && c.length >= 2) [el, pct] = [pyStr(c, 0), pyStr(c, 1)];
    else if (c && typeof c === "object") [el, pct] = [pyStr(c, "element", "?"), pyStr(c, "pct", "-")];
    else [el, pct] = [strValue(c), "-"];
    return `<tr><td class='el'>${esc(el)}</td><td>${esc(pct)}</td></tr>`;
  }).join("");
}

function rangeText(c, loKey, hiKey) {
  return `${pyStr(c, loKey)}~${pyStr(c, hiKey)}`;
}

function htRows(ht) {
  if (!truthy(ht)) return '<tr><td colspan="7" class="muted">(no heat-treatment data)</td></tr>';
  const rows = [];
  for (const [key, hd] of Object.entries(ht)) {
    if (!hd || typeof hd !== "object" || Array.isArray(hd)) continue;
    const lo = hd.surface_ra_lo ?? null, hi = hd.surface_ra_hi ?? null;
    const ra = lo !== null && hi !== null && lo !== hi
      ? rangeText(hd, "surface_ra_lo", "surface_ra_hi")
      : fmt(firstTruthy([hd, "surface_ra_um"], [hd, "surface_ra_lo"], [hd, "surface_ra_hi"]));
    rows.push("<tr>"
      + `<td><b>${esc(key)}</b></td>`
      + `<td>${fmt(hd.uts, 0)}</td>`
      + `<td>${fmt(hd.ys, 0)}</td>`
      + `<td>${fmt(hd.elong, 1)}</td>`
      + `<td>${fmt(hd.hardness_HV, 0)}</td>`
      + `<td>${ra}</td>`
      + `<td class='muted small'>${esc(pyOr(hd, "notes", "-"))}</td>`
      + "</tr>");
  }
  return rows.join("") || '<tr><td colspan="7" class="muted">(none)</td></tr>';
}

function vendorDetailRows(selected) {
  return selected.map(([, vd]) => {
    const tds = vd.tds_link;
    const tdsHtml = truthy(tds) && isHttpUrl(tds)
      ? `<a href="${esc(tds)}" target="_blank" rel="noopener noreferrer">TDS</a>`
      : '<span class="muted">-</span>';
    const xy = vd.elongation_xy_pct ?? null, z = vd.elongation_z_pct ?? null;
    const elong = xy !== null && z !== null && xy !== z
      ? `${fmt(xy, 1)} / ${fmt(z, 1)}`
      : fmt(xy !== null ? xy : z, 1);
    const lo = vd.surface_ra_lo ?? null, hi = vd.surface_ra_hi ?? null;
    const ra = lo !== null && hi !== null && lo !== hi
      ? rangeText(vd, "surface_ra_lo", "surface_ra_hi")
      : fmt(lo !== null ? lo : hi);
    return "<tr>"
      + `<td>${esc(pyOr(vd, "manufacturer", "-"))}</td>`
      + `<td>${esc(pyOr(vd, "machine", "-"))}</td>`
      + `<td>${esc(pyOr(vd, "post_treatment", "-"))}</td>`
      + `<td>${fmt(vd.layer_thickness_um, 0)}</td>`
      + `<td>${fmt(vd.yield_MPa, 0)}</td>`
      + `<td>${fmt(vd.yield_z_MPa, 0)}</td>`
      + `<td>${fmt(vd.uts_xy_MPa, 0)}</td>`
      + `<td>${fmt(vd.uts_z_MPa, 0)}</td>`
      + `<td>${elong}</td>`
      + `<td>${fmt(vd.hardness_HV, 0)}</td>`
      + `<td>${ra}</td>`
      + `<td>${tdsHtml}</td>`
      + "</tr>";
  }).join("");
}

const CSS = `
    :root { color-scheme: light; }
    body { font-family: -apple-system, "Segoe UI", "Helvetica Neue", sans-serif;
           margin: 0; padding: 24px; background: #f5f7fa; color: #222; }
    h1 { color: #1a3a6a; margin: 0 0 4px; }
    h2 { color: #1a3a6a; border-bottom: 2px solid #d0d4da; padding-bottom: 6px;
         margin-top: 28px; }
    h3 { color: #1a3a6a; margin: 6px 0; font-size: 14px; }
    .meta { color: #666; font-size: 13px; }
    .section { background: #fff; border: 1px solid #d0d4da; border-radius: 6px;
               padding: 16px 20px; margin-top: 18px; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; }
    th, td { border: 1px solid #d0d4da; padding: 6px 8px; text-align: center; }
    th { background: #eef1f5; color: #1a3a6a; }
    td.el { font-weight: bold; }
    td.small { font-size: 11px; }
    .muted { color: #888; }
    .props-grid { display: grid; grid-template-columns: repeat(4, 1fr);
                  gap: 8px 18px; margin-top: 6px; }
    .props-grid div { font-size: 13px; padding: 4px 0; }
    .props-grid b { color: #1a3a6a; }
    .chart-block { margin: 14px 0 22px; }
    .chart-empty { padding: 12px; background: #f5f7fa; border: 1px dashed #c0c4ca;
                   border-radius: 4px; }
    .bar-chart { width: 100%; max-width: 760px; height: auto; }
    .unit { color: #888; font-weight: normal; font-size: 12px; }
    a { color: #0066cc; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .footer { color: #888; font-size: 11px; margin-top: 32px; text-align: center; }
    `;

const pad2 = (n) => String(n).padStart(2, "0");

// selected: [vendor_key, vendor_entry] for every checked row, in tree order.
export function buildReportHtml(materialName, props, selected, now = new Date()) {
  const stamp = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())} `
    + `${pad2(now.getHours())}:${pad2(now.getMinutes())}`;

  const charts = METRICS.map(([field, unit, header]) => {
    const points = [];
    for (const [, vd] of selected) {
      const n = num(vd[field]);
      if (n !== null) points.push([vendorShortLabel(vd), n]);
    }
    return svgBarChart(header, unit, points);
  });

  const physical = [
    ["Density", fmt(props.density, 3), "g/cm³"],
    ["Melting point", fmt(props.melt, 0), "°C"],
    ["Magnetic", esc(pyOr(props, "magnetic", "-")), ""],
    ["Young's modulus E", fmt(props.E, 0), "GPa"],
    ["Poisson ratio", fmt(props.poisson, 3), ""],
    ["Thermal cond.", fmt(props.thermal_k, 1), "W/m·K"],
    ["Specific heat Cp", fmt(props.cp, 0), "J/kg·K"],
    ["Thermal expansion", fmt(props.cte, 1), "1e-6/K"],
  ];
  const propsHtml = physical.map(([lbl, v, u]) =>
    `<div><b>${esc(lbl)}</b>: ${v} <span class="muted">${esc(u)}</span></div>`).join("");

  const refs = Array.isArray(props.ref_urls) ? props.ref_urls : [];
  const refsHtml = refs.filter((e) => Array.isArray(e) && e.length >= 2).map((e) => {
    const [label, u] = [pyStr(e, 0), pyStr(e, 1)];
    return isHttpUrl(u)
      ? `<li><a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a></li>`
      : `<li>${esc(label)}</li>`;
  }).join("") || '<li class="muted">(none)</li>';

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>MDS Report — ${esc(materialName)}</title>
<style>${CSS}</style>
</head>
<body>

<h1>MDS Comparison Report</h1>
<div class="meta">
  <strong>Material:</strong> ${esc(materialName)}
  &nbsp;·&nbsp; <strong>Category:</strong> ${esc(pyOr(props, "category", "-"))}
  &nbsp;·&nbsp; <strong>Generated:</strong> ${stamp}
  &nbsp;·&nbsp; <strong>Selected entries:</strong> ${selected.length}
</div>

<div class="section">
  <h2>Basic Physical &amp; Thermal Properties</h2>
  <div class="props-grid">${propsHtml}</div>
</div>

<div class="section">
  <h2>Chemical Composition (wt%)</h2>
  <table>
    <thead><tr><th style="width: 30%">Element</th><th>wt %</th></tr></thead>
    <tbody>${compositionRows(props.composition)}</tbody>
  </table>
</div>

<div class="section">
  <h2>Aggregate Values by Heat Treatment</h2>
  <table>
    <thead><tr>
      <th>Heat treatment</th>
      <th>UTS<br>MPa</th><th>YS<br>MPa</th>
      <th>Elong<br>%</th><th>Hardness<br>HV</th><th>Ra<br>μm</th>
      <th style="width: 28%">Notes</th>
    </tr></thead>
    <tbody>${htRows(props.heat_treatments || {})}</tbody>
  </table>
</div>

<div class="section">
  <h2>Selected Vendor Entries (${selected.length})</h2>
  <table>
    <thead><tr>
      <th>Manufacturer</th><th>Machine</th><th>Post</th><th>Layer<br>μm</th>
      <th>YS XY<br>MPa</th><th>YS Z<br>MPa</th>
      <th>UTS XY<br>MPa</th><th>UTS Z<br>MPa</th>
      <th>Elong<br>XY / Z %</th><th>Hardness<br>HV</th><th>Ra<br>μm</th>
      <th>TDS</th>
    </tr></thead>
    <tbody>${vendorDetailRows(selected)}</tbody>
  </table>
</div>

<div class="section">
  <h2>Per-Vendor Comparison Charts</h2>
  ${charts.join("")}
</div>

<div class="section">
  <h2>References</h2>
  <ul>${refsHtml}</ul>
</div>

<div class="footer">
  Generated by MDS Viewer · ${stamp}
</div>

</body>
</html>
`;
}

// MDS_<material>_<YYYYmmdd_HHMMSS>.html, as the desktop's save dialog suggests.
export function reportFilename(materialName, now = new Date()) {
  const safe = Array.from(materialName, (ch) => (/[\p{L}\p{N}]/u.test(ch) || " -_".includes(ch) ? ch : "_")).join("");
  const ts = `${now.getFullYear()}${pad2(now.getMonth() + 1)}${pad2(now.getDate())}_`
    + `${pad2(now.getHours())}${pad2(now.getMinutes())}${pad2(now.getSeconds())}`;
  return `MDS_${safe}_${ts}.html`;
}
