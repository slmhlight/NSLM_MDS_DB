# GE Additive (Colibrium) catalog & TDS format notes

## Catalog landing pages

URL shape: `https://www.colibriumadditive.com/printers/l-pbf-printers/<printer>`
where `<printer>` ∈ `m2-series-5`, `m-line`, `x-line-2000r`, `mlab`.

Pages are server-rendered; the materials section lists each material with
a "Material Data Sheet" download button linking to a PDF.

## TDS PDF naming

`/sites/default/files/<PRINTER>_<MATERIAL>_<POWER>W_CMDS_<YYYYMMDD>_Rev<X>.pdf`

Examples:
- `M2SERIES5_316L_400W_CMDS_20241111_RevA.pdf`
- `M2SERIES5_Ti64_400W_CMDS_20241018_RevA.pdf`
- `MLINE_A205_MLine_CMDS_20250821_RevC.pdf` (M-Line printer, A205 alloy — new)

Material part is the field with the highest variability (Al-Mg-Sc / Scalmalloy,
Nickel%20X = "Nickel X" / Hastelloy X-like, A205, AlSi7Mg, AlSi10Mg, ...).

## PDF parsing characteristics

`pdftotext -layout` works for most M2 Series 5 sheets. However, some sheets
(especially the Ti64 and CP-Ti revisions from 2024-10/11) embed numeric
table cells as positioned glyphs that pdftotext drops — the .txt file ends
up < 1 KB. The skill flags those and the user must run an Agent that
re-renders pages via PyMuPDF.

Table structure when text extracts cleanly:

```
Parameter <name> - <power> W / <layer> µm

Tensile Performance at Room Temperature
Thermal State   Modulus (GPa)   Yield (MPa)   UTS (MPa)
                H               H             H        <- header marker
                <Mod_H> <Mod_V> <YS_H> <YS_V> <UTS_H> <UTS_V>
                <next thermal state row>
                ...

Thermal State   Elongation (%)   Area Reduction (%)
<state>         <E_H> <E_V>       <AR_H> <AR_V>
```

Thermal-state labels (`As-Built`, `SR`, `SOLN1`, `SOLN2`, `H900`, `H1025`,
`H1150`, `SA+Aging`, `SOLN+AGE`, `T6`, `Direct Aging`) live in column 1; data
rows in columns 2+. **pdftotext often places the last label on the same line
as the first data row** because they're vertically aligned in the source PDF.
Tools/parsers must align labels to rows by vertical position rather than line
number — easiest with the Agent fallback path.

Surface roughness Ra and hardness HV10 appear in the Physical Properties
section, one value per (thermal-state × direction).
