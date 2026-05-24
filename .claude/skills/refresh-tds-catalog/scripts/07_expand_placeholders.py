"""Phase 7 — Expand single-placeholder entries into multi-record actuals.

When `05_seed_new.py` seeds a vendor entry from a URL it doesn't yet know
the (machine × layer × heat-treatment) breakdown, so it creates ONE
placeholder vendor entry. After agent extraction often produces N>1 records
from the same URL (e.g. one EOS MDS PDF covers 4 machines × 2 HT states).

This pass:
  1. Finds each vendor entry with `_tds_extraction_missing: true`.
  2. Looks up its `tds_link` in any `_tds_workspace/agent_*.json` files.
  3. If records exist for that URL, deletes the placeholder and inserts N
     new vendor entries — one per record, with proper machine/layer/HT.
  4. Entries whose URL still has no records remain as-is (truly missing).

After this, run `04_apply.py` once more to re-verify all values.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib   # noqa: E402


def collect_records_by_url() -> dict:
    """Tolerant collector — agents have produced two JSON shapes:
      a) {"manufacturer": "...", "by_url": {url: {"records": [...]}}}
      b) {url: {"records": [...]}}  (URL as top-level key)
    """
    by_url: dict[str, list] = {}

    def absorb(url, blk):
        if not isinstance(blk, dict): return
        for r in blk.get("records", []):
            by_url.setdefault(url, []).append(r)

    for f in glob.glob(str(_lib.WORKSPACE / "agent_*.json")):
        j = json.loads(Path(f).read_text(encoding="utf-8"))
        if "by_url" in j and isinstance(j["by_url"], dict):
            for url, blk in j["by_url"].items():
                absorb(url, blk)
        # Flat shape: any top-level key that looks like a URL
        for k, v in j.items():
            if isinstance(k, str) and k.startswith(("http://", "https://")):
                absorb(k, v)

    extracted = _lib.load_json(_lib.EXTRACTED_PATH, {})
    for url, blk in extracted.items():
        for r in blk.get("records", []):
            r2 = dict(r); r2.setdefault("_manufacturer", "EOS")
            by_url.setdefault(url, []).append(r2)
    return by_url


def build_vendor_key(manufacturer, machine, post_treatment, layer, variant):
    parts = [manufacturer]
    if machine: parts.append(f"[{machine}]")
    pt = post_treatment or "as-built"
    layer_s = f"({layer}μm)" if layer else "(layer ?)"
    base = " ".join(parts) + f" @ {pt} {layer_s}"
    if variant: base += f" ({variant})"
    return base


def main():
    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))
    by_url = collect_records_by_url()

    stats = {"placeholders_found": 0, "expanded_to_entries": 0,
             "still_missing": 0, "expanded_from_urls": 0}

    for mat_name, mat in db.get("materials", {}).items():
        vendors = mat.get("vendors") or {}
        to_remove = []
        to_add = []
        for vk, vd in vendors.items():
            if not isinstance(vd, dict): continue
            if not vd.get("_tds_extraction_missing"): continue
            stats["placeholders_found"] += 1
            url = vd.get("tds_link")
            if not url or url not in by_url:
                stats["still_missing"] += 1
                continue
            records = by_url[url]
            if not records:
                stats["still_missing"] += 1
                continue
            variant = vd.get("_variant_label")
            manufacturer = vd.get("manufacturer", "?")
            to_remove.append(vk)
            for r in records:
                new_entry = {
                    "manufacturer":          manufacturer,
                    "machine":               r.get("machine"),
                    "post_treatment":        r.get("post_treatment"),
                    "layer_thickness_um":    r.get("layer_thickness_um"),
                    "yield_MPa":             r.get("yield_xy_MPa"),
                    "yield_z_MPa":           r.get("yield_z_MPa"),
                    "uts_xy_MPa":            r.get("uts_xy_MPa"),
                    "uts_z_MPa":             r.get("uts_z_MPa"),
                    "elongation_xy_pct":     r.get("elongation_xy_pct"),
                    "elongation_z_pct":      r.get("elongation_z_pct"),
                    "elongation_pct":        (r.get("elongation_xy_pct") or
                                              r.get("elongation_z_pct")),
                    "hardness_HV":           r.get("hardness_HV"),
                    "surface_ra_lo":         r.get("surface_ra_lo"),
                    "surface_ra_hi":         r.get("surface_ra_hi"),
                    "tds_link":              url,
                    "_tds_verified":         True,
                }
                if variant: new_entry["_variant_label"] = variant
                key = build_vendor_key(
                    manufacturer, r.get("machine"), r.get("post_treatment"),
                    r.get("layer_thickness_um"), variant)
                to_add.append((key, new_entry))
                stats["expanded_to_entries"] += 1
            stats["expanded_from_urls"] += 1

        for vk in to_remove:
            vendors.pop(vk, None)
        for base_key, entry in to_add:
            key = base_key
            n = 1
            while key in vendors:
                key = f"{base_key} #{n}"; n += 1
            vendors[key] = entry

    _lib.DB_PATH.write_text(
        json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Placeholders found:    {stats['placeholders_found']}")
    print(f"  expanded to entries: {stats['expanded_to_entries']} "
          f"(from {stats['expanded_from_urls']} URLs)")
    print(f"  still no records:    {stats['still_missing']}")


if __name__ == "__main__":
    main()
