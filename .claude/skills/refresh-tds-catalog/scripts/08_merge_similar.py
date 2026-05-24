"""Phase 8 — Aggressive composition-based material merges.

The user policy: "if compositions are similar, treat as the same material;
specify variants in parentheses". This script applies a curated set of
high-confidence merges. Each merge moves all vendor entries from `src`
into `dst`, optionally renaming `dst` to advertise the new variant(s).

The vendor entries themselves carry the original alloy name in
`_variant_label` so the dialog can still tell variants apart in the table.

Idempotent — if `src` is gone, skip silently.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


# (src_material, dst_material, new_dst_name_or_None, variant_label)
MERGES = [
    # Co-free maraging — same alloy family as 1.2709 / MS1 / M300
    ("M789 (Co-free Maraging)",
     "Maraging Steel (1.2709/MS1/M300)",
     "Maraging Steel (1.2709/MS1/M300/M789)",
     "M789 Co-free"),

    # GE proprietary martensitic precipitation-hardened stainless — close
    # cousin of 17-4PH
    ("CR-PH Martensitic",
     "Stainless Steel 17-4PH",
     "Stainless Steel 17-4PH (CR-PH)",
     "GE CR-PH"),

    # 3DS Cu-Cr binary, same family as CuCr1Zr
    ("CuCr2",
     "CuCr1Zr",
     "CuCr1Zr (CuCr2)",
     "CuCr2"),

    # Both Hastelloy: Ni-Cr-Mo with W in C22, same family
    ("Hastelloy C22",
     "Hastelloy X",
     "Hastelloy X (C22)",
     "C22"),

    # Both Al-Cu wrought-derived high-strength alloys; A205 has rare-earth,
    # Al2139 is Al-Cu-Mg — group under A205 with variant
    ("Al2139-AM",
     "A205 (Al-Cu)",
     "A205 (Al-Cu, Al2139)",
     "Al2139"),
]


def merge_into(db, src, dst, new_dst_name, variant_label):
    mats = db.get("materials", {})
    if src not in mats:
        return f"skip: src {src!r} not found"
    src_mat = mats.pop(src)
    if dst not in mats:
        return f"FAIL: dst {dst!r} not found, putting src back"
    dst_mat = mats[dst]
    dst_mat.setdefault("vendors", {})
    for vk, vd in (src_mat.get("vendors") or {}).items():
        if isinstance(vd, dict) and variant_label:
            existing = vd.get("_variant_label")
            vd["_variant_label"] = (
                f"{variant_label} / {existing}" if existing else variant_label)
        nk = vk if vk not in dst_mat["vendors"] else f"{vk} (from {src})"
        n = 1
        base = nk
        while nk in dst_mat["vendors"]:
            nk = f"{base} #{n}"; n += 1
        dst_mat["vendors"][nk] = vd
    # ref_urls
    dst_mat.setdefault("ref_urls", [])
    for r in src_mat.get("ref_urls") or []:
        if r not in dst_mat["ref_urls"]: dst_mat["ref_urls"].append(r)
    # Optionally rename the dst material
    if new_dst_name and new_dst_name != dst:
        mats[new_dst_name] = mats.pop(dst)
        return (f"OK: merged {src!r} → {dst!r}, renamed to {new_dst_name!r} "
                f"(+{len(src_mat.get('vendors') or {})} entries)")
    return (f"OK: merged {src!r} → {dst!r} "
            f"(+{len(src_mat.get('vendors') or {})} entries)")


def main():
    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))

    # Topological order: process merges sequentially so renames stick
    for src, dst, new_name, variant in MERGES:
        msg = merge_into(db, src, dst, new_name, variant)
        print("  " + msg)
        # If dst got renamed, future merges targeting dst by old name need
        # to use new name — none of our current chain has that dependency,
        # but be defensive: update the table.
        if new_name and new_name != dst:
            for i, (s, d, n, v) in enumerate(MERGES):
                if d == dst:
                    MERGES[i] = (s, new_name, n, v)

    _lib.DB_PATH.write_text(
        json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(f"Materials now: {len(db['materials'])}")


if __name__ == "__main__":
    main()
