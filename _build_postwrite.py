"""
Post-build helper: writes keys.txt.example and README_DIST.txt into the
dist\MDS_Viewer\ folder. Split out of build_mds.bat because AV heuristics
flag cmd-line `python -c` calls that drop text files (a common malware
dropper pattern), causing build_mds.bat to be silently truncated on disk.
"""
from pathlib import Path
import sys

DIST = Path("dist") / "MDS_Viewer"
if not DIST.exists():
    print(f"[ERROR] {DIST} does not exist - run Nuitka first", file=sys.stderr)
    sys.exit(1)

KEYS_EXAMPLE = """# MDS Viewer keystore
# ===================
# The maintainer issues one line per release. Paste each line you
# receive into this file, then rename it to "keys.txt" (drop the
# .example suffix) - the launcher picks it up automatically.
#
# The app will load the newest encrypted release whose key_id appears
# below; older keys are kept so older releases stay accessible.
#
# Format: <key_id> = <passphrase>
#
# Example after pasting:
# 2026-05-24 = _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR
"""

README_DIST = """MDS Viewer - distributed build
==============================

1) Rename keys.txt.example to keys.txt
2) Add the line your maintainer sent: <key_id> = <passphrase>
3) Launch MDS_Viewer.exe

The encrypted material database lives in data/archive/. The app
automatically picks the newest release whose key_id is in your keys.txt.

Receiving a new release:
  - Drop the new .enc file into data/archive/
  - Append the new key line to keys.txt
  - Restart MDS_Viewer.exe

Old keys remain valid for old .enc files; if you skip an update the app
continues running the previous release without complaint.

Troubleshooting:
  - "keystore not found": keys.txt missing or in wrong folder
  - "no decryptable release": your keys.txt does not cover any of the
    .enc files present - request a fresh key from the maintainer.
"""

(DIST / "keys.txt.example").write_text(KEYS_EXAMPLE, encoding="utf-8")
(DIST / "README_DIST.txt").write_text(README_DIST, encoding="utf-8")

print(f"[OK] wrote {DIST}/keys.txt.example")
print(f"[OK] wrote {DIST}/README_DIST.txt")
