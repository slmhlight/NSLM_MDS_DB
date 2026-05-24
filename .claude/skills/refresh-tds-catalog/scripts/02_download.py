"""Phase 2 — Download every TDS URL discovered in phase 1.

Reads _tds_workspace/discovery.json, fetches each tds_url, writes cached
copies into _tds_workspace/cache/, and persists a manifest.

3D Systems URLs that hit HTTP 403 are listed in
_tds_workspace/cache/needs_webfetch.json — the Claude orchestrator should
invoke WebFetch on those (since the WebFetch tool bypasses the urllib 403)
and write the downloaded PDFs into the cache manually before phase 3.

Usage:
  python 02_download.py [--vendor eos|ge_additive|three_d_systems|nikon]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", default=None)
    args = ap.parse_args()

    _lib.ensure_workspace()
    discovery = _lib.load_json(_lib.DISCOVERY_PATH, {})
    manifest = _lib.load_json(_lib.MANIFEST_PATH, {})
    needs_webfetch: list[dict] = []

    for vendor, cats in discovery.items():
        if args.vendor and vendor != args.vendor: continue
        urls = []
        for cat_url, info in cats.items():
            for ref in info.get("tds_urls", []):
                u = ref["tds_url"]
                # Skip 3D Systems for direct fetch — known 403
                if "3dsystems.com" in u:
                    needs_webfetch.append(ref | {"vendor": vendor})
                    continue
                # Skip follow-up "material_page" placeholders
                if ref.get("kind") == "material_page_followup":
                    continue
                urls.append(u)

        urls = [u for u in urls if u not in manifest
                or not manifest[u].get("path")
                or not Path(manifest[u].get("path", "")).exists()]
        if not urls:
            print(f"[{vendor}] nothing to fetch (all cached)"); continue
        print(f"[{vendor}] fetching {len(urls)} URL(s)...")
        results = _lib.fetch_parallel(urls)
        for u, entry in results.items():
            manifest[u] = entry
            if entry.get("error"):
                _lib.append_anomaly(
                    f"[{vendor}] TDS download failed: {u} → {entry['error']}")
        ok = sum(1 for u in urls if not manifest[u].get("error"))
        print(f"   ok={ok}  fail={len(urls) - ok}")

    _lib.save_json(_lib.MANIFEST_PATH, manifest)
    _lib.save_json(_lib.WORKSPACE / "needs_webfetch.json", needs_webfetch)
    if needs_webfetch:
        print(f"\n{len(needs_webfetch)} 3D Systems URL(s) need WebFetch — "
              f"see {_lib.WORKSPACE / 'needs_webfetch.json'}.")
        _lib.append_anomaly(
            f"3D Systems requires WebFetch fallback for "
            f"{len(needs_webfetch)} URL(s).")


if __name__ == "__main__":
    main()
