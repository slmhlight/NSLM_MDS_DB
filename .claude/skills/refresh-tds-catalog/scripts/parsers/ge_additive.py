"""GE Additive (Colibrium) catalog + TDS parser.

Printer pages (e.g. /printers/l-pbf-printers/m2-series-5) list materials with
"Material Data Sheet" download links. The actual files live at
colibriumadditive.com/sites/default/files/M2SERIES5_<MATERIAL>_<POWER>W_CMDS_<DATE>_Rev<X>.pdf
"""
from __future__ import annotations

import re
from urllib.parse import urljoin


_HREF_RE = re.compile(
    r'href=["\'](?P<href>(?:https?://(?:www\.)?colibriumadditive\.com)?'
    r'/sites/default/files/[^"\'#]+\.pdf)["\']',
    re.IGNORECASE)


def discover_from_catalog(catalog_url: str, html: str) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()
    printer_slug = catalog_url.rstrip("/").rsplit("/", 1)[-1]

    for m in _HREF_RE.finditer(html):
        href = m.group("href")
        full = urljoin("https://www.colibriumadditive.com", href)
        # Only TDS-looking PDFs, skip generic brochures
        tail = full.rsplit("/", 1)[-1]
        if not re.search(r"CMDS|MDS|Datasheet|DataSheet|material.?data",
                          tail, re.IGNORECASE):
            continue
        if full in seen: continue
        seen.add(full)
        # Material hint from filename
        material_hint = re.sub(
            r"^(M2SERIES5|MLINE|XLINE2000R|MLAB)_|"
            r"_\d+W?_CMDS.*$|\.pdf$|_RevA.*$",
            "", tail, flags=re.IGNORECASE).replace("_", " ").strip()
        found.append({
            "tds_url":       full,
            "kind":          "cmds_pdf",
            "catalog_slug":  printer_slug,
            "material_hint": material_hint,
        })
    return found
