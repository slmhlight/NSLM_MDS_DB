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

```bat
build_mds.bat
```

Produces `dist/MDS_Viewer/` containing:

```
MDS_Viewer\
├── MDS_Viewer.exe                ← main executable
├── <Python runtime + Qt DLLs>    ← bundled by Nuitka
├── data\archive\*.enc            ← encrypted DB releases
├── keys.txt.example              ← keystore template
├── README_DIST.txt               ← end-user instructions
└── LICENSE_NOTICE.txt
```

Distribute the entire folder (zip or installer). Plain `material_db.json`
is **never** copied into `dist/` — users only get encrypted releases.

Faster iteration build:
```bat
set BUILD_DEBUG=1
build_mds.bat
```

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
├── report_generator.py           ← HTML report builder
├── lang.py                       ← i18n strings
├── contribute.py                 ← user-side contribution wizard
├── build_mds.bat                 ← Nuitka standalone build
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
```

---

## UI features

- Category dropdown (Aluminium / Cobalt / Copper / Nickel / Steel /
  Titanium / Niobium / Other — Nikon-aligned)
- Material dropdown (filtered by category)
- 4 tabs per material:
  1. Basic Physical / Thermal Properties
  2. Mechanical Properties by Heat Treatment (per-direction XY/Z)
  3. **Vendor differences** — checkbox tree + bar chart + TDS shortcut
     column + 📊 report generator (standalone HTML w/ inline SVG charts)
  4. Chemical Composition + References (TDS / standards)
- Forces a light palette so the dialog renders correctly under
  OS-level dark mode

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
