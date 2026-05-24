"""Phase 3 — Extract structured records from cached TDS files.

PDF strategy:
  1. Convert via pdftotext -layout -enc UTF-8
  2. If text size < 1 KB ("near empty"), assume positioned-glyph layout
     → write entry to extraction_misses.json so Claude/Agent can re-process
     via PyMuPDF rendering. See SKILL.md "Agent fallback".

HTML strategy:
  - EOS HTML data sheet pages have a regular table structure parsed inline
    (yield/UTS/elongation per Vertical|Horizontal row, plus Hardness/Ra).

Output: _tds_workspace/extracted.json keyed by tds_url → list of records.
Schema documented in SKILL.md.

Usage:
  python 03_extract.py [--vendor ...]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


def _num(s):
    if s is None: return None
    s = str(s).strip()
    if s in ("", "-", "—", "n/a", "N/A"): return None
    m = re.match(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_eos_html(html: str) -> list[dict]:
    """Parse one EOS data-sheet HTML into records.

    Looks for the per-(heat treatment × layer) table:
      "<state> EN ISO 6892-1 Room Temperature | <layer> µm"
      "Yield Strength [MPa]  Tensile Strength [MPa]  Elongation at Break A [%]"
      "Vertical    Y  U  E  ..."
      "Horizontal  Y  U  E  ..."
    """
    txt = _lib.html_to_text(html)
    txt = re.sub(r"\s+", " ", txt)

    records: list[dict] = []
    pattern = re.compile(
        r"(As Manufactured|Solution[- ]Annealed|Stress[- ]Relieved|"
        r"Heat[- ]Treated|Hot Isostatic Press[a-z ]*|HIP|Aged|H?\d{3,4}|"
        r"Annealed|Solution Heat Treated|T6)"
        r".{0,80}?Room Temperature\s*\|\s*(\d{2,3})\s*µm"
        r".{0,200}?Yield Strength.{0,30}Tensile Strength.{0,30}Elongation",
        re.IGNORECASE)

    for m in pattern.finditer(txt):
        ht = m.group(1).strip()
        layer = int(m.group(2))
        tail = txt[m.end():m.end() + 600]

        def row(direction):
            r = re.search(direction + r"\s+(-?[\d.]+|-)\s+(-?[\d.]+|-)\s+"
                          r"(-?[\d.]+|-)", tail, re.IGNORECASE)
            if not r: return (None, None, None)
            return tuple(_num(g) for g in r.groups())

        v_ys, v_uts, v_e = row("Vertical")
        h_ys, h_uts, h_e = row("Horizontal")
        if not any([v_ys, v_uts, v_e, h_ys, h_uts, h_e]): continue

        records.append({
            "post_treatment":    canonical_pt(ht),
            "layer_thickness_um": layer,
            "yield_xy_MPa":      h_ys,
            "yield_z_MPa":       v_ys,
            "uts_xy_MPa":        h_uts,
            "uts_z_MPa":         v_uts,
            "elongation_xy_pct": h_e,
            "elongation_z_pct":  v_e,
            "hardness_HV":       None,
            "surface_ra_lo":     None,
            "surface_ra_hi":     None,
        })

    # Hardness HV + Surface Ra (apply to all records of this URL)
    hv = ra_lo = ra_hi = None
    hv_m = re.search(r"Hardness.{0,200}?HV\d*[^0-9]{0,40}(\d+(?:\.\d+)?)",
                      txt, re.IGNORECASE)
    if hv_m: hv = _num(hv_m.group(1))
    ra_m = re.search(
        r"Surface Roughness.{0,400}?Ra\s*\[µm\][^0-9]{0,40}(\d+(?:\.\d+)?)"
        r"(?:[^0-9]{0,40}(\d+(?:\.\d+)?))?", txt, re.IGNORECASE)
    if ra_m:
        ra_lo = _num(ra_m.group(1))
        ra_hi = _num(ra_m.group(2)) if ra_m.group(2) else ra_lo

    for r in records:
        if hv is not None:    r["hardness_HV"] = hv
        if ra_lo is not None: r["surface_ra_lo"] = ra_lo
        if ra_hi is not None: r["surface_ra_hi"] = ra_hi

    return records


def canonical_pt(label: str) -> str:
    p = (label or "").lower().strip()
    if "as manufactured" in p or "as-built" in p or p == "as built": return "as-built"
    if "h900"  in p: return "H900"
    if "h1025" in p: return "H1025"
    if "h1150" in p: return "H1150"
    if "hip" in p and "age" in p: return "HT_HIP_age"
    if "hip" in p: return "HT_HIP"
    if "solution" in p and ("age" in p or "aged" in p): return "solution+age"
    if "t6" in p: return "T6"
    if "stress" in p: return "stress-relieved"
    if "solution-anneal" in p or "solution anneal" in p: return "solution-annealed"
    if "anneal" in p: return "annealed"
    if "aged" in p or "aging" in p: return "aged"
    if "heat-treated" in p or "heat treat" in p: return "heat-treated"
    return p


def extract_one(vendor: str, url: str, entry: dict) -> dict:
    """Run the appropriate parser for one cached file. Returns
    {records: [...], misses: bool, reason: str|None}.
    """
    if entry.get("error") or not entry.get("path"):
        return {"records": [], "misses": False, "reason": "no_local_file"}
    path = Path(entry["path"])
    if path.suffix.lower() == ".html" and vendor == "eos":
        try:
            html = path.read_text(encoding="utf-8", errors="replace")
            records = parse_eos_html(html)
            return {"records": records, "misses": False, "reason": None}
        except Exception as e:
            return {"records": [], "misses": True, "reason": str(e)}
    if path.suffix.lower() == ".pdf":
        txt_path = path.with_suffix(".txt")
        if not txt_path.exists() or txt_path.stat().st_size == 0:
            if not _lib.pdftotext(str(path), str(txt_path)):
                return {"records": [], "misses": True,
                        "reason": "pdftotext_unavailable"}
        size = txt_path.stat().st_size if txt_path.exists() else 0
        # Any PDF below this size has near-empty text; defer to Agent.
        if size < 1024:
            return {"records": [], "misses": True,
                    "reason": f"pdf_text_too_sparse ({size} B)"}
        # All vendor-specific PDF parsers are intentionally deferred to Agent
        # in this skill's first revision — see "Agent fallback" in SKILL.md.
        # That keeps the skill robust against TDS layout drift.
        return {"records": [], "misses": True,
                "reason": "pdf_parser_deferred_to_agent",
                "txt_path": str(txt_path)}
    return {"records": [], "misses": True, "reason": "unsupported_format"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", default=None)
    args = ap.parse_args()

    _lib.ensure_workspace()
    discovery = _lib.load_json(_lib.DISCOVERY_PATH, {})
    manifest = _lib.load_json(_lib.MANIFEST_PATH, {})
    extracted = _lib.load_json(_lib.EXTRACTED_PATH, {})
    misses: list[dict] = []

    for vendor, cats in discovery.items():
        if args.vendor and vendor != args.vendor: continue
        urls = {ref["tds_url"]: ref
                for info in cats.values() for ref in info.get("tds_urls", [])
                if ref.get("kind") != "material_page_followup"}
        print(f"[{vendor}] {len(urls)} URL(s) to extract...")
        ok = miss = 0
        for url, ref in urls.items():
            mentry = manifest.get(url, {})
            res = extract_one(vendor, url, mentry)
            if res["records"]:
                extracted[url] = {
                    "vendor": vendor,
                    "catalog_slug": ref.get("catalog_slug"),
                    "material_hint": ref.get("material_hint"),
                    "records": res["records"],
                }
                ok += 1
            elif res["misses"]:
                misses.append({
                    "vendor": vendor, "url": url, "reason": res["reason"],
                    "local_path": mentry.get("path"),
                    "txt_path": res.get("txt_path"),
                    "material_hint": ref.get("material_hint"),
                })
                miss += 1
        print(f"   ok={ok}  needs-agent={miss}")

    _lib.save_json(_lib.EXTRACTED_PATH, extracted)
    _lib.save_json(_lib.MISSES_PATH, misses)
    if misses:
        _lib.append_anomaly(
            f"{len(misses)} TDS file(s) need Agent extraction — "
            f"see _tds_workspace/extraction_misses.json")


if __name__ == "__main__":
    main()
