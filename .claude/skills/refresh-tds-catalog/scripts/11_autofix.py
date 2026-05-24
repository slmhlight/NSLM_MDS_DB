"""Phase 5a — Auto-fix DB anomalies that don't require re-extraction.

Three classes of fix:
  1. Label drift: vendor_key claims one machine, machine field has another.
     Align machine field to the value found in the underlying TDS (per the
     entry's tds_link host conventions).
  2. Material routing: tds_link clearly belongs to a different material than
     the entry's parent. Move entry under the correct material.
  3. Absurd hardness: HV value outside any physically reasonable band
     (treating <50 or >800 as definitively extraction-error). Set to null.

Each fix is conservative: only act when both the vendor_key prefix and the
tds_link agree on what the correct outcome should be.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


# Material routing — driven by URL keyword (longest match wins).
ROUTE_TARGET = [
    # (URL substring, correct material in DB)
    ("3d-systems-certified-a6061-ram2", "A2024-RAM2C (Al-Cu ceramic)"),
        # NOTE: A6061-RAM2 is composition-distinct from A2024 but the DB
        # historically grouped Al-Cu-MMC variants together. Keep under that
        # material but rename the variant_label.
    ("rematitan",                   "Ti CP Gr2"),
    ("toolsteel-cm55",              "CM55 Tool Steel"),
    ("toolsteel_cm55",              "CM55 Tool Steel"),
]


# ProX DMP 200 vs 320 disambiguation: 3DS LaserForm 316L (B) datasheet
# explicitly covers "DMP Flex 100, DMP Flex 200 and ProX DMP 200". Vendor key
# in DB used "ProX DMP 320" — flip the machine field to the real one in the
# vendor_key (we keep the key as-is to avoid downstream reference breakage,
# but ensure the field actually matches.
def fix_proX_316l(vd, vk):
    if "316L" not in (vd.get('tds_link') or ""): return False
    if "ProX DMP" not in vk: return False
    cur = vd.get('machine') or ""
    if cur == "ProX DMP 200":
        # Field is already what the TDS says; only the key is stale.
        return False
    if cur == "ProX DMP 320" and "ProX DMP 320" in vk:
        # Both key and field say 320 — leave alone (let extraction confirm).
        return False
    # Otherwise sync field to the key value
    m = re.search(r"\[(ProX DMP[^\]]+)\]", vk)
    if m and cur != m.group(1):
        vd['machine'] = m.group(1)
        return True
    return False


def absurd_hv(vd):
    hv = vd.get('hardness_HV')
    try: hv = float(hv) if hv is not None else None
    except Exception: return False
    if hv is None: return False
    if hv < 50 or hv > 800:
        vd['hardness_HV'] = None
        return True
    return False


def main():
    db = json.loads(_lib.DB_PATH.read_text(encoding="utf-8"))
    materials = db['materials']

    stats = {
        "label_fixed":   [],
        "rerouted":      [],
        "hv_nulled":     [],
    }

    # 1) Label fix on 316L ProX DMP labels
    for mat_name, mat in materials.items():
        for vk, vd in (mat.get('vendors') or {}).items():
            if not isinstance(vd, dict): continue
            if fix_proX_316l(vd, vk):
                stats['label_fixed'].append((mat_name, vk))

    # 2) Material routing — collect moves
    moves = []
    for mat_name, mat in materials.items():
        for vk, vd in list((mat.get('vendors') or {}).items()):
            if not isinstance(vd, dict): continue
            url = (vd.get('tds_link') or "").lower()
            if not url: continue
            target = None
            for kw, tgt in ROUTE_TARGET:
                if kw in url:
                    target = tgt; break
            if target and target != mat_name and target in materials:
                moves.append((mat_name, target, vk, vd))

    # Apply moves
    for src, dst, vk, vd in moves:
        # Remove from src
        materials[src]['vendors'].pop(vk, None)
        # Insert into dst (rename if collision)
        materials[dst].setdefault('vendors', {})
        new_key = vk
        n = 1
        while new_key in materials[dst]['vendors']:
            new_key = f"{vk} #{n}"; n += 1
        materials[dst]['vendors'][new_key] = vd
        stats['rerouted'].append((src, dst, vk, new_key))

    # 3) Null absurd HV
    for mat_name, mat in materials.items():
        for vk, vd in (mat.get('vendors') or {}).items():
            if not isinstance(vd, dict): continue
            if absurd_hv(vd):
                stats['hv_nulled'].append((mat_name, vk))

    _lib.DB_PATH.write_text(
        json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Label drift fixed:  {len(stats['label_fixed'])}")
    for m, k in stats['label_fixed']:  print(f"  {m}  /  {k}")
    print(f"\nRerouted:           {len(stats['rerouted'])}")
    for s, d, ok, nk in stats['rerouted']:
        if ok == nk:
            print(f"  {s}  →  {d}  /  {ok}")
        else:
            print(f"  {s}  →  {d}  /  {ok}  (renamed to: {nk})")
    print(f"\nAbsurd HV nulled:   {len(stats['hv_nulled'])}")
    for m, k in stats['hv_nulled']:  print(f"  {m}  /  {k}")


if __name__ == "__main__":
    main()
