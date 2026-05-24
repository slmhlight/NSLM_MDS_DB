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
    "Paste the access-key line your maintainer sent you below. "
    "The format is:<br>"
    "<code>YYYY-MM-DD = &lt;your-key-here&gt;</code><br><br>"
    "The pass-phrase part is masked. Once saved you won't be asked again."
)

_ADD_KEY_INTRO_HTML = (
    "<b>Add a new release access key.</b><br>"
    "Paste the line your maintainer sent you below.<br>"
    "Format: <code>YYYY-MM-DD = &lt;your-key-here&gt;</code><br><br>"
    "Saved to your user profile. <b>Restart MDS Viewer</b> "
    "afterward to load any newer release this key unlocks.<br>"
    "Older keys stay valid — no harm in keeping them."
)


def ask_user_for_key(parent=None, message: str = "",
                     title: str = None, intro_html: str = None) -> bool:
    """Show a modal key-entry dialog. Returns True iff the user saved a key.

    Caller should then re-attempt the encrypted-DB load (or, when called
    from the add-key flow, prompt the user to restart).

    Security
    --------
    The passphrase part of the entered line is masked at all times by
    default. A "Show" toggle reveals it temporarily for verification.
    The visible-only feedback is the parsed key_id (the date prefix),
    so the user can confirm they pasted the right release without ever
    exposing the secret on screen.
    """
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QMessageBox, QCheckBox,
    )
    from PySide6.QtGui import QPalette, QColor, QFont

    dlg = QDialog(parent)
    dlg.setWindowTitle(title or "MDS Viewer - Enter access key")
    dlg.setModal(True)
    # Block close-on-Escape so user must explicitly Cancel.
    dlg.resize(540, 230)

    layout = QVBoxLayout(dlg)

    intro = QLabel(intro_html or _DEFAULT_INTRO_HTML)
    intro.setWordWrap(True)
    layout.addWidget(intro)

    if message:
        warn = QLabel(message)
        warn.setWordWrap(True)
        warn.setStyleSheet("color:#a04020; font-style:italic;")
        layout.addWidget(warn)

    # Masked single-line input + "Show" toggle.
    row = QHBoxLayout()
    edit = QLineEdit()
    edit.setEchoMode(QLineEdit.Password)
    edit.setPlaceholderText("paste the line: YYYY-MM-DD = <key>")
    mono = QFont("Consolas")
    mono.setStyleHint(QFont.Monospace)
    edit.setFont(mono)
    row.addWidget(edit, 1)

    show_chk = QCheckBox("Show")
    show_chk.setToolTip("Temporarily reveal the pasted line for verification")
    def _on_show(state):
        edit.setEchoMode(QLineEdit.Normal if show_chk.isChecked()
                          else QLineEdit.Password)
    show_chk.stateChanged.connect(_on_show)
    row.addWidget(show_chk)
    layout.addLayout(row)

    # Live key_id feedback — visible-safe (no passphrase shown).
    id_status = QLabel(" ")
    id_status.setStyleSheet("color:#1a3a6a; padding-left:4px;")
    layout.addWidget(id_status)

    def _on_text_changed(text):
        parsed = parse_key_line(text)
        if not text.strip():
            id_status.setText(" ")
            id_status.setStyleSheet("color:#666;")
        elif parsed is None:
            id_status.setText("✗  format not recognised — expected: YYYY-MM-DD = <key>")
            id_status.setStyleSheet("color:#a04020;")
        else:
            kid, _ = parsed
            id_status.setText(f"✓  detected key ID:  {kid}   (passphrase hidden)")
            id_status.setStyleSheet("color:#1f7a3f; font-weight:bold;")
    edit.textChanged.connect(_on_text_changed)

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
        parsed = parse_key_line(edit.text())
        if parsed is None:
            QMessageBox.warning(
                dlg, "Invalid key",
                "Couldn't recognise a key line in your input.\n\n"
                "Expected format:  <key_id> = <passphrase>\n"
                "                  (e.g. YYYY-MM-DD = <key>)\n\n"
                "Make sure both sides of the '=' are present."
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
