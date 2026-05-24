"""Material alias table — composition-based grouping rules.

The user's policy: new materials/equipment may be added, but materials that
share composition with an existing DB material are grouped under it, with
the variant noted in parentheses. This file is the single source of truth
for those grouping decisions. Edit when you encounter a new vendor variant.

The matcher checks vendor TDS filenames / material_hint strings against
each alias list (case-insensitive substring). The FIRST match wins, so
order more specific aliases before generic ones (e.g. "ti6al4v-eli" before
"ti6al4v").
"""
from __future__ import annotations

import re
from urllib.parse import unquote

# Existing DB material → list of (substring, optional_variant_label)
# When matched, the vendor entry stays under the existing material; the
# variant_label (if present) is shown in parens inside the vendor key, e.g.
# "EOS [M290] @ as-built (40μm) (316L-4404)" for an EOS-4404 grade entry.
ALIAS_TABLE: dict[str, list[tuple[str, str | None]]] = {
    "Stainless Steel 316L": [
        ("316l-4441", "316L-4441"),
        ("316l-4404", "316L-4404"),
        ("316l(b)", None),
        ("316l", None),
        ("316la-",  None),
        ("stainlesssteel-316", None),
    ],
    "Stainless Steel 17-4PH": [
        ("17-4ph", None), ("17-4-ph", None), ("17-4 ph", None),
        ("ph17-4", None),
        ("stainlesssteel-ph1", "EOS PH1 (17-4 grade)"),
    ],
    "Stainless Steel 15-5PH": [("15-5ph", None), ("15-5 ph", None)],
    "Maraging Steel (1.2709/MS1/M300)": [
        ("1-2709", None), ("1.2709", None),
        ("maragingsteel", None), ("maraging-steel", None), ("maraging_steel", None),
        ("maraging", None),
        ("toolsteel-1-2709", None),
        ("ms1", "EOS MS1"),
        ("m300", "GE M300"),
    ],
    "H13": [("h13", None), ("toolsteel-h13", None)],
    "Ti6Al4V (Gr5, Gr23)": [
        ("ti64eli", "ELI"),
        ("ti6al4v-g23", "Gr23"),
        ("ti64-grade23", "Gr23"),
        ("ti-gr23", "Gr23"),
        ("ti64-grade5", "Gr5"),
        ("ti-gr5", "Gr5"),
        ("ti64-gr5", "Gr5"),
        ("ti6al4v", None),
        ("ti64", None),
        ("ti-64", None),
        ("rematitan", "Rematitan dental"),
    ],
    "Ti CP Gr2": [
        ("titanium-ticp", None), ("ti-gr1", "Gr1"),
        ("ti-cp", None), ("cpti", None), ("cp-ti", None),
        ("titanium-ti-grade-2", None),
    ],
    "AlSi10Mg": [("alsi10mg", None), ("alsi10", None)],
    "AlSi7Mg": [
        ("alsi7mg", None),
        ("alf357", "F357 ~ AlSi7Mg"),
        ("a6061-ram2", "A6061-RAM2 ceramic"),  # Al-based composite variant
    ],
    "Scalmalloy": [("scalmalloy", None), ("al-mg-sc", None), ("almgsc", None)],
    "Inconel 625": [
        ("nickelalloy-in625", None),
        ("nickelalloy_in625", None),
        ("ni625", None), ("alloy625", None), ("in625", None),
        ("inconel-625", None), ("inconel 625", None),
    ],
    "Inconel 718": [
        ("nickelalloy-in718api", "API grade"),
        ("ni718api", "API grade"),
        ("nickelalloy-in718", None),
        ("nickelalloy_in718", None),
        ("ni718", None), ("in718", None), ("nickel718", None),
        ("inconel-718", None), ("inconel 718", None),
    ],
    "Hastelloy X": [
        ("hastelloy", None),
        ("nickelalloy-hx", None), ("nickelalloy_hx", None),
        ("nickel-x", None), ("nickel%20x", None), ("nickel x", None),
        ("hxa-", None),  # 3DS certifiedhxa
        ("certifiedhxa", None),
    ],
    "CoCr (CoCrMo)": [
        ("cobaltchromemp1", "EOS MP1"),
        ("cobalt-chrome-mp1", "EOS MP1"),
        ("cobaltchrome", None),
        ("cobalt-chrome", None), ("cobalt chrome", None),
        ("cocrmo", None),
        ("cocr(b)", None), ("cocrf75", "F75"),
        ("cocr-", None), ("cocr_", None),
        ("laserform-cocr", None),
        ("remaniumstar", "Remanium dental"),
    ],
    "Cu (Pure)": [
        ("copper-cu-", None),
        ("eos-copper-cu", None),
        ("copper-cucp", "CP-Cu"),
        ("copper-cu_", None),
    ],
    "CuCr1Zr": [
        ("cucr1zr", None),
        ("copperalloy-cucrzr", None),
        ("copperalloy_cucrzr", None),
        ("cucrzr", None),
    ],
    "CuNi2SiCr": [("cuni2sicr", None), ("cuni2si", None)],
    "Invar 36 (Fe-36Ni)": [
        ("invar", None), ("invarr36", None),
        ("feni36", None), ("fe-ni36", None),
    ],
    "M789 (Co-free Maraging)": [("m789", None)],
    "Haynes 282": [
        ("haynes282", None), ("haynes-282", None), ("haynes_282", None),
        ("nickelalloy-haynes-282", None),
        ("nickelalloy_haynes282", None),
        ("h282", None), ("282-2025", None),
    ],
    "Monel K-500": [
        ("k-500", None), ("k500", None), ("monel", None),
        ("nickelalloyk500", None),
    ],
    "Aheadd CP1 (Al-Cr-Fe-Zr)": [("aheadd", None), ("cp1", None)],
    "A2024-RAM2C (Al-Cu ceramic)": [
        ("a2024", None), ("ram2c", None),
        # A6061-RAM2 is a related Al-RAM ceramic; map under AlSi7Mg per
        # composition (Al matrix with strengthening), with variant noted.
    ],
    "CuNi30 (Copper-Nickel 70/30)": [
        ("cuni30", None), ("copperalloy-cuni30", None), ("copperalloy_cuni30", None),
    ],
    "CP-Nickel": [
        ("nickel_nicp", None), ("nickel-nicp", None),
        ("cp-nickel", None), ("cpni", None), ("ni-cp", None),
    ],
}

