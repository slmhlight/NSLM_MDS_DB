"""Phase 0-4 DB verification.

Cheap, no-Agent sanity sweep over material_db.json:
  0. Baseline stats — counts by manufacturer/material/URL
  1. Label/link consistency — vendor_key ↔ manufacturer / machine / layer / post
  2. Material routing — TDS URL filename keyword vs containing material
  3. Duplicate value blocks — identical mechanical tuples across distinct
     (manufacturer, machine, layer, post) — flag potential leakage
  4. Per-category value ranges — flag entries whose YS/UTS/elong/HV are
     impossible for the material class

Writes _tds_workspace/verify_summary.md (human-readable) and
_tds_workspace/verify_anomalies.json (machine-readable, for Phase 5+).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


# ---------- helpers ----------------------------------------------------------

URL_VENDOR = {
    "eos.info":              "EOS",
    "colibriumadditive.com": "GE Additive",
    "3dsystems.com":         "3D Systems",
    "nikon-slm-solutions.com": "Nikon SLM Solutions",
}


def url_vendor(url):
    if not url: return None
    for host, v in URL_VENDOR.items():
        if host in url: return v
    return None


def _norm(s):
    return re.sub(r"[\s_\-®®/+\.]+", "", str(s or "").lower())


def parse_key(vk: str):
    """Pull (manufacturer, machine, layer_um, post_treatment) from a vendor_key.

    Canonical shape: "<Manufacturer> [<Machine>] @ <post> (<layer>μm)"
    Missing pieces return None.
    """
    m = re.match(r"^(.+?)(?:\s*\[([^\]]+)\])?\s*@\s*(.+?)\s*(?:\(([0-9]+)μm\))?\s*(?:#\d+)?\s*$", vk)
    if not m: return (None, None, None, None)
    return (m.group(1).strip(),
            (m.group(2) or "").strip() or None,
            int(m.group(4)) if m.group(4) else None,
            m.group(3).strip())


# Per-category sanity ranges (YS_MPa, UTS_MPa, Elong_pct, HV).
# None = no upper/lower bound. Conservative bands; warnings only.
# Bands widened after first verification pass picked up legitimate edge
# cases: Cobalt LPBF often hits 45-55% elong in solution-annealed; pure
# CP-Nickel is intentionally low-strength (UTS as low as 400 MPa); some
# Cu superalloys exceed 1000 MPa UTS.
RANGES = {
    "Aluminium":   {"YS": (80, 650),  "UTS": (150, 800), "Elong": (1, 35), "HV": (40, 220)},
    "Cobalt":      {"YS": (400, 1200),"UTS": (700, 1500),"Elong": (3, 60), "HV": (200, 550)},
    "Copper":      {"YS": (40, 800),  "UTS": (120, 1100),"Elong": (2, 60), "HV": (40, 350)},
    "Nickel":      {"YS": (150, 1700),"UTS": (350, 2100),"Elong": (3, 70), "HV": (110, 550)},
    "Steel":       {"YS": (200, 2400),"UTS": (400, 2700),"Elong": (1, 75), "HV": (130, 750)},
    "Titanium":    {"YS": (300, 1400),"UTS": (400, 1600),"Elong": (2, 45), "HV": (180, 480)},
    "Niobium":     {"YS": (150, 800), "UTS": (250, 950), "Elong": (2, 40), "HV": (80, 450)},
    "Other":       {"YS": (50, 2000), "UTS": (100, 2500),"Elong": (1, 80), "HV": (60, 700)},
}


# ---------- run --------------------------------------------------------------

def main():
    _lib.ensure_workspace()
    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))
    mats = db.get("materials", {})

    anomalies = {
        "phase1_label_link":    [],
        "phase2_material_route":[],
        "phase3_duplicate_vals":[],
        "phase4_value_range":   [],
    }
    summary_lines = []

    # ----- Phase 0: baseline stats -----------------------------------------
    summary_lines.append("# DB Verification Report")
    summary_lines.append("")
    summary_lines.append("## Phase 0 — Baseline stats")
    summary_lines.append("")
    summary_lines.append(f"- materials: **{len(mats)}**")
    total_v = sum(len(m.get('vendors') or {}) for m in mats.values())
    summary_lines.append(f"- vendor entries: **{total_v}**")

    by_mfg = Counter()
    by_mat = []
    by_url = defaultdict(int)
    for n, m in mats.items():
        v = m.get('vendors') or {}
        by_mat.append((n, len(v)))
        for vk, vd in v.items():
            if isinstance(vd, dict):
                by_mfg[vd.get('manufacturer', '?')] += 1
                if vd.get('tds_link'): by_url[vd['tds_link']] += 1

    summary_lines.append(f"- unique tds_links: **{len(by_url)}**")
    summary_lines.append("")
    summary_lines.append("Manufacturer entry counts:")
    for mfg, n in sorted(by_mfg.items(), key=lambda x: -x[1]):
        summary_lines.append(f"  - {mfg}: {n}")

    # ----- Phase 1: label/link consistency ---------------------------------
    summary_lines.append("\n## Phase 1 — Label/link consistency")
    for mat_name, mat in mats.items():
        for vk, vd in (mat.get('vendors') or {}).items():
            if not isinstance(vd, dict): continue
            key_mfg, key_machine, key_layer, key_post = parse_key(vk)
            f_mfg = vd.get('manufacturer')
            f_machine = vd.get('machine')
            f_layer = vd.get('layer_thickness_um')
            f_post = vd.get('post_treatment')
            link_mfg = url_vendor(vd.get('tds_link'))

            local = []
            # 1.1 vendor_key prefix vs manufacturer field
            if key_mfg and f_mfg and key_mfg != f_mfg:
                local.append(f"key prefix {key_mfg!r} ≠ manufacturer {f_mfg!r}")
            # 1.2 link host vs manufacturer
            if link_mfg and f_mfg and link_mfg != f_mfg:
                local.append(f"tds_link host {link_mfg!r} ≠ manufacturer {f_mfg!r}")
            # 1.3 machine in key vs field (only if both present)
            if key_machine and f_machine and _norm(key_machine) != _norm(f_machine):
                local.append(f"key machine {key_machine!r} ≠ machine field {f_machine!r}")
            # 1.4 layer in key vs field
            if key_layer is not None and f_layer is not None and key_layer != f_layer:
                local.append(f"key layer {key_layer} ≠ field {f_layer}")

            if local:
                anomalies["phase1_label_link"].append({
                    "material": mat_name, "vendor_key": vk, "issues": local,
                    "tds_link": vd.get('tds_link'),
                })

    n1 = len(anomalies['phase1_label_link'])
    summary_lines.append(f"\nIssues: **{n1}**")
    for a in anomalies['phase1_label_link'][:20]:
        summary_lines.append(f"\n- **{a['material']}** / `{a['vendor_key']}`")
        for issue in a['issues']:
            summary_lines.append(f"  - {issue}")
    if n1 > 20:
        summary_lines.append(f"\n... +{n1 - 20} more (see verify_anomalies.json)")

    # ----- Phase 2: material routing ---------------------------------------
    # For each URL, infer material keyword and see if it matches the
    # material it's nested under.
    MATERIAL_KEYWORDS = {
        # keyword (lowercased, in URL) -> canonical material name in DB
        "316l-4441":"Stainless Steel 316L", "316l-4404":"Stainless Steel 316L",
        "316l(b)":"Stainless Steel 316L", "316la":"Stainless Steel 316L",
        "316l":"Stainless Steel 316L",
        "17-4ph":"Stainless Steel 17-4PH (CR-PH)",
        "stainlesssteel-ph1":"Stainless Steel 17-4PH (CR-PH)",
        "cr-ph":"Stainless Steel 17-4PH (CR-PH)",
        "stainlesssteel-cx":"CX (PH Tool Stainless)",
        "stainlesssteel-254":"AISI 254 SMO",
        "superduplex":"Superduplex Stainless",
        "1.2709":"Maraging Steel (1.2709/MS1/M300/M789)",
        "1-2709":"Maraging Steel (1.2709/MS1/M300/M789)",
        "maragingsteel":"Maraging Steel (1.2709/MS1/M300/M789)",
        "maraging-steel":"Maraging Steel (1.2709/MS1/M300/M789)",
        "m789":"Maraging Steel (1.2709/MS1/M300/M789)",
        "m300_400w":"Maraging Steel (1.2709/MS1/M300/M789)",
        "h13":"H13", "toolsteel-h13":"H13", "toolsteel_h13":"H13",
        "toolsteel-cm55":"CM55 Tool Steel",
        "casehardeningsteel-20mncr5":"20MnCr5", "20mncr5":"20MnCr5",
        "case-hardening-steel-20mncr5":"20MnCr5",
        "steel-42crmo4":"42CrMo4", "42crmo4":"42CrMo4",
        "feni36":"Invar 36 (Fe-36Ni)", "invar":"Invar 36 (Fe-36Ni)",
        "invarr36":"Invar 36 (Fe-36Ni)",
        "ti6al4v":"Ti6Al4V (Gr5, Gr23)", "ti-gr5":"Ti6Al4V (Gr5, Gr23)",
        "ti-gr23":"Ti6Al4V (Gr5, Gr23)", "ti64":"Ti6Al4V (Gr5, Gr23)",
        "ti64eli":"Ti6Al4V (Gr5, Gr23)",
        "ti6242":"Ti6242 (Ti-6Al-2Sn-4Zr-2Mo)",
        "ti-gr1":"Ti CP Gr2", "ticp":"Ti CP Gr2", "titanium-ticp":"Ti CP Gr2",
        "rematitan":"Ti CP Gr2",
        "alsi10mg":"AlSi10Mg",
        "alsi7mg":"AlSi7Mg", "alf357":"AlSi7Mg",
        "scalmalloy":"Scalmalloy", "al-mg-sc":"Scalmalloy",
        "almgsc":"Scalmalloy",
        "aheadd":"Aheadd CP1 (Al-Cr-Fe-Zr)",
        "a205":"A205 (Al-Cu, Al2139)", "al2139":"A205 (Al-Cu, Al2139)",
        "a6061-ram2":"A20X / A6061-RAM2 (Al MMC ceramic)",
        "ram2c":"A20X / A6061-RAM2 (Al MMC ceramic)",
        "a2024":"A20X / A6061-RAM2 (Al MMC ceramic)",
        "al5x1":"Al5x1 (Al-X)",
        # (legacy A2024-RAM2C label removed — now folded under A20X / A6061-RAM2)
        "in625":"Inconel 625", "alloy625":"Inconel 625",
        "nickelalloy-in625":"Inconel 625", "nickelalloy_in625":"Inconel 625",
        "ni625":"Inconel 625", "laserform-ni625":"Inconel 625",
        "in718":"Inconel 718", "nickel718":"Inconel 718",
        "nickelalloy-in718":"Inconel 718", "nickelalloy_in718":"Inconel 718",
        "ni718":"Inconel 718", "laserform-ni718":"Inconel 718",
        "in718api":"Inconel 718", "nickelalloy-in718-api":"Inconel 718",
        "in738":"Inconel 738 (IN738)", "nickelalloy-in738":"Inconel 738 (IN738)",
        "in939":"Inconel 939 (IN939)", "nickelalloy-in939":"Inconel 939 (IN939)",
        "in247":"CM247LC (IN247)", "nickelalloy-247":"CM247LC (IN247)",
        "haynes":"Haynes 282", "haynes282":"Haynes 282", "haynes-282":"Haynes 282",
        "h282":"Haynes 282",
        "hastelloy":"Hastelloy X (C22)", "nickelalloy-hx":"Hastelloy X (C22)",
        "nickelalloy_hx":"Hastelloy X (C22)", "nickel-x":"Hastelloy X (C22)",
        "nickel%20x":"Hastelloy X (C22)", "certifiedhxa":"Hastelloy X (C22)",
        "c22":"Hastelloy X (C22)", "nickelalloy-c22":"Hastelloy X (C22)",
        "k500":"Monel K-500", "k-500":"Monel K-500",
        "nickelalloyk500":"Monel K-500", "monel":"Monel K-500",
        "nickel_nicp":"CP-Nickel", "nickel-nicp":"CP-Nickel",
        "cobaltchrome":"CoCr (CoCrMo)", "cobalt-chrome":"CoCr (CoCrMo)",
        "cocrmo":"CoCr (CoCrMo)", "cocrf75":"CoCr (CoCrMo)",
        "laserform-cocr":"CoCr (CoCrMo)", "remaniumstar":"CoCr (CoCrMo)",
        "copper-cu":"Cu (Pure)", "copper-cucp":"Cu (Pure)",
        "cucr1zr":"CuCr1Zr (CuCr2)", "copperalloy-cucrzr":"CuCr1Zr (CuCr2)",
        "copperalloy_cucrzr":"CuCr1Zr (CuCr2)", "cucr2":"CuCr1Zr (CuCr2)",
        "cuni2sicr":"CuNi2SiCr",
        "cuni30":"CuNi30 (Copper-Nickel 70/30)",
        "copperalloy-cuni30":"CuNi30 (Copper-Nickel 70/30)",
        "copperalloy_cuni30":"CuNi30 (Copper-Nickel 70/30)",
        "grcop-42":"GRCop-42 (Cu-Cr-Nb)",
        "c-103":"C-103 (Nb-Hf-Ti)", "niobium":"C-103 (Nb-Hf-Ti)",
        "mds5145":"C-103 (Nb-Hf-Ti)",
        "tantalum":"Tantalum (Ta)",
        "tungsten":"Tungsten (W)",
    }

    summary_lines.append("\n## Phase 2 — Material routing")
    for mat_name, mat in mats.items():
        for vk, vd in (mat.get('vendors') or {}).items():
            if not isinstance(vd, dict): continue
            url = (vd.get('tds_link') or "").lower()
            if not url: continue
            from urllib.parse import unquote
            url_dec = unquote(url)
            # find best keyword
            best_mat = None
            best_kw = None
            for kw in sorted(MATERIAL_KEYWORDS, key=len, reverse=True):
                if kw in url_dec:
                    best_mat = MATERIAL_KEYWORDS[kw]; best_kw = kw; break
            if best_mat and best_mat != mat_name:
                anomalies["phase2_material_route"].append({
                    "material": mat_name, "vendor_key": vk,
                    "url_keyword": best_kw,
                    "should_be_under": best_mat,
                    "tds_link": vd.get('tds_link'),
                })

    n2 = len(anomalies['phase2_material_route'])
    summary_lines.append(f"\nIssues: **{n2}**")
    for a in anomalies['phase2_material_route'][:20]:
        summary_lines.append(f"\n- **{a['material']}** / `{a['vendor_key']}`")
        summary_lines.append(f"  - URL keyword `{a['url_keyword']}` suggests **{a['should_be_under']}**")
        summary_lines.append(f"  - {a['tds_link']}")
    if n2 > 20:
        summary_lines.append(f"\n... +{n2 - 20} more")

    # ----- Phase 3: duplicate value blocks ---------------------------------
    # Fingerprint each entry's mechanical tuple. Same tuple across distinct
    # (manufacturer, machine, layer, post) is suspicious.
    fingerprints = defaultdict(list)
    for mat_name, mat in mats.items():
        for vk, vd in (mat.get('vendors') or {}).items():
            if not isinstance(vd, dict): continue
            tup = (vd.get('yield_MPa'), vd.get('yield_z_MPa'),
                   vd.get('uts_xy_MPa'), vd.get('uts_z_MPa'),
                   vd.get('elongation_xy_pct'), vd.get('elongation_z_pct'),
                   vd.get('hardness_HV'))
            # Skip all-null fingerprints
            if all(v is None for v in tup): continue
            sig = (vd.get('manufacturer'), vd.get('machine'),
                   vd.get('layer_thickness_um'), vd.get('post_treatment'))
            fingerprints[tup].append({
                "material": mat_name, "vendor_key": vk, "signature": sig,
                "tds_link": vd.get('tds_link'),
            })

    for tup, entries in fingerprints.items():
        # Collect unique (manuf, machine, layer, post) signatures
        sigs = {e['signature'] for e in entries}
        if len(entries) > 1 and len(sigs) > 1:
            anomalies["phase3_duplicate_vals"].append({
                "values": list(tup),
                "entries": entries,
            })

    n3 = len(anomalies['phase3_duplicate_vals'])
    summary_lines.append("\n## Phase 3 — Duplicate value blocks")
    summary_lines.append(
        f"\nGroups where identical mechanical values appear across distinct "
        f"(mfg, machine, layer, post): **{n3}**")
    for a in anomalies['phase3_duplicate_vals'][:15]:
        summary_lines.append(f"\nValues {a['values']}:")
        for e in a['entries']:
            summary_lines.append(f"  - {e['material']} / {e['vendor_key']}")
    if n3 > 15:
        summary_lines.append(f"\n... +{n3 - 15} more")

    # ----- Phase 4: value range sanity --------------------------------------
    summary_lines.append("\n## Phase 4 — Per-category value ranges")
    for mat_name, mat in mats.items():
        cat_top = mat.get('category_top') or 'Other'
        rng = RANGES.get(cat_top) or RANGES['Other']
        for vk, vd in (mat.get('vendors') or {}).items():
            if not isinstance(vd, dict): continue
            issues = []
            ys = vd.get('yield_MPa') or vd.get('yield_z_MPa')
            uts = vd.get('uts_xy_MPa') or vd.get('uts_z_MPa')
            for name, val, (lo, hi) in [
                ("YS", ys, rng["YS"]),
                ("UTS", uts, rng["UTS"]),
                ("Elong", vd.get('elongation_xy_pct') or vd.get('elongation_z_pct'),
                 rng["Elong"]),
                ("HV", vd.get('hardness_HV'), rng["HV"]),
            ]:
                if val is None: continue
                try: f = float(val)
                except Exception: continue
                if f < lo or f > hi:
                    issues.append(f"{name}={f} out of [{lo}, {hi}] for {cat_top}")
            # YS > UTS check (per direction)
            for ys_k, uts_k in [("yield_MPa", "uts_xy_MPa"),
                                ("yield_z_MPa", "uts_z_MPa")]:
                ysv = vd.get(ys_k); utsv = vd.get(uts_k)
                if ysv and utsv:
                    try:
                        if float(ysv) > float(utsv) + 1:
                            issues.append(f"{ys_k}={ysv} > {uts_k}={utsv} (impossible)")
                    except Exception: pass
            if issues:
                anomalies["phase4_value_range"].append({
                    "material": mat_name, "vendor_key": vk,
                    "category_top": cat_top, "issues": issues,
                })

    n4 = len(anomalies['phase4_value_range'])
    summary_lines.append(f"\nIssues: **{n4}**")
    for a in anomalies['phase4_value_range'][:25]:
        summary_lines.append(f"\n- **{a['material']}** [{a['category_top']}] / `{a['vendor_key']}`")
        for issue in a['issues']:
            summary_lines.append(f"  - {issue}")
    if n4 > 25:
        summary_lines.append(f"\n... +{n4 - 25} more")

    # ----- Save outputs ----------------------------------------------------
    summary_lines.append("\n---")
    summary_lines.append(
        f"\n**Total anomalies**: Phase 1: {n1}, Phase 2: {n2}, "
        f"Phase 3: {n3}, Phase 4: {n4}")

    out_md = _lib.WORKSPACE / "verify_summary.md"
    out_md.write_text("\n".join(summary_lines), encoding="utf-8")
    out_json = _lib.WORKSPACE / "verify_anomalies.json"
    out_json.write_text(json.dumps(anomalies, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    print(f"materials={len(mats)}  vendors={total_v}  unique_URLs={len(by_url)}")
    print(f"  Phase 1 (label/link):        {n1}")
    print(f"  Phase 2 (material routing):  {n2}")
    print(f"  Phase 3 (duplicate values):  {n3}")
    print(f"  Phase 4 (range sanity):      {n4}")
    print(f"\nSummary: {out_md}")
    print(f"Details: {out_json}")


if __name__ == "__main__":
    main()
