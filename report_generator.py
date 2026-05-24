"""HTML report generator for the MDS Viewer (English UI).

Given a material's properties and a set of selected vendor entries (the ones
the user ticked in the "Vendor differences" tab), this module produces a
self-contained HTML document with inline SVG bar charts. No external
dependencies — everything renders offline.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
from typing import Sequence


# ---------------------------------------------------------------------------
# small numeric / formatting helpers
# ---------------------------------------------------------------------------

def _num(v):
    """Return v as float if numeric & non-zero, else None."""
    if v is None: return None
    try:
        f = float(v)
        return f if f != 0 else None
    except (TypeError, ValueError):
        return None


def _fmt(v, spec=".0f", suffix=""):
    n = _num(v)
    if n is None: return "-"
    try: return f"{n:{spec}}{suffix}"
    except Exception: return f"{n}{suffix}"


def _esc(s):
    return _html.escape("" if s is None else str(s))


# ---------------------------------------------------------------------------
# inline SVG bar chart
# ---------------------------------------------------------------------------

# 12 colors cycling — same palette as the in-app Qt canvas so the report
# matches what the user just saw in the dialog.
_COLORS = ["#3a78d8", "#cc6622", "#1a8a3a", "#a82a82", "#d8a800", "#6a4ac8",
           "#aa3030", "#3a8a8a", "#5a9ad8", "#dc7632", "#2a9a4a", "#b83a92"]


def _svg_bar_chart(title: str, unit: str, points: Sequence[tuple[str, float]],
                    width: int = 760, height: int = 320) -> str:
    """Build an SVG bar chart for one metric.

    points: list of (label, numeric_value). Empty / None values should be
    filtered out before calling.
    """
    if not points:
        return (
            f'<div class="chart-empty"><strong>{_esc(title)}</strong>'
            f'<br><span class="muted">No measured values</span></div>'
        )

    pad_l, pad_r, pad_t, pad_b = 60, 24, 40, 100
    max_v = max(v for _, v in points) * 1.18 or 1.0
    n = len(points)
    avail_w = width - pad_l - pad_r
    bar_w = avail_w / n * 0.72
    gap = avail_w / n * 0.28
    plot_h = height - pad_t - pad_b

    out = [
        f'<div class="chart-block">',
        f'<h3>{_esc(title)} <span class="unit">[{_esc(unit)}]</span></h3>',
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" class="bar-chart">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fafbfc"/>',
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" '
        f'y2="{height - pad_b}" stroke="#999"/>',
        f'<line x1="{pad_l}" y1="{height - pad_b}" '
        f'x2="{width - pad_r}" y2="{height - pad_b}" stroke="#999"/>',
        f'<text x="6" y="{pad_t - 6}" fill="#444" font-size="11">'
        f'{int(max_v)}</text>',
        f'<text x="6" y="{height - pad_b + 14}" fill="#444" font-size="11">0</text>',
        f'<line x1="{pad_l}" y1="{pad_t + plot_h/2}" '
        f'x2="{width - pad_r}" y2="{pad_t + plot_h/2}" '
        f'stroke="#e0e0e0" stroke-dasharray="4 4"/>',
        f'<text x="6" y="{pad_t + plot_h/2 + 4}" fill="#666" font-size="10">'
        f'{int(max_v / 2)}</text>',
    ]

    for i, (lbl, val) in enumerate(points):
        x = pad_l + i * (bar_w + gap) + gap / 2
        bar_h = (val / max_v) * plot_h
        y1 = height - pad_b - bar_h
        col = _COLORS[i % len(_COLORS)]
        out.append(
            f'<rect x="{x:.1f}" y="{y1:.1f}" width="{bar_w:.1f}" '
            f'height="{bar_h:.1f}" fill="{col}" stroke="#333" stroke-width="0.5"/>'
        )
        out.append(
            f'<text x="{x + bar_w/2:.1f}" y="{y1 - 6:.1f}" '
            f'text-anchor="middle" fill="#111" font-size="11" '
            f'font-weight="bold">{val:.1f}</text>'
        )
        for li, part in enumerate(str(lbl).split(" | ")):
            ty = height - pad_b + 14 + li * 12
            out.append(
                f'<text x="{x + bar_w/2:.1f}" y="{ty:.1f}" '
                f'text-anchor="middle" fill="#222" font-size="10">'
                f'{_esc(part)}</text>'
            )

    out.append('</svg></div>')
    return "".join(out)


# ---------------------------------------------------------------------------
# main report builder
# ---------------------------------------------------------------------------

# (db field, unit, header)
_METRICS = [
    ("yield_MPa",          "MPa", "YS XY — Yield Strength (in-plane)"),
    ("yield_z_MPa",        "MPa", "YS Z — Yield Strength (build direction)"),
    ("uts_xy_MPa",         "MPa", "UTS XY — Tensile Strength (in-plane)"),
    ("uts_z_MPa",          "MPa", "UTS Z — Tensile Strength (build direction)"),
    ("elongation_xy_pct",  "%",   "Elongation XY"),
    ("elongation_z_pct",   "%",   "Elongation Z"),
    ("hardness_HV",        "HV",  "Hardness (Vickers)"),
    ("surface_ra_hi",      "μm",  "Surface Roughness Ra (upper bound, side wall as-built)"),
]


def _vendor_short_label(vendor_key: str, vd: dict) -> str:
    """Compact label for chart x-axis — uses ' | ' as a line-break sentinel
    consumed by _svg_bar_chart."""
    manuf = (vd.get("manufacturer") or "?")[:14]
    machine = (vd.get("machine") or "")[:14]
    post = (vd.get("post_treatment") or "") or ""
    layer = vd.get("layer_thickness_um")
    line2 = (machine + (f" {layer}μm" if layer else "")).strip() or "-"
    line3 = post[:14] if post.lower() not in ("as-built", "") else ""
    parts = [manuf, line2]
    if line3: parts.append(f"({line3})")
    return " | ".join(parts)


def _composition_rows(comp) -> str:
    if not comp: return '<tr><td colspan="2" class="muted">(not reported)</td></tr>'
    rows = []
    for c in comp:
        if isinstance(c, (list, tuple)) and len(c) >= 2:
            el, pct = c[0], c[1]
        elif isinstance(c, dict):
            el, pct = c.get("element", "?"), c.get("pct", "-")
        else:
            el, pct = str(c), "-"
        rows.append(
            f"<tr><td class='el'>{_esc(el)}</td><td>{_esc(pct)}</td></tr>")
    return "".join(rows)


def _ht_rows(ht: dict) -> str:
    if not ht: return '<tr><td colspan="7" class="muted">(no heat-treatment data)</td></tr>'
    rows = []
    for ht_key, hd in ht.items():
        if not isinstance(hd, dict): continue
        ra_lo = hd.get("surface_ra_lo")
        ra_hi = hd.get("surface_ra_hi")
        if ra_lo is not None and ra_hi is not None and ra_lo != ra_hi:
            ra = f"{ra_lo}~{ra_hi}"
        else:
            ra = _fmt(hd.get("surface_ra_um") or ra_lo or ra_hi)
        rows.append(
            "<tr>"
            f"<td><b>{_esc(ht_key)}</b></td>"
            f"<td>{_fmt(hd.get('uts'), '.0f')}</td>"
            f"<td>{_fmt(hd.get('ys'),  '.0f')}</td>"
            f"<td>{_fmt(hd.get('elong'), '.1f')}</td>"
            f"<td>{_fmt(hd.get('hardness_HV'), '.0f')}</td>"
            f"<td>{ra}</td>"
            f"<td class='muted small'>{_esc(hd.get('notes') or '-')}</td>"
            "</tr>"
        )
    return "".join(rows) or '<tr><td colspan="7" class="muted">(none)</td></tr>'


def _vendor_detail_rows(selected: list[tuple[str, dict]]) -> str:
    rows = []
    for vk, vd in selected:
        tds = vd.get("tds_link")
        tds_html = (
            f'<a href="{_esc(tds)}" target="_blank">TDS</a>'
            if tds else '<span class="muted">-</span>')
        elong_xy = vd.get("elongation_xy_pct")
        elong_z = vd.get("elongation_z_pct")
        if elong_xy is not None and elong_z is not None and elong_xy != elong_z:
            elong = f"{_fmt(elong_xy, '.1f')} / {_fmt(elong_z, '.1f')}"
        else:
            elong = _fmt(elong_xy if elong_xy is not None else elong_z, '.1f')
        ra_lo, ra_hi = vd.get("surface_ra_lo"), vd.get("surface_ra_hi")
        if ra_lo is not None and ra_hi is not None and ra_lo != ra_hi:
            ra = f"{ra_lo}~{ra_hi}"
        else:
            ra = _fmt(ra_lo if ra_lo is not None else ra_hi)
        rows.append(
            "<tr>"
            f"<td>{_esc(vd.get('manufacturer') or '-')}</td>"
            f"<td>{_esc(vd.get('machine') or '-')}</td>"
            f"<td>{_esc(vd.get('post_treatment') or '-')}</td>"
            f"<td>{_fmt(vd.get('layer_thickness_um'), '.0f')}</td>"
            f"<td>{_fmt(vd.get('yield_MPa'), '.0f')}</td>"
            f"<td>{_fmt(vd.get('yield_z_MPa'), '.0f')}</td>"
            f"<td>{_fmt(vd.get('uts_xy_MPa'), '.0f')}</td>"
            f"<td>{_fmt(vd.get('uts_z_MPa'), '.0f')}</td>"
            f"<td>{elong}</td>"
            f"<td>{_fmt(vd.get('hardness_HV'), '.0f')}</td>"
            f"<td>{ra}</td>"
            f"<td>{tds_html}</td>"
            "</tr>"
        )
    return "".join(rows)


def build_report_html(material_name: str, props: dict,
                       selected: list[tuple[str, dict]]) -> str:
    """Render the full HTML report.

    selected: list of (vendor_key, vendor_data_dict) — the checked rows.
    """
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    charts = []
    for field, unit, header in _METRICS:
        points = []
        for vk, vd in selected:
            n = _num(vd.get(field))
            if n is None: continue
            points.append((_vendor_short_label(vk, vd), n))
        charts.append(_svg_bar_chart(header, unit, points))

    css = """
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
    """

    physical = [
        ("Density",            _fmt(props.get("density"), ".3f"),   "g/cm³"),
        ("Melting point",      _fmt(props.get("melt"), ".0f"),      "°C"),
        ("Magnetic",           _esc(props.get("magnetic") or "-"),  ""),
        ("Young's modulus E",  _fmt(props.get("E"), ".0f"),         "GPa"),
        ("Poisson ratio",      _fmt(props.get("poisson"), ".3f"),   ""),
        ("Thermal cond.",      _fmt(props.get("thermal_k"), ".1f"), "W/m·K"),
        ("Specific heat Cp",   _fmt(props.get("cp"), ".0f"),        "J/kg·K"),
        ("Thermal expansion",  _fmt(props.get("cte"), ".1f"),       "1e-6/K"),
    ]
    props_html = "".join(
        f'<div><b>{_esc(lbl)}</b>: {v} <span class="muted">{_esc(u)}</span></div>'
        for lbl, v, u in physical
    )

    refs = props.get("ref_urls") or []
    refs_html = "".join(
        f'<li><a href="{_esc(u)}" target="_blank">{_esc(label)}</a></li>'
        for entry in refs
        if isinstance(entry, (list, tuple)) and len(entry) >= 2
        for label, u in [entry[:2]]
    ) or '<li class="muted">(none)</li>'

    selected_table_rows = _vendor_detail_rows(selected)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MDS Report — {_esc(material_name)}</title>
<style>{css}</style>
</head>
<body>

<h1>MDS Comparison Report</h1>
<div class="meta">
  <strong>Material:</strong> {_esc(material_name)}
  &nbsp;·&nbsp; <strong>Category:</strong> {_esc(props.get("category") or "-")}
  &nbsp;·&nbsp; <strong>Generated:</strong> {now}
  &nbsp;·&nbsp; <strong>Selected entries:</strong> {len(selected)}
</div>

<div class="section">
  <h2>Basic Physical &amp; Thermal Properties</h2>
  <div class="props-grid">{props_html}</div>
</div>

<div class="section">
  <h2>Chemical Composition (wt%)</h2>
  <table>
    <thead><tr><th style="width: 30%">Element</th><th>wt %</th></tr></thead>
    <tbody>{_composition_rows(props.get("composition"))}</tbody>
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
    <tbody>{_ht_rows(props.get("heat_treatments") or {})}</tbody>
  </table>
</div>

<div class="section">
  <h2>Selected Vendor Entries ({len(selected)})</h2>
  <table>
    <thead><tr>
      <th>Manufacturer</th><th>Machine</th><th>Post</th><th>Layer<br>μm</th>
      <th>YS XY<br>MPa</th><th>YS Z<br>MPa</th>
      <th>UTS XY<br>MPa</th><th>UTS Z<br>MPa</th>
      <th>Elong<br>XY / Z %</th><th>Hardness<br>HV</th><th>Ra<br>μm</th>
      <th>TDS</th>
    </tr></thead>
    <tbody>{selected_table_rows}</tbody>
  </table>
</div>

<div class="section">
  <h2>Per-Vendor Comparison Charts</h2>
  {''.join(charts)}
</div>

<div class="section">
  <h2>References</h2>
  <ul>{refs_html}</ul>
</div>

<div class="footer">
  Generated by MDS Viewer · {now}
</div>

</body>
</html>
"""
