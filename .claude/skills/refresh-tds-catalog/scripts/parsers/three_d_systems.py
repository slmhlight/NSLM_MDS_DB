"""3D Systems material-finder catalog parser.

The /material-finder page is a JS-rendered React/Vue app — the raw HTML
contains the app shell but not the list of materials. Two-stage workaround:

  1. The orchestrator detects 0 hits and falls back to the WebFetch tool
     (which executes JS) to get a rendered DOM, then re-runs this parser.
  2. As a manual backstop, this parser also recognises /materials/<slug>
     follow-up pages and the LaserForm / Certified PDF URL pattern, so
     if you point it at a fully-rendered HTML it still works.

PDF downloads themselves are HTTP-403 blocked from urllib — the download
phase routes 3D Systems URLs through WebFetch automatically.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin


_PDF_HREF_RE = re.compile(
    r'href=["\'](?P<href>(?:https?://(?:www\.)?3dsystems\.com)?'
    r'/sites/default/files/[^"\'#]+\.pdf)["\']',
    re.IGNORECASE)

_MATERIAL_PAGE_RE = re.compile(
    r'href=["\'](?P<href>(?:https?://(?:www\.)?3dsystems\.com)?'
    r'/materials/[a-z0-9\-]+)["\']',
    re.IGNORECASE)


def discover_from_catalog(catalog_url: str, html: str) -> list[dict]:
    """The material finder lists per-material pages; per-material pages then
    link to the actual PDF TDS. This function returns BOTH direct-PDF links
    found on the catalog and material-page URLs that need a follow-up fetch.
    The orchestrator handles the two-step lookup.
    """
    found: list[dict] = []
    seen: set[str] = set()

    for m in _PDF_HREF_RE.finditer(html):
        href = m.group("href")
        full = urljoin("https://www.3dsystems.com", href)
        if full in seen: continue
        seen.add(full)
        tail = full.rsplit("/", 1)[-1]
        if not re.search(r"laserform|certified|mds|datasheet",
                          tail, re.IGNORECASE):
            continue
        material_hint = re.sub(
            r"^3d-systems-laserform-|^3d-systems-certified-|\.pdf.*$|"
            r"-datasheet.*$|-mds.*$",
            "", tail, flags=re.IGNORECASE)
        material_hint = re.sub(r"[-_]+", " ", material_hint).strip()
        found.append({
            "tds_url":       full,
            "kind":          "laserform_pdf",
            "catalog_slug":  "material-finder",
            "material_hint": material_hint,
        })

    # If no direct PDFs surfaced, return per-material page URLs for the
    # orchestrator to follow up on.
    if not found:
        for m in _MATERIAL_PAGE_RE.finditer(html):
            full = urljoin("https://www.3dsystems.com", m.group("href"))
            if full in seen: continue
            seen.add(full)
            found.append({
                "tds_url":       full,
                "kind":          "material_page_followup",
                "catalog_slug":  "material-finder",
                "material_hint": full.rsplit("/", 1)[-1],
            })

    return found
