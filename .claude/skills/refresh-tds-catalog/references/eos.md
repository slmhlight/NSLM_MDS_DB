# EOS catalog & TDS format notes

## Catalog landing pages

URL shape: `https://www.eos.info/metal-solutions/metal-materials/<category>`
where `<category>` is one of: `nickel-alloys`, `cobalt-chrome`, `copper`,
`aluminium`, `other-steels`, `special-metal-materials`, `stainless-steel`,
`titanium`, `tool-steel`.

These pages render server-side — the discovered HTML already contains the
anchor tags. Each material card has multiple "Data Sheet" buttons (one per
machine × layer combination) linking to per-combo HTML PDS pages.

## TDS document types

EOS publishes per (material × machine × layer-thickness) combination as a
**Process Data Sheet (PDS)** under `/metal-solutions/data-sheets/<category>/`,
plus per-material aggregated PDFs under `/var/assets/05-datasheet-images/`.
The skill prefers the HTML PDS pages because they have a tidy machine-readable
table; the PDFs are kept as a fallback.

URL patterns:

- PDS HTML: `/metal-solutions/data-sheets/<category>/pds-eos-<material>-<grade>-eos-m-<machine>-<layer>um`
- MDS PDF:  `/var/assets/05-datasheet-images/Assets_MDS_Metal/EOS_<Material>_en.pdf?v=<N>`

Skip the aggregator URL `data-sheets/all-processes-and-materials?id=...`
— it's a list page that re-points to the same PDS pages we already crawled.

## PDS HTML structure

The mechanical properties section in EOS PDS pages is:

```
<heat-treatment-state> EN ISO 6892-1 Room Temperature | <layer> µm
  Yield Strength [MPa]  Tensile Strength [MPa]  Elongation at Break A [%]  Reduction of Area Z [%]  Modulus [GPa]  N
  Vertical    490   590  45  -  -  120
  Horizontal  550   650  40  -  -  96
```

Notes:
- `Vertical` = Z (build direction), `Horizontal` = XY (in-plane).
- "EN ISO 6892-1" is the test standard — the per-state pattern always appears
  after a standard name.
- Some pages list **only Vertical** results (e.g. for materials that EOS
  doesn't qualify for horizontal use); XY columns should be `null`.
- Heat-treatment label varies: `As Manufactured`, `Solution Annealed`,
  `Stress Relieved`, `Solution Heat Treated`, `Heat Treated`, `Hot Isostatic
  Pressing`, `Aged`, etc. Map to canonical (see SKILL.md).

Surface roughness and hardness are reported once per PDS page (apply to all
heat-treatment rows of that combo):

```
Hardness ...  HV<scale>  <value>
Surface Roughness ...  Ra [µm]  <lo>  [<hi>]
```

Some pages report `Sa` (areal) instead of `Ra` — leave `surface_ra_*` null.
Some materials report HRC/HRB instead of HV — leave `hardness_HV` null.

## Aggregator (`/all-processes-and-materials`) pages

These are dynamic list views with a `?id=` query string. Their HTML still
contains anchor tags back to the same PDS pages — so we **skip** the
aggregator URL itself (would just duplicate the PDS pages we already have)
but rely on the catalog category pages to surface the PDS pages directly.
