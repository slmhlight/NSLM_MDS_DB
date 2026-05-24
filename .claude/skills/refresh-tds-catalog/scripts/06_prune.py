"""Phase 6 — Prune unhelpful placeholder vendor entries.

Identifies vendor entries whose `tds_link` points to a "material-summary"
page rather than a per-(machine × layer) data sheet — these don't carry
mechanical-property tables and shouldn't pose as vendor entries. Currently
that means EOS `/metal-solutions/metal-materials/data-sheets/mds-eos-...`
URLs that the EOS HTML agent confirmed empty.

For each such entry:
  - Move the URL onto the material's `ref_urls` list (so the catalog page
    is still discoverable from the dialog as a reference).
  - Remove the vendor entry itself.

Idempotent: skips entries already migrated. Reports the changes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


PRUNE_PATTERNS = [
    r"/metal-solutions/metal-materials/data-sheets/mds-eos-",
]


def is_aggregator_url(url: str) -> bool:
    if not url: return False
    return any(re.search(p, url) for p in PRUNE_PATTERNS)


def main():
    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))
    pruned = added_ref = 0
    for mat_name, mat in db.get("materials", {}).items():
        vendors = mat.get("vendors") or {}
        to_remove = []
        for vk, vd in vendors.items():
            if not isinstance(vd, dict): continue
            url = vd.get("tds_link")
            if not is_aggregator_url(url): continue
            # Only prune if the entry didn't acquire mechanical data
            if vd.get("_tds_verified"): continue
            to_remove.append((vk, url))
        for vk, url in to_remove:
            # Add to ref_urls (avoid duplicate)
            mat.setdefault("ref_urls", [])
            already = any(isinstance(r, (list, tuple)) and len(r) >= 2 and r[1] == url
                          for r in mat["ref_urls"])
            if not already:
                tail = url.rstrip("/").rsplit("/", 1)[-1]
                label = f"EOS MDS summary — {tail.replace('mds-eos-', '').replace('-', ' ')}"
                mat["ref_urls"].append([label, url])
                added_ref += 1
            del vendors[vk]
            pruned += 1
        if pruned:
            mat["vendors"] = vendors

    _lib.DB_PATH.write_text(
        json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Pruned {pruned} placeholder vendor entries (aggregator URLs).")
    print(f"Migrated {added_ref} URL(s) to material-level ref_urls.")


if __name__ == "__main__":
    main()
