"""Contribution helper — create / validate new-entry submissions.

Use cases for end users who have a TDS the maintainer hasn't indexed yet:

    python contribute.py add-vendor    # interactive wizard
    python contribute.py add-material  # interactive wizard
    python contribute.py validate <file.json>
    python contribute.py find-key <mfg> <machine> <post> <layer>
    python contribute.py list          # show pending contributions

Each command writes a JSON file into `contributions/pending/` that you
can commit and submit as a pull request. See `contributions/SCHEMA.md`
for the full schema.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "material_db.json"
PENDING_DIR = PROJECT_ROOT / "contributions" / "pending"

CATEGORY_TOPS = ["Aluminium", "Cobalt", "Copper", "Nickel",
                  "Steel", "Titanium", "Niobium", "Other"]


# ---------------------------------------------------------------------------
# DB awareness
# ---------------------------------------------------------------------------

def _load_db():
    """Try to load DB so we can validate target_material / find_key.

    Falls back to (None, "") if the DB isn't accessible — validation
    still runs the structural checks, just can't confirm material names.
    """
    if DB_PATH.exists():
        try:
            return json.loads(DB_PATH.read_text(encoding="utf-8")), str(DB_PATH)
        except Exception: pass
    # Try the encrypted archive path for contributors who don't have
    # the plain file (most contributors).
    try:
        from resource_helper import load_material_db
        return load_material_db()
    except Exception:
        return None, ""


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def _ask(prompt, default=None, required=True, cast=None, choices=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"  {prompt}{suffix}: ").strip()
        if not raw:
            if default is not None: raw = str(default)
            elif not required: return None
            else:
                print("    (required)"); continue
        if choices and raw not in choices:
            print(f"    (choose from {choices})"); continue
        if cast:
            try: return cast(raw)
            except Exception as e:
                print(f"    (cast {cast.__name__} failed: {e})"); continue
        return raw


def _ask_optional_float(prompt):
    raw = _ask(prompt + " (blank = null)", default="", required=False)
    if raw in (None, ""): return None
    try: return float(raw)
    except Exception:
        print("    (not a number — leaving null)"); return None


def _build_entry(default_machine=""):
    """Prompt for one vendor-entry dict."""
    return {
        "manufacturer":        _ask("manufacturer (e.g. EOS, Nikon SLM Solutions)"),
        "machine":             _ask("machine", default=default_machine),
        "post_treatment":      _ask("post_treatment (as-built / heat-treated / H900 / ...)",
                                    default="as-built"),
        "layer_thickness_um":  _ask("layer thickness µm", cast=int),
        "yield_MPa":           _ask_optional_float("YS XY (MPa)"),
        "yield_z_MPa":         _ask_optional_float("YS Z (MPa)"),
        "uts_xy_MPa":          _ask_optional_float("UTS XY (MPa)"),
        "uts_z_MPa":           _ask_optional_float("UTS Z (MPa)"),
        "elongation_xy_pct":   _ask_optional_float("Elong XY (%)"),
        "elongation_z_pct":    _ask_optional_float("Elong Z (%)"),
        "hardness_HV":         _ask_optional_float("Hardness HV"),
        "surface_ra_lo":       _ask_optional_float("Surface Ra lo (µm)"),
        "surface_ra_hi":       _ask_optional_float("Surface Ra hi (µm)"),
        "tds_link":            _ask("tds_link (URL)"),
    }


def _envelope(type_str, source, rationale):
    return {
        "schema_version": 1,
        "type":           type_str,
        "submitted_by":   _ask("your GitHub username"),
        "submitted_at":   _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "source":         source,
        "rationale":      rationale,
    }


def _slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", s.strip().lower()).strip("-")
    return s or "unknown"


def _write_pending(contribution: dict) -> Path:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    typ = contribution["type"]
    if typ in ("add_vendor_entry", "update_vendor_entry"):
        target = contribution["payload"].get("target_material") or "unknown"
    elif typ == "add_material":
        target = contribution["payload"].get("name") or "unknown"
    else:
        target = "unknown"
    date = _dt.date.today().isoformat().replace("-", "")
    author = contribution.get("submitted_by", "anon")
    name = f"{typ}_{_slug(target)}_{date}_{_slug(author)}.json"
    out = PENDING_DIR / name
    out.write_text(json.dumps(contribution, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_add_vendor():
    db, _ = _load_db()
    materials = list((db.get("materials") or {}).keys()) if db else []
    print("\n=== Add vendor entry to an existing material ===\n")
    target = _ask("target_material (must match the DB exactly)")
    if db and target not in materials:
        # Suggest close matches
        suggestions = [m for m in materials
                       if target.lower() in m.lower()
                       or any(w in m.lower() for w in target.lower().split())]
        print(f"\n  WARN: '{target}' not in DB.")
        if suggestions:
            print(f"  Did you mean: {suggestions[:8]}")
        if _ask("continue anyway? (y/N)", default="N").lower() != "y":
            return
    src = _ask("\nsource URL (TDS link)")
    rat = _ask("rationale (one sentence)")
    print("\n=== Vendor entry values (leave blank for null) ===\n")
    entry = _build_entry()
    # Use the same URL for tds_link if user didn't override
    if not entry.get("tds_link"): entry["tds_link"] = src

    contrib = _envelope("add_vendor_entry", src, rat)
    contrib["payload"] = {"target_material": target, "entry": entry}

    out = _write_pending(contrib)
    print(f"\nSaved: {out}")
    print("Next: `python contribute.py validate <that path>` then commit/PR.")


def cmd_add_material():
    print("\n=== Add a brand-new material ===\n")
    name = _ask("name (e.g. 'Inconel 706')")
    cat = _ask("category (free text, e.g. 'Nickel Alloy')")
    cat_top = _ask("category_top",
                    choices=CATEGORY_TOPS, default="Other")
    src = _ask("\nsource URL (TDS / authoritative spec)")
    rat = _ask("rationale (why a new slot vs. merging into existing?)")
    print("\n=== Basic physical / thermal (leave blank = null) ===\n")
    density = _ask_optional_float("density g/cm³")
    melt = _ask_optional_float("melting point °C")
    therm_k = _ask_optional_float("thermal conductivity W/m·K")
    cp = _ask_optional_float("Cp J/kg·K")
    cte = _ask_optional_float("CTE 1e-6/K")
    E = _ask_optional_float("Young's modulus GPa")
    poisson = _ask_optional_float("Poisson ratio")
    mag = _ask("magnetic (non-magnetic / ferromagnetic / paramagnetic / -)",
                default="-")
    apps = _ask("applications (short description)")

    print("\n=== Composition rows — repeat element:wt% lines, blank to finish ===")
    comp = []
    while True:
        ln = input("  element[:wt%] (blank to end): ").strip()
        if not ln: break
        if ":" in ln:
            el, pct = ln.split(":", 1)
        elif "=" in ln:
            el, pct = ln.split("=", 1)
        elif " " in ln:
            el, pct = ln.split(None, 1)
        else:
            el, pct = ln, "?"
        comp.append([el.strip(), pct.strip()])

    print("\n=== First vendor entry ===\n")
    entry = _build_entry()
    if not entry.get("tds_link"): entry["tds_link"] = src

    contrib = _envelope("add_material", src, rat)
    contrib["payload"] = {
        "name": name, "category": cat, "category_top": cat_top,
        "density": density, "melt": melt, "thermal_k": therm_k,
        "cp": cp, "cte": cte, "E": E, "poisson": poisson,
        "magnetic": mag, "composition": comp,
        "applications": apps,
        "ref_urls": [[ f"{name} reference", src ]],
        "first_vendor_entry": entry,
    }

    out = _write_pending(contrib)
    print(f"\nSaved: {out}")
    print("Next: `python contribute.py validate <that path>` then commit/PR.")


def cmd_validate(path):
    p = Path(path)
    if not p.is_file():
        print(f"ERROR — {path} not found"); return 1
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR — JSON parse: {e}"); return 1

    issues = []
    # Envelope
    for f in ("schema_version", "type", "submitted_by", "submitted_at",
              "source", "rationale", "payload"):
        if f not in d:
            issues.append(f"envelope missing: {f}")
    if d.get("schema_version") != 1:
        issues.append(f"schema_version != 1 (got {d.get('schema_version')!r})")
    typ = d.get("type")
    if typ not in ("add_vendor_entry", "add_material", "update_vendor_entry"):
        issues.append(f"unknown type: {typ!r}")
    src = d.get("source") or ""
    if not src.startswith(("http://", "https://")):
        issues.append(f"source must be an http(s) URL, got: {src!r}")

    payload = d.get("payload") or {}
    db, _ = _load_db()
    db_mats = set((db.get("materials") or {}).keys()) if db else set()

    def _check_entry(e, ctx):
        if not isinstance(e, dict):
            issues.append(f"{ctx}: entry must be a dict"); return
        for f in ("manufacturer", "machine", "post_treatment",
                  "layer_thickness_um", "tds_link"):
            if not e.get(f): issues.append(f"{ctx}: entry.{f} missing")
        # Physical sanity
        def _f(k):
            v = e.get(k);
            try: return float(v) if v is not None else None
            except: return None
        for ys_k, uts_k in [("yield_MPa", "uts_xy_MPa"),
                             ("yield_z_MPa", "uts_z_MPa")]:
            ys, uts = _f(ys_k), _f(uts_k)
            if ys is not None and uts is not None and ys > uts + 1:
                issues.append(f"{ctx}: {ys_k}={ys} > {uts_k}={uts} "
                              f"(physically impossible)")
        for elf in ("elongation_xy_pct", "elongation_z_pct"):
            v = _f(elf)
            if v is not None and not (0 <= v <= 100):
                issues.append(f"{ctx}: {elf}={v} out of [0,100]")
        hv = _f("hardness_HV")
        if hv is not None and not (10 <= hv <= 1000):
            issues.append(f"{ctx}: hardness_HV={hv} out of [10,1000]")
        u = e.get("tds_link") or ""
        if not u.startswith(("http://", "https://")):
            issues.append(f"{ctx}: entry.tds_link not a valid URL: {u!r}")

    if typ == "add_vendor_entry":
        tgt = payload.get("target_material")
        if not tgt:
            issues.append("payload.target_material missing")
        elif db_mats and tgt not in db_mats:
            issues.append(f"payload.target_material {tgt!r} not in current "
                          f"DB ({len(db_mats)} materials)")
        _check_entry(payload.get("entry"), "payload.entry")
    elif typ == "add_material":
        name = payload.get("name")
        if not name: issues.append("payload.name missing")
        elif db_mats and name in db_mats:
            issues.append(f"payload.name {name!r} already exists in DB — "
                          "use add_vendor_entry or update_vendor_entry instead")
        if payload.get("category_top") not in CATEGORY_TOPS:
            issues.append(f"payload.category_top must be one of {CATEGORY_TOPS}")
        comp = payload.get("composition") or []
        if not comp:
            issues.append("payload.composition empty — at least the base "
                          "element + 'balance' should be provided")
        _check_entry(payload.get("first_vendor_entry"),
                     "payload.first_vendor_entry")
    elif typ == "update_vendor_entry":
        if not payload.get("target_material"):
            issues.append("payload.target_material missing")
        if not payload.get("vendor_key"):
            issues.append("payload.vendor_key missing")
        if not isinstance(payload.get("changes"), dict):
            issues.append("payload.changes must be a dict")

    if issues:
        print(f"FAIL — {len(issues)} issue(s):")
        for i in issues: print(f"  - {i}")
        return 2
    print("OK")
    return 0


def cmd_find_key(mfg, machine, post, layer):
    db, _ = _load_db()
    if not db:
        print("ERROR — DB not loadable"); return 1
    target_layer = int(layer)
    hits = []
    for mat_name, mat in db['materials'].items():
        for vk, vd in (mat.get('vendors') or {}).items():
            if not isinstance(vd, dict): continue
            if vd.get('manufacturer') != mfg: continue
            if vd.get('machine') != machine: continue
            if vd.get('post_treatment') != post: continue
            if vd.get('layer_thickness_um') != target_layer: continue
            hits.append((mat_name, vk))
    if not hits:
        print(f"no entries matching ({mfg!r}, {machine!r}, "
              f"{post!r}, {target_layer}μm)")
        return 1
    for mat, vk in hits:
        print(f"{mat}  /  {vk}")


def cmd_list():
    if not PENDING_DIR.is_dir():
        print("(no pending/ folder yet)"); return
    files = sorted(PENDING_DIR.glob("*.json"))
    if not files:
        print("(no pending contributions)"); return
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            typ = d.get("type")
            who = d.get("submitted_by", "?")
            payload = d.get("payload") or {}
            target = (payload.get("target_material")
                      or payload.get("name")
                      or "?")
            print(f"  {f.name}")
            print(f"    {typ}  →  {target}  (by {who})")
        except Exception as e:
            print(f"  {f.name}  — UNREADABLE ({e})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("add-vendor",
                    help="Interactive wizard — add a vendor entry to an "
                         "existing material")
    sub.add_parser("add-material",
                    help="Interactive wizard — propose a brand-new material")
    v = sub.add_parser("validate", help="Validate a contribution JSON file")
    v.add_argument("file")
    fk = sub.add_parser("find-key",
                        help="Look up a vendor_key by its 4-tuple")
    fk.add_argument("manufacturer")
    fk.add_argument("machine")
    fk.add_argument("post")
    fk.add_argument("layer")
    sub.add_parser("list", help="List pending contributions")

    args = ap.parse_args()
    if args.cmd == "add-vendor":   cmd_add_vendor()
    elif args.cmd == "add-material": cmd_add_material()
    elif args.cmd == "validate":   sys.exit(cmd_validate(args.file))
    elif args.cmd == "find-key":
        sys.exit(cmd_find_key(args.manufacturer, args.machine, args.post,
                               args.layer) or 0)
    elif args.cmd == "list":       cmd_list()


if __name__ == "__main__":
    main()
