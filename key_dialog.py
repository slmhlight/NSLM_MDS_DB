"""GUI keystore input dialog for MDS Viewer.

Shown when the app cannot load the encrypted DB because:
  - no keystore file exists anywhere on the system, or
  - the keystore exists but doesn't cover any .enc release present

Lets the user paste the `<key_id> = <passphrase>` line the maintainer
sent (out-of-band) and saves it to ~/.mds_viewer_keys, then the loader
retries.

Storage choice
--------------
Saved to ``~/.mds_viewer_keys`` (the user's home directory) rather than
next to the .exe. This way:
  - distribution bundles never accidentally carry user keys
  - one user can have a single keystore that works for multiple builds
  - uninstalling the app folder doesn't lose the key
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple


# Accept the same format as keys.txt:  <key_id> = <passphrase>
_KEY_LINE_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*=\s*(\S.*?)\s*$")


def parse_key_line(text: str) -> Optional[Tuple[str, str]]:
    """Parse user-pasted input. Returns (key_id, passphrase) or None.

    Tolerates leading prose / blank lines / '#'-comments — picks the
    first plausible `<id> = <pass>` line.
    """
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _KEY_LINE_RE.match(line)
        if m:
            return m.group(1), m.group(2)
    return None


def keystore_path() -> Path:
    """Where user-entered keys are saved (~/.mds_viewer_keys)."""
    return Path.home() / ".mds_viewer_keys"


def append_key(key_id: str, passphrase: str) -> Path:
    """Add / replace a single key in ~/.mds_viewer_keys.

    If the file already has a line for the same key_id, that line is
    replaced (no duplicates accumulate).
    """
    p = keystore_path()
    existing = p.read_text(encoding="utf-8") if p.is_file() else ""
    out_lines = []
    for raw in existing.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            out_lines.append(raw)
            continue
        kid = s.split("=", 1)[0].strip()
        if kid == key_id:
            continue  # drop old, will replace below
        out_lines.append(raw)
    out_lines.append(f"{key_id} = {passphrase}")
    p.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return p


_DEFAULT_INTRO_HTML = (
    "<b>This release is encrypted.</b><br>"
    "Paste the key line your maintainer sent you below. "
    "The line looks like:<br>"
    "<code>2026-05-24 = _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR</code><br><br>"
    "The key will be saved to your user profile "
    "(<code>~/.mds_viewer_keys</code>) so you only have to enter it once.<br>"
    "Older keys stay valid for older releases."
)

_ADD_KEY_INTRO_HTML = (
    "<b>Add a new release access key.</b><br>"
    "Paste the line your maintainer sent you below, e.g.:<br>"
    "<code>2026-05-24 = _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR</code><br><br>"
    "Saved to <code>~/.mds_viewer_keys</code>. <b>Restart MDS Viewer</b> "
    "afterward to load any newer release this key unlocks.<br>"
    "Older keys stay valid - no harm in keeping them."
)


def ask_user_for_key(parent=None, message: str = "",
                     title: str = None, intro_html: str = None) -> bool:
    """Show a modal key-entry dialog. Returns True iff the user saved a key.

    Caller should then re-attempt the encrypted-DB load (or, when called
    from the add-key flow, prompt the user to restart).
    """
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
        QPushButton, QMessageBox,
    )
    from PySide6.QtGui import QPalette, QColor, QFont

    dlg = QDialog(parent)
    dlg.setWindowTitle(title or "MDS Viewer - Enter access key")
    dlg.setModal(True)
    dlg.resize(580, 260)

    layout = QVBoxLayout(dlg)

    intro = QLabel(intro_html or _DEFAULT_INTRO_HTML)
    intro.setWordWrap(True)
    layout.addWidget(intro)

    if message:
        warn = QLabel(message)
        warn.setWordWrap(True)
        warn.setStyleSheet("color:#a04020; font-style:italic;")
        layout.addWidget(warn)

    edit = QPlainTextEdit()
    edit.setPlaceholderText("2026-05-24 = _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR")
    mono = QFont("Consolas")
    mono.setStyleHint(QFont.Monospace)
    edit.setFont(mono)
    layout.addWidget(edit)

    btns = QHBoxLayout()
    btn_cancel = QPushButton("Cancel")
    btn_ok = QPushButton("Save key && continue")
    btn_ok.setDefault(True)
    btns.addStretch(1)
    btns.addWidget(btn_cancel)
    btns.addWidget(btn_ok)
    layout.addLayout(btns)

    state = {"saved": False}

    def on_ok():
        parsed = parse_key_line(edit.toPlainText())
        if parsed is None:
            QMessageBox.warning(
                dlg, "Invalid key",
                "Couldn't recognise a key line in your input.\n\n"
                "Expected format:\n  <key_id> = <passphrase>\n\n"
                "Example:\n  2026-05-24 = _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR"
            )
            return
        kid, pw = parsed
        try:
            append_key(kid, pw)
        except Exception as e:
            QMessageBox.critical(
                dlg, "Could not save",
                f"Failed to write keystore:\n{e}"
            )
            return
        state["saved"] = True
        dlg.accept()

    btn_ok.clicked.connect(on_ok)
    btn_cancel.clicked.connect(dlg.reject)

    # Force a light palette so dark-mode OS doesn't render this unreadable.
    pal = dlg.palette()
    pal.setColor(QPalette.Window, QColor(0xF6, 0xF6, 0xF6))
    pal.setColor(QPalette.Base, QColor(0xFF, 0xFF, 0xFF))
    pal.setColor(QPalette.Text, QColor(0x20, 0x20, 0x20))
    pal.setColor(QPalette.WindowText, QColor(0x20, 0x20, 0x20))
    pal.setColor(QPalette.Button, QColor(0xEE, 0xEE, 0xEE))
    pal.setColor(QPalette.ButtonText, QColor(0x20, 0x20, 0x20))
    dlg.setPalette(pal)

    dlg.exec()
    return state["saved"]


def looks_like_keystore_problem(db_info: str) -> bool:
    """Heuristic: did load_material_db() fail because of the keystore?

    Used by the caller to decide whether to show the key dialog vs
    show a generic 'DB missing' error.
    """
    s = (db_info or "").lower()
    return ("keystore" in s) or ("no decryptable" in s)


def open_add_key_dialog(parent=None) -> bool:
    """Add-a-key flow for the running app (vs failure-recovery flow).

    Shown from a menu / button. After save, a follow-up dialog suggests
    restarting to pick up any newer release the key unlocks.
    """
    saved = ask_user_for_key(
        parent=parent,
        title="MDS Viewer - Add release key",
        intro_html=_ADD_KEY_INTRO_HTML,
    )
    if saved:
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                parent, "Key saved",
                "The key was added to your keystore.\n\n"
                "Restart MDS Viewer to load any newer release this "
                "key unlocks. The current session will keep showing "
                "whatever release it has already loaded."
            )
        except Exception:
            pass
    return saved


def list_stored_key_ids() -> list[str]:
    """Return the key_ids currently in ~/.mds_viewer_keys (sorted)."""
    p = keystore_path()
    if not p.is_file():
        return []
    out = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        out.append(s.split("=", 1)[0].strip())
    return sorted(set(out))
