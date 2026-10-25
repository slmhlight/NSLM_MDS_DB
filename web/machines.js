// The machine catalog window (machines_dialog.open_machines_dialog) and its
// side-by-side compare window. The formatting helpers keep the desktop's
// names and order so the two files can be read together.
import { h, openExternal, messageBox } from "./util.js";
import { pyFormatG, pyFixed, pyFloat, pyStr, strValue, truthy, isFloat } from "./py.js";
import { SortFilterProxy, I, D, S } from "./proxy.js";
import { catalogTable } from "./table.js";
import { openWindow } from "./window.js";

const g = (v) => pyFormatG(v);                      // f"{v:g}"
const isList = Array.isArray;
const isDict = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const notesOf = (m) => (truthy(m.notes) ? String(m.notes) : "");

// sorted(set(values)): numbers only, as Python's sort would demand.
function uniqSorted(values) {
  const out = [];
  for (const v of values) {
    if (typeof v !== "number") throw new TypeError("'<' not supported");
    if (!out.some((u) => u === v)) out.push(v);
  }
  return out.sort((a, b) => a - b);
}

// m.get(k, dflt) as the QVariant a sort role returns
function tagged(m, k, dflt) {
  const v = Object.hasOwn(m, k) ? m[k] : dflt;
  if (v === null || v === undefined) return null;
  if (typeof v === "string") return S(v);
  if (typeof v === "number") return isFloat(m, k) ? D(v) : I(v);
  return S(strValue(v));
}

// ---- formatting helpers ----
export function fmtBuild(m) {
  const bv = m.build_volume_mm;
  if (!truthy(bv) || !isList(bv)) return "-";
  // cylindrical chambers are documented as Ø in notes
  if (notesOf(m).includes("Ø") && bv.length === 3) return `Ø${g(bv[0])} × ${g(bv[2])}`;
  try {
    return bv.map(g).join(" × ");
  } catch {
    return "-";
  }
}

function buildSortKey(m) {
  const bv = m.build_volume_mm;
  if (!truthy(bv) || !isList(bv)) return -1;
  let vol = 1;
  for (const v of bv) {
    const f = pyFloat(v);
    if (f === null) return -1;
    vol *= f;
  }
  return vol;
}

function fmtLasers(m) {
  const n = m.laser_count, pw = m.laser_power_W;
  if (!truthy(n) && !truthy(pw)) return "-";
  let pwStr = "";
  if (isList(pw) && pw.length) {
    const uniq = uniqSorted(pw);
    pwStr = uniq.length === 1 ? `${g(uniq[0])} W` : `${uniq.map(g).join("/")} W`;
  }
  if (truthy(n) && pwStr) return `${pyStr(m, "laser_count")} × ${pwStr}`;
  if (truthy(n)) return `${pyStr(m, "laser_count")} ×`;
  return pwStr || "-";
}

function laserCountDisp(m) {
  return truthy(m.laser_count) ? pyStr(m, "laser_count") : "-";
}

function laserCountSort(m) {
  const f = pyFloat(m.laser_count);
  return f === null ? -1 : f;
}

function laserPowerDisp(m) {
  const pw = m.laser_power_W;
  if (!truthy(pw) || !isList(pw)) return "-";
  const uniq = uniqSorted(pw);
  return uniq.length === 1 ? g(uniq[0]) : uniq.map(g).join(" / ");
}

function laserPowerSort(m) {
  const pw = m.laser_power_W;
  if (isList(pw) && pw.length && pw.every((v) => typeof v === "number")) return Math.max(...pw);
  return -1;
}

function laserArrayDisp(m) {
  const n = m.laser_count, pw = m.laser_power_W;
  if (!truthy(pw) || !isList(pw)) return truthy(n) ? `${pyStr(m, "laser_count")} ×` : "-";
  const uniq = uniqSorted(pw);
  const p = uniq.length === 1 ? `${g(uniq[0])} W` : `${uniq.map(g).join(" / ")} W`;
  return truthy(n) ? `${pyStr(m, "laser_count")} × ${p}` : p;
}

