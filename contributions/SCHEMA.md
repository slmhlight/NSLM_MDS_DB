# Contribution schema

A contribution is a single JSON file placed in `contributions/pending/`,
named `<type>_<material-slug>_<YYYYMMDD>_<author>.json`. The maintainer
reviews PRs against this folder, merges them into the master DB, and
moves accepted contributions to `contributions/applied/<merge-date>/`.

## File envelope (all contribution types)

```json
{
  "schema_version":  1,
  "type":            "add_vendor_entry" | "add_material" | "update_vendor_entry",
  "submitted_by":    "your-github-username",
  "submitted_at":    "2026-05-24T10:30:00Z",
  "source":          "https://vendor.com/path/to/tds.pdf",
  "rationale":       "Short note on why this is being added/changed",
  "payload":         { ... type-specific body ... }
}
```

`source` must link to the underlying TDS / data sheet that justifies the
numbers. Maintainer will not merge without a verifiable source.

## Type: `add_vendor_entry`

Adds one vendor entry to an existing material.

```json
{
  ...envelope...,
  "type": "add_vendor_entry",
  "payload": {
    "target_material": "Inconel 625",
    "entry": {
      "manufacturer":        "EOS",
      "machine":             "EOS M-290 HiPro",
      "post_treatment":      "as-built",
      "layer_thickness_um":  50,
      "yield_MPa":           720,
      "yield_z_MPa":         640,
      "uts_xy_MPa":          985,
      "uts_z_MPa":           895,
      "elongation_xy_pct":   34,
      "elongation_z_pct":    42,
      "hardness_HV":         null,
      "surface_ra_lo":       7,
      "surface_ra_hi":       12,
      "tds_link":            "https://www.eos.info/.../in625-m290-hipro-50um.pdf"
    }
  }
}
```

Rules:
- `target_material` MUST exist in the current DB (see `material_db.json`
  → `materials` keys). Otherwise submit as `add_material` instead.
- All numeric fields are MPa / % / HV / μm — null only when the TDS
  itself doesn't report the value.
- YS must be ≤ UTS in each direction (physical sanity).
- `tds_link` must be a public, verifiable URL — vendor's official site
  preferred.

## Type: `add_material`

Adds a brand-new material entry (not yet in DB).

```json
{
  ...envelope...,
  "type": "add_material",
  "payload": {
    "name":          "Inconel 706",
    "category":      "Nickel Alloy",
    "category_top":  "Nickel",
    "density":       8.05,
    "melt":          1335,
    "thermal_k":     11.5,
    "cp":            440,
    "cte":           14.0,
    "E":             210,
    "poisson":       0.30,
    "magnetic":      "non-magnetic",
    "composition": [
      ["Ni","balance"], ["Fe","37"], ["Cr","16"],
      ["Nb","2.9"], ["Ti","1.75"], ["Al","0.20"]
    ],
    "applications":  "Aerospace turbine disks (gamma-prime + gamma-double-prime strengthened Ni-Fe-Cr)",
    "ref_urls": [
      ["Special Metals — Inconel 706", "https://www.specialmetals.com/..."]
    ],
    "first_vendor_entry": {
      "manufacturer":     "EOS",
      "machine":          "EOS M-290",
      "post_treatment":   "as-built",
      ... (same shape as add_vendor_entry's `entry`) ...
    }
  }
}
```

Rules:
- `category_top` MUST be one of the 8 canonical values (run
  `python -c "import json; print(json.load(open('data/material_db.json'))['_category_top_order'])"`
  or read SKILL.md's `_material_aliases.py`).
- `first_vendor_entry` is required — a material with no vendor entries
  serves no purpose.

## Type: `update_vendor_entry`

Corrects values on an existing entry (e.g., new TDS revision).

```json
{
  ...envelope...,
  "type": "update_vendor_entry",
  "payload": {
    "target_material": "Inconel 625",
    "vendor_key":      "EOS [EOS M 290] @ as-built (40μm)",
    "changes": {
      "uts_xy_MPa":   985,
      "elongation_xy_pct": 32
    },
    "old_tds_link": "https://www.eos.info/.../v=5.pdf",
    "new_tds_link": "https://www.eos.info/.../v=6.pdf"
  }
}
```

Rules:
- `vendor_key` must match exactly. Run
  `python contribute.py find-key "<manufacturer>" "<machine>" "<post>" <layer>`
  to look it up.
- `changes` lists only the fields that should be overwritten. Anything
  not mentioned is preserved.

## Validation

Before submitting:

```bash
python contribute.py validate contributions/pending/your-file.json
```

The validator checks JSON parseability, the envelope, the type-specific
payload, and physical sanity (YS ≤ UTS, elong in [0, 100], etc.).
