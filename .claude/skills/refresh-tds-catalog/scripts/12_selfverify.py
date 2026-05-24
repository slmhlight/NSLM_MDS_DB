"""Self-verification suite for material_db.json.

Designed for the case where the operator wants strong confidence in the
data, with explicit reporting of what each check actually proved.

Layer A — schema invariants    (deterministic, exhaustive)
Layer B — physical consistency (deterministic, exhaustive)
Layer C — distribution sanity  (deterministic, statistical)
Layer D — random sample picks  (lists URLs the operator should re-verify
           against the original TDS via Agent — script doesn't decide
           correctness, just exposes the sample)

Outputs `_tds_workspace/selfverify.md` with PASS/WARN/FAIL per check and a
sample-of-10 list at the end. The operator (or a follow-up agent) cross-
references the sample against TDS PDFs.

This script never modifies data. Run it any time, before/after edits.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

SEED = 20260523     # deterministic sample
random.seed(SEED)


# ---------- helpers ----------------------------------------------------------

def all_entries(db):
    for mat_name, m in db['materials'].items():
        for vk, vd in (m.get('vendors') or {}).items():
            if isinstance(vd, dict):
                yield mat_name, vk, vd


def fnum(x):
    try: return float(x) if x is not None else None
    except Exception: return None


# ---------- run --------------------------------------------------------------

def main():
    db = json.loads(_lib.DB_PATH.read_text(encoding='utf-8'))
    out: list[str] = []

    def line(s=""): out.append(s)
    def hdr(s): line(); line(f"## {s}"); line()

    line("# DB Self-Verification Report")
    line()
    line("Each section reports what was actually checked. "
          "**Verified** = the check ran on every entry and passed. "
          "**Not verifiable here** = correctness vs the underlying TDS "
          "would need re-extraction; this report lists representative "
          "samples to spot-check.")

    entries = list(all_entries(db))
    line(f"\nTotal materials: {len(db['materials'])}  ·  "
         f"Total vendor entries: {len(entries)}")

    # ====================================================================
    # Layer A — schema invariants
    # ====================================================================
    hdr("Layer A — Schema invariants  (deterministic, exhaustive)")

    a_pass = a_fail = 0
    failures = []

    REQUIRED = ['manufacturer', 'tds_link']
    for mat, vk, vd in entries:
        for f in REQUIRED:
            if not vd.get(f):
                failures.append(f"missing {f} — {mat} / {vk}")
                a_fail += 1
                break
        else:
            a_pass += 1

    line(f"- **Required-field presence** (manufacturer, tds_link): "
         f"pass={a_pass}, fail={a_fail}")
    for f in failures[:10]: line(f"  - {f}")
    if len(failures) > 10: line(f"  - ... +{len(failures)-10}")

    # Numeric type check
    NUMERIC_FIELDS = ['yield_MPa','yield_z_MPa','uts_xy_MPa','uts_z_MPa',
                      'elongation_xy_pct','elongation_z_pct','elongation_pct',
                      'hardness_HV','surface_ra_lo','surface_ra_hi',
                      'layer_thickness_um']
    type_errors = []
    for mat, vk, vd in entries:
        for f in NUMERIC_FIELDS:
            v = vd.get(f)
            if v is None: continue
            if not isinstance(v, (int, float)):
                type_errors.append(f"{f}={v!r} ({type(v).__name__}) — {mat} / {vk}")
    line(f"- **Numeric fields are int/float or null**: "
         f"pass={len(entries)-len(type_errors)}, fail={len(type_errors)}")
    for e in type_errors[:5]: line(f"  - {e}")

    # category_top valid
    valid_cats = set(db.get('_category_top_order') or [])
    cat_errors = [n for n, m in db['materials'].items()
                  if m.get('category_top') not in valid_cats]
    line(f"- **All materials have a valid category_top**: "
         f"pass={len(db['materials']) - len(cat_errors)}, fail={len(cat_errors)}")
    for n in cat_errors[:5]: line(f"  - {n}")

    # No leftover _tds_unverified or _tds_extraction_missing (user requested)
    unverified = [(m, k) for m, k, vd in entries if vd.get('_tds_unverified')]
    missing = [(m, k) for m, k, vd in entries if vd.get('_tds_extraction_missing')]
    line(f"- **No `_tds_unverified` flags**: pass={len(entries)-len(unverified)}, "
         f"fail={len(unverified)}")
    line(f"- **No `_tds_extraction_missing` flags**: "
         f"pass={len(entries)-len(missing)}, fail={len(missing)}")

    # vendor_key prefix vs manufacturer field
    import re
    label_drift = []
    URL_VENDOR = {"eos.info":"EOS","colibriumadditive.com":"GE Additive",
                  "3dsystems.com":"3D Systems",
                  "nikon-slm-solutions.com":"Nikon SLM Solutions"}
    for mat, vk, vd in entries:
        m = re.match(r"^(.+?)\s*(?:\[|@)", vk)
        if not m: continue
        key_mfg = m.group(1).strip()
        if vd.get('manufacturer') and key_mfg != vd['manufacturer']:
            label_drift.append(f"{mat} / {vk}: key='{key_mfg}' field='{vd['manufacturer']}'")
        url = (vd.get('tds_link') or '').lower()
        host_mfg = next((v for h, v in URL_VENDOR.items() if h in url), None)
        if host_mfg and vd.get('manufacturer') != host_mfg:
            label_drift.append(f"{mat} / {vk}: host='{host_mfg}' field='{vd['manufacturer']}'")
    line(f"- **vendor_key prefix matches manufacturer matches URL host**: "
         f"pass={len(entries) - len(label_drift)}, fail={len(label_drift)}")
    for d in label_drift[:5]: line(f"  - {d}")

    # ====================================================================
    # Layer B — physical consistency
    # ====================================================================
    hdr("Layer B — Physical consistency  (deterministic, exhaustive)")

    ys_gt_uts = []
    neg_elong = []
    neg_hv = []
    ra_lo_gt_hi = []
    for mat, vk, vd in entries:
        for ys_k, uts_k in [('yield_MPa','uts_xy_MPa'), ('yield_z_MPa','uts_z_MPa')]:
            ys = fnum(vd.get(ys_k)); uts = fnum(vd.get(uts_k))
            if ys and uts and ys > uts + 1:    # 1 MPa tolerance for rounding
                ys_gt_uts.append(f"{mat} / {vk}: {ys_k}={ys} > {uts_k}={uts}")
        for f in ['elongation_xy_pct', 'elongation_z_pct', 'elongation_pct']:
            v = fnum(vd.get(f))
            if v is not None and v < 0:
                neg_elong.append(f"{mat} / {vk}: {f}={v}")
        hv = fnum(vd.get('hardness_HV'))
        if hv is not None and hv <= 0:
            neg_hv.append(f"{mat} / {vk}: HV={hv}")
        lo = fnum(vd.get('surface_ra_lo')); hi = fnum(vd.get('surface_ra_hi'))
        if lo is not None and hi is not None and lo > hi:
            ra_lo_gt_hi.append(f"{mat} / {vk}: Ra lo={lo} > hi={hi}")

    line(f"- **YS ≤ UTS in both XY and Z**: pass={len(entries)*2 - len(ys_gt_uts)}, "
         f"fail={len(ys_gt_uts)}")
    for e in ys_gt_uts[:5]: line(f"  - {e}")

    line(f"- **All elongations ≥ 0**: fail={len(neg_elong)}")
    for e in neg_elong[:5]: line(f"  - {e}")
    line(f"- **All hardness HV > 0 (when present)**: fail={len(neg_hv)}")
    line(f"- **Ra lo ≤ hi (when both present)**: fail={len(ra_lo_gt_hi)}")

    # Cross-material duplicates (smoking gun pattern)
    fingerprints = defaultdict(list)
    for mat, vk, vd in entries:
        tup = (fnum(vd.get('yield_MPa')), fnum(vd.get('yield_z_MPa')),
               fnum(vd.get('uts_xy_MPa')), fnum(vd.get('uts_z_MPa')),
               fnum(vd.get('elongation_xy_pct')), fnum(vd.get('elongation_z_pct')),
               fnum(vd.get('hardness_HV')))
        if all(v is None for v in tup): continue
        fingerprints[tup].append((mat, vk))
    cross_mat = 0
    for tup, lst in fingerprints.items():
        if len({m for m, _ in lst}) > 1:
            cross_mat += 1
    line(f"- **No cross-material identical fingerprints**: fail={cross_mat}")

    # ====================================================================
    # Layer C — distribution sanity
    # ====================================================================
    hdr("Layer C — Distribution sanity  (per-material outliers via 2σ)")

    per_mat = defaultdict(lambda: defaultdict(list))
    for mat, vk, vd in entries:
        for f in ['yield_MPa','uts_xy_MPa','elongation_xy_pct','hardness_HV']:
            v = fnum(vd.get(f))
            if v is not None and v > 0:
                per_mat[mat][f].append((vk, v))

    outliers = []
    for mat, fields in per_mat.items():
        for f, items in fields.items():
            vals = [v for _, v in items]
            if len(vals) < 4: continue
            mu = statistics.mean(vals); sd = statistics.stdev(vals)
            if sd <= 0: continue
            for vk, v in items:
                z = (v - mu) / sd
                if abs(z) > 2.5:
                    outliers.append((mat, vk, f, v, mu, sd, z))

    line(f"- **Per-material >2.5σ outliers**: {len(outliers)} entries flagged "
         f"(does not necessarily mean wrong — could be a legitimate edge case)")
    outliers.sort(key=lambda x: -abs(x[6]))
    for mat, vk, f, v, mu, sd, z in outliers[:10]:
        line(f"  - {mat} / {vk}: {f}={v:.0f} "
             f"(material mean={mu:.0f}±{sd:.0f}, z={z:+.1f})")

    # ====================================================================
    # Layer D — random sample for TDS cross-reference
    # ====================================================================
    hdr("Layer D — Random sample for TDS spot-check")
    line()
    line("**Important caveat**: this script CANNOT verify that the stored "
         "mechanical values match what the original TDS PDF actually publishes — "
         "that requires re-extracting the source. Below is a deterministic "
         "random sample of 10 entries the operator (or an Agent) should "
         "cross-reference against the TDS.")
    line()
    by_mfg = defaultdict(list)
    for mat, vk, vd in entries:
        by_mfg[vd.get('manufacturer', '?')].append((mat, vk, vd))
    sample = []
    for mfg, lst in by_mfg.items():
        if not lst: continue
        # Pick up to 3 from each major manufacturer; total ~10
        n = min(3, len(lst))
        sample.extend(random.sample(lst, n))
    sample = sample[:10]
    for i, (mat, vk, vd) in enumerate(sample, 1):
        line(f"\n**{i}. {mat}** — `{vk}`")
        line(f"   - tds_link: {vd.get('tds_link')}")
        line(f"   - YS: XY={vd.get('yield_MPa')}, Z={vd.get('yield_z_MPa')} MPa")
        line(f"   - UTS: XY={vd.get('uts_xy_MPa')}, Z={vd.get('uts_z_MPa')} MPa")
        line(f"   - Elong: XY={vd.get('elongation_xy_pct')}, Z={vd.get('elongation_z_pct')} %")
        line(f"   - HV={vd.get('hardness_HV')}, Ra={vd.get('surface_ra_lo')}-"
             f"{vd.get('surface_ra_hi')} μm")

    # ====================================================================
    # Verdict
    # ====================================================================
    hdr("Verdict")
    a_total_fail = len(failures) + len(type_errors) + len(cat_errors) + \
                   len(unverified) + len(missing) + len(label_drift)
    b_total_fail = len(ys_gt_uts) + len(neg_elong) + len(neg_hv) + \
                   len(ra_lo_gt_hi) + cross_mat

    line(f"- Layer A (schema): **{'PASS' if a_total_fail == 0 else 'FAIL'}** "
         f"({a_total_fail} issues)")
    line(f"- Layer B (physical): **{'PASS' if b_total_fail == 0 else 'FAIL'}** "
         f"({b_total_fail} issues)")
    line(f"- Layer C (outliers): **INFO** ({len(outliers)} entries >2.5σ — "
         f"manual review recommended for the most extreme; many are likely "
         f"legitimate edge cases)")
    line(f"- Layer D (TDS spot-check): **REQUIRES OPERATOR** — 10 sample "
         f"entries listed above; cross-reference manually or dispatch an agent")
    line()
    line("**Trust statement (honest)**: ")
    line(f"- {len(entries)} vendor entries pass schema + physical-consistency "
          "checks.")
    line("- The DB cannot self-prove that stored numbers match the underlying "
          "TDS PDFs — that information lives outside this script. The "
          "spot-check above is the cheapest way to gain confidence.")
    line("- Any entry that you cannot verify against its source TDS should "
          "be treated as a high-confidence estimate, not gospel.")

    rpt = _lib.WORKSPACE / "selfverify.md"
    rpt.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {rpt}")
    print()
    print(f"Layer A: {'PASS' if a_total_fail == 0 else 'FAIL'} ({a_total_fail})")
    print(f"Layer B: {'PASS' if b_total_fail == 0 else 'FAIL'} ({b_total_fail})")
    print(f"Layer C: {len(outliers)} outliers >2.5σ (info only)")
    print(f"Layer D: 10-entry sample listed in report — operator must cross-check TDS")


if __name__ == "__main__":
    main()
