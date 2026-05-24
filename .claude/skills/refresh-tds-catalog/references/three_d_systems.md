# 3D Systems catalog & TDS format notes

## Catalog page — no usable crawl path

The discovery situation for 3D Systems is unusually hostile:

| Endpoint | urllib | WebFetch | Notes |
|---|---|---|---|
| `/material-finder?type[0]=Metal` | 403 | 403 | bot-blocked AND JS-rendered |
| `/material-finder?type[0]=<sub>` | 403 | 403 | same |
| `/materials/metal` | 403 | 200 | lists 8 category names but no TDS URLs |
| `/materials/<slug>` | 403 | 200 if slug exists | most LaserForm slugs 404 |
| `/sitemap.xml?page=1..4` | 403 | 200 | does NOT include metal materials |
| `/sites/default/files/*.pdf` (TDS) | 403 | 200 | PDFs themselves are fetchable via WebFetch |

So neither catalog crawling nor the sitemap reveals which TDS PDFs exist —
3D Systems intentionally hides this surface from bots. The pragmatic
workaround the skill uses:

1. Keep a **known-good TDS URL list** in `assets/catalogs.json` under
   `vendors.three_d_systems.fallback_tds_urls`. The discover script appends
   any URLs from that list when the catalog crawl returns fewer hits than
   expected.
2. Periodically (every 1-2 quarters) a maintainer should manually visit
   `https://www.3dsystems.com/material-finder?type[0]=Metal` in a real
   browser, copy out any new material PDFs, and edit `assets/catalogs.json`.
3. The download script routes any 3D Systems URL through WebFetch instead
   of urllib (WebFetch passes Cloudflare on the PDF endpoints, even though
   it doesn't pass on the catalog page).

## TDS PDFs

URL shape: `https://www.3dsystems.com/sites/default/files/<YYYY>-<MM>/3d-systems-<series>-<MATERIAL>-<form>-<rev>.pdf`

Series:
- **LaserForm**: older 2017-2023 documents, often A4 vs Letter variants
- **Certified**: newer 2021-2024 documents in "letter-us" format

All PDF downloads return HTTP 403 from urllib (bot protection). WebFetch
bypasses this. The skill's `02_download.py` routes 3D Systems URLs through
the `needs_webfetch.json` outbox.

## PDF parsing

`pdftotext -layout` extracts the table cleanly. Mechanical Properties row
layout (one column per condition):

```
MEASUREMENT                CONDITION        NHT      SR       FA
Ultimate strength MPa     ASTM E8M
  Horizontal — XY                           710 ±50  740 ±50  670 ±50
  Vertical — Z                              630 ±50  660 ±50  600 ±50
Yield strength MPa        ASTM E8M
  Horizontal — XY                           590 ±50  610 ±60  440 ±60
  Vertical — Z                              520 ±50  530 ±60  410 ±60
Elongation at break (%)   ASTM E8M
  Horizontal — XY                           37 ±5    37 ±5    44 ±5
  Vertical — Z                              41 ±5    34 ±5    42 ±5
Hardness Vickers HV30     ISO 6507-1        227 ±10  230 ±10  200 ±10
```

NHT = Non-Heat-Treated → "as-built"; SR = Stress-Relieved; FA = Full-Annealed
(or HT/H900/etc. depending on material). Take the MEAN only (ignore ± sd).

Layer thickness is typically 30 µm for 3DS LaserForm (DMP Flex / ProX 200).
Newer "letter" format PDFs sometimes report H+V averaged values rather than
splitting — record the same value in both `_xy_` and `_z_` fields.

3DS LaserForm sheets do **not** report sidewall Ra in the schema we use
(`surface_ra_*` stays null).
