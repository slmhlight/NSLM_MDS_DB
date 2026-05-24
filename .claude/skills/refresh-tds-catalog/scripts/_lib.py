"""Shared utilities for the refresh-tds-catalog skill."""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")

# Resolve project paths. Skill lives at <project>/.claude/skills/<skill>/scripts/
HERE = Path(__file__).resolve().parent           # .../scripts
SKILL_ROOT = HERE.parent                          # .../refresh-tds-catalog
PROJECT_ROOT = SKILL_ROOT.parents[2]              # <project>
WORKSPACE = PROJECT_ROOT / "_tds_workspace"
CACHE = WORKSPACE / "cache"
DB_PATH = PROJECT_ROOT / "data" / "material_db.json"
CATALOGS_PATH = SKILL_ROOT / "assets" / "catalogs.json"
DISCOVERY_PATH = WORKSPACE / "discovery.json"
MANIFEST_PATH = CACHE / "manifest.json"
EXTRACTED_PATH = WORKSPACE / "extracted.json"
MISSES_PATH = WORKSPACE / "extraction_misses.json"
ANOMALIES_PATH = WORKSPACE / "anomalies.md"

PDFTOTEXT_CANDIDATES = [
    r"C:\Program Files\Git\mingw64\bin\pdftotext.exe",
    "pdftotext",
]


def ensure_workspace():
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)


def url_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def http_get(url: str, timeout: int = 30,
             extra_headers: dict | None = None) -> tuple[bytes, str]:
    headers = {"User-Agent": UA, "Accept": "*/*"}
    if extra_headers: headers.update(extra_headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read(), (r.headers.get("Content-Type") or "").lower()


def fetch_to_cache(url: str) -> dict:
    """Download URL into CACHE; return manifest entry dict."""
    key = url_key(url)
    try:
        if not (url.startswith("http://") or url.startswith("https://")):
            return {"url": url, "error": "invalid_url"}
        data, ct = http_get(url)
        if "pdf" in ct or url.lower().endswith(".pdf"):
            ext = ".pdf"
        elif "html" in ct or "xml" in ct:
            ext = ".html"
        else:
            ext = ".bin"
        path = CACHE / f"{key}{ext}"
        path.write_bytes(data)
        return {"url": url, "path": str(path), "size": len(data),
                "content_type": ct}
    except Exception as e:
        return {"url": url, "error": f"{type(e).__name__}: {e}"}


def fetch_parallel(urls: list[str], max_workers: int = 8) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_to_cache, u): u for u in urls}
        for fut in as_completed(futs):
            entry = fut.result()
            out[entry["url"]] = entry
    return out


def pdftotext(pdf_path: str, txt_path: str) -> bool:
    for cmd in PDFTOTEXT_CANDIDATES:
        try:
            subprocess.run(
                [cmd, "-layout", "-enc", "UTF-8", pdf_path, txt_path],
                check=True, capture_output=True, timeout=60)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired):
            continue
    return False


def html_to_text(html: str) -> str:
    """Quick-and-dirty HTML → text. Preserves block boundaries with newlines."""
    html = re.sub(r"<script.*?</script>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style.*?</style>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"</(p|tr|div|li|h\d|td|br)>", "\n", html,
                  flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                 .replace("&quot;", '"').replace("&#39;", "'"))
    text = re.sub(r"&[a-zA-Z]+;|&#\d+;", " ", text)
    return text


def load_json(path: Path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def load_catalogs() -> dict:
    """Return the vendors dict from assets/catalogs.json."""
    raw = load_json(CATALOGS_PATH, {})
    return raw.get("vendors", {})


def append_anomaly(line: str):
    """Append a line to anomalies.md (creates header if missing)."""
    ANOMALIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not ANOMALIES_PATH.exists()
    with ANOMALIES_PATH.open("a", encoding="utf-8") as f:
        if is_new:
            f.write("# refresh-tds-catalog anomalies\n\n")
        f.write(f"- {line}\n")


def reset_anomalies():
    if ANOMALIES_PATH.exists():
        ANOMALIES_PATH.unlink()
