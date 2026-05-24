# Contributing new entries

If you have a TDS that isn't in the current release — a new vendor, new
material, new layer-thickness combo, or a revised value — you can
propose it via a pull request to the `contributions/pending/` folder.
The maintainer reviews each PR, merges accepted submissions into the
master database, and rolls them into the next encrypted release.

## What you need

- A public, verifiable source for the values: vendor's official TDS,
  ASTM/MMPDS spec sheet, or a peer-reviewed paper. Screenshots from
  conference talks don't count.
- A GitHub account for the PR.
- A working clone of this repo plus `pip install -r requirements.txt`.

## The 90-second path

```bash
git checkout -b add-eos-in625-50um
python contribute.py add-vendor
# follow the prompts — material, manufacturer, machine, values
python contribute.py validate contributions/pending/<the new file>.json
git add contributions/pending/<the new file>.json
git commit -m "Add EOS M-290 IN625 50μm as-built (new TDS rev)"
git push origin add-eos-in625-50um
# open PR on GitHub
```

The maintainer sees your PR, runs `15_merge_contributions.py`, and if
your numbers match the linked TDS, accepts the merge. Your file moves to
`contributions/applied/<merge-date>/<your-file>.json` and the next
release includes your entry.

## Contribution types

See `contributions/SCHEMA.md` for the full schema. Three types so far:

| Type | When to use |
|---|---|
| `add_vendor_entry` | Adding a new (manufacturer, machine, layer, post) combo under a material that already exists in the DB |
| `add_material` | The material itself isn't in the DB — needs its own slot, composition, basic properties |
| `update_vendor_entry` | Fixing a value on an existing entry (e.g., vendor published a corrected TDS revision) |

## Templates

Copy one of these and fill in the blanks:

- `contributions/TEMPLATE_add_vendor_entry.json`
- `contributions/TEMPLATE_add_material.json`

Or run the interactive wizard:

```bash
python contribute.py add-vendor
python contribute.py add-material
```

## What gets validated

The same validator runs on your machine before commit and on the
maintainer's side at merge:

- JSON parseable, envelope fields present.
- `type` is one of the supported values.
- `source` is an http(s) URL.
- For `add_vendor_entry`: `target_material` exists in the current DB.
- For `add_material`: `name` isn't already in the DB,
  `category_top` is one of the 8 canonical buckets (Aluminium / Cobalt /
  Copper / Nickel / Steel / Titanium / Niobium / Other), composition has
  at least one row, a `first_vendor_entry` is included.
- Mechanical sanity: YS ≤ UTS per direction, elongation in [0,100], HV in
  [10,1000], `tds_link` is a URL.

Run before submitting:

```bash
python contribute.py validate contributions/pending/<your file>.json
```

## PR review checklist (maintainer)

- [ ] Source URL is reachable and shows the same numbers
- [ ] `target_material` (or the proposed new material) makes physical
      sense given the source
- [ ] Composition matches a reasonable standard (ASTM/AMS/DIN) for that
      grade
- [ ] No values look extracted from the wrong column (UTS = ~YS or HV =
      ~hardness scale conversion artifact)
- [ ] Run `15_merge_contributions.py` interactively → confirm each
- [ ] Run `10_verify.py` after — should still be all-PASS

## What happens after merge

1. Your file moves from `pending/` to `applied/<merge-date>/`.
2. The maintainer encrypts a new release:
   `python db_crypto.py encrypt data/material_db.json --also-append-keystore keys.master.txt`
3. A new `.enc` file lands in `data/archive/`.
4. The new line in the maintainer's master keystore (a fresh random
   passphrase) gets shared out-of-band with the audience entitled to
   the new release.
5. Users with the new key auto-pick up the change on their next launch;
   users without it stay on the previous release until they get the key.

## Code-of-conduct shortlist

- Don't submit values you can't link to a source.
- Don't submit competitor-IP (closed beta TDS, NDA'd drafts, etc.).
- One PR per contribution where reasonable — easier to review than a
  bundle of unrelated entries.
- If you spot an error in someone else's already-merged entry, open an
  `update_vendor_entry` contribution rather than editing the DB directly
  (the DB is generated from these contributions over time).
