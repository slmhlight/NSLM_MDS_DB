// QSortFilterProxyModel, as the catalog windows drive it: rows sorted by a
// per-column sort value under Qt's comparison rules, and a filter re-run on
// every change. Qt does not re-sort after a filter change: rows that leave
// drop out, rows that come back are sorted among themselves and slotted in
// after their equals. Ties therefore depend on the click history, so this
// replays Qt's own bookkeeping step by step, and the table reads exactly as
// the desktop's does after the same clicks.

// Sort values are tagged as the QVariant was: an int, a float or a string
// from Python; null is an invalid QVariant (None, or a sort key that raised).
export const I = (v) => ({ k: "i", v });
export const D = (v) => ({ k: "d", v });
export const S = (v) => ({ k: "s", v });

// QAbstractItemModelPrivate::isVariantLessThan: an invalid value is never
// less and is greater than any valid one; otherwise the LEFT value's type
// decides the comparison (strings case-sensitively, by UTF-16 unit).
export function variantLess(l, r) {
  if (l === null) return false;
  if (r === null) return true;
  if (l.k === "s") return l.v < (r.k === "s" ? r.v : String(r.v));
  const rn = r.k === "s" ? Number(r.v) || 0 : r.v;
  return l.k === "i" ? Math.trunc(l.v) < Math.trunc(rn) : l.v < rn;
}

export class SortFilterProxy {
  // sortValue(sourceRow, column) -> tagged value; accepts(sourceRow) -> bool
  constructor(count, sortValue, accepts) {
    this.count = count;
    this.sortValue = sortValue;
    this.accepts = accepts;
    this.column = -1;
    this.descending = false;
    this.rows = [];                         // proxy row -> source row
    for (let s = 0; s < count; s++) if (accepts(s)) this.rows.push(s);
  }

  // a comes before b in the current order
  before(a, b) {
    const x = this.sortValue(a, this.column), y = this.sortValue(b, this.column);
    return this.descending ? variantLess(y, x) : variantLess(x, y);
  }

  // std::stable_sort; with no sort column, source order (reversed if descending)
  sortList(list) {
    if (this.column < 0) list.sort((a, b) => (this.descending ? b - a : a - b));
    else list.sort((a, b) => (this.before(a, b) ? -1 : this.before(b, a) ? 1 : 0));
  }

  // QSortFilterProxyModel::sort -- a no-op when column and order are unchanged.
  sort(column, descending) {
    if (column === this.column && descending === this.descending) return;
    this.column = column;
    this.descending = descending;
    this.sortList(this.rows);
  }

  // invalidateFilter -> handle_filter_changed
  refilter() {
    const shown = new Set(this.rows);
    const kept = this.rows.filter((s) => this.accepts(s));
    const added = [];
    for (let s = 0; s < this.count; s++) if (!shown.has(s) && this.accepts(s)) added.push(s);
    if (kept.length === this.rows.length && !added.length) return;
    this.sortList(added);
    this.rows = this.#insert(kept, added);
  }

  // proxy_intervals_for_source_items_to_add + insert_source_items: each new
  // row goes after every row it does not sort before (a binary search whose
  // low bound carries over from one new row to the next), and the new rows
  // that fit before the same existing row go in as one run.
  #insert(rows, added) {
    const sorted = this.column >= 0;
    const goesBefore = (a, b) => (sorted ? this.before(a, b) : a < b);
    const runs = [];
    let low = 0;
    let k = 0;
    while (k < added.length) {
      const first = added[k++];
      const run = [first];
      let high = rows.length - 1;
      while (low <= high) {
        const mid = (low + high) >> 1;
        if (goesBefore(first, rows[mid])) high = mid - 1;
        else low = mid + 1;
      }
      if (low >= rows.length) {
        while (k < added.length) run.push(added[k++]);
      } else {
        while (k < added.length && !goesBefore(rows[low], added[k])) run.push(added[k++]);
      }
      runs.push([low, run]);
    }
    const out = rows.slice();
    for (let i = runs.length - 1; i >= 0; i--) out.splice(runs[i][0], 0, ...runs[i][1]);
    return out;
  }
}
