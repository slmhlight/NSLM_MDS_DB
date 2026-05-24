"""AES-256-GCM encrypted material_db distribution.

Distribution model
------------------

* Encrypted DB releases accumulate in `data/archive/` as
  `material_db_<YYYY-MM-DD>.enc` (or `_<release_tag>.enc`).
* Each release is encrypted under a *release key*. The key has an
  identifier (`key_id`, free-form string) that is written into the
  file header so the loader knows which passphrase to try.
* Users hold a **keystore** (`keys.txt`) mapping each `key_id` to its
  passphrase. They obtain keys out-of-band from the maintainer.
* At startup the app scans `data/archive/`, picks the newest .enc whose
  `key_id` is in the user's keystore, and decrypts it in memory.

Result: a user with only older keys is "frozen" at whatever release
they last received a key for. Issue the next key and they advance.

File format v2
--------------

    offset  size   field
    ------  ----   -----
     0       4    magic   = b"MDSE"
     4       1    version = 2
     5       1    key_id_len (n, 0..255)
     6       n    key_id  (UTF-8 string, no whitespace ideal)
     6+n    16    salt    (PBKDF2-HMAC-SHA256, 200_000 iters)
    22+n    12    nonce   (AES-GCM IV)
    34+n   var    ciphertext
    end-16  16    auth_tag (GCM)

Keystore format
---------------

`keys.txt` — one entry per line, `<key_id> = <passphrase>`. Lines
starting with `#` are comments. Whitespace around `=` is trimmed.

    # 2026-05 release — issued 2026-05-23
    2026-05-23 = correct horse battery staple
    # 2026-06 release
    2026-06-01 = another one bites the dust

Resolution order:
  1. `MDS_DB_KEYS` env var (path to a keystore file)
  2. `<exe-or-project>/keys.txt`
  3. `~/.mds_viewer_keys`
"""
from __future__ import annotations

import os
import re
import sys
from hashlib import pbkdf2_hmac
from pathlib import Path

# Lazy import — only fails if encrypted path is actually used.
def _aesgcm():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM


MAGIC = b"MDSE"
VERSION = 2
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16

KDF_ITERATIONS = 200_000
KEY_LEN = 32

KEYSTORE_FILENAME = "keys.txt"


# =========================================================================
# Header parsing
# =========================================================================

def _read_header(blob: bytes) -> tuple[str, bytes, bytes, int]:
    """Return (key_id, salt, nonce, header_size). Raises on bad magic."""
    if len(blob) < 6:
        raise ValueError("encrypted blob too short")
    if blob[:4] != MAGIC:
        raise ValueError(f"bad magic header (expected {MAGIC!r})")
    ver = blob[4]
    if ver != VERSION:
        raise ValueError(
            f"unsupported file version: {ver} (this build understands v{VERSION})")
    kid_len = blob[5]
    off = 6
    if len(blob) < off + kid_len + SALT_LEN + NONCE_LEN + TAG_LEN:
        raise ValueError("encrypted blob shorter than header expects")
    key_id = blob[off:off + kid_len].decode("utf-8")
    off += kid_len
    salt = blob[off:off + SALT_LEN]; off += SALT_LEN
    nonce = blob[off:off + NONCE_LEN]; off += NONCE_LEN
    return key_id, salt, nonce, off


def _build_header(key_id: str, salt: bytes, nonce: bytes) -> bytes:
    kid_bytes = key_id.encode("utf-8")
    if len(kid_bytes) > 255:
        raise ValueError("key_id too long (max 255 bytes UTF-8)")
    return (MAGIC + bytes([VERSION, len(kid_bytes)])
            + kid_bytes + salt + nonce)


def read_key_id(path: str | Path) -> str:
    """Read just the key_id from a .enc file (without decrypting)."""
    blob = Path(path).read_bytes()
    key_id, _, _, _ = _read_header(blob)
    return key_id


# =========================================================================
# Key derivation
# =========================================================================

