"""resource_helper - DB load + path resolution for MDS Viewer.

Strict source policy
--------------------
The encrypted ``.enc`` releases are read **only** from
``<exe-dir>/data/archive/``. No fallback to LOCALAPPDATA, no fallback
to cwd, no fallback to script-dir lookups during a frozen run.

If that folder is missing, the loader returns an explicit "data folder
missing" error and the app refuses to show anything. This rules out
the failure mode where a bare exe (without its accompanying data
folder) silently reads cached state from elsewhere.

Plain ``material_db.json`` is loaded ONLY in dev mode (running from
source). A frozen build never even looks at a plain file — encrypted
release + valid keystore is mandatory.
"""
import json
import logging
import os
import sys
from pathlib import Path

_LOG = logging.getLogger("mds_viewer.resource_helper")


def get_resource_dir(type_name="data"):
    """Best shipped-data directory for ``type_name`` (e.g. 'data').

    Frozen mode: ``<exe-dir>/<type>`` only.
    Dev mode:    next-to-this-script then cwd as fallback.
    """
    env_key = f"STL_{type_name.upper()}_DIR"
    p = os.environ.get(env_key)
    if p and os.path.isdir(p):
        return p

    from app_paths import is_frozen, exe_dir
    if is_frozen():
        return str(exe_dir() / type_name)

    here = Path(__file__).resolve().parent / type_name
    if here.is_dir():
        return str(here)
    cwd = Path.cwd() / type_name
    if cwd.is_dir():
        return str(cwd)
    return str(here)


def load_material_db():
    """Load the material DB and return (dict_or_None, info_string).

    Frozen mode (packaged exe):
      Requires <exe-dir>/data/archive/ to exist with at least one
      decryptable .enc. Nothing else is consulted.

    Dev mode (python main.py from source):
      1. Plain ``data/material_db.json`` (maintainer working file)
      2. Encrypted ``data/archive/*.enc`` (same as frozen)
    """
    from app_paths import is_frozen, required_archive_dir

    # ---- Dev-only: plain JSON shortcut for maintainer iteration ----
    if not is_frozen():
        data_dir = get_resource_dir("data")
        plain_path = os.path.join(data_dir, "material_db.json")
        if os.path.isfile(plain_path):
            try:
                with open(plain_path, "r", encoding="utf-8") as f:
                    return json.load(f), plain_path
            except Exception as e:
                return None, f"{plain_path}: {e}"

    # ---- Strict path: only <exe-dir>/data/archive ----
    archive_dir = required_archive_dir()
    if not archive_dir.is_dir():
        return None, (
            f"data folder not found.\n\n"
            f"Expected:  {archive_dir}\n\n"
            f"This build refuses to start without the data\\archive\\ "
            f"folder next to the executable. Reinstall from the "
            f"distributed zip — the zip ships the baseline .enc "
            f"files."
        )

    from db_crypto import (
        load_keystore, read_key_id, decrypt_file, _sort_key_for_filename,
    )

    files = []
    for f in archive_dir.glob("*.enc"):
        try:
            kid = read_key_id(f)
        except Exception as e:
            _LOG.info(f"resource: cannot read {f.name}: {e}")
            continue
        files.append((f, kid))
    if not files:
        return None, (
            f"{archive_dir} exists but contains no usable .enc files."
        )

    files.sort(key=lambda fk: _sort_key_for_filename(fk[0]), reverse=True)

    keystore, _ks_path = load_keystore()
    if not keystore:
        return None, (
            f"keystore not found "
            f"(expected keys.txt next to the app, in $MDS_DB_KEYS, "
            f"or ~/.mds_viewer_keys)"
        )

    for path, kid in files:
        if kid not in keystore:
            continue
        try:
            plain_bytes = decrypt_file(path, keystore[kid])
            return (json.loads(plain_bytes.decode("utf-8")),
                    f"{path}  (key_id={kid})")
        except Exception as e:
            _LOG.warning(f"resource: decrypt failed for {path.name}: {e}")
            continue

    ids = sorted(keystore.keys())
    available = sorted({kid for _, kid in files})
    return None, (
        f"no decryptable release. Keystore has {ids!r}, "
        f"available releases are {available!r} — none overlap. "
        f"Ask the maintainer for a fresh key."
    )