// total installed power = count x strongest laser; max() raising -> no value
function laserArraySort(m) {
  const n = truthy(m.laser_count) ? m.laser_count : 0;
  const pw = m.laser_power_W;
  let p = 0;
  if (isList(pw) && pw.length) {
    if (!pw.every((v) => typeof v === "number")) return null;
    p = Math.max(...pw);
  }
  const a = pyFloat(n), b = pyFloat(p);
  return a === null || b === null ? -1 : a * b;
}

function fmtLayer(m) {
  const lt = m.layer_thickness_um;
  if (!truthy(lt) || !isList(lt)) return "-";
  if (lt.length === 2) return `${g(lt[0])}–${g(lt[1])}`;
  return lt.map(g).join("/");
}

function layerSortKey(m) {
  const lt = m.layer_thickness_um;
  if (isList(lt) && lt.length) {
    const f = pyFloat(lt[0]);
    if (f !== null) return f;
  }
  return 1e9;          // unknown sorts last ascending
}

export function fmtPrice(m) {
  const pr = m.price_usd_range;
  if (!truthy(pr) || !isList(pr) || pr.length !== 2) return "—";
  const fm = (v) => (v >= 1e6 ? `${pyFixed(v / 1e6, 2)}M` : `${pyFixed(v / 1e3, 0)}k`);
  const [lo, hi] = pr;
  if (typeof lo !== "number" || typeof hi !== "number") throw new TypeError("price is not a number");
  if (lo === hi) return `~$${fm(lo)}`;
  return `$${fm(lo)}–${fm(hi)}`;
}

function priceSortKey(m) {
  const pr = m.price_usd_range;
  if (isList(pr) && pr.length === 2) {
    const f = pyFloat(pr[0]);
    if (f !== null) return f;
  }
  return -1;            // unknown price sorts first ascending / last descending
}

function fmtRelease(m) {
  return truthy(m.release_year) ? pyStr(m, "release_year") : "—";
}

function releaseSortKey(m) {
  const f = pyFloat(m.release_year);
  return f === null ? -1 : f;
}

function statusDisp(m) {
  return m.product_status === "active" ? "● active"
    : m.product_status === "discontinued" ? "○ discontinued" : "? unknown";
}

// COLUMNS: (header, display, sort role); column 0 is the picture.
export const COLUMNS = [
  ["", null, (m) => I(truthy(m.image_path) ? 1 : 0)],
  ["Manufacturer", (m) => (Object.hasOwn(m, "manufacturer") ? m.manufacturer : "-"), (m) => tagged(m, "manufacturer", "")],
  ["Model", (m) => (Object.hasOwn(m, "model_canonical") ? m.model_canonical : "-"), (m) => tagged(m, "model_canonical", "")],
  ["Status", statusDisp, (m) => tagged(m, "product_status", "z")],
  ["Build vol (mm)", fmtBuild, (m) => D(buildSortKey(m))],
  ["Lasers", laserCountDisp, (m) => D(laserCountSort(m))],
  ["Power (W)", laserPowerDisp, (m) => D(laserPowerSort(m))],
  ["Array", laserArrayDisp, (m) => { const v = laserArraySort(m); return v === null ? null : D(v); }],
  ["Layer µm", fmtLayer, (m) => D(layerSortKey(m))],
  ["Price (USD)", fmtPrice, (m) => D(priceSortKey(m))],
  ["Released", fmtRelease, (m) => D(releaseSortKey(m))],
];
// Columns whose values are numeric and right-aligned.
const NUMERIC_COLS = [4, 5, 6, 8, 9, 10];

// MachineModel.data(DisplayRole): a failing formatter shows "-".
export function displayText(m, col) {
  let v;
  try {
    v = COLUMNS[col][1](m);
  } catch {
    return "-";
  }
  return v === null || v === undefined ? "" : typeof v === "string" ? v : strValue(v);
}

export function sortValue(m, col) {
  try {
    return COLUMNS[col][2](m);
  } catch {
    return null;
  }
}

// MachineFilter.filterAcceptsRow
export function accepts(m, f) {
  if (f.vendor && m.vendor_slug !== f.vendor) return false;
  if (f.status && m.product_status !== f.status) return false;
  if (f.text) {
    const aliases = truthy(m.model_aliases) && isList(m.model_aliases) ? m.model_aliases.map((a) => strValue(a)).join(" ") : "";
    const hay = [pyStr(m, "manufacturer", ""), pyStr(m, "model_canonical", ""), aliases, pyStr(m, "notes", "")]
      .join(" ").toLowerCase();
    if (!hay.includes(f.text)) return false;
  }
  return true;
}

