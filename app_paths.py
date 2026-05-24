"""Canonical filesystem locations for MDS Viewer.

Security stance
---------------
The encrypted ``.enc`` releases MUST live next to the executable
(``<exe-dir>/data/archive/``). The app refuses to load anything if that
directory is absent — distributing a bare exe (without the matching
data folder) yields no data. This rules out silent cached-state leaks.

Auto-fetch only writes into that same neighbouring folder, and only if
it already exists. The folder is never auto-created — its presence is
the maintainer's signal that this build was distributed correctly.

Per-user writable area (LOCALAPPDATA on Windows) is used **only for
logs**, never for data.

Nuitka --onefile path quirk
---------------------------
``sys.executable`` for a onefile build points at the temp-unpacked
Python runtime, NOT the .exe the user clicked. The real exe path is
in ``sys.argv[0]`` (Nuitka rewrites argv0 to the outer binary). We
fall back to ``sys.executable`` only when argv0 doesn't resolve to a
real file.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "MDS_Viewer"


# -------------------------------------------------------------------------
# Frozen / Nuitka detection
# -------------------------------------------------------------------------

def is_frozen() -> bool:
    if getattr(sys, "frozen", False):
        return True
    if "__compiled__" in globals():
        return True
    if any(os.environ.get(k) for k in (
            "NUITKA_ONEFILE_PARENT", "NUITKA_ONEFILE_DIRECTORY",
            "NUITKA_ONEFILE_BINARY", "NUITKA_PACKAGE_HOME")):
        return True
    if os.path.basename(sys.executable).lower().startswith("mds_viewer"):
        return True
    return False


# -------------------------------------------------------------------------
# Locate the running exe (or script in dev mode)
# -------------------------------------------------------------------------

def exe_path() -> Path:
    """Best-effort resolution of the actual running binary path.

    Resolution order:
      1. ``sys.argv[0]`` if it points to an existing file (correct path
         for Nuitka --onefile in practice)
      2. ``sys.executable`` (correct for standalone build; for onefile
         this is the temp-unpacked python, only used as last resort)
    """
    try:
        if sys.argv and sys.argv[0]:
            p = Path(sys.argv[0]).resolve()
            if p.is_file():
                return p
    except Exception:
        pass
    return Path(sys.executable).resolve()


def exe_dir() -> Path:
    """Directory of the running binary."""
    return exe_path().parent


# -------------------------------------------------------------------------
# Data folder — MUST exist next to the exe (no auto-create)
# -------------------------------------------------------------------------

def required_archive_dir() -> Path:
    """The one and only place .enc files are read from / written to.

    For a packaged build this is ``<real-exe-dir>/data/archive``. For
    dev mode it is ``<repo>/data/archive``.

    Existence is **not** guaranteed; callers must check
    ``required_archive_dir().is_dir()`` and refuse to operate if absent.
    """
    if is_frozen():
        return exe_dir() / "data" / "archive"
    return Path(__file__).resolve().parent / "data" / "archive"


def required_archive_dir_exists() -> bool:
    return required_archive_dir().is_dir()


def required_data_dir() -> Path:
    """Same parent of the archive dir — used by maintainer to find
    plain ``material_db.json`` in dev mode."""
    return required_archive_dir().parent


# -------------------------------------------------------------------------
# Logs — per-user writable, not next to exe
# -------------------------------------------------------------------------

def _user_app_root() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.environ.get("USERPROFILE", str(Path.home())),
            "AppData", "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


def log_dir() -> Path:
    """Where ``mds_viewer.log`` is written. Always per-user, survives
    exe replacement, never holds the encrypted releases."""
    if is_frozen():
        p = _user_app_root() / "log"
    else:
        p = Path(__file__).resolve().parent / "log"
    p.mkdir(parents=True, exist_ok=True)
    return p


# -------------------------------------------------------------------------
# Startup diagnostic
# -------------------------------------------------------------------------

def runtime_report() -> dict:
    """Snapshot of every path-related variable. Dumped to the log so a
    misbehaving build can be debugged from a single log file."""
    ad = required_archive_dir()
    return {
        "is_frozen":        is_frozen(),
        "sys.executable":   sys.executable,
        "sys.argv[0]":      sys.argv[0] if sys.argv else None,
        "exe_path":         str(exe_path()),
        "exe_dir":          str(exe_dir()),
        "required_archive_dir":         str(ad),
        "required_archive_dir_exists":  ad.is_dir(),
        "required_archive_entries":     (
            sorted(f.name for f in ad.glob("*.enc"))[:20] if ad.is_dir() else []
        ),
        "cwd":              os.getcwd(),
        "USERPROFILE":      os.environ.get("USERPROFILE"),
        "LOCALAPPDATA":     os.environ.get("LOCALAPPDATA"),
        "TEMP":             os.environ.get("TEMP"),
        "NUITKA_ONEFILE_PARENT":    os.environ.get("NUITKA_ONEFILE_PARENT"),
        "NUITKA_ONEFILE_DIRECTORY": os.environ.get("NUITKA_ONEFILE_DIRECTORY"),
        "log_dir":          str(log_dir()),
    }
