# BLT (Bright Laser Technologies, Xi'an) — TDS extraction notes

BLT publishes powder catalogue pages at `https://www.xa-blt.com/en/powders/`.
Each material has its own page under `/en/powder/<slug>/`. Unlike the other
vendors in this skill, BLT does NOT expose a downloadable PDF — the "PDF
download" button on every page is a JavaScript stub that opens a contact
form. Their actual TDS document is gated.

What's actually accessible: a **rendered summary chart image** embedded in
the page, showing particle-size cuts, flowability, apparent density,
sphericity, oxygen content, and (most usefully) the mechanical property
ranges for printed-and-annealed parts. The skill extracts these via
**vision OCR**.

## Page anatomy

```
https://www.xa-blt.com/en/powder/<slug>/
  ├── powder morphology micrographs (4 SEM images at different size cuts)
  ├── description block ("Good flowability", "In accordance with GB/ASTM
  │    standard chemical composition", "Uniform composition, high purity")
  └── property chart image, baked-in as a single PNG
      └── /wp-content/uploads/2023/05/<Slug>_2-<W>x<H>.png  (srcset variants)
          └── original: <Slug>_2.png  (~3-5 MB, used only if a sized
              variant is unavailable)
```

## URL conventions

| Item | URL |
|---|---|
| Catalog landing | `https://www.xa-blt.com/en/powders/` |
| Powder page     | `https://www.xa-blt.com/en/powder/<slug>/` |
| Property image  | `.../wp-content/uploads/2023/05/<Slug>_2-1024x807.png` |

`<Slug>` in the image filename matches the URL slug but is title-cased and
uses hyphens (e.g. URL slug `ti-6al-4v-grade23` → image basename
`Ti-6Al-4V-Grade23_2`). The `_2` suffix is BLT's per-page image index — the
first image on the page (powder morphology composite) is `_1`, the chart we
want is `_2`.

## Required HTTP headers

Bare urllib / curl-without-headers requests get **HTTP 404** from this
WordPress install. Both HTML and image fetches need:

```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...
Referer:    https://www.xa-blt.com/en/
```

`parsers/blt.py` defines `BROWSER_HEADERS` for re-use.

## What the chart contains

Reading the chart from top to bottom:

| Row | Field | Example value |
|---|---|---|
| 1 | Grade                              | "Inconel 625" |
| 2 | Product Specification (particle size) | "0-20μm" / "15-53μm" / "53-105μm" / "75-180μm" (4 cuts) |
| 3 | Flowability                        | "≤30s" (or "≤40s/50g", "≤22s", "≤80s") |
| 4 | Apparent Density                   | "≥4.1g/cm³" |
| 5 | Sphericity                         | "≥0.8" or "≥0.9" |
| 6 | Oxygen Content                     | "≤200ppm", "≤1300ppm" |
| 7 | Mechanical Properties (Annealing)  | "Tensile strength: 830-910MPa<br>Yield strength: 390-480 MPa<br>Elongation: 30-60%" |

Notes:
- Mechanical values are **always ranges (lo-hi)**, not single points.
- They apply to the **annealed** post-treatment for every powder EXCEPT
  **420 stainless**, where only `Hardness: 50-58HRC` is listed (martensitic
  Q+T condition — record as `hardened`).
- Convert HRC → HV via ASTM E140 linear fit in the HRC 50-58 range:
  `HV ≈ 17.9 × HRC - 379`.
- BLT does not separate XY vs Z values — treat as isotropic (write the
  same midpoint to both fields).

## Storage convention in `material_db.json`

```json
"BLT [BLT (any)] @ annealed (30μm)": {
  "manufacturer": "BLT",
  "machine":      "BLT (any)",
  "layer_thickness_um": 30,
  "post_treatment": "annealed",
  "tds_link": "https://www.xa-blt.com/en/powder/inconel-625/",
  "_tds_verified": true,
  "_source_note": "BLT vision-OCR from <slug> property chart. ...",
  "_value_ranges": {
    "tensile_MPa":    [830, 910],
    "yield_MPa":      [390, 480],
    "elongation_pct": [30, 60]
  },
  "_powder_properties": {
    "flowability": "≤30s",
    "apparent_density_g_cm3": 4.1,
    "sphericity_min": 0.8,
    "oxygen_ppm_max": 200,
    "particle_size_cuts_um": [[0,20], [15,53], [53,105], [75,180]]
  },
  "yield_MPa":         435,    "yield_z_MPa":       435,
  "uts_xy_MPa":        870,    "uts_z_MPa":         870,
  "elongation_pct":    45,
  "elongation_xy_pct": 45,     "elongation_z_pct":  45,
  "hardness_HV":       null,
  "surface_ra_hi":     null,   "surface_ra_lo":     null
}
```

The midpoint in the standard fields keeps existing UI / bar-chart code
unchanged; the lo-hi pair in `_value_ranges` is the authoritative datum.

## Machine identification

BLT sells multiple printers (S210, S310, S400, S510, S600, S800), but the
TDS chart does not specify which machine the values apply to — they are
published as machine-agnostic for the powder grade. The skill records the
machine field as `"BLT (any)"` rather than fabricating a specific model.

## Layer thickness

Same caveat — not stated on the chart. BLT's default LPBF process is 30 μm
across the S-series, so the skill records `30` as the canonical value.
If BLT ever publishes per-machine variants, add additional vendor entries
rather than overwriting.

## Per-powder material mapping (verified 2026-05-24)

| BLT slug | DB material |
|---|---|
| `cp-ti-grade1`                       | `Ti CP Gr1` (new) |
| `ti-6al-4v-grade23`                  | `Ti6Al4V (Gr5, Gr23)` |
| `ti-6-5al-1mo-1v-2zr`                | `TA15 (Ti-6.5Al-1Mo-1V-2Zr)` (new) |
| `ti-6al-2mo-2nb-2zr-2sn-1-5cr`       | `Ti-6Al-2Mo-2Nb-2Zr-2Sn-1.5Cr (BLT)` (new) |
| `hastelloyx`                         | `Hastelloy X (C22)` |
| `inconel-625`                        | `Inconel 625` |
| `inconel-718`                        | `Inconel 718` |
| `alsi10mg`                           | `AlSi10Mg` |
| `alsi7mg`                            | `AlSi7Mg` |
| `316l`                               | `Stainless Steel 316L` |
| `420`                                | `Stainless Steel 420 (martensitic)` (new) |

When `discover_from_catalog()` finds a NEW slug, route it through
`scripts/_material_aliases.py` first. If no alias matches, mark it as a
candidate for `05_seed_new.py` (new material seeding) rather than
auto-creating.

## Refresh discipline

Once a quarter:
1. Crawl `https://www.xa-blt.com/en/powders/` and diff against the table
   above.
2. For any **new powders**: download the property image, OCR, route via
   alias map, create new vendor entries (and a new material if needed).
3. For any **removed powders**: do NOT silently drop the corresponding
   vendor entries — manually inspect first. BLT occasionally reorders the
   catalog without semantic change.
4. For **existing powders**: re-extract the image. If property ranges
   shift by more than ~5 %, BLT issued a new TDS revision — apply as an
   `update_vendor_entry` contribution rather than overwriting in place.
