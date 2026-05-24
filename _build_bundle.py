"""Post-onefile-build packager.

Takes dist\MDS_Viewer.exe (produced by Nuitka --onefile) and bundles it
together with the encrypted DB releases and a user-facing README into a
single distributable zip:

    dist/
      MDS_Viewer.exe                          (from Nuitka)
      MDS_Viewer_<release-tag>/                (staging)
        MDS_Viewer.exe
        data/
          archive/
            material_db_2026-XX-XX.enc        (all .enc files copied)
        README_DIST.txt
        LICENSE_NOTICE.txt
      MDS_Viewer_<release-tag>.zip            (final, send this)

The release tag is the key_id of the newest .enc file in data/archive/.
Keystore files (keys.txt, keys.master.txt, ~/.mds_viewer_keys) are
NEVER copied into the bundle.

Safety guards:
  - explicit check that no plain material_db.json sneaks into the zip
  - explicit check that no file matching keys.txt / keys.master.txt /
    *.mds_viewer_keys ends up in the zip
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
EXE = DIST / "MDS_Viewer.exe"
ARCHIVE_SRC = ROOT / "data" / "archive"
LICENSE_SRC = ROOT / "LICENSE_NOTICE.txt"


README_DIST = """\
MDS Viewer - distributed build (onefile)
========================================

What's in this folder
---------------------
  MDS_Viewer.exe              single-file executable
  data/archive/*.enc          encrypted material database releases
  README_DIST.txt             this file
  LICENSE_NOTICE.txt          licensing notice

How to launch
-------------
  1) Double-click MDS_Viewer.exe.
  2) On first launch the app will pop a dialog asking for your
     access key. Paste the line your maintainer sent you, e.g.:
         2026-05-24 = _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR
     The key is saved to your user profile
     (Windows: %USERPROFILE%\\.mds_viewer_keys) so you won't be
     asked again.
  3) The app picks the newest release your key can decrypt.

Receiving a new release
-----------------------
  - You receive a new zip + a new key line from the maintainer.
  - Replace the .exe folder (or just drop the new .enc into
    data/archive/ of the existing install).
  - Launch the .exe. The first time the new .enc shows up, the
    dialog will pop again asking for the new key.
  - Old keys remain valid for old releases - you can keep them.

Manual key management (advanced)
--------------------------------
The keystore is a plain text file at:
    %USERPROFILE%\\.mds_viewer_keys
Format - one line per release:
    <key_id> = <passphrase>
Lines starting with # are comments. Add / remove / edit freely.

Troubleshooting
---------------
  - "This release is encrypted" dialog keeps coming back: your
    keystore doesn't cover any of the .enc files present. Ask
    the maintainer for a fresh key.
  - App won't launch / Windows SmartScreen warning: right-click
    the exe -> Properties -> "Unblock" -> OK, then launch.
"""


def _newest_release_tag() -> str:
    """Return key_id of the newest .enc file (used as zip name suffix)."""
    from db_crypto import read_key_id, _sort_key_for_filename
    files = sorted(ARCHIVE_SRC.glob("*.enc"),
                   key=_sort_key_for_filename, reverse=True)
    if not files:
        raise SystemExit("[ERROR] no .enc files in data/archive/")
    return read_key_id(files[0])


def _assert_no_secrets_in(folder: Path) -> None:
    """Fail loudly if the staging folder contains anything sensitive."""
    bad_names = {
        "material_db.json",       # plain DB
        "keys.txt",                # user keystore
        "keys.master.txt",         # maintainer master keystore
        ".mds_viewer_keys",        # home keystore
    }
    bad_suffixes = (".master.txt",)
    for f in folder.rglob("*"):
        if not f.is_file():
            continue
        if f.name in bad_names:
            raise SystemExit(
                f"[SECURITY] bundle would have included {f} — aborting")
        if f.name.endswith(bad_suffixes):
            raise SystemExit(
                f"[SECURITY] bundle would have included {f} — aborting")


def main() -> int:
    if not EXE.is_file():
        print(f"[ERROR] {EXE} not found — run Nuitka first", file=sys.stderr)
        return 1
    if not ARCHIVE_SRC.is_dir():
        print(f"[ERROR] {ARCHIVE_SRC} not found", file=sys.stderr)
        return 1
    enc_files = sorted(ARCHIVE_SRC.glob("*.enc"))
    if not enc_files:
        print(f"[ERROR] no .enc files in {ARCHIVE_SRC}", file=sys.stderr)
        return 1

    tag = _newest_release_tag()
    bundle_name = f"MDS_Viewer_{tag}"
    stage = DIST / bundle_name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    (stage / "data" / "archive").mkdir(parents=True)

    # 1) the executable
    shutil.copy2(EXE, stage / "MDS_Viewer.exe")
    print(f"  + MDS_Viewer.exe ({EXE.stat().st_size / 1048576:.1f} MB)")

    # 2) all encrypted releases
    for enc in enc_files:
        shutil.copy2(enc, stage / "data" / "archive" / enc.name)
        print(f"  + data/archive/{enc.name}")

    # 3) end-user readme
    (stage / "README_DIST.txt").write_text(README_DIST, encoding="utf-8")
    print("  + README_DIST.txt")

    # 4) license notice
    if LICENSE_SRC.is_file():
        shutil.copy2(LICENSE_SRC, stage / "LICENSE_NOTICE.txt")
        print("  + LICENSE_NOTICE.txt")

    # 5) safety: no secrets sneaked in
    _assert_no_secrets_in(stage)

    # 6) zip it
    zip_path = DIST / f"{bundle_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED,
                          compresslevel=9) as zf:
        for f in sorted(stage.rglob("*")):
            if f.is_file():
                arcname = f.relative_to(DIST)  # keep MDS_Viewer_<tag>/ prefix
                zf.write(f, arcname)
    size_mb = zip_path.stat().st_size / 1048576
    print()
    print(f"[OK] {zip_path}  ({size_mb:.1f} MB)")
    print(f"[OK] staging:   {stage}")
    print()
    print("Distribute the .zip. Send the matching key line out-of-band:")
    print(f"   {tag} = <passphrase from keys.master.txt>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
