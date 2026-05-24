"""Nikon SLM Solutions catalog parser.

Material category pages (e.g. /materials/aluminium/) list machines + MDS PDF
download buttons. PDFs live at /wp-content/uploads/<year>/<MM>/MDS_<MAT>_<DATE>_EN.pdf
or /wp-content/uploads/<year>/<MM>/mds<NNNN>.pdf.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin


_HREF_RE = re.compile(
    r'href=["\'](?P<href>(?:https?://nikon-slm-solutions\.com)?'
    r'/wp-content/uploads/[^"\'#]+\.pdf)["\']',
    re.IGNORECASE)


def discover_from_catalog(catalog_url: str, html: str) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()
    cat_slug = catalog_url.rstrip("/").rsplit("/", 1)[-1]

    for m in _HREF_RE.finditer(html):
        href = m.group("href")
        full = urljoin("https://nikon-slm-solutions.com", href)
        if full in seen: continue
        seen.add(full)
        tail = full.rsplit("/", 1)[-1]
        if not re.search(r"mds|datasheet|material.?data",
                          tail, re.IGNORECASE):
            continue
        material_hint = re.sub(
            r"^MDS_|^mds|_\d{4}-\d{2}(?:\.\d+)?(?:_\d+)?_EN.*$|\.pdf$",
            "", tail, flags=re.IGNORECASE).replace("_", " ").strip()
        found.append({
            "tds_url":       full,
            "kind":          "mds_pdf",
            "catalog_slug":  cat_slug,
            "material_hint": material_hint or cat_slug,
        })
    return found
