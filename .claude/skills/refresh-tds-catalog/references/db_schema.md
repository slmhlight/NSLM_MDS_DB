# material_db.json schema (subset relevant to this skill)

```json
{
  "_default_4": ["Nikon SLM Solutions", "EOS", "GE Additive", "3D Systems"],
  "materials": {
    "<material_name>": {
      "category": "...",
      "magnetic": "...",
      "density": <float>,
      "...basic physical/thermal fields...": ...,
      "composition": [["Fe","balance"], ...],
      "applications": "...",
      "ref_urls": [["label","url"], ...],
      "heat_treatments": {
        "<bucket>": {
          "uts": <median XY UTS>, "uts_z": <median Z UTS>,
          "ys": ..., "ys_z": ...,
          "elong": <median XY elong>, "elong_z": ...,
          "hardness_HV": ..., "hardness_HRC": null, "hardness_HB": null,
          "surface_ra_lo": ..., "surface_ra_hi": ..., "surface_ra_um": "lo~hi",
          "notes": "free text from previous curation"
        }
      },
      "vendors": {
        "<vendor_key>": {
          "manufacturer": "EOS|Nikon SLM Solutions|3D Systems|GE Additive|...",
          "machine": "M290 / SLM 280 / ProX DMP 320 / M2 Series 5 / ...",
          "post_treatment": "as-built|stress-relieved|annealed|T6|H900|...",
          "layer_thickness_um": 20|30|40|50|60|80|...,
          "yield_MPa": <XY YS>, "yield_z_MPa": <Z YS>,
          "uts_xy_MPa": ..., "uts_z_MPa": ...,
          "elongation_pct": <legacy=XY>,
          "elongation_xy_pct": ..., "elongation_z_pct": ...,
          "hardness_HV": ...,
          "surface_ra_lo": ..., "surface_ra_hi": ...,
          "tds_link": "https://...",
          "_tds_verified": true       // or
          "_tds_unverified": true     // when TDS unreachable/fake URL
        }
      }
    }
  }
}
```

## Vendor key naming convention

`"<Manufacturer> [<Machine>] @ <post_treatment> (<layer>μm)"`

E.g. `"Nikon SLM Solutions [SLM 280] @ as-built (30μm)"`.

The key is human-readable; matching for skill updates uses the structured
fields (`manufacturer`, `machine`, `layer_thickness_um`, `post_treatment`)
inside the entry, not the key string itself.

## Heat-treatment bucket vocabulary

Canonical bucket names in `heat_treatments`:
`as_built`, `stress_relieved`, `annealed`, `solution+age`, `T6`, `H900`,
`H1025`, `H1150`, `HT_HIP`, `HT_HIP_age`, `aged`, `tempered`, `heat-treated`.

The same canonical names (with hyphen variants — `as-built` / `stress-relieved`)
are used as `post_treatment` values in vendor entries; the skill normalises
them when aggregating into the heat_treatments table.

## Flag semantics

- `_tds_verified: true` — record was overwritten from a directly parsed TDS
  in the current run. Authoritative.
- `_tds_unverified: true` — TDS URL was unreachable or known-fake; all
  numeric tensile fields nulled out so the UI renders "-".
- Neither flag — legacy entry from before the skill existed; values present
  but provenance unclear. Future runs should try to verify.

The dialog (`mds_dialog.py`) doesn't read these flags directly; they're for
the skill's bookkeeping only.
