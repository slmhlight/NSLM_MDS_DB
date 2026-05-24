# Encrypted material_db distribution — archive + per-release keys

The DB you assembled is **not** committed to GitHub as plain JSON. Instead,
encrypted snapshots accumulate by date in `data/archive/`, each tagged with a
`key_id`. Users hold a keystore mapping `key_id → passphrase`. The app
picks the newest archived release that the user's keystore can decrypt.

A user with only older keys is naturally pinned to whatever release they
last received a key for. Issue a new key out-of-band, drop the new `.enc`
into the repo, and they advance automatically on next pull / next launch.

## Files

| Path | Owned by | Committed to git? |
|---|---|---|
| `data/material_db.json` | maintainer working file | **no** (gitignored) |
| `data/archive/material_db_YYYY-MM-DD.enc` | per-release artifact | **yes** |
| `keys.txt` (user side) | each end-user | **no** (gitignored) |
| `keys.master.txt` (maintainer's master record) | maintainer only | **no** (gitignored) |
| `db_crypto.py` | crypto module + CLI | yes |

## File format (v2)

```
offset  size   field
-----   ----   -----
 0       4    magic       = b"MDSE"
 4       1    version     = 2
 5       1    key_id_len  (n)
 6       n    key_id      (UTF-8, e.g. "2026-05-24")
 6+n    16    salt        (PBKDF2-HMAC-SHA256, 200_000 iters)
22+n    12    nonce       (AES-256-GCM IV)
34+n   var    ciphertext
end-16  16    auth_tag    (GCM)
```

`key_id` is exposed in clear so the loader can pick the right key without
trying every passphrase. The actual material data is fully encrypted.

## Keystore format (`keys.txt`)

```
# Issued 2026-05-24
2026-05-24 = _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR

# Issued 2026-06-01 — share with users on the new subscription
2026-06-01 = jDxr3xJp2qkNzU0FU6IjxxF-aBcCdEfG
```

Lookup order (first hit wins):
1. `$MDS_DB_KEYS` env var (path)
2. `keys.txt` next to `main.py` / the exe
3. `~/.mds_viewer_keys`

## Maintainer workflow

```bash
# 1. Update + verify the plain DB
python .claude/skills/refresh-tds-catalog/scripts/12_selfverify.py

# 2. Encrypt as a new release (random passphrase, today's date)
python db_crypto.py encrypt data/material_db.json --also-append-keystore keys.master.txt
# → data/archive/material_db_2026-05-24.enc
# → keys.master.txt grows by one line: "2026-05-24 = <random>"

# 3. Commit only the .enc + module changes
git add data/archive/material_db_2026-05-24.enc db_crypto.py resource_helper.py
git commit -m "Release 2026-05-24"
git push

# 4. Share the new key out-of-band (Slack/email/Telegram) — only the
#    one new line from keys.master.txt. Older keys remain valid for
#    older .enc files, never expire.
```

To set an explicit release date (e.g. backdated, or a release tag like
`v1.0`):

```bash
python db_crypto.py encrypt data/material_db.json \
    --release-date 2026-06-01 \
    --passphrase "your-chosen-passphrase" \
    --also-append-keystore keys.master.txt
```

## User workflow (source / dev)

1. Clone the repo or install the app.
2. Create `keys.txt` (or `~/.mds_viewer_keys`) with the line you were
   given out-of-band:

   ```
   2026-05-24 = _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR
   ```

3. Run `python main.py`. The app finds `data/archive/*.enc`, picks the
   newest whose `key_id` matches one in your keystore, and decrypts in
   memory. Nothing is written to disk.

When the maintainer issues a new release, the user **pulls the repo** to
get the new `.enc` file, **appends the new key line** to their `keys.txt`,
relaunches. Old releases remain accessible too (loader prefers newest).

## User workflow (onefile zip distribution)

End users who get the **onefile zip** (produced by `build_mds_onefile.bat`)
don't need to touch any text files:

1. Unzip `MDS_Viewer_<release>.zip` somewhere on disk. Contents:
   ```
   MDS_Viewer_<release>/
     MDS_Viewer.exe
     data/archive/*.enc
     README_DIST.txt
     LICENSE_NOTICE.txt
   ```
2. Double-click `MDS_Viewer.exe`.
3. First-launch dialog pops asking for the access key. Paste the line
   the maintainer sent (the exact same `<key_id> = <passphrase>` format),
   click **Save key & continue**.
4. The key is written to `%USERPROFILE%\.mds_viewer_keys` — the user
   never has to enter it again on that machine.

Receiving a new release — **fully automatic on next launch**:
- App startup fetches the latest `.enc` list from GitHub (best-effort,
  silent if offline). New `.enc` files land in the local
  `data/archive/`.
- App picks the newest release the user's keystore can decrypt. If
  they don't have the matching key yet, it falls back to whatever
  older release they DO have a key for — never a hard fail.
- When the user receives the new key line (out-of-band), they click
  **Add release key…** in the top-right of the main window, paste,
  save. On the next restart the new release is loaded.

This path keeps the keystore in the user's profile (so replacing the
app folder with a fresh unzip doesn't erase it) and means a user can
go from "received the zip" to "viewing data" without ever touching a
text file.

## Auto-update behavior

On every startup the app does one short HTTP call to:

```
GET https://api.github.com/repos/slmhlight/NSLM_MDS_DB/contents/data/archive?ref=main
```

For each remote `.enc` not already on disk (or whose size doesn't
match), it downloads to `<exe_dir>/data/archive/<filename>`. The
encrypted blob is useless without a key, so prefetching is safe — the
user only sees the new release if they also have the matching key.

**Failure modes are all silent**:
- no internet → log info, fall back to local files
- GitHub rate-limit (60/h unauthenticated) → fall back
- write-protected install location (Program Files w/o admin) → fall back
- private repo without credentials → fall back

**Disabling**: end users can set `MDS_NO_UPDATE=1` (env var) or pass
`--no-update` on the command line.

**Repo override**: `MDS_REPO=owner/repo` lets a fork swap the update
source without rebuilding. `MDS_BRANCH=main` overrides the branch.

For a fully offline deployment, set `MDS_NO_UPDATE=1` in a system /
user env var on the target machine — the app then never tries to reach
GitHub and only loads from whatever is in `data/archive/`.

## What happens to users without an update

- They `git pull` → see new `.enc` files in `data/archive/`.
- Their `keys.txt` doesn't have the new `key_id` → the loader's resolver
  walks down from newest to oldest, skipping releases it can't decrypt,
  and lands on whichever older release they still have a key for.
- Effect: they keep using the last DB they had access to. No silent
  downgrade message, no surprise lockout — just no upgrade.

## CLI helpers

```bash
# Inspect a .enc without decrypting
python db_crypto.py info data/archive/material_db_2026-05-24.enc
# → key_id: 2026-05-24

# Show which release a given keystore would load
python db_crypto.py resolve --archive-dir data/archive
# → selected: data/archive/material_db_2026-05-24.enc (key_id=2026-05-24)

# Generate a fresh random passphrase (for the next release)
python db_crypto.py genkey

# Manually decrypt to stdout (for piping into jq etc.)
python db_crypto.py decrypt data/archive/material_db_2026-05-24.enc \
    --passphrase _XlpDYEpplRgqmDSYQnjht2WTnfLkCVR
```

## Threat model

**Mitigates**:
- Casual scraping of the repo for raw material data
- Tampering of any committed `.enc` (GCM auth fails → app refuses to load)
- Accidental plain-DB commits (gitignored)
- Lapsed-subscription user pulling latest repo but without a fresh key —
  they're naturally pinned to their last paid release

**Does NOT mitigate**:
- A user who has been given the latest key and is determined to leak it
  (rotate keys for next release if you suspect leakage; that release
  uses a fresh key_id and `.enc`).
- Compromise of the maintainer's machine (`material_db.json` and
  `keys.master.txt` live there in cleartext).

## Migration from v1

If you have a v1 single-file `data/material_db.json.enc` from the
previous scheme, it will not load — v2 expects archive-folder layout.
Encrypt fresh into the archive:

```bash
python db_crypto.py encrypt data/material_db.json --also-append-keystore keys.master.txt
```

Delete the old `material_db.json.enc` (already in `.gitignore`).
