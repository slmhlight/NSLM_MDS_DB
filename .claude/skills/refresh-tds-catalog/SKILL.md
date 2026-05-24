---
name: refresh-tds-catalog
description: Periodically refresh the MDS Viewer material database from vendor LPBF catalog pages — EOS, GE Additive (Colibrium), 3D Systems, Nikon SLM Solutions. Crawls each manufacturer's material catalog, discovers TDS document URLs, downloads the documents, extracts per-(machine × layer × heat-treatment) mechanical property records, and applies them to data/material_db.json. Use this skill whenever the user asks to refresh / re-sync / update the MDS data from vendor sources, or mentions stale TDS, broken tds_link, missing vendor entries, new vendor machines, or a periodic catalog sync. URLs in assets/catalogs.json can drift over time; always re-discover from the catalog landing pages rather than trusting the cached tds_link inside material_db.json.
---

# refresh-tds-catalog

Goal: keep `data/material_db.json` faithful to whatever each manufacturer publishes today. Don't trust cached `tds_link` URLs — they rot.

The skill has four phases. Each phase has a script in `scripts/`. Run them in order:

1. **Discover** (`scripts/01_discover.py`) — visit each vendor catalog landing page in `assets/catalogs.json`, scrape the list of available materials/machines, and resolve the actual TDS file URL for each combination. Output: `_tds_workspace/discovery.json`.
2. **Download** (`scripts/02_download.py`) — fetch every discovered URL into `_tds_workspace/cache/`. Persist a manifest mapping URL → local path or error. Handles bot-blocked hosts (3D Systems) via the WebFetch tool fallback hint in the report.
3. **Extract** (`scripts/03_extract.py`) — convert PDFs via `pdftotext -layout -enc UTF-8` and parse via vendor-specific routines into a uniform record schema. HTML pages are parsed in-process. PDFs whose layout the regex parsers can't handle are flagged for an Agent-based pass; the skill caller (Claude) should dispatch agents to handle those (see "Agent fallback" below).
4. **Apply** (`scripts/04_apply.py`) — match each extracted record back to a vendor entry in `data/material_db.json` (by tds_link URL → machine → layer → post-treatment), and overwrite the mechanical property fields. Entries whose URL is no longer reachable get NULL values and `_tds_unverified: true`. Re-runs the heat_treatments aggregation at the end.

## Vocabulary

- **TDS** = technical data sheet (vendor-published material/machine combo PDF or HTML)
- **post_treatment** = lowercase canonical: `as-built`, `stress-relieved`, `annealed`, `solution-annealed`, `solution+age`, `heat-treated`, `T6`, `H900` / `H1025` / `H1150`, `aged`, `HT_HIP`, `HT_HIP_age`, `tempered`
- **XY** = horizontal in-plane (perpendicular to build direction). Sometimes labeled "H" or "Horizontal"
- **Z** = build direction (vertical). Sometimes labeled "V" or "Vertical"
- A record covers one (vendor, machine, layer_thickness_um, post_treatment) cell

## Record schema (uniform across vendors)

```json
{
  "manufacturer":       "Nikon SLM Solutions",
  "machine":            "SLM 280",
  "layer_thickness_um": 30,
  "post_treatment":     "as-built",
  "yield_xy_MPa":       305,
  "yield_z_MPa":        270,
  "uts_xy_MPa":         465,
  "uts_z_MPa":          475,
  "elongation_xy_pct":  9,
  "elongation_z_pct":   6,
  "hardness_HV":        128,
  "surface_ra_lo":      11,
  "surface_ra_hi":      22,
  "tds_link":           "https://...",
  "_tds_verified":      true
}
```

Fields the TDS doesn't report must be `null`. Never guess.

## Usage

Default run (all four phases, all vendors):

```bash
python .claude/skills/refresh-tds-catalog/scripts/01_discover.py
python .claude/skills/refresh-tds-catalog/scripts/02_download.py
python .claude/skills/refresh-tds-catalog/scripts/03_extract.py
python .claude/skills/refresh-tds-catalog/scripts/04_apply.py
```

