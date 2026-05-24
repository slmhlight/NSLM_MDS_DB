"""Phase 1 — Discover TDS URLs from each vendor's catalog landing page(s).

Writes _tds_workspace/discovery.json with shape:

  {
    "<vendor>": {
      "<catalog_url>": {
        "fetched": true|false,
        "error": "...",
        "tds_urls": [
          {"tds_url": "...", "kind": "...", "catalog_slug": "...",
           "material_hint": "..."}, ...
        ]
      }
    }
  }

Usage:
  python 01_discover.py [--vendor eos|ge_additive|three_d_systems|nikon]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib                                                  # noqa: E402
from parsers import eos, ge_additive, three_d_systems, nikon  # noqa: E402


PARSERS = {
    "eos":              eos.discover_from_catalog,
    "ge_additive":      ge_additive.discover_from_catalog,
    "three_d_systems":  three_d_systems.discover_from_catalog,
    "nikon":            nikon.discover_from_catalog,
}


def discover_vendor(vendor: str, catalogs: list[str]) -> dict:
    out = {}
    parser = PARSERS[vendor]
    for cat_url in catalogs:
        try:
            html_bytes, _ct = _lib.http_get(cat_url)
            html = html_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            _lib.append_anomaly(
                f"[{vendor}] catalog page fetch failed: {cat_url} → "
                f"{type(e).__name__}: {e}")
            out[cat_url] = {"fetched": False, "error": str(e), "tds_urls": []}
            continue
        try:
            urls = parser(cat_url, html)
        except Exception as e:
            _lib.append_anomaly(
                f"[{vendor}] catalog parser raised on {cat_url}: "
                f"{type(e).__name__}: {e}")
            urls = []
        if not urls:
            _lib.append_anomaly(
                f"[{vendor}] no TDS URLs discovered on {cat_url} "
                "(page layout changed?)")
        out[cat_url] = {"fetched": True, "tds_urls": urls}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", choices=list(PARSERS.keys()),
                     help="Limit discovery to one vendor")
    args = ap.parse_args()

    _lib.ensure_workspace()
    _lib.reset_anomalies()

    vendors_cfg = _lib.load_catalogs()
    target = [args.vendor] if args.vendor else list(vendors_cfg.keys())

    discovery: dict = _lib.load_json(_lib.DISCOVERY_PATH, {})

    for vendor in target:
        if vendor not in vendors_cfg:
            print(f"[warn] {vendor} not in catalogs.json"); continue
        cfg = vendors_cfg[vendor]
        catalogs = cfg.get("catalogs", [])
        print(f"== {vendor} ({len(catalogs)} catalog page(s)) ==")
        discovery[vendor] = discover_vendor(vendor, catalogs)
        total = sum(len(v["tds_urls"]) for v in discovery[vendor].values())
        # Fallback for vendors whose catalogs are bot-blocked / SPA-rendered:
        # supplement with a known-good URL list from catalogs.json. The skill
        # owner refreshes this list manually whenever a new TDS version is
        # released (3D Systems being the current case).
        fallback = cfg.get("fallback_tds_urls") or []
        if fallback:
            existing = {u["tds_url"] for cat in discovery[vendor].values()
                        for u in cat["tds_urls"]}
            extra = [u for u in fallback if u not in existing]
            if extra:
                discovery[vendor].setdefault("_fallback", {
                    "fetched": True, "from_fallback_list": True,
                    "tds_urls": [],
                })
                for u in extra:
                    discovery[vendor]["_fallback"]["tds_urls"].append({
                        "tds_url":       u,
                        "kind":          "pdf_fallback",
                        "catalog_slug":  "fallback_known_urls",
                        "material_hint": u.rsplit("/", 1)[-1],
                    })
                total += len(extra)
                _lib.append_anomaly(
                    f"[{vendor}] used fallback_tds_urls list "
                    f"({len(extra)} extra URLs) because catalog crawl returned "
                    f"too few results")
        print(f"   discovered {total} TDS URL(s)")

    _lib.save_json(_lib.DISCOVERY_PATH, discovery)
    print(f"\nWrote {_lib.DISCOVERY_PATH}")


if __name__ == "__main__":
    main()
