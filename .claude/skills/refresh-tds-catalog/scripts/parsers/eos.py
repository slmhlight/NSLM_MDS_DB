"""EOS catalog + TDS parser.

Catalog landing pages (e.g. /metal-solutions/metal-materials/stainless-steel)
list materials. Each material card links to per-(material, machine, layer) data
sheet pages under /metal-solutions/data-sheets/ — these are the actual TDS
HTML pages with mechanical-property tables. Some materials additionally have
PDF MDS files under /var/assets/05-datasheet-images/Assets_MDS_Metal/.

Discovery strategy:
  1. Fetch each catalog category page
  2. Find anchor hrefs matching /metal-solutions/data-sheets/...
     (these are the per-combo PDS pages)
  3. Also surface /var/assets/.../Material_DataSheet_*.pdf links
  4. Return (material_hint, tds_url) pairs
"""
from __future__ import annotations

import re
from urllib.parse import urljoin


_HREF_RE = re.compile(
    r'href=["\'](?P<href>(?:https?://www\.eos\.info)?'
    r'/('
    # Per-(material × machine × layer) HTML data sheet pages
    r'metal-solutions/data-sheets/[^"\'#]+'
    # Per-material aggregated HTML MDS pages
    r'|metal-solutions/metal-materials/data-sheets/[^"\'#]+'
    # PDF MDS files — observed paths use both /var/assets/ and bare /
    r'|(?:var/assets/)?(?:05-)?datasheet-images/[^"\'#]*'
        r'(?:Material_DataSheet|MDS)[^"\'#]*\.pdf'
    r'))["\']',
    re.IGNORECASE)


def discover_from_catalog(catalog_url: str, html: str) -> list[dict]:
    """Return list of {tds_url, kind, material_hint} from one EOS catalog page.

    `kind` is one of 'pds_html' (per-combo HTML data sheet) or 'mds_pdf'.
    `material_hint` is derived from the catalog URL slug ('nickel-alloys',
    'stainless-steel', ...) and the TDS URL slug — enough to route the result
    later but not authoritative.
    """
    found: list[dict] = []
    seen: set[str] = set()
    cat_slug = catalog_url.rstrip("/").rsplit("/", 1)[-1]

    for m in _HREF_RE.finditer(html):
        href = m.group("href")
        full = urljoin("https://www.eos.info", href)
        # Strip query strings except the ?v= cache-buster on PDFs
        clean = re.sub(r"#.*$", "", full)
        if clean in seen: continue
        seen.add(clean)

        # EOS aggregator page lists every (material × machine) combo via
        # query-string ID; the per-combo PDS pages already cover those so
        # we skip the aggregator to avoid duplicates and noisy "list page"
        # responses that aren't real TDS docs.
        if "all-processes-and-materials" in clean: continue

        if clean.lower().endswith(".pdf"):
            kind = "mds_pdf"
        elif "/data-sheets/mds-" in clean:
            kind = "mds_html"          # per-material aggregated HTML page
        elif "/data-sheets/" in clean:
            kind = "pds_html"          # per-(material × machine × layer)
        else:
            continue

        # Pull a material hint from the URL slug
        tail = clean.rsplit("/", 1)[-1]
        material_hint = re.sub(
            r"^pds-eos-|^Material_DataSheet_EOS_|\.pdf.*$|_en$", "",
            tail, flags=re.IGNORECASE)
        material_hint = re.sub(r"[-_]+", " ", material_hint).strip()

        found.append({
            "tds_url":       clean,
            "kind":          kind,
            "catalog_slug":  cat_slug,
            "material_hint": material_hint,
        })

    return found