// ---- shared spec extraction (the compare window) ----
function rng(v, unit = "") {
  if (!truthy(v) || !isList(v)) return null;
  if (v.length === 2 && v[0] !== v[1]) return `${g(v[0])}–${g(v[1])}${unit}`;
  return `${g(v[0])}${unit}`;
}

function priceWithConf(m) {
  if (!truthy(m.price_usd_range)) return null;
  let s = fmtPrice(m);
  if (m.price_confidence === "low") s += " (rough est.)";
  else if (m.price_confidence === "medium") s += " (est.)";
  return s;
}

const raw = (m, k) => (m[k] === null || m[k] === undefined || m[k] === "" ? null : pyStr(m, k));

// _machine_spec_items: [label, str(value) | null]
export function specItems(m) {
  const bv = m.build_volume_mm;
  let bvStr = null;
  if (truthy(bv) && isList(bv)) {
    bvStr = notesOf(m).includes("Ø") && bv.length === 3 ? `Ø${g(bv[0])} × ${g(bv[2])} mm` : `${bv.map(g).join(" × ")} mm`;
  }
  const fp = m.footprint_mm;
  const atm = truthy(m.atmosphere) ? m.atmosphere.map((a) => strValue(a)).join(", ") : "";
  return [
    ["Manufacturer", raw(m, "manufacturer")],
    ["Status", raw(m, "product_status")],
    ["Released", raw(m, "release_year")],
    ["Build volume", bvStr],
    ["Lasers", truthy(m.laser_count) ? laserCountDisp(m) : null],
    ["Power / laser", truthy(m.laser_power_W) ? `${laserPowerDisp(m)} W` : null],
    ["Array", truthy(m.laser_count) ? laserArrayDisp(m) : null],
    ["Laser type", raw(m, "laser_type")],
    ["Spot size", rng(m.spot_size_um, " µm")],
    ["Scan speed", truthy(m.scan_speed_max_m_s) ? `${g(m.scan_speed_max_m_s)} m/s` : null],
    ["Layer thickness", rng(m.layer_thickness_um, " µm")],
    ["Atmosphere", atm || null],
    ["Max O2", truthy(m.oxygen_ppm_max) ? `<= ${g(m.oxygen_ppm_max)} ppm` : null],
    ["Footprint", truthy(fp) ? `${fp.map(g).join(" × ")} mm` : null],
    ["Weight", truthy(m.weight_kg) ? `${g(m.weight_kg)} kg` : null],
    ["Power draw", truthy(m.power_kW) ? `${g(m.power_kW)} kW` : null],
    ["Est. price (USD)", priceWithConf(m)],
  ];
}

// The compare table: [label, a, b, differs]; "" stands for a blank value.
export function compareRows(ma, mb) {
  const b = new Map(specItems(mb));
  return specItems(ma).map(([label, va]) => {
    const sa = va ?? "", sb = b.get(label) ?? "";
    return [label, sa, sb, Boolean((sa || sb) && sa !== sb)];
  });
}

// ---- the detail pane (_render_detail) ----
const span = (style, ...kids) => h("span", { style }, ...kids);
const link = (url) => h("a", { href: String(url), target: "_blank", rel: "noopener noreferrer" }, String(url));

