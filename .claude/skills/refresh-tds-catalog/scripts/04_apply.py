"""Phase 4 — Apply extracted records to data/material_db.json.

Strategy:
  - Build a map { tds_url -> [records] } from extracted.json + any
    _agent_*.json files the user wrote during the Agent-fallback step.
  - For each vendor entry in the DB: if its tds_link matches an extracted
    source, match the best record by (machine, layer, post_treatment) and
    overwrite the mechanical-property fields + add `_tds_verified: true`.
    Drop stale `_tds_unverified` / `_tds_extraction_missing` flags.
  - For entries whose URL is in the manifest with an error (or known fake
    pattern): null the tensile fields, set `_tds_unverified: true`.
  - Recompute heat_treatments aggregates from updated vendor entries.

Anomaly reporting:
  - New (material, machine, layer) combinations found in extractions
    that the DB doesn't expose are appended to anomalies.md so the user
    can decide whether to add them.
  - Per-entry value changes >15 % relative drift are flagged.

Usage:
  python 04_apply.py [--dry-run]
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import statistics
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


def _norm(s):
    return re.sub(r"[\s_\-®/+]+", "", str(s or "").lower())


def _machine_match(a, b):
    na, nb = _norm(a), _norm(b)
    return bool(na) and bool(nb) and (na == nb or na in nb or nb in na)


def _pt_match(a, b):
    na, nb = _norm(a), _norm(b)
    return bool(na) and bool(nb) and (na == nb or na in nb or nb in na)


def best_match(entry, records):
    target_m = entry.get("machine") or ""
    target_l = entry.get("layer_thickness_um")
    target_p = entry.get("post_treatment") or ""
    scored = []
    for r in records:
        s = 0
        if _machine_match(target_m, r.get("machine", "")): s += 100
        if target_l and r.get("layer_thickness_um") == target_l: s += 50
        if _pt_match(target_p, r.get("post_treatment", "")): s += 30
        scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    return scored[0][1] if scored and scored[0][0] > 0 else None


def apply_record(entry, rec, anomalies_url=None):
    """Overwrite fields; report >15% drift if prior values present."""
    pairs = [
        ("yield_MPa",           "yield_xy_MPa"),
        ("yield_z_MPa",         "yield_z_MPa"),
        ("uts_xy_MPa",          "uts_xy_MPa"),
        ("uts_z_MPa",           "uts_z_MPa"),
        ("elongation_xy_pct",   "elongation_xy_pct"),
        ("elongation_z_pct",    "elongation_z_pct"),
        ("hardness_HV",         "hardness_HV"),
        ("surface_ra_lo",       "surface_ra_lo"),
        ("surface_ra_hi",       "surface_ra_hi"),
    ]
    for db_key, rec_key in pairs:
        new = rec.get(rec_key)
        old = entry.get(db_key)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) \
                and old > 0:
            drift = abs(new - old) / old
            if drift > 0.15:
                _lib.append_anomaly(
                    f"value drift >{int(drift*100)}% in {anomalies_url}: "
                    f"{db_key} {old} -> {new}")
        entry[db_key] = new
    # Legacy compat: keep elongation_pct in sync with XY value
    e_xy = rec.get("elongation_xy_pct")
    e_z = rec.get("elongation_z_pct")
    entry["elongation_pct"] = e_xy if e_xy is not None else e_z
    entry["_tds_verified"] = True
    for f in ("_tds_unverified", "_tds_extraction_missing", "_tds_no_match"):
        entry.pop(f, None)


NUM_FIELDS = (
    "yield_MPa", "yield_z_MPa", "uts_xy_MPa", "uts_z_MPa",
    "elongation_pct", "elongation_xy_pct", "elongation_z_pct",
    "hardness_HV", "surface_ra_lo", "surface_ra_hi",
)


def null_entry(entry):
    for f in NUM_FIELDS:
        if f in entry: entry[f] = None
    entry["_tds_unverified"] = True
    for f in ("_tds_verified", "_tds_extraction_missing", "_tds_no_match"):
        entry.pop(f, None)


# --- heat_treatments aggregation (uses TDS-updated values) ----------------

def normalize_pt(pt):
    p = (pt or "").lower().strip()
    if not p: return None
    if "as-built" in p or "as_built" in p or p == "as built" or "as manufactured" in p:
        return "as_built"
    if "h900" in p: return "H900"
    if "h1025" in p: return "H1025"
    if "h1150" in p: return "H1150"
    if "hip" in p: return "HT_HIP_age" if "age" in p else "HT_HIP"
    if ("solution" in p or "soln" in p) and ("age" in p or "aging" in p):
        return "solution+age"
    if "t6" in p: return "T6"
    if "stress" in p: return "stress_relieved"
    if "temper" in p: return "tempered"
    if "solution-anneal" in p or "solution_annealed" in p: return "annealed"
    if "anneal" in p: return "annealed"
    if "aged" in p or "aging" in p: return "aged"
    if "heat-treated" in p or "heat_treated" in p: return "heat-treated"
    return None


def _median(vs):
    vs = [float(v) for v in vs if v is not None and float(v) > 0]
    return round(statistics.median(vs), 1) if vs else None


def reagg_material(mat):
    vendors = mat.get("vendors") or {}
    buckets: dict[str, list] = {}
    for vk, vd in vendors.items():
        if not isinstance(vd, dict): continue
        b = normalize_pt(vd.get("post_treatment", ""))
        if b: buckets.setdefault(b, []).append(vd)

    new_ht = OrderedDict()
    for ht_key, ht_data in (mat.get("heat_treatments") or {}).items():
        entries = buckets.get(ht_key, [])
        if entries:
            agg = {
                "uts":         _median([v.get("uts_xy_MPa") for v in entries]),
                "uts_z":       _median([v.get("uts_z_MPa")  for v in entries]),
                "ys":          _median([v.get("yield_MPa")  for v in entries]),
                "ys_z":        _median([v.get("yield_z_MPa") for v in entries]),
                "elong":       _median([v.get("elongation_xy_pct") or v.get("elongation_pct")
                                       for v in entries]),
                "elong_z":     _median([v.get("elongation_z_pct") for v in entries]),
                "hardness_HV": _median([v.get("hardness_HV") for v in entries]),
                "hardness_HRC": None, "hardness_HB": None,
                "surface_ra_lo": min([v.get("surface_ra_lo") for v in entries if v.get("surface_ra_lo")] or [None]),
                "surface_ra_hi": max([v.get("surface_ra_hi") for v in entries if v.get("surface_ra_hi")] or [None]),
            }
        else:
            agg = {k: None for k in ("uts","uts_z","ys","ys_z","elong",
                                      "elong_z","hardness_HV","hardness_HRC",
                                      "hardness_HB","surface_ra_lo","surface_ra_hi")}
        agg["surface_ra_um"] = (
            f"{int(agg['surface_ra_lo'])}~{int(agg['surface_ra_hi'])}"
            if agg["surface_ra_lo"] and agg["surface_ra_hi"]
               and agg["surface_ra_lo"] != agg["surface_ra_hi"] else None)
        agg["notes"] = ht_data.get("notes") if isinstance(ht_data, dict) else None
        new_ht[ht_key] = agg

    for bucket, entries in buckets.items():
        if bucket in new_ht: continue
        # Surface new bucket from vendor data with same aggregation
        new_ht[bucket] = {
            "uts":         _median([v.get("uts_xy_MPa") for v in entries]),
            "uts_z":       _median([v.get("uts_z_MPa")  for v in entries]),
            "ys":          _median([v.get("yield_MPa")  for v in entries]),
            "ys_z":        _median([v.get("yield_z_MPa") for v in entries]),
            "elong":       _median([v.get("elongation_xy_pct") or v.get("elongation_pct") for v in entries]),
            "elong_z":     _median([v.get("elongation_z_pct") for v in entries]),
            "hardness_HV": _median([v.get("hardness_HV") for v in entries]),
            "hardness_HRC": None, "hardness_HB": None,
            "surface_ra_lo": None, "surface_ra_hi": None, "surface_ra_um": None,
            "notes": None,
        }

    mat["heat_treatments"] = new_ht


# --- main -----------------------------------------------------------------

def collect_records() -> dict:
    """Return {tds_url: [records_with_manufacturer]}."""
    by_url: dict[str, list] = {}
    extracted = _lib.load_json(_lib.EXTRACTED_PATH, {})
    for url, blk in extracted.items():
        vendor = blk.get("vendor")
        mfg = {
            "eos": "EOS",
            "ge_additive": "GE Additive",
            "three_d_systems": "3D Systems",
            "nikon": "Nikon SLM Solutions",
        }.get(vendor, vendor)
        for r in blk.get("records", []):
            r2 = dict(r); r2["_manufacturer"] = mfg
            by_url.setdefault(url, []).append(r2)
    # Also merge any agent-side JSON: _tds_workspace/agent_*.json
    for f in glob.glob(str(_lib.WORKSPACE / "agent_*.json")):
        j = json.loads(Path(f).read_text(encoding="utf-8"))
        for url, blk in (j.get("by_url") or {}).items():
            for r in blk.get("records", []):
                r2 = dict(r)
                r2.setdefault("_manufacturer", blk.get("manufacturer"))
                by_url.setdefault(url, []).append(r2)
    return by_url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))
    by_url = collect_records()
    manifest = _lib.load_json(_lib.MANIFEST_PATH, {})
    bad_urls = {u for u, v in manifest.items() if v.get("error")}

    stats = {"verified": 0, "nulled": 0, "preserved": 0, "missed": 0}
    for mat_name, mat in db.get("materials", {}).items():
        for vk, vd in (mat.get("vendors") or {}).items():
            if not isinstance(vd, dict): continue
            url = vd.get("tds_link")
            if url and url in by_url:
                rec = best_match(vd, by_url[url])
                if rec:
                    apply_record(vd, rec, anomalies_url=f"{mat_name}/{vk}")
                    stats["verified"] += 1
                    continue
                else:
                    _lib.append_anomaly(
                        f"no record matched {mat_name}/{vk} in {url}")
                    stats["missed"] += 1
                    continue
            if url and url in bad_urls:
                null_entry(vd)
                stats["nulled"] += 1
                continue
            # Preserve whatever state the entry already has
            stats["preserved"] += 1

        reagg_material(mat)

    # New (vendor, material) combos in extractions that no DB entry references
    db_urls = set()
    for mat in db.get("materials", {}).values():
        for vd in (mat.get("vendors") or {}).values():
            if isinstance(vd, dict) and vd.get("tds_link"):
                db_urls.add(vd["tds_link"])
    new_urls = [u for u in by_url.keys() if u not in db_urls]
    if new_urls:
        _lib.append_anomaly(
            f"{len(new_urls)} new TDS URL(s) extracted but not referenced by "
            f"any vendor entry — likely new (material × machine) products. "
            f"See _tds_workspace/extracted.json for details.")

    if not args.dry_run:
        _lib.DB_PATH.write_text(
            json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"verified={stats['verified']}  nulled={stats['nulled']}  "
          f"preserved={stats['preserved']}  missed={stats['missed']}  "
          f"new_unreferenced_urls={len(new_urls)}")


if __name__ == "__main__":
    main()
