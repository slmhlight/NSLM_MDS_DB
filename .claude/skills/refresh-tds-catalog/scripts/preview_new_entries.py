"""Show what would change if we accepted every discovered URL.

Categorises each newly-discovered TDS URL (not already in material_db.json's
tds_link set) into one of:
  - existing-material  : matches a current DB material → new vendor entry
  - new-material       : composition-distinct → adds a new top-level material
  - unmapped           : no rule matched → user must extend _material_aliases.py

Pure preview — does not modify the DB.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse, parse_qsl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib                            # noqa: E402
from _material_aliases import match_material  # noqa: E402


def normalize_url(u: str) -> str:
    p = urlparse(u)
    qs = "&".join(f"{k}={v}" for k, v in parse_qsl(p.query) if k == "v")
    return f"{p.scheme}://{p.netloc.lower()}{p.path}" + (f"?{qs}" if qs else "")


def main():
    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))
    discovery = _lib.load_json(_lib.DISCOVERY_PATH, {})

    db_urls = set()
    for mat in db.get("materials", {}).values():
        for vd in (mat.get("vendors") or {}).values():
            if isinstance(vd, dict) and vd.get("tds_link"):
                db_urls.add(normalize_url(vd["tds_link"]))

    buckets = {
        "existing-material": defaultdict(list),  # mat_name -> [(url, variant)]
        "new-material":      defaultdict(list),  # proposed_name -> [(url, note)]
        "unmapped":          [],
    }

    by_vendor_summary = defaultdict(lambda: defaultdict(int))

    VENDOR_LABEL = {
        "eos": "EOS",
        "ge_additive": "GE Additive",
        "three_d_systems": "3D Systems",
        "nikon": "Nikon SLM Solutions",
    }

    for vendor, cats in discovery.items():
        for cat_url, info in cats.items():
            for ref in info.get("tds_urls", []):
                u = ref["tds_url"]
                if normalize_url(u) in db_urls: continue
                tail = u.rsplit("/", 1)[-1]
                hint = ref.get("material_hint") or tail
                slug = ref.get("catalog_slug") or ""
                ex, variant, new = match_material(
                    tail + " " + hint + " " + slug)
                vlabel = VENDOR_LABEL.get(vendor, vendor)
                if ex:
                    buckets["existing-material"][ex].append(
                        (vlabel, variant, u))
                    by_vendor_summary[vlabel]["existing"] += 1
                elif new:
                    buckets["new-material"][new["name"]].append(
                        (vlabel, new["category"], new["note"], u))
                    by_vendor_summary[vlabel]["new"] += 1
                else:
                    buckets["unmapped"].append((vlabel, u))
                    by_vendor_summary[vlabel]["unmapped"] += 1

    # ---- print report -----------------------------------------------------
    print("=" * 70)
    print("NEW URLS — proposed disposition")
    print("=" * 70)
    print()
    print("Summary by vendor:")
    for v, counts in sorted(by_vendor_summary.items()):
        print(f"  {v:25} existing={counts['existing']:3}  "
              f"new={counts['new']:3}  unmapped={counts['unmapped']:3}")
    print()

    print(f"--- adds vendor entries to EXISTING materials "
          f"({sum(len(v) for v in buckets['existing-material'].values())} URLs) ---")
    for mat, lst in sorted(buckets["existing-material"].items()):
        print(f"  {mat}  ({len(lst)} new entries)")
        for vlabel, variant, u in lst[:6]:
            v = f" «{variant}»" if variant else ""
            print(f"    + [{vlabel}]{v}  {u.rsplit('/', 1)[-1]}")
        if len(lst) > 6:
            print(f"    ... +{len(lst) - 6} more")

    print()
    nm_count = sum(len(v) for v in buckets['new-material'].values())
    print(f"--- adds NEW top-level materials "
          f"({len(buckets['new-material'])} materials, {nm_count} URLs) ---")
    for mat_name, lst in sorted(buckets["new-material"].items()):
        first = lst[0]
        print(f"  + {mat_name}  [{first[1]}]  ({len(lst)} URL(s))")
        print(f"      note: {first[2]}")
        for vlabel, _cat, _note, u in lst:
            print(f"      - [{vlabel}]  {u.rsplit('/', 1)[-1]}")

    if buckets["unmapped"]:
        print()
        print(f"--- UNMAPPED ({len(buckets['unmapped'])} URLs — need rule "
              f"in _material_aliases.py) ---")
        for vlabel, u in buckets["unmapped"]:
            print(f"  ? [{vlabel}]  {u.rsplit('/', 1)[-1]}")

    print()
    print("=" * 70)
    print(f"Will add {sum(len(v) for v in buckets['existing-material'].values())} "
          f"vendor entries to existing materials, "
          f"create {len(buckets['new-material'])} new materials, "
          f"and leave {len(buckets['unmapped'])} unmapped URLs.")


if __name__ == "__main__":
    main()