export function detailRows(m) {
  const status = m.product_status ?? "unknown";
  const statusNode = status === "active" ? span("color:#1a6a3a;font-weight:bold", "● Active")
    : status === "discontinued" ? span("color:#b03030;font-weight:bold", "○ Discontinued")
      : span("color:#888", "? Unknown");

  // link: product_url if present, else vendor homepage marked (discontinued)
  let linkNode;
  if (truthy(m.product_url)) linkNode = link(m.product_url);
  else if (truthy(m.vendor_home)) {
    linkNode = [link(m.vendor_home), " ", span("color:#b03030", "(product page retired — vendor homepage)")];
  } else linkNode = span("color:#b03030", "(no link — discontinued)");

  const bv = m.build_volume_mm;
  let bvStr = null;
  if (truthy(bv) && isList(bv)) {
    bvStr = notesOf(m).includes("Ø") && bv.length === 3
      ? `Ø${g(bv[0])} × ${g(bv[2])} mm (cylindrical)` : `${bv.map(g).join(" × ")} mm`;
  }
  const fp = m.footprint_mm;

  let price = fmtPrice(m);
  if (price !== "—") {
    const parts = [price];
    if (m.price_confidence === "low" || m.price_confidence === "medium") {
      parts.push(" ", span("color:#999;font-size:11px", `(${m.price_confidence === "low" ? "rough estimate" : "estimate"})`));
    }
    if (truthy(m.price_source_url)) {
      parts.push("  ", h("a", { href: String(m.price_source_url), target: "_blank", rel: "noopener noreferrer",
                                     style: "font-size:11px" }, "[source]"));
    }
    price = parts;
  }

  const rel = Object.hasOwn(m, "release_year") && m.release_year !== null ? pyStr(m, "release_year") : null;
  return [
    ["Status", statusNode],
    ["Released", rel],
    ["Build volume", bvStr],
    ["Lasers", fmtLasers(m)],
    ["Laser type", Object.hasOwn(m, "laser_type") && m.laser_type !== null ? pyStr(m, "laser_type") : null],
    ["Spot size", rng(m.spot_size_um, " µm")],
    ["Scan speed", truthy(m.scan_speed_max_m_s) ? `${g(m.scan_speed_max_m_s)} m/s` : null],
    ["Layer thickness", rng(m.layer_thickness_um, " µm")],
    ["Atmosphere", (truthy(m.atmosphere) ? m.atmosphere.map((a) => strValue(a)).join(", ") : "") || null],
    ["Max O₂", truthy(m.oxygen_ppm_max) ? `≤ ${g(m.oxygen_ppm_max)} ppm` : null],
    ["Footprint", truthy(fp) ? `${fp.map(g).join(" × ")} mm` : null],
    ["Weight", truthy(m.weight_kg) ? `${g(m.weight_kg)} kg` : null],
    ["Power", truthy(m.power_kW) ? `${g(m.power_kW)} kW` : null],
    ["Est. price", price],
    ["Link", linkNode],
    ["Aliases", (truthy(m.model_aliases) ? m.model_aliases.map((a) => strValue(a)).join(", ") : "") || null],
  ].filter(([, v]) => !(v === null || v === "" || v === "-" || v === "—"));
}

export function detailNode(m) {
  const rows = detailRows(m).map(([label, v]) => h("tr", {}, h("td", { class: "dt-label" }, label),
                                                   h("td", { class: "dt-value" }, v)));
  return h("div", { class: "detail-doc" },
    h("div", { class: "dt-title" }, `${pyStr(m, "manufacturer", "")} — ${pyStr(m, "model_canonical", "")}`),
    h("table", { class: "dt-specs" }, h("tbody", {}, rows)),
    h("div", { class: "dt-notes" }, notesOf(m)));
}

// ---- windows ----
function machineImage(images, m, { thumb = false } = {}) {
  const box = h("div", { class: thumb ? "thumb" : "pic" });
  images.url(m.image_path).then((url) => {
    if (!url) {
      if (!thumb) box.textContent = "(no image available)";
      return;
    }
    const img = h("img", { src: url, alt: "", loading: "lazy", decoding: "async" });
    img.addEventListener("error", () => { box.textContent = thumb ? "" : "(no image available)"; });
    box.replaceChildren(img);
  });
  return box;
}

