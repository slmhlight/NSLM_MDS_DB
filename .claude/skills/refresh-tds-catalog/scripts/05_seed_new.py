"""Phase 5 (out-of-band) — Seed new vendor entries + new materials.

For each newly-discovered TDS URL that isn't in material_db.json yet:
  * If the material aliases map it to an EXISTING material → append a
    placeholder vendor entry under that material with `_tds_extraction_missing`.
  * If aliases say NEW material → create the top-level material slot
    (empty composition, empty heat_treatments) and seed one placeholder
    vendor entry.

Placeholder vendor entries carry only `manufacturer`, `tds_link`, the
parsed-from-URL machine / layer hints (best-effort), and the
`_tds_extraction_missing: true` flag. A later run of `03_extract.py` +
`04_apply.py` will fill in actual numbers from the TDS.

Idempotent — running twice is safe; URLs already present in DB are skipped.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qsl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib                                  # noqa: E402
from _material_aliases import match_material  # noqa: E402


VENDOR_LABEL = {
    "eos": "EOS",
    "ge_additive": "GE Additive",
    "three_d_systems": "3D Systems",
    "nikon": "Nikon SLM Solutions",
}


def normalize_url(u: str) -> str:
    p = urlparse(u)
    qs = "&".join(f"{k}={v}" for k, v in parse_qsl(p.query) if k == "v")
    return f"{p.scheme}://{p.netloc.lower()}{p.path}" + (f"?{qs}" if qs else "")


def guess_machine_and_layer(url: str, vendor: str) -> tuple[str | None, int | None]:
    """Best-effort parse of (machine, layer_um) from a TDS filename.

    None values mean the file doesn't encode that info — the real extraction
    step will fill them in.
    """
    tail = unquote(url.rsplit("/", 1)[-1]).lower()

    layer = None
    m = re.search(r"(\d{2,3})\s*um|(\d{2,3})\s*µm|_(\d{2,3})um", tail)
    if m:
        for g in m.groups():
            if g: layer = int(g); break

    machine = None
    if vendor == "eos":
        m = re.search(r"eos-m-?(\d{2,3})(?:-(\d))?", tail)
        if m:
            machine = f"M{m.group(1)}"
            if m.group(2): machine += f"-{m.group(2)}"
        elif "m4-onyx" in tail:
            machine = "M4 Onyx"
    elif vendor == "ge_additive":
        if tail.startswith("m2series5") or "m2series5" in tail:
            machine = "M2 Series 5"
        elif tail.startswith("mline") or "mline" in tail or "m line" in tail:
            machine = "M Line"
        elif "xline" in tail:
            machine = "X Line 2000R"
        elif "mlab" in tail:
            machine = "MLab"
    elif vendor == "nikon":
        # mds5xxx filenames don't say machine; will be filled by extractor
        machine = None
    elif vendor == "three_d_systems":
        if "laserform" in tail and ("dmp" in tail or "prox" in tail):
            machine = "ProX DMP 320"
        elif "certified" in tail or "laserform" in tail:
            machine = "DMP Flex 350"

    return machine, layer


def guess_post_treatment(url: str) -> str:
    """For URL patterns alone we can rarely tell HT state — default to
    'as-built' and let the extractor refine. The placeholder is marked
    `_tds_extraction_missing` so this never sticks long-term.
    """
    tail = unquote(url.rsplit("/", 1)[-1]).lower()
    if "h900"  in tail: return "H900"
    if "h1025" in tail: return "H1025"
    if "h1150" in tail: return "H1150"
    if "t6"    in tail: return "T6"
    if "aged"  in tail: return "aged"
    if "ht"    in tail and "hip" in tail: return "HT_HIP"
    return "as-built"


def build_vendor_key(manufacturer, machine, post_treatment, layer, variant):
    parts = []
    parts.append(manufacturer)
    if machine: parts.append(f"[{machine}]")
    pt = post_treatment or "as-built"
    layer_s = f"({layer}μm)" if layer else "(layer ?)"
    base = " ".join(parts) + f" @ {pt} {layer_s}"
    if variant: base += f" ({variant})"
    return base


def build_placeholder_entry(vendor, url, ref, variant=None):
    mfg = VENDOR_LABEL.get(vendor, vendor)
    machine, layer = guess_machine_and_layer(url, vendor)
    pt = guess_post_treatment(url)
    return {
        "manufacturer":          mfg,
        "machine":               machine,
        "post_treatment":        pt,
        "layer_thickness_um":    layer,
        "yield_MPa":             None,
        "yield_z_MPa":           None,
        "uts_xy_MPa":            None,
        "uts_z_MPa":             None,
        "elongation_xy_pct":     None,
        "elongation_z_pct":      None,
        "elongation_pct":        None,
        "hardness_HV":           None,
        "surface_ra_lo":         None,
        "surface_ra_hi":         None,
        "tds_link":              url,
        "_tds_extraction_missing": True,
        "_variant_label":        variant,
    }


def main():
    _lib.ensure_workspace()
    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))
    discovery = _lib.load_json(_lib.DISCOVERY_PATH, {})
    materials = db.setdefault("materials", {})

    db_urls = set()
    for mat in materials.values():
        for vd in (mat.get("vendors") or {}).values():
            if isinstance(vd, dict) and vd.get("tds_link"):
                db_urls.add(normalize_url(vd["tds_link"]))

    plan = {"added_existing": [], "added_new_material": [], "skipped": []}

    for vendor, cats in discovery.items():
        for cat_url, info in cats.items():
            for ref in info.get("tds_urls", []):
                u = ref["tds_url"]
                if normalize_url(u) in db_urls:
                    plan["skipped"].append(u); continue
                tail = u.rsplit("/", 1)[-1]
                hint = ref.get("material_hint") or tail
                slug = ref.get("catalog_slug") or ""
                ex, variant, new = match_material(
                    tail + " " + hint + " " + slug)
                if ex:
                    target = materials.get(ex)
                    if target is None:
                        plan["skipped"].append(u); continue
                    target.setdefault("vendors", {})
                    entry = build_placeholder_entry(vendor, u, ref, variant)
                    key = build_vendor_key(
                        entry["manufacturer"], entry["machine"],
                        entry["post_treatment"],
                        entry["layer_thickness_um"], variant)
                    # Avoid clobbering an existing same-key entry
                    n = 1
                    base_key = key
                    while key in target["vendors"]:
                        key = f"{base_key} #{n}"; n += 1
                    target["vendors"][key] = entry
                    db_urls.add(normalize_url(u))
                    plan["added_existing"].append(
                        {"material": ex, "url": u, "vendor_key": key})
                elif new:
                    name = new["name"]
                    if name not in materials:
                        materials[name] = {
                            "category":         new["category"],
                            "magnetic":         "-",
                            "density":          None,
                            "melt":             None,
                            "thermal_k":        None,
                            "cp":               None,
                            "cte":              None,
                            "E":                None,
                            "poisson":          None,
                            "composition":      [],
                            "applications":     new.get("note", "-"),
                            "ref_urls":         [],
                            "heat_treatments":  {},
                            "vendors":          {},
                            "_seeded_by_skill": True,
                        }
                    target = materials[name]
                    target.setdefault("vendors", {})
                    entry = build_placeholder_entry(vendor, u, ref)
                    key = build_vendor_key(
                        entry["manufacturer"], entry["machine"],
                        entry["post_treatment"],
                        entry["layer_thickness_um"], None)
                    n = 1; base_key = key
                    while key in target["vendors"]:
                        key = f"{base_key} #{n}"; n += 1
                    target["vendors"][key] = entry
                    db_urls.add(normalize_url(u))
                    plan["added_new_material"].append(
                        {"material": name, "url": u, "vendor_key": key,
                         "category": new["category"]})

    _lib.save_json(_lib.WORKSPACE / "new_entries_plan.json", plan)
    _lib.DB_PATH.write_text(
        json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Seeded {len(plan['added_existing'])} vendor entries to existing "
          f"materials.")
    print(f"Created {len({p['material'] for p in plan['added_new_material']})} "
          f"new top-level materials ({len(plan['added_new_material'])} URLs).")
    print(f"Plan saved to {_lib.WORKSPACE / 'new_entries_plan.json'}")
    print()
    print("Next: dispatch agents to extract TDS contents for the seeded "
          "URLs (they currently have _tds_extraction_missing: true).")


if __name__ == "__main__":
    main()
