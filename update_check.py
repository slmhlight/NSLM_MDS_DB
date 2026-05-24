"""Best-effort auto-update of encrypted DB releases from GitHub.

On startup the app asks GitHub for the list of ``.enc`` files in the
configured repo's ``data/archive/`` folder and downloads any that
aren't already on disk. Encrypted blobs are useless without a key, so
fetching them ahead of time is harmless even if the user never receives
the matching key.

Failure modes are ALL silent (best-effort):
  - no internet              → skip, log INFO
  - DNS failure              → skip
  - GitHub rate-limit (60/h) → skip
  - any HTTP error           → skip
  - write-protected folder   → skip per-file

Configuration
-------------
- ``MDS_NO_UPDATE=1``  disables the check entirely
- ``MDS_REPO=owner/repo``  override the default repo
- ``MDS_BRANCH=main``  override the default branch
- ``--no-update`` CLI flag in ``main.py`` disables for one run

Network discipline
------------------
- 5 s timeout on the listing call
- 30 s timeout per download (each .enc is < 1 MB)
- One sequential pass — we never re-fetch within a session
"""
from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

LOG = logging.getLogger("mds_viewer.update")

DEFAULT_REPO = "slmhlight/NSLM_MDS_DB"
DEFAULT_BRANCH = "main"
DEFAULT_PATH = "data/archive"

LISTING_TIMEOUT = 5.0
DOWNLOAD_TIMEOUT = 30.0


# =========================================================================
# Configuration / paths
# =========================================================================

def _archive_dir() -> Path | None:
    """Where auto-downloaded .enc files are written.

    Returns the single trusted location: ``<exe-dir>/data/archive``.
    Returns ``None`` if that folder doesn't exist — auto-fetch is
    SILENTLY DISABLED when the distribution is incomplete (so we never
    create false trust by auto-creating data folders).
    """
    env = os.environ.get("STL_DATA_DIR")
    if env and os.path.isdir(env):
        return Path(env) / "archive"
    from app_paths import required_archive_dir
    p = required_archive_dir()
    return p if p.is_dir() else None


def is_update_enabled() -> bool:
    v = os.environ.get("MDS_NO_UPDATE", "").strip().lower()
    return v in ("", "0", "false", "no")


def _repo() -> str:
    return os.environ.get("MDS_REPO", DEFAULT_REPO).strip() or DEFAULT_REPO


def _branch() -> str:
    return os.environ.get("MDS_BRANCH", DEFAULT_BRANCH).strip() or DEFAULT_BRANCH


# =========================================================================
# GitHub API helpers
# =========================================================================

def _http_get(url: str, timeout: float) -> bytes | None:
    """GET ``url`` with a short timeout. Returns body bytes, or None on any
    failure (network, HTTP, decoding). Never raises."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "MDS-Viewer-Updater/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                LOG.info(f"update: HTTP {resp.status} for {url}")
                return None
            return resp.read()
    except urllib.error.HTTPError as e:
        # Rate-limited (403) or moved (404) etc.
        LOG.info(f"update: HTTP {e.code} for {url}")
        return None
    except urllib.error.URLError as e:
        LOG.info(f"update: network error ({e.reason}) — offline?")
        return None
    except Exception as e:
        LOG.info(f"update: {type(e).__name__}: {e}")
        return None


def fetch_archive_listing(repo: str | None = None,
                          branch: str | None = None,
                          path: str = DEFAULT_PATH) -> list[dict] | None:
    """Return a list of {name, download_url, size, sha} for .enc files
    in the repo's archive folder, or None on any failure."""
    repo = repo or _repo()
    branch = branch or _branch()
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    raw = _http_get(url, LISTING_TIMEOUT)
    if raw is None:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        LOG.info(f"update: cannot parse listing JSON: {e}")
        return None
    if not isinstance(data, list):
        # GitHub returns a dict (with a 'message' key) for errors.
        LOG.info(f"update: listing was not a list (likely error): "
                 f"{str(data)[:120]}")
        return None
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "file":
            continue
        name = item.get("name", "")
        if not name.endswith(".enc"):
            continue
        dl = item.get("download_url")
        if not dl:
            continue
        out.append({
            "name": name,
            "download_url": dl,
            "size": int(item.get("size", 0) or 0),
            "sha": item.get("sha", ""),
        })
    return out


# =========================================================================
# Sync
# =========================================================================

def _download_one(url: str, dest: Path) -> bool:
    """Download ``url`` to ``dest`` atomically (write to .tmp then rename)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "MDS-Viewer-Updater/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            if resp.status != 200:
                LOG.info(f"update: HTTP {resp.status} for {url}")
                return False
            data = resp.read()
    except Exception as e:
        LOG.info(f"update: download failed for {dest.name}: {e}")
        return False
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        return True
    except OSError as e:
        # Write-protected location (e.g. Program Files without admin),
        # disk full, antivirus block, etc.
        LOG.info(f"update: cannot write {dest}: {e}")
        return False


def sync_archive(repo: str | None = None,
                 branch: str | None = None,
                 path: str = DEFAULT_PATH) -> tuple[int, int, int]:
    """Pull new .enc files from GitHub into the local archive dir.

    Returns (downloaded, already_present, failed).
    Silent on every failure — never raises.
    """
    if not is_update_enabled():
        LOG.info("update: disabled via MDS_NO_UPDATE")
        return 0, 0, 0
    archive_dir = _archive_dir()
    if archive_dir is None:
        LOG.info("update: <exe>/data/archive folder is absent — skipping "
                  "(refusing to auto-create, distribution must include data/)")
        return 0, 0, 0
    listing = fetch_archive_listing(repo, branch, path)
    if listing is None:
        return 0, 0, 0  # network/API failure — silently skip
    if not listing:
        LOG.info("update: remote archive folder empty / no .enc files")
        return 0, 0, 0
    dl, present, fail = 0, 0, 0
    for item in listing:
        local = archive_dir / item["name"]
        if local.is_file():
            try:
                if local.stat().st_size == item["size"]:
                    present += 1
                    continue
            except OSError:
                pass  # fall through and re-download
        ok = _download_one(item["download_url"], local)
        if ok:
            dl += 1
            LOG.info(f"update: downloaded {item['name']} ({item['size']} B)")
        else:
            fail += 1
    return dl, present, fail