export function openMachinesWindow(cat, { isMobile }) {
  const doc = cat.doc;
  const machines = Object.values(isDict(doc.machines) ? doc.machines : {}).filter(isDict);
  const vendors = isDict(doc._vendors) ? doc._vendors : {};
  const filter = { vendor: null, status: null, text: "" };

  return openWindow("MDS Viewer — Machine Catalog", (win) => {
    const proxy = new SortFilterProxy(machines.length, (s, c) => sortValue(machines[s], c),
                                      (s) => accepts(machines[s], filter));

    const vendorCombo = h("select", { class: "combo vendor", "aria-label": "Vendor" },
      h("option", { value: "" }, "All vendors"),
      Object.entries(vendors).map(([slug, name]) => h("option", { value: slug }, strValue(name))));
    const statusCombo = h("select", { class: "combo", "aria-label": "Status" },
      h("option", { value: "" }, "All"), h("option", { value: "active" }, "Active only"),
      h("option", { value: "discontinued" }, "Discontinued only"));
    const search = h("input", { type: "search", class: "combo search", placeholder: "model, alias, or keyword…",
                                "aria-label": "Search", autocomplete: "off" });
    const compareBtn = h("button", { type: "button", class: "tool compare",
                                     tip: "Pick exactly two machines (click one row, then Ctrl+click another),\n"
                                       + "then press this to open a side-by-side comparison window." }, "⇄ Compare 2");
    const count = h("span", { class: "cat-count" });

    const detailImg = h("div", { class: "detail-img" }, "Select a machine");
    const detailTxt = h("div", { class: "detail-txt" });

    const table = catalogTable({
      columns: COLUMNS.map(([label], ci) => ({ label, cls: ci === 0 ? "c-img" : NUMERIC_COLS.includes(ci) ? "num" : null })),
      proxy,
      rowKey: (s) => strValue(machines[s].id ?? s),
      multi: true,
      initialSort: 1,            // manufacturer ascending, then model
      cell(s, ci) {
        const m = machines[s];
        if (ci === 0) return { node: machineImage(cat.images, m, { thumb: true }), cls: "c-img" };
        const cls = [NUMERIC_COLS.includes(ci) ? "num" : "",
          m.product_status === "discontinued" ? "muted" : ci === 3 && m.product_status === "active" ? "ok" : "",
          ci === 2 ? "wrap" : ""].filter(Boolean).join(" ");
        return { text: displayText(m, ci), cls, tip: truthy(m.notes) ? strValue(m.notes) : null };
      },
      onSelect({ selected, current }) {
        const m = current !== null ? machines[current] : selected.length ? machines[selected[0]] : null;
        if (m) renderDetail(m);
        // keep the compare button hint in sync with how many are picked
        compareBtn.textContent = selected.length === 2 ? "⇄ Compare these 2" : "⇄ Compare 2";
      },
      // double-click opens product page
      onActivate(s) {
        const m = machines[s];
        const url = truthy(m.product_url) ? m.product_url : m.vendor_home;
        if (truthy(url)) openExternal(String(url));
      },
      // a phone shows the details on a page of their own
      onTap(s) {
        if (!isMobile()) return false;
        openDetailSheet(cat, machines[s]);
        return true;
      },
    });

    function renderDetail(m) {
      detailImg.replaceChildren(machineImage(cat.images, m));
      detailTxt.replaceChildren(detailNode(m));
      detailTxt.scrollTop = 0;
    }

    const updateCount = () => { count.textContent = `${proxy.rows.length} / ${machines.length} machines`; };
    vendorCombo.addEventListener("change", () => { filter.vendor = vendorCombo.value || null; table.refilter(); updateCount(); });
    statusCombo.addEventListener("change", () => { filter.status = statusCombo.value || null; table.refilter(); updateCount(); });
    search.addEventListener("input", () => { filter.text = search.value.trim().toLowerCase(); table.refilter(); updateCount(); });

    compareBtn.addEventListener("click", () => {
      const sel = table.selected();
      if (sel.length !== 2) {
        messageBox("Compare machines", "Select exactly TWO machines to compare.\n\n" + (isMobile()
          ? "Tip: tick the boxes of two rows, then press Compare."
          : "Tip: click one row, then Ctrl+click a second row, then press Compare."));
        return;
      }
      openCompareWindow(cat, machines[sel[0]], machines[sel[1]]);
    });

    updateCount();
    // A phone has no detail pane, and a first row picked for it would be
    // a third tick next to the two the user picks for Compare.
    if (!isMobile()) table.selectFirst();

    const bar = h("div", { class: "cat-bar" },
      h("span", { class: "cat-title" }, "🔧 LPBF / AM Machine Catalog"),
      h("label", { class: "field" }, h("span", { class: "lbl" }, "Vendor:"), vendorCombo),
      h("label", { class: "field" }, h("span", { class: "lbl" }, "Status:"), statusCombo),
      h("label", { class: "field" }, h("span", { class: "lbl" }, "Search:"), search),
      compareBtn, h("span", { class: "stretch" }), count);
    const foot = h("div", { class: "cat-foot" },
      "Static hardware reference — not part of the encrypted material DB, not auto-updated. "
      + "Prices are rough industry estimates. ", h("span", { class: "dim" }, pyStr(doc, "_updated", "")));
    return [bar, catSplit(table.el, h("div", { class: "cat-detail" }, detailImg, detailTxt), "machines"), foot];
  }, { className: "catalog machines" });
}

