// The catalog windows' QTableView over a SortFilterProxy: click-to-sort
// headers with Qt's ▲/▼ indicator, alternating rows, row selection (Ctrl
// toggles, Shift extends), arrow keys, double-click to activate. A phone
// has no Ctrl key, so multi-select tables also get a tick box per row.
import { h } from "./util.js";

// columns: [{label, cls?}]; cell(row, col) -> {text | node, cls?, tip?}
export function catalogTable({ columns, proxy, rowKey, cell, multi = false, initialSort,
                               onSelect, onActivate, onTap }) {
  const ths = columns.map((c, ci) => h("th", { scope: "col", class: c.cls || null, onclick: () => onHeader(ci) },
    h("span", { class: "th-label" }, c.label), h("span", { class: "sort-ind" })));
  const tbody = h("tbody", {});
  const table = h("table", { class: "ctable" }, h("thead", {}, h("tr", {}, ths)), tbody);
  const wrap = h("div", { class: "ctable-wrap", tabindex: "0" }, table);
  const trs = new Map();           // source row -> <tr>, built once
  let sel = [];                    // selected source rows, in the order picked
  let cur = null;                  // current row (follows the last click)
  let anchor = null;               // where a Shift-click range starts

  function trOf(row) {
    if (!trs.has(row)) {
      const tds = columns.map((_, ci) => {
        const c = cell(row, ci);
        const td = h("td", { class: c.cls || null, tip: c.tip || null }, c.node ?? c.text ?? "");
        if (ci === 0 && multi) {
          const box = h("input", { type: "checkbox", class: "pick", "aria-label": "Select for comparison",
                                   tabindex: "-1" });
          td.prepend(box);
        }
        return td;
      });
      trs.set(row, h("tr", { dataset: { key: rowKey(row) } }, tds));
      trs.get(row)._row = row;
    }
    return trs.get(row);
  }

  function paint() {
    ths.forEach((th, ci) => {
      const on = ci === proxy.column;
      th.classList.toggle("sorted", on);
      th.querySelector(".sort-ind").textContent = on ? (proxy.descending ? "▼" : "▲") : "";
      th.setAttribute("aria-sort", on ? (proxy.descending ? "descending" : "ascending") : "none");
    });
    tbody.replaceChildren(...proxy.rows.map(trOf));
    markSelection();
  }

  function markSelection() {
    const set = new Set(sel);
    for (const [row, tr] of trs) {
      const on = set.has(row);
      tr.classList.toggle("selected", on);
      tr.classList.toggle("current", row === cur);
      const box = tr.querySelector("input.pick");
      if (box) box.checked = on;
    }
  }

  function changed() {
    markSelection();
    onSelect?.({ selected: sel.slice(), current: cur });
  }

  // QHeaderView: the sorted column flips; another column starts ascending.
  function onHeader(ci) {
    proxy.sort(ci, ci === proxy.column ? !proxy.descending : false);
    paint();
  }

  function click(row, { ctrl = false, shift = false } = {}) {
    if (shift && multi && anchor !== null && proxy.rows.includes(anchor)) {
      const a = proxy.rows.indexOf(anchor), b = proxy.rows.indexOf(row);
      const range = proxy.rows.slice(Math.min(a, b), Math.max(a, b) + 1);
      sel = ctrl ? [...sel, ...range.filter((r) => !sel.includes(r))] : range;
    } else if (ctrl) {
      if (sel.includes(row)) sel = sel.filter((r) => r !== row);
      else sel = multi ? [...sel, row] : [row];
      anchor = row;
    } else {
      sel = [row];
      anchor = row;
    }
    cur = row;
    changed();
  }

  tbody.addEventListener("click", (e) => {
    const tr = e.target.closest("tr");
    if (!tr || tr._row === undefined) return;
    if (e.target.matches("input.pick")) {
      click(tr._row, { ctrl: true });
      return;
    }
    const ctrl = e.ctrlKey || e.metaKey;
    // On a phone a tap opens the row's details (onTap returns true) and
    // the tick boxes do the picking.
    if (!ctrl && !e.shiftKey && onTap?.(tr._row)) return;
    click(tr._row, { ctrl, shift: e.shiftKey });
  });
  tbody.addEventListener("dblclick", (e) => {
    const tr = e.target.closest("tr");
    if (tr && tr._row !== undefined && !e.target.matches("input.pick")) onActivate?.(tr._row);
  });
  // Shift-click would otherwise select the page's text.
  tbody.addEventListener("mousedown", (e) => { if (e.shiftKey) e.preventDefault(); });

  wrap.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    if (!proxy.rows.length) return;
    e.preventDefault();
    const at = cur === null ? -1 : proxy.rows.indexOf(cur);
    const next = e.key === "ArrowDown" ? Math.min(proxy.rows.length - 1, at + 1) : Math.max(0, at - 1);
    click(proxy.rows[next]);
    trOf(proxy.rows[next]).scrollIntoView({ block: "nearest" });
  });

  // Qt's setSortingEnabled(True) sorts by column 0 descending first; the
  // window's own sortByColumn then sorts stably on top of that order.
  proxy.sort(0, true);
  proxy.sort(initialSort, false);
  paint();

  return {
    el: wrap,
    // After the filter changed: rows that left the table leave the selection.
    // A current row that left moves as Qt moves it on rowsAboutToBeRemoved:
    // with multi-selection (QItemSelectionModel) to the nearest row above
    // that stayed, else below; with single selection (QAbstractItemView) to
    // the nearest row below, else above - and that row becomes the selection.
    refilter() {
      const was = proxy.rows.slice();
      proxy.refilter();
      const shown = new Set(proxy.rows);
      const before = sel.slice();
      sel = sel.filter((r) => shown.has(r));
      if (cur !== null && !shown.has(cur)) {
        const at = was.indexOf(cur);
        const above = was.slice(0, at).reverse().find((r) => shown.has(r)) ?? null;
        const below = was.slice(at + 1).find((r) => shown.has(r)) ?? null;
        if (multi) {
          cur = above ?? below;
        } else {
          cur = below ?? above;
          sel = cur === null ? [] : [cur];
        }
      }
      paint();
      if (sel.length !== before.length || sel.some((r, i) => r !== before[i])) {
        onSelect?.({ selected: sel.slice(), current: cur });
      }
    },
    // table.selectRow(0)
    selectFirst() {
      if (proxy.rows.length) click(proxy.rows[0]);
    },
    selected: () => sel.slice(),
    rowElement: trOf,
  };
}