# NEW material entries to create (composition-distinct from any DB material)
# Each entry: filename-substring → (proposed material name, category, brief note)
NEW_MATERIALS: dict[str, tuple[str, str, str]] = {
    "grx-810":     ("GRX-810 (Ni-Co-Cr ODS)",       "Nickel Alloy",
                    "NASA GRX-810 oxide-dispersion-strengthened superalloy"),
    "c-103":       ("C-103 (Nb-Hf-Ti)",             "Refractory",
                    "Niobium alloy C-103"),
    "grcop-42":    ("GRCop-42 (Cu-Cr-Nb)",          "Copper Alloy",
                    "NASA GRCop-42 high-conductivity Cu alloy"),
    "cucr2":       ("CuCr2",                         "Copper Alloy",
                    "Cu-Cr alloy variant (3DS)"),
    "tungsten":    ("Tungsten (W)",                  "Refractory",
                    "Pure tungsten for refractory parts"),
    "ta_":         ("Tantalum (Ta)",                 "Refractory",
                    "Pure tantalum"),
    "ta-":         ("Tantalum (Ta)",                 "Refractory",
                    "Pure tantalum"),
    "tantalum":    ("Tantalum (Ta)",                 "Refractory",
                    "Pure tantalum"),
    "a205":        ("A205 (Al-Cu)",                  "Aluminum",
                    "Al-Cu high-strength alloy (GE A205)"),
    "al5x1":       ("Al5x1 (Al-X)",                  "Aluminum",
                    "EOS proprietary Al-X high-strength alloy"),
    "al2139":      ("Al2139-AM",                     "Aluminum",
                    "Al-Cu wrought-derived alloy 2139"),
    "ti6242":      ("Ti6242 (Ti-6Al-2Sn-4Zr-2Mo)",   "Titanium",
                    "Alpha-beta near-alpha Ti alloy"),
    "in738":       ("Inconel 738 (IN738)",           "Nickel Alloy",
                    "Ni-base superalloy IN738"),
    "in939":       ("Inconel 939 (IN939)",           "Nickel Alloy",
                    "Ni-base superalloy IN939"),
    "in247":       ("CM247LC (IN247)",               "Nickel Alloy",
                    "Cast Ni-base superalloy CM247LC / MAR-M247"),
    "nickelalloy-247": ("CM247LC (IN247)",           "Nickel Alloy",
                    "Cast Ni-base superalloy CM247LC / MAR-M247"),
    "nickelalloy_247": ("CM247LC (IN247)",           "Nickel Alloy",
                    "Cast Ni-base superalloy CM247LC / MAR-M247"),
    "nickelalloy-c22": ("Hastelloy C22",             "Nickel Alloy",
                    "Ni-Cr-Mo corrosion-resistant alloy C22"),
    "20mncr5":     ("20MnCr5",                       "Case-hardening Steel",
                    "DIN low-alloy case-hardening steel"),
    "42crmo4":     ("42CrMo4",                       "Alloy Steel",
                    "DIN medium-C low-alloy steel (AISI 4140)"),
    "stainlesssteel-254": ("AISI 254 SMO",           "Stainless Steel",
                    "Super-austenitic stainless steel"),
    "superduplex": ("Superduplex Stainless",         "Stainless Steel",
                    "Duplex/superduplex grade (~25Cr-7Ni-Mo-N)"),
    "stainlesssteel-cx": ("CX (PH Tool Stainless)",  "PH Stainless",
                    "EOS CX precipitation-hardenable tool steel"),
    "toolsteel-cm55": ("CM55 Tool Steel",            "Tool Steel",
                    "EOS CM55 tool steel"),
    "toolsteel_cm55": ("CM55 Tool Steel",            "Tool Steel",
                    "EOS CM55 tool steel"),
    "cr-ph":       ("CR-PH Martensitic",             "PH Stainless",
                    "GE Cr-PH martensitic stainless"),
    # Note: Nikon mds5145 is C-103 (Nb-Hf-Ti), not pure niobium. The
    # "niobium" catalog-slug match here intentionally folds into C-103.
    "niobium":     ("C-103 (Nb-Hf-Ti)",               "Refractory",
                    "Niobium-based alloy (Nikon catalog slug)"),
}


def _norm(s):
    return re.sub(r"[\s_\-.]+", "", (s or "").lower())


def match_material(filename_or_hint: str) -> tuple[str | None, str | None, dict | None]:
    """Return (existing_material_name, variant_label, new_material_info).

    `filename_or_hint` should concatenate everything textual we know about
    the URL — filename, material_hint, catalog_slug — so the matcher has
    enough surface area to find the right rule. URL-encoded sequences are
    decoded so substrings like "cocr(b)" hit a URL like "cocr%28b%29".
    Exactly one of (existing_material_name, new_material_info) is non-None
    when there's a confident match.
    """
    key = unquote((filename_or_hint or "")).lower()

    # Check NEW_MATERIALS first since they're more specific
    for sub, (name, cat, note) in NEW_MATERIALS.items():
        if sub in key:
            return (None, None, {"name": name, "category": cat, "note": note})

    # Then existing materials
    for db_name, aliases in ALIAS_TABLE.items():
        for sub, variant in aliases:
            if sub in key:
                return (db_name, variant, None)

    return (None, None, None)
