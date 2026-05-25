# NSLM_MDS_DB

Distribution channel for the **MDS Viewer** material database.

This repository hosts encrypted release snapshots of the LPBF / AM
material data — nothing else. The viewer application is built and
distributed separately to authorised users.

```
data/archive/material_db_YYYY-MM-DD.enc   AES-256-GCM, header-tagged with key_id
```

## What lives here

- `data/archive/*.enc` — each file is one immutable release of the
  database, encrypted under a per-release key. Newer releases
  accumulate; older ones stay accessible to users who only have older
  keys.

## What does NOT live here

- The viewer source code, build scripts, contribution tools, and the
  refresh skill all live in the maintainer's working tree and are not
  needed by end users. The shipped `.exe` is self-contained.
- The plain database (`material_db.json`) — accessible only to the
  maintainer.
- Any keystore. Keys are distributed out-of-band, one line per
  release, to users entitled to it.

## How the viewer uses this repo

On startup the viewer fetches the file listing for
`data/archive/` via the GitHub Contents API and downloads any
``.enc`` it doesn't already have locally. Without a matching
key the file is useless, so prefetching is safe.

A user without a current key stays on whichever older release they
last had a key for. When the maintainer issues a new key, the user
pastes it via the in-app dialog and the new release becomes
accessible on the next launch.

## Contribution

End users can submit new vendor entries from inside the viewer
(menu → **Submit TDS data…**). The dialog writes a JSON contribution
file locally and copies the same JSON to the clipboard; the user then
sends it to the maintainer via whatever channel was provided. The
maintainer reviews, merges into the working DB, and rolls the change
into the next release.
