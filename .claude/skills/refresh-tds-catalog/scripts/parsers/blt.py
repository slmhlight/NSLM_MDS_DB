"""BLT (Bright Laser Technologies, Xi'an) catalog + TDS parser.

BLT is the exception in this skill: their per-material pages don't link
to a downloadable PDF TDS — the actual PDF is gated behind a contact
form. Mechanical/physical property values are baked into a per-material
SUMMARY IMAGE embedded on the powder catalog page (rendered chart, not
text). The skill extracts them via vision OCR.

URL pattern
-----------
Catalog landing:   https://www.xa-blt.com/en/powders/
Per-powder page:   https://www.xa-blt.com/en/powder/<slug>/
Summary image:     https://www.xa-blt.com/en/wp-content/uploads/2023/05/
                       <Slug>_2-<W>x<H>.png         (sized variants for srcset)
                       <Slug>_2.png                  (original, ~3-5 MB)
                   The 1024-wide variant is the sweet spot for vision OCR.

Both image and HTML fetches require a browser User-Agent and a Referer
header — bare urllib requests get 404 from the WordPress install.

Discovery
---------
The catalog page is plain HTML with <a href="/en/powder/<slug>/"> links
for every powder. Filter for hrefs matching that pattern.

Property image URL
------------------
On the powder page, the chart image's HTML looks like:
    <img src="...wp-content/uploads/2023/05/<Slug>_2-1024x807.png" srcset="...">
The base name is "<Slug>_2" — the "_2" suffix is BLT's per-page index.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin


BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": ("text/html,image/avif,image/webp,image/apng,image/svg+xml,"
                "image/*,*/*;q=0.8"),
    "Referer": "https://www.xa-blt.com/en/",
}


_POWDER_HREF_RE = re.compile(
    r'href=["\'](?:https?://www\.xa-blt\.com)?(?P<href>/en/powder/[^"\'#]+/?)["\']',
    re.IGNORECASE)


def discover_from_catalog(catalog_url: str, html: str) -> list[dict]:
    """Return list of {tds_url, kind, material_hint} for BLT powders.

    `kind` is always 'blt_page' here — the value extraction is then a
    separate step (download property image + vision OCR), not a direct
    PDF/HTML parse.
    """
    found: list[dict] = []
    seen: set[str] = set()
    for m in _POWDER_HREF_RE.finditer(html):
        href = m.group("href")
        full = urljoin("https://www.xa-blt.com", href)
        # The catalog page itself uses /en/powders/ — skip self-links.
        if "/en/powders/" in full and full.rstrip("/").endswith("/powders"):
            continue
        if full in seen:
            continue
        seen.add(full)
        slug = full.rstrip("/").rsplit("/", 1)[-1]
        found.append({
            "tds_url":       full,
            "kind":          "blt_page",
            "material_hint": slug,
        })
    return found


# Image-name patterns we want to SKIP when extracting the property image
# (site decoration on every powder page).
_SKIP_IMG_RE = re.compile(
    r"(POWDER|nav_|banner|Company_|aerospace|Medical|EVENT|MEDIA|"
    r"automotive|aviation|engine|placeholder|logo|icon)",
    re.IGNORECASE)

_IMG_URL_RE = re.compile(
    r"https://www\.xa-blt\.com/en/?/?wp-content/uploads/\d{4}/\d{2}/"
    r"[^\"\s'>]+\.(?:png|jpg|jpeg)",
    re.IGNORECASE)


def find_property_image_url(page_url: str, html: str,
                             prefer_width: int = 1024) -> str | None:
    """Pick the per-material property chart image URL on a powder page.

    Heuristic:
      1. Collect every wp-content/uploads/*.png URL on the page
      2. Drop generic site decoration (POWDER banner, nav, etc.)
      3. Group by base filename (strip -WxH suffix); pick highest-res
         in each group
      4. Prefer the group whose base name contains the page slug
      5. Return the variant nearest to `prefer_width` for OCR speed
    """
    candidates = set(_IMG_URL_RE.findall(html))
    real = [u for u in candidates if not _SKIP_IMG_RE.search(u)]
    if not real:
        return None

    by_base: dict[str, tuple[str, int]] = {}
    for u in real:
        m = re.search(r"(.+)-(\d+)x(\d+)\.(png|jpg|jpeg)$", u, re.IGNORECASE)
        if m:
            base, w = m.group(1), int(m.group(2))
        else:
            base, w = u.rsplit(".", 1)[0], 0
        cur = by_base.get(base)
        if cur is None or w > cur[1]:
            by_base[base] = (u, w)

    slug = page_url.rstrip("/").rsplit("/", 1)[-1].lower().replace("-", "")

    def score(item):
        u, w = item
        fname = u.rsplit("/", 1)[-1].lower().replace("-", "").replace("_", "")
        return (slug in fname, w)

    best_url, best_w = max(by_base.values(), key=score)

    # Swap to the preferred-width variant if it exists.
    m = re.search(r"-(\d+)x(\d+)\.(png|jpg|jpeg)$", best_url, re.IGNORECASE)
    if m:
        w, h, ext = int(m.group(1)), int(m.group(2)), m.group(3)
        if w >= prefer_width:
            target_w = prefer_width
            target_h = int(h * target_w / w)
            return re.sub(r"-\d+x\d+\.(png|jpg|jpeg)$",
                            f"-{target_w}x{target_h}.{ext}",
                            best_url)
    return best_url


# -------------------------------------------------------------------------
# Vendor-entry building blocks — used by 03_extract.py after vision OCR
# -------------------------------------------------------------------------

MANUFACTURER = "BLT"
MACHINE      = "BLT (any)"
LAYER_UM     = 30  # BLT publishes one TDS across their S-series machines


def vendor_key(post_treatment: str) -> str:
    return f"{MANUFACTURER} [{MACHINE}] @ {post_treatment} ({LAYER_UM}μm)"


def build_vendor_entry(*,
                       slug: str,
                       post: str,
                       tensile_range: tuple[int, int] | None,
                       yield_range:   tuple[int, int] | None,
                       elong_range:   tuple[float, float] | None,
                       hardness_HRC:  tuple[int, int] | None = None,
                       flowability:   str | None = None,
                       apparent_density_g_cm3: float | None = None,
                       sphericity_min: float | None = None,
                       oxygen_ppm_max: int | None = None,
                       ) -> dict:
    """Construct one BLT vendor entry from vision-OCR'd values.

    Ranges are converted to midpoint for the standard mechanical fields;
    the raw lo-hi pair is preserved under ``_value_ranges`` so a future
    UI can show ranges natively.
    """
    def _mid(rng):
        return None if rng is None else round((rng[0] + rng[1]) / 2)

    hv = None
    if hardness_HRC is not None:
        # ASTM E140 linearised for HRC 50-58 — used for 420 stainless.
        hv = int(round(17.9 * (sum(hardness_HRC) / 2) - 379))

    return {
        "manufacturer":       MANUFACTURER,
        "machine":            MACHINE,
        "layer_thickness_um": LAYER_UM,
        "post_treatment":     post,
        "tds_link":           f"https://www.xa-blt.com/en/powder/{slug}/",
        "_tds_verified":      True,
        "_source_note": (
            f"BLT vision-OCR from {slug} property chart. "
            f"Single values are midpoints of BLT's published ranges."
        ),
        "_value_ranges": {
            "tensile_MPa":    list(tensile_range)  if tensile_range else None,
            "yield_MPa":      list(yield_range)    if yield_range   else None,
            "elongation_pct": list(elong_range)    if elong_range   else None,
            "hardness_HRC":   list(hardness_HRC)   if hardness_HRC  else None,
        },
        "_powder_properties": {
            "flowability":            flowability,
            "apparent_density_g_cm3": apparent_density_g_cm3,
            "sphericity_min":         sphericity_min,
            "oxygen_ppm_max":         oxygen_ppm_max,
            "particle_size_cuts_um":  [(0, 20), (15, 53), (53, 105), (75, 180)],
        },
        # BLT TDS does not split XY/Z — use same midpoint both ways.
        "yield_MPa":         _mid(yield_range),
        "yield_z_MPa":       _mid(yield_range),
        "uts_xy_MPa":        _mid(tensile_range),
        "uts_z_MPa":         _mid(tensile_range),
        "elongation_pct":    _mid(elong_range),
        "elongation_xy_pct": _mid(elong_range),
        "elongation_z_pct":  _mid(elong_range),
        "hardness_HV":       hv,
        "surface_ra_hi":     None,
        "surface_ra_lo":     None,
    }
