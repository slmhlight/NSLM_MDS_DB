# MDS Viewer

Standalone Material Data Sheet viewer for LPBF/AM materials.
39 materials × 395 vendor entries across EOS, Nikon SLM Solutions,
GE Additive, and 3D Systems.

---

## Run from source

```bash
git clone <repo>
cd MDS_VIEWER
pip install -r requirements.txt   # PySide6 + cryptography
python main.py
```

First run needs a keystore — see [Distribution / keystore](#distribution).

---

## Build standalone exe (Nuitka)

Two build modes — pick based on how you distribute:

### A) Standalone folder (`build_mds.bat`)

```bat
build_mds.bat
```

Produces `dist/MDS_Viewer/` — a folder containing the exe + bundled
Python runtime + Qt DLLs (~85 MB total, ~14 MB exe). Zip the folder
or wrap it in an installer. Fast startup (no extraction).

### B) Onefile zip (`build_mds_onefile.bat`) — recommended for end users

```bat
build_mds_onefile.bat
```

Produces:

```
dist\
├── MDS_Viewer.exe                  single ~50 MB file (no DLLs alongside)
├── MDS_Viewer_<release-tag>\        staging folder
│   ├── MDS_Viewer.exe
│   ├── data\archive\*.enc
│   ├── README_DIST.txt
│   └── LICENSE_NOTICE.txt
└── MDS_Viewer_<release-tag>.zip     final distributable — send this
```

Send the `.zip`. On first launch the app pops a **GUI dialog** asking
for the access-key line (no manual file editing) and saves it to
`%USERPROFILE%\.mds_viewer_keys`. Slightly slower startup (Nuitka
unpacks on first run, then caches).

Plain `material_db.json`, `keys.txt`, `keys.master.txt` are **never**
included in either build — explicit guards abort the build if they
would be.

### Build options

```bat
set BUILD_DEBUG=1
build_mds.bat               REM or build_mds_onefile.bat
```
→ MinGW + LTO off for faster iteration.

Pre-flight: `data/archive/*.enc` must exist (build aborts otherwise).
Generate one with `python db_crypto.py encrypt data/material_db.json
--also-append-keystore keys.master.txt`.

---

## Distribution

The repo ships encrypted DB snapshots under `data/archive/` rather than
plain JSON. Each `.enc` carries a `key_id` (typically a release date).
Users hold a `keys.txt` mapping `key_id → passphrase`. The loader picks
the newest accessible release.

See **DISTRIBUTION.md** for the full maintainer + user workflow,
**CONTRIBUTING.md** for proposing new vendor entries / materials, and
`contributions/SCHEMA.md` for the contribution file format.

---

## Project layout

```
MDS_VIEWER\
├── main.py                       ← entry point
├── mds_dialog.py                 ← Qt MDS UI
├── qt_helper.py                  ← QApplication bootstrap
├── resource_helper.py            ← data/ lookup + decrypt
├── db_crypto.py                  ← AES-256-GCM crypto module + CLI
├── key_dialog.py                 ← GUI key-entry dialog (encrypted DB)
├── update_check.py               ← best-effort GitHub .enc auto-fetch
├── report_generator.py           ← HTML report builder
├── lang.py                       ← i18n strings
├── contribute.py                 ← user-side contribution wizard
├── build_mds.bat                 ← Nuitka standalone (folder) build
├── build_mds_onefile.bat         ← Nuitka onefile + zip build
├── _build_postwrite.py           ← post-build helper (standalone)
├── _build_bundle.py              ← post-build helper (onefile zip)
├── data\
│   ├── material_db.json          ← maintainer-only (gitignored)
│   └── archive\*.enc             ← encrypted releases (committed)
├── contributions\
│   ├── pending\*.json            ← PR's submitted but not yet merged
│   ├── applied\<date>\*.json     ← merged contributions, by date
│   ├── SCHEMA.md
│   └── TEMPLATE_*.json
├── .claude\skills\refresh-tds-catalog\
│   ├── SKILL.md
│   ├── scripts\01..15_*.py       ← discover / download / extract /
│   │                                apply / verify / merge / encrypt
│   ├── parsers\eos|ge|nikon|three_d_systems.py
│   └── references\*.md
├── requirements.txt
├── README.md
├── DISTRIBUTION.md               ← crypto + keystore workflow
├── CONTRIBUTING.md               ← user-facing contribution guide
└── LICENSE_NOTICE.txt
```

---

## CLI

```bat
MDS_Viewer.exe                    # open first material
MDS_Viewer.exe --material 316L    # specific material
MDS_Viewer.exe --check-db         # validate DB, no GUI
MDS_Viewer.exe --no-update        # skip the startup GitHub fetch
```

`MDS_NO_UPDATE=1` env var also disables the auto-fetch. `MDS_REPO=owner/repo`
points the updater at a different source. See **DISTRIBUTION.md** for the
full auto-update behavior and offline notes.

---

## UI features

- Category dropdown (Aluminium / Cobalt / Copper / Nickel / Steel /
  Titanium / Niobium / Other — Nikon-aligned)
- Material dropdown (filtered by category)
- **Add release key…** button (top-right) — paste a new key line any
  time, no file editing needed
- 4 tabs per material:
  1. Basic Physical / Thermal Properties
  2. Mechanical Properties by Heat Treatment (per-direction XY/Z)
  3. **Vendor differences** — checkbox tree + bar chart + TDS shortcut
     column + 📊 report generator (standalone HTML w/ inline SVG charts)
  4. Chemical Composition + References (TDS / standards)
- Forces a light palette so the dialog renders correctly under
  OS-level dark mode
- Best-effort startup fetch of new `.enc` releases from GitHub; silent
  fallback if offline

---

## Update the database (maintainer)

```bash
# Discover new TDS URLs + refresh existing entries
python .claude/skills/refresh-tds-catalog/scripts/01_discover.py
python .claude/skills/refresh-tds-catalog/scripts/02_download.py
python .claude/skills/refresh-tds-catalog/scripts/03_extract.py
python .claude/skills/refresh-tds-catalog/scripts/04_apply.py

# Verify integrity
python .claude/skills/refresh-tds-catalog/scripts/12_selfverify.py

# Merge any pending contributions
python .claude/skills/refresh-tds-catalog/scripts/15_merge_contributions.py

# Cut a new encrypted release
python db_crypto.py encrypt data/material_db.json \
    --also-append-keystore keys.master.txt
```

`refresh-tds-catalog` skill auto-triggers on phrases like
"refresh TDS catalog" / "재료 DB 갱신" inside Claude Code.

---

## Requirements

- Python 3.10+
- PySide6 ≥ 6.5
- cryptography ≥ 41

Build dependency only: Nuitka.

---

## License

PySide6 — LGPL-3.0
Nuitka — Apache-2.0
This project — see `LICENSE_NOTICE.txt`
