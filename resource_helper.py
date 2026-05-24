"""resource_helper - minimal version for MDS Viewer.

Finds data/material_db.json next to the executable (frozen) or script (dev).
"""
import os
import sys


def get_resource_dir(type_name="data"):
    """Return path to <type_name> directory (e.g. 'data', 'refs').

    Priority:
      1. STL_<TYPE>_DIR env var
      2. <exe_dir>/<type>   (frozen / bundled)
      3. <script_dir>/<type>  (dev)
      4. <cwd>/<type>
    """
    env_key = f"STL_{type_name.upper()}_DIR"
    p = os.environ.get(env_key)
    if p and os.path.isdir(p):
        return p

    # frozen (Nuitka onefile) — sys.executable is the exe
    if getattr(sys, "frozen", False) or "__compiled__" in globals() \
            or os.path.basename(sys.executable).lower().startswith("mds_viewer"):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidate = os.path.join(exe_dir, type_name)
        if os.path.isdir(candidate):
            return candidate

    # dev — next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(script_dir, type_name)
    if os.path.isdir(candidate):
        return candidate

    # cwd fallback
    cwd_candidate = os.path.join(os.getcwd(), type_name)
    if os.path.isdir(cwd_candidate):
        return cwd_candidate

    # No match - return best guess (script_dir/type)
    return candidate


def load_material_db():
    """Load material_db.json as dict, or None on failure.

    Lookup order:
      1. Plain `data/material_db.json`        — maintainer / dev workflow
      2. Newest decryptable `data/archive/*.enc` — distributed users

    For (2) we read each .enc file's `key_id` header, cross-reference
    against the user's keystore (`keys.txt`), and pick the newest entry
    the user has a key for. A user without the latest key is effectively
    pinned at their last received release.

    The decrypted payload lives in memory only — no plain JSON ever
    lands on the user's disk.
    """
    import json
    data_dir = get_resource_dir("data")
    plain_path = os.path.join(data_dir, "material_db.json")
    archive_dir = os.path.join(data_dir, "archive")

    # 1) Plain file (maintainer path)
    if os.path.isfile(plain_path):
        try:
            with open(plain_path, "r", encoding="utf-8") as f:
                return json.load(f), plain_path
        except Exception as e:
            return None, f"{plain_path}: {e}"

    # 2) Archive + keystore
    if os.path.isdir(archive_dir):
        try:
            from db_crypto import load_keystore, find_accessible_archive
            keystore, ks_path = load_keystore()
            if not keystore:
                return None, (f"{archive_dir}: keystore not found "
                              f"(expected keys.txt next to the app, "
                              f"in $MDS_DB_KEYS, or ~/.mds_viewer_keys)")
            hit = find_accessible_archive(archive_dir, keystore)
            if not hit:
                ids = sorted(keystore.keys())
                return None, (f"{archive_dir}: no decryptable release. "
                              f"Your keystore covers {ids!r} — none of those "
                              f"match the files present. Ask the maintainer "
                              f"for a fresh key.")
            enc_path, key_id, passphrase = hit
            from db_crypto import decrypt_file
            plain_bytes = decrypt_file(enc_path, passphrase)
            return (json.loads(plain_bytes.decode("utf-8")),
                    f"{enc_path}  (key_id={key_id})")
        except Exception as e:
            return None, f"{archive_dir}: decrypt failed: {e}"

    return None, f"{plain_path} (or {archive_dir}/*.enc)"
