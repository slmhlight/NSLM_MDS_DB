"""MDS Viewer v1.0 - standalone Material Data Sheet viewer.

Source: STL Analyzer v2.992.beta-5 (ui/qt/mds_dialog.py)
This is a minimal entry point that:
  1. Locates data/material_db.json (next to exe / script)
  2. Loads it
  3. Opens the MDS dialog with the first material selected

Usage:
  python main.py                      # opens MDS dialog
  python main.py --material 316L      # opens with specific material selected
  python main.py --check-db           # validates JSON only, no GUI
"""
import sys
import os
import logging
import argparse


def setup_logging():
    """File log next to exe; console log to stderr."""
    log_dir = _find_log_dir()
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "mds_viewer.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

    root = logging.getLogger("mds_viewer")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # mds_dialog logger uses "stl_analyzer.mds_dialog" prefix from the source code.
    # Mirror it to our root by adding the same handlers.
    stla = logging.getLogger("stl_analyzer")
    stla.setLevel(logging.DEBUG)
    stla.handlers.clear()
    stla.addHandler(fh)
    stla.addHandler(sh)


def _find_log_dir():
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return os.path.join(
            os.path.dirname(os.path.abspath(sys.executable)), "log")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")


def main():
    parser = argparse.ArgumentParser(
        description="MDS Viewer - Material Data Sheet standalone")
    parser.add_argument("--material", "-m", default=None,
                         help="Initial material name (default: first in DB)")
    parser.add_argument("--check-db", action="store_true",
                         help="Validate material_db.json then exit")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("mds_viewer")
    # Force English UI strings regardless of the lang.py default.
    try:
        from lang import set_language
        set_language("en")
    except Exception as e:
        log.warning(f"set_language('en') failed: {e}")
    log.info("=== MDS Viewer v1.0 starting ===")
    log.info(f"sys.executable: {sys.executable}")
    log.info(f"frozen: {getattr(sys, 'frozen', False)}, "
              f"compiled: {'__compiled__' in globals()}")

    # Load material DB
    from resource_helper import load_material_db
    db, db_info = load_material_db()

    # If the load failed because of a keystore issue (no keys.txt /
    # keystore doesn't cover any .enc), pop a GUI dialog instead of
    # dying. Loop until the user either succeeds or hits Cancel.
    if db is None:
        try:
            from key_dialog import ask_user_for_key, looks_like_keystore_problem
            from qt_helper import get_qt
            attempts = 0
            while db is None and looks_like_keystore_problem(db_info):
                qt = get_qt()
                if qt is None:
                    break  # no Qt — fall through to error message
                attempts += 1
                if attempts > 6:
                    log.warning("giving up after 6 key-entry attempts")
                    break
                cont = ask_user_for_key(parent=None, message=db_info)
                if not cont:
                    log.info("user cancelled key entry")
                    return 0
                db, db_info = load_material_db()
        except Exception as e:
            log.exception(f"key dialog flow failed: {e}")

    if db is None:
        msg = (f"material_db.json not found or invalid.\n"
                f"Expected location: {db_info}\n"
                f"Place the file at: <exe>/data/material_db.json")
        log.error(msg)
        try:
            from qt_helper import get_qt
            qt = get_qt()
            if qt:
                Q = qt["QtWidgets"]
                Q.QMessageBox.critical(None, "MDS Viewer - Error", msg)
        except Exception:
            pass
        print(msg, file=sys.stderr)
        return 1

    materials = db.get("materials", {})
    log.info(f"Loaded {len(materials)} materials from {db_info}")

    if args.check_db:
        # Stats
        vendor_count = 0
        for m, info in materials.items():
            vendor_count += len(info.get("vendors", {}) or {})
        print(f"[OK] material_db.json valid")
        print(f"     materials: {len(materials)}")
        print(f"     vendors:   {vendor_count}")
        print(f"     path:      {db_info}")
        return 0

    # Pick initial material
    mat_list = list(materials.keys())
    if not mat_list:
        log.error("material_db.json has no materials")
        return 1

    initial = args.material if args.material in mat_list else mat_list[0]
    props = materials[initial]
    mds_urls = props.get("ref_urls", [])
    # _default_4 lives at top-level (preferred) or under db.vendors (legacy)
    default_4 = (db.get("_default_4")
                 or (db.get("vendors") or {}).get("_default_4"))

    log.info(f"Opening MDS dialog for material: {initial}")
    log.info(f"  vendor entries: {len(props.get('vendors') or {})}")

    # Initialize Qt (creates QApplication)
    from qt_helper import get_qt
    qt = get_qt()
    if qt is None:
        log.error("Qt initialization failed")
        print("ERROR: PySide6 not available. pip install PySide6", file=sys.stderr)
        return 1

    app = qt["app"]

    # Open MDS dialog (blocking)
    from mds_dialog import open_mds_qt
    try:
        ok = open_mds_qt(
            material_name=initial,
            properties=props,
            mds_urls=mds_urls,
            default_vendors_4=default_4,
            material_db=db,
        )
        if not ok:
            log.error("open_mds_qt returned False")
            return 1
    except Exception as e:
        log.exception(f"MDS dialog error: {e}")
        try:
            qt["QtWidgets"].QMessageBox.critical(
                None, "MDS Viewer - Fatal", f"{type(e).__name__}: {e}")
        except Exception:
            pass
        return 1

    # Run Qt event loop
    try:
        app.exec()
    except AttributeError:
        app.exec_()  # PyQt5 fallback (unused but safe)

    log.info("=== MDS Viewer exit ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
