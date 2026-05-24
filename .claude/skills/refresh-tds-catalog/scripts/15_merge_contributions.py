"""Phase 15 — Merge contributions/pending/*.json into the master DB.

Walks `contributions/pending/`, runs the same validation as `contribute.py
validate` on each file, and applies the change interactively (default) or
in batch (`--yes`). Accepted files move to `contributions/applied/<merge-
date>/`. Rejected files stay in `pending/` with a `.rejected` sibling
explaining why.

Pipeline expectation:
  1. Maintainer pulls a PR with new files in pending/
  2. Runs this script — reviews each one
  3. Runs the verifier (10_verify.py)
  4. Encrypts a new release (db_crypto.py encrypt --also-append-keystore)
  5. Commits the .enc + the applied/ moves, force-pushes the release

This script never writes the plain DB to a place that would be committed
— it only edits `data/material_db.json`, which is in `.gitignore`.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

PROJECT_ROOT = _lib.PROJECT_ROOT
DB_PATH = _lib.DB_PATH
PENDING_DIR = PROJECT_ROOT / "contributions" / "pending"
APPLIED_DIR = PROJECT_ROOT / "contributions" / "applied"


# ---------- helpers ---------------------------------------------------------

def _confirm(prompt, default="y"):
    suffix = " [Y/n]" if default.lower() == "y" else " [y/N]"
    raw = input(f"{prompt}{suffix} ").strip().lower() or default.lower()
    return raw in ("y", "yes")


def _build_vendor_key(entry):
    mfg = entry.get('manufacturer') or '?'
    machine = entry.get('machine') or '?'
    post = entry.get('post_treatment') or 'as-built'
    layer = entry.get('layer_thickness_um')
    layer_s = f"({layer}μm)" if layer else "(layer ?)"
    return f"{mfg} [{machine}] @ {post} {layer_s}"


def _ensure_unique_key(vendors_dict, base_key):
    if base_key not in vendors_dict: return base_key
    n = 1
    while f"{base_key} #{n}" in vendors_dict: n += 1
    return f"{base_key} #{n}"


def _apply_add_vendor(db, payload, contribution):
    target = payload.get("target_material")
    mat = db['materials'].get(target)
    if not mat:
        return False, f"target_material {target!r} not in DB"
    entry = dict(payload['entry'])
    entry['_tds_verified'] = True
    entry['_submitted_by'] = contribution.get('submitted_by')
    entry['_submitted_at'] = contribution.get('submitted_at')
    entry['_contribution_source'] = contribution.get('source')
    # Compute elongation_pct from XY (legacy fallback)
    e_xy = entry.get('elongation_xy_pct')
    e_z = entry.get('elongation_z_pct')
    if 'elongation_pct' not in entry:
        entry['elongation_pct'] = e_xy if e_xy is not None else e_z
    mat.setdefault('vendors', {})
    key = _ensure_unique_key(mat['vendors'], _build_vendor_key(entry))
    mat['vendors'][key] = entry
    return True, key


def _apply_add_material(db, payload, contribution):
    name = payload.get("name")
    if not name:
        return False, "payload.name missing"
    if name in db['materials']:
        return False, f"material {name!r} already exists"
    fve = payload.get('first_vendor_entry') or {}
    if not fve:
        return False, "first_vendor_entry missing"
    new_mat = {
        "category":         payload.get("category", "Other"),
        "category_top":     payload.get("category_top", "Other"),
        "density":          payload.get("density"),
        "melt":             payload.get("melt"),
        "thermal_k":        payload.get("thermal_k"),
        "cp":               payload.get("cp"),
        "cte":              payload.get("cte"),
        "E":                payload.get("E"),
        "poisson":          payload.get("poisson"),
        "magnetic":         payload.get("magnetic", "-"),
        "composition":      payload.get("composition", []),
        "applications":     payload.get("applications", "-"),
        "ref_urls":         payload.get("ref_urls", []),
        "heat_treatments":  {},
        "vendors":          {},
        "_added_by_contribution": contribution.get("submitted_by"),
        "_added_at":              contribution.get("submitted_at"),
        "_added_source":          contribution.get("source"),
    }
    # Seed the first vendor entry
    fve_copy = dict(fve)
    fve_copy['_tds_verified'] = True
    fve_copy['_submitted_by'] = contribution.get('submitted_by')
    fve_copy['_submitted_at'] = contribution.get('submitted_at')
    fve_copy['_contribution_source'] = contribution.get('source')
    e_xy = fve_copy.get('elongation_xy_pct')
    e_z = fve_copy.get('elongation_z_pct')
    fve_copy['elongation_pct'] = e_xy if e_xy is not None else e_z
    key = _build_vendor_key(fve_copy)
    new_mat['vendors'][key] = fve_copy
    db['materials'][name] = new_mat
    return True, name


def _apply_update_vendor(db, payload, contribution):
    target = payload.get('target_material')
    vk = payload.get('vendor_key')
    mat = db['materials'].get(target)
    if not mat:
        return False, f"target_material {target!r} not in DB"
    vd = mat.get('vendors', {}).get(vk)
    if not vd:
        return False, f"vendor_key {vk!r} not found under {target!r}"
    changes = payload.get('changes') or {}
    for k, v in changes.items():
        vd[k] = v
    if payload.get('new_tds_link'):
        vd['tds_link'] = payload['new_tds_link']
    vd['_last_update_by'] = contribution.get('submitted_by')
    vd['_last_update_at'] = contribution.get('submitted_at')
    vd['_last_update_source'] = contribution.get('source')
    return True, f"{target} / {vk}"


APPLY = {
    "add_vendor_entry":     _apply_add_vendor,
    "add_material":         _apply_add_material,
    "update_vendor_entry":  _apply_update_vendor,
}


# ---------- validation re-use ----------------------------------------------

def _validate(d):
    """Same checks as contribute.py validate, condensed."""
    issues = []
    for f in ("schema_version", "type", "submitted_by", "submitted_at",
              "source", "rationale", "payload"):
        if f not in d: issues.append(f"missing: {f}")
    if d.get("schema_version") != 1:
        issues.append(f"schema_version != 1")
    if d.get("type") not in APPLY:
        issues.append(f"unsupported type: {d.get('type')!r}")
    return issues


# ---------- main ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--yes", "-y", action="store_true",
                     help="Accept every valid contribution without prompting")
    ap.add_argument("--dry-run", action="store_true",
                     help="Validate + show plan; don't modify DB or move files")
    args = ap.parse_args()

    if not PENDING_DIR.is_dir():
        print(f"(no {PENDING_DIR} folder — nothing to do)"); return

    files = sorted(PENDING_DIR.glob("*.json"))
    if not files:
        print("No pending contributions."); return

    db = json.loads(DB_PATH.read_text(encoding="utf-8"))

    today_dir = APPLIED_DIR / _dt.date.today().isoformat()
    summary = {"applied": [], "rejected": []}

    for f in files:
        print(f"\n────── {f.name} ──────")
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  REJECT — JSON parse failed: {e}")
            summary['rejected'].append((f.name, "json_parse"))
            continue

        issues = _validate(d)
        if issues:
            print("  REJECT — validation:")
            for i in issues: print(f"    - {i}")
            summary['rejected'].append((f.name, "validation"))
            continue

        typ = d['type']
        payload = d.get('payload') or {}
        print(f"  type:        {typ}")
        print(f"  submitted:   {d['submitted_by']} @ {d['submitted_at']}")
        print(f"  source:      {d['source']}")
        print(f"  rationale:   {d['rationale']}")
        if typ == "add_vendor_entry":
            entry = payload.get('entry', {})
            print(f"  → {payload.get('target_material')} / {_build_vendor_key(entry)}")
            print(f"    YS XY={entry.get('yield_MPa')} Z={entry.get('yield_z_MPa')}  "
                  f"UTS XY={entry.get('uts_xy_MPa')} Z={entry.get('uts_z_MPa')}  "
                  f"Elong XY={entry.get('elongation_xy_pct')} Z={entry.get('elongation_z_pct')}")
        elif typ == "add_material":
            print(f"  → new material: {payload.get('name')} "
                  f"[{payload.get('category_top')}]")
            print(f"    composition: {len(payload.get('composition') or [])} elements")
        elif typ == "update_vendor_entry":
            print(f"  → update {payload.get('target_material')} / {payload.get('vendor_key')}")
            print(f"    changes: {payload.get('changes')}")

        if not args.yes:
            if not _confirm("\n  apply?"):
                print("  skipped (left in pending/)")
                continue

        if args.dry_run:
            print("  [dry-run — not modifying DB]")
            continue

        fn = APPLY[typ]
        ok, msg = fn(db, payload, d)
        if not ok:
            print(f"  REJECT — apply failed: {msg}")
            (f.parent / (f.name + ".rejected")).write_text(
                f"# Rejected at {_dt.datetime.utcnow().isoformat()}\n"
                f"# reason: {msg}\n", encoding="utf-8")
            summary['rejected'].append((f.name, f"apply: {msg}"))
            continue

        print(f"  ✓ applied: {msg}")
        # Move file to applied/<today>/
        today_dir.mkdir(parents=True, exist_ok=True)
        dst = today_dir / f.name
        shutil.move(str(f), str(dst))
        summary['applied'].append((f.name, msg))

    if not args.dry_run:
        DB_PATH.write_text(json.dumps(db, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    print(f"\n────── summary ──────")
    print(f"applied:  {len(summary['applied'])}")
    for n, m in summary['applied']: print(f"  + {n}  →  {m}")
    print(f"rejected: {len(summary['rejected'])}")
    for n, r in summary['rejected']: print(f"  - {n}  →  {r}")
    if summary['applied'] and not args.dry_run:
        print(f"\nNext: ")
        print(f"  python .claude/skills/refresh-tds-catalog/scripts/12_selfverify.py")
        print(f"  python db_crypto.py encrypt data/material_db.json \\")
        print(f"      --also-append-keystore keys.master.txt")


if __name__ == "__main__":
    main()
