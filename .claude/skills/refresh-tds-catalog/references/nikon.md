# Nikon SLM Solutions catalog & TDS format notes

## Catalog pages

`https://nikon-slm-solutions.com/materials/<category>/` where `<category>`
∈ `aluminium`, `cobalt`, `copper`, `nickel`, `steel`, `titanium`, `niobium`.

The catalog renders server-side with each material section showing machine
applicability plus a "Download Material Data Sheet" button per machine.

Some category pages are marketing-only with no PDF link (we've observed this
for `cobalt`). The skill records a single anomaly for those — don't treat
0-PDF discovery as an error globally.

## TDS PDF naming

`/wp-content/uploads/<YYYY>/<MM>/MDS_<MATERIAL>_<YYYY-MM[.r]>_EN.pdf`
or          `/wp-content/uploads/<YYYY>/<MM>/mds<NNNN>.pdf`

The 4-digit `mds<NNNN>` filenames are older and don't encode the material in
the filename — you only know what they cover by opening the document.

## PDF parsing characteristics

`pdftotext -layout -enc UTF-8` extracts cleanly for almost every Nikon MDS.
A small minority embed numeric tables as positioned glyphs (we've seen this
on Aheadd CP1 and CuNi30 revisions) — those need the Agent fallback path.

Per-machine table structure (one section per machine × parameter set ×
layer thickness):

```
SLM® <MACHINE> <PARAM>          <MATERIAL>_<MACHINE>_<PARAM>_..._V1 (<layer> µm)

MECHANICAL PROPERTIES
Non-heat-treated  /  Heat-treated (SR1) / Heat-treated (AGED) / ...
            Rm [MPa]      Rp0.2 [MPa]    A [%]
Machined    M     MIN     M     MIN     M     MIN
Horizontal  <UTS_xy> <UTS_xy_min> <YS_xy> <YS_xy_min> <E_xy> <E_xy_min>
Vertical    <UTS_z>  <UTS_z_min>  <YS_z>  <YS_z_min>  <E_z>  <E_z_min>

Near-Net-Shape  M  MIN  M  MIN  M  MIN
Vertical    <UTS_z_NNS> ...
```

Take only Mean (M) values. Ignore MIN bounds and Near-Net-Shape rows
(those are as-printed surface, not the machined coupons we use elsewhere).

Hardness + Surface Roughness section, one combined row per heat treatment:

```
HARDNESS9                              SURFACE ROUGHNESS10
            M    MIN                              M    MAX    M       MAX
                                                  (Ra)        (Rz)
NHT         <HV> <HV_min>   As built  <Ra_lo> <Ra_hi> <Rz_lo> <Rz_hi>
```

**Watch out**: for some machines the hardness label is also "As built"
instead of "NHT", which collides with the Ra column label. Parsers must
treat the line as `<label1> <HV_M> <HV_min> <label2> <Ra_lo> <Ra_hi> ...`
and use the position of the value pair rather than the label name.

Materials with versioned filenames (`MDS_AlSi10Mg_2026-01.1_EN.pdf`) — the
`.1` suffix means a point revision; the underlying URL changes each release
so always re-derive from the catalog page.