def _derive_key(salt: bytes, passphrase: str | bytes) -> bytes:
    if isinstance(passphrase, str):
        passphrase = passphrase.encode("utf-8")
    return pbkdf2_hmac("sha256", passphrase, salt, KDF_ITERATIONS, KEY_LEN)


# =========================================================================
# Encrypt / decrypt
# =========================================================================

def encrypt_bytes(plaintext: bytes, key_id: str, passphrase: str | bytes) -> bytes:
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(salt, passphrase)
    ct_plus_tag = _aesgcm()(key).encrypt(nonce, plaintext, associated_data=None)
    return _build_header(key_id, salt, nonce) + ct_plus_tag


def decrypt_bytes(blob: bytes, passphrase: str | bytes) -> bytes:
    key_id, salt, nonce, off = _read_header(blob)
    key = _derive_key(salt, passphrase)
    ct_plus_tag = blob[off:]
    return _aesgcm()(key).decrypt(nonce, ct_plus_tag, associated_data=None)


def encrypt_file(plain_path, enc_path, key_id, passphrase):
    plain_path = Path(plain_path); enc_path = Path(enc_path)
    data = plain_path.read_bytes()
    out = encrypt_bytes(data, key_id, passphrase)
    enc_path.parent.mkdir(parents=True, exist_ok=True)
    enc_path.write_bytes(out)
    return len(out)


def decrypt_file(enc_path, passphrase):
    return decrypt_bytes(Path(enc_path).read_bytes(), passphrase)


# =========================================================================
# Keystore — text file mapping key_id → passphrase
# =========================================================================

def _candidate_keystore_paths() -> list[Path]:
    out = []
    env = os.environ.get("MDS_DB_KEYS")
    if env:
        out.append(Path(env))
    # Project / executable dir
    if getattr(sys, "frozen", False):
        out.append(Path(sys.executable).parent / KEYSTORE_FILENAME)
    out.append(Path(__file__).resolve().parent / KEYSTORE_FILENAME)
    out.append(Path.home() / ".mds_viewer_keys")
    return out


def load_keystore(path: str | Path | None = None) -> dict[str, str]:
    """Return {key_id: passphrase}. Empty dict if nothing readable."""
    paths = [Path(path)] if path else _candidate_keystore_paths()
    for p in paths:
        if p and p.is_file():
            return _parse_keystore(p.read_text(encoding="utf-8")), p
    return {}, None


def _parse_keystore(text: str) -> dict[str, str]:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"): continue
        if "=" not in line: continue
        kid, pw = line.split("=", 1)
        kid = kid.strip(); pw = pw.strip()
        if kid: out[kid] = pw
    return out


# =========================================================================
# Resolve newest accessible .enc in an archive folder
# =========================================================================

_DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _sort_key_for_filename(p: Path) -> str:
    """Prefer date encoded in filename; fall back to mtime."""
    m = _DATE_IN_NAME.search(p.name)
    return m.group(1) if m else f"0000-00-00_{p.stat().st_mtime:.0f}"


def find_accessible_archive(archive_dir: str | Path,
                             keystore: dict[str, str] | None = None):
    """Return (path, key_id, passphrase) of the newest .enc the keystore can
    decrypt — or None if nothing is accessible.

    "Newest" is determined by the date encoded in the filename, with
    file mtime as a tie-breaker.
    """
    archive = Path(archive_dir)
    if not archive.is_dir():
        return None
    if keystore is None:
        keystore, _ = load_keystore()
    if not keystore:
        return None
    files = sorted(archive.glob("*.enc"),
                    key=_sort_key_for_filename, reverse=True)
    for f in files:
        try:
            kid = read_key_id(f)
        except Exception:
            continue
        if kid in keystore:
            return f, kid, keystore[kid]
    return None


# =========================================================================
# CLI
# =========================================================================

