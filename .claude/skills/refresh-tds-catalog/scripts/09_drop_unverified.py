"""Phase 9 — Delete vendor entries that don't have a usable TDS.

Targets:
  - Entries flagged `_tds_unverified: true` (URL was unreachable / fake /
    chart-only / placeholder host)
  - Entries with NO `tds_link` at all (legacy stubs)

Then prune any material that ends with zero vendor entries — no source-of-
truth means nothing to show in the MDS viewer.

Idempotent. Reports what was removed.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


def main():
    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))

    removed_entries = []
    by_reason = defaultdict(int)
    for mat_name, mat in db.get("materials", {}).items():
        vendors = mat.get("vendors") or {}
        to_drop = []
        for vk, vd in vendors.items():
            if not isinstance(vd, dict):
                to_drop.append((vk, "not_a_dict")); continue
            if vd.get("_tds_unverified"):
                to_drop.append((vk, "unverified")); continue
            if not vd.get("tds_link"):
                to_drop.append((vk, "no_link")); continue
        for vk, reason in to_drop:
            del vendors[vk]
            removed_entries.append((mat_name, vk, reason))
            by_reason[reason] += 1
        mat["vendors"] = vendors

    # Now prune empty materials
    removed_materials = []
    for mat_name in list(db.get("materials", {}).keys()):
        mat = db["materials"][mat_name]
        if not (mat.get("vendors") or {}):
            del db["materials"][mat_name]
            removed_materials.append(mat_name)

    _lib.DB_PATH.write_text(
        json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Removed {len(removed_entries)} vendor entries:")
    for reason, n in by_reason.items():
        print(f"  [{reason}]: {n}")
    print()
    if removed_materials:
        print(f"Pruned {len(removed_materials)} empty material(s):")
        for n in removed_materials:
            print(f"  - {n}")
    else:
        print("No empty materials to prune.")
    print()
    print(f"DB now: {len(db['materials'])} materials, "
          f"{sum(len(m.get('vendors') or {}) for m in db['materials'].values())}"
          f" vendor entries.")


if __name__ == "__main__":
    main()