Limit to one vendor (faster iteration when debugging):

```bash
python .claude/skills/refresh-tds-catalog/scripts/01_discover.py --vendor eos
```

All scripts accept `--vendor {eos|ge_additive|three_d_systems|nikon}` and `--dry-run`.

## Catalog URL list (assets/catalogs.json)

The skill ships with the vendor catalog landing pages the user provided. If the vendor moves a page (e.g. EOS reorganizes `/metal-solutions/` to `/materials/`), edit `assets/catalogs.json` rather than chasing `tds_link`s in material_db.json — those get re-derived each run.

## Vendor-specific details

Each manufacturer's catalog and TDS document have idiosyncrasies that affect parsing. Read the relevant file from `references/` when you encounter problems with a vendor:

- `references/eos.md`           — EOS metal-solutions catalog + HTML data sheet pages + `/var/assets/` PDFs
- `references/ge_additive.md`   — Colibrium Additive printer pages + M2 Series 5 / X Line PDFs
- `references/three_d_systems.md` — Material finder + LaserForm / Certified PDFs (bot-blocked)
- `references/nikon.md`         — Material category pages + `wp-content/uploads/` MDS PDFs
- `references/db_schema.md`     — material_db.json structure, vendor entry keys, heat_treatments buckets

## Agent fallback for tricky PDFs

Some vendor PDFs render numerics as positioned glyphs rather than text. `pdftotext` produces a near-empty file for those. The extract script detects this (output `< 1 KB`) and flags the URL in `_tds_workspace/extraction_misses.json` with the saved PDF path.

When you (Claude) see entries in that file, spawn one general-purpose agent per misses-batch (or one per PDF if the count is small) with a prompt like:

```
Read <pdf-path>. Re-render pages to PNG via PyMuPDF if pdftotext output is sparse.
Extract per (machine × layer × post_treatment) records into the uniform schema
documented in SKILL.md. Write to _tds_workspace/agent_<vendor>_<material>.json.
```

After agents finish, re-run `04_apply.py` to merge their JSON outputs.

## Anomaly reporting

`scripts/03_extract.py` and `scripts/04_apply.py` both write to `_tds_workspace/anomalies.md` with bullet entries:

- Catalog page returned 404 / 5xx
- TDS URL changed (cached link in DB doesn't match what catalog now points to)
- New material discovered that isn't in `data/material_db.json["materials"]`
- New machine discovered for an existing material
- Existing material in DB no longer listed by the vendor (likely product discontinued)
- TDS file failed to download or parser failed to extract any records
- Numeric values changed by >15% vs. prior DB values for the same (machine, layer, post_treatment)

Surface this file to the user at the end of every run, including a brief in-chat summary.

## Output checklist

After a full run, expect:

1. Updated `data/material_db.json` (overwrites in place; back up first if paranoid)
2. `_tds_workspace/discovery.json` — what catalog crawling found
3. `_tds_workspace/cache/manifest.json` — local cache state
4. `_tds_workspace/extracted.json` — uniform records, pre-apply
5. `_tds_workspace/extraction_misses.json` — PDFs needing Agent fallback (may be empty)
6. `_tds_workspace/anomalies.md` — human-readable change log

Print a final one-line summary: `verified=<N>/<total>  unverified=<M>  anomalies=<K>  agent-fallbacks-needed=<P>`.

## Why discover URLs every run instead of trusting cached `tds_link`

Manufacturers re-publish TDS PDFs with new version suffixes (e.g. `MDS_AlSi10Mg_2026-01.1_EN.pdf` will become `_2026-04_EN.pdf` next quarter). The old URL 404s silently and the data goes stale without anyone noticing. The catalog landing page is the only stable surface to anchor on. So: always start from `assets/catalogs.json`, never start from the DB's existing `tds_link`s.