def _cli():
    import argparse
    import datetime as _dt
    import secrets

    ap = argparse.ArgumentParser(
        description="MDS Viewer DB crypto (v2: archive + per-release keys)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("encrypt",
        help="Encrypt a plain DB into a release-tagged archive file")
    e.add_argument("plain", help="Plain material_db.json path")
    e.add_argument("--archive-dir", default="data/archive",
        help="Destination folder (default: data/archive)")
    e.add_argument("--release-date",
        default=_dt.date.today().isoformat(),
        help="Release date / key_id (default: today's YYYY-MM-DD)")
    e.add_argument("--passphrase",
        help="Passphrase for this release. If omitted a random 32-char "
             "passphrase is generated and printed to stdout.")
    e.add_argument("--also-append-keystore", metavar="KEYSTORE_PATH",
        help="If set, append the generated key_id=passphrase line to "
             "this keystore (helpful for the maintainer's master copy).")

    d = sub.add_parser("decrypt",
        help="Decrypt a .enc using the keystore (or --passphrase)")
    d.add_argument("enc", help="Path to .enc file")
    d.add_argument("--passphrase",
        help="Override: passphrase string (otherwise looked up in keystore)")
    d.add_argument("--keystore",
        help="Path to keys.txt (otherwise default lookup)")
    d.add_argument("--out", help="Write plaintext here (else stdout)")

    inf = sub.add_parser("info", help="Show key_id of a .enc without decrypting")
    inf.add_argument("enc")

    res = sub.add_parser("resolve",
        help="Print the newest .enc in <archive_dir> that the user's "
             "keystore can decrypt")
    res.add_argument("--archive-dir", default="data/archive")
    res.add_argument("--keystore")

    sub.add_parser("genkey", help="Print a fresh random passphrase")

    args = ap.parse_args()

    if args.cmd == "encrypt":
        archive = Path(args.archive_dir)
        archive.mkdir(parents=True, exist_ok=True)
        pw = args.passphrase
        if not pw:
            pw = secrets.token_urlsafe(24)
        out_path = archive / f"material_db_{args.release_date}.enc"
        n = encrypt_file(args.plain, out_path, args.release_date, pw)
        print(f"encrypted {args.plain} → {out_path}  ({n} bytes)")
        print(f"key_id={args.release_date}")
        print(f"passphrase={pw}")
        if args.also_append_keystore:
            ks = Path(args.also_append_keystore)
            line = f"\n{args.release_date} = {pw}\n"
            with ks.open("a", encoding="utf-8") as f: f.write(line)
            print(f"appended to keystore: {ks}")

    elif args.cmd == "decrypt":
        if args.passphrase:
            pw = args.passphrase
        else:
            ks_path = args.keystore
            store, _ = load_keystore(ks_path)
            kid = read_key_id(args.enc)
            if kid not in store:
                print(f"ERROR — no key for key_id={kid!r} in keystore",
                      file=sys.stderr)
                sys.exit(2)
            pw = store[kid]
        plain = decrypt_file(args.enc, pw)
        if args.out:
            Path(args.out).write_bytes(plain)
            print(f"decrypted {args.enc} → {args.out}  ({len(plain)} bytes)")
        else:
            sys.stdout.buffer.write(plain)

    elif args.cmd == "info":
        print(f"key_id: {read_key_id(args.enc)}")

    elif args.cmd == "resolve":
        store, ks_path = load_keystore(args.keystore)
        if not store:
            print("ERROR — no keystore found / empty", file=sys.stderr)
            sys.exit(2)
        print(f"keystore: {ks_path}  ({len(store)} keys)")
        hit = find_accessible_archive(args.archive_dir, store)
        if not hit:
            print(f"ERROR — no decryptable .enc in {args.archive_dir}",
                  file=sys.stderr)
            sys.exit(3)
        path, kid, _ = hit
        print(f"selected: {path}  (key_id={kid})")

    elif args.cmd == "genkey":
        print(secrets.token_urlsafe(24))


if __name__ == "__main__":
    _cli()