// A table | detail splitter, the window's QSplitter (stretch 3 : 2).
export function catSplit(left, right, name) {
  const handle = h("div", { class: "splitter", role: "separator", "aria-orientation": "vertical", tip: "Drag to resize" });
  const split = h("div", { class: "cat-split" }, left, handle, right);
  const key = `mds_split_${name}`;
  const apply = (f) => split.style.setProperty("--cat-split", String(f));
  let saved = NaN;
  try { saved = Number(localStorage.getItem(key)); } catch { /* storage off */ }
  if (saved > 0.25 && saved < 0.85) apply(saved);
  handle.addEventListener("pointerdown", (e) => {
    const box = split.getBoundingClientRect();
    handle.setPointerCapture(e.pointerId);
    let f = null;
    const move = (ev) => { f = Math.min(0.85, Math.max(0.25, (ev.clientX - box.left) / box.width)); apply(f); };
    const up = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", up);
      if (f !== null) { try { localStorage.setItem(key, String(f)); } catch { /* storage off */ } }
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", up);
    e.preventDefault();
  });
  return split;
}

function openDetailSheet(cat, m) {
  openWindow(pyStr(m, "model_canonical", ""), () => [
    h("div", { class: "detail-img" }, machineImage(cat.images, m)),
    h("div", { class: "detail-txt" }, detailNode(m)),
  ], { className: "sheet" });
}

// open_compare_dialog
export function openCompareWindow(cat, ma, mb) {
  const title = `Compare — ${pyStr(ma, "model_canonical", "?")} vs ${pyStr(mb, "model_canonical", "?")}`;
  openWindow(title, () => {
    const cards = [ma, mb].map((m) => h("div", { class: "cmp-card" },
      h("div", { class: "cmp-img" }, compareImage(cat.images, m)),
      h("div", { class: "cmp-cap" },
        h("div", { class: "cmp-man" }, pyStr(m, "manufacturer", "")),
        h("div", { class: "cmp-model" }, pyStr(m, "model_canonical", "")))));
    const rows = compareRows(ma, mb).map(([label, a, b, differs]) => h("tr", { class: differs ? "diff" : null },
      h("td", { class: "spec" }, label), h("td", {}, a || "—"), h("td", {}, b || "—")));
    const table = h("table", { class: "cmp-table" },
      h("thead", {}, h("tr", {}, h("th", {}, "Spec"), h("th", {}, pyStr(ma, "model_canonical", "A")),
                         h("th", {}, pyStr(mb, "model_canonical", "B")))),
      h("tbody", {}, rows));
    const notes = [ma, mb].filter((m) => notesOf(m).trim()).map((m) => h("p", {},
      h("b", {}, `${pyStr(m, "model_canonical", "")}:`), " ", h("span", { class: "dim2" }, notesOf(m).trim())));
    return [h("div", { class: "cmp-head" }, cards), h("div", { class: "cmp-table-wrap" }, table),
      notes.length ? h("div", { class: "cmp-notes" }, notes) : null,
      h("div", { class: "cat-foot" }, "Amber-highlighted rows differ between the two machines. "
        + "Prices are rough industry estimates.")];
  }, { className: "compare" });
}

function compareImage(images, m) {
  const box = h("div", { class: "pic" });
  images.url(m.image_path).then((url) => {
    if (!url) { box.textContent = "(no image)"; return; }
    const img = h("img", { src: url, alt: "" });
    img.addEventListener("error", () => { box.textContent = "(no image)"; });
    box.replaceChildren(img);
  });
  return box;
}
