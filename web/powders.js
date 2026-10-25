// The third-party powder supplier window (powders_dialog.open_powders_dialog).
// Rows are individual powders (supplier x alloy x PSD cut), each carrying
// its supplier's qualification gates (A: marketed for AM/PBF, B: PSD suits
// LPBF, C: validated on a named OEM machine).
import { h, openExternal } from "./util.js";
import { pyFormatG, pyFixed, pyFloat, pyStr, strValue, truthy, isFloat, pyCmp } from "./py.js";
import { SortFilterProxy, I, D, S } from "./proxy.js";
import { catalogTable } from "./table.js";
import { openWindow } from "./window.js";
import { catSplit } from "./machines.js";

const isList = Array.isArray;
const isDict = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

// One row per powder, carrying its supplier's qualification down.
export function flatten(doc) {
  const rows = [];
  for (const [slug, sup] of Object.entries(isDict(doc.suppliers) ? doc.suppliers : {})) {
    const q = isDict(sup.qualification) ? sup.qualification : {};
    const gates = new Set(truthy(q.gates_passed) ? q.gates_passed : []);
    for (const pw of truthy(sup.powders) ? sup.powders : []) {
      rows.push({
        ...pw,
        _supplier: truthy(sup.supplier) ? sup.supplier : slug,
        _supplier_slug: slug,
        _homepage: sup.homepage ?? null,
        _region: truthy(sup.region) ? sup.region : truthy(sup._region_group) ? sup._region_group : "",
        _gates: gates,
        _confidence: q.confidence ?? null,
        _supplier_oem: truthy(q.oem_machine_validated) ? q.oem_machine_validated : [],
        _supplier_notes: truthy(sup.notes) ? sup.notes : "",
        _src: pw,                                   // where the float flags live
      });
    }
  }
  return rows;
}

// str(r.get(k, dflt)) for a flattened row
const rstr = (r, k, dflt = null) => (Object.hasOwn(r._src, k) ? pyStr(r._src, k, dflt) : pyStr(r, k, dflt));

// _as_number: one float from a value that may be a range or a string like
// '<250' (the low end of a range; nothing at all rather than a guess).
export function asNumber(v) {
  if (isList(v)) v = v.length ? v[0] : null;
  if (typeof v === "string") {
    const m = /-?\d+(?:\.\d+)?/.exec(v);
    v = m ? m[0] : null;
  }
  return pyFloat(v);
}

const G = (n) => pyFormatG(n), F2 = (n) => pyFixed(n, 2), F0 = (n) => pyFixed(n, 0);

// _fmt_range: a value that may legitimately be a range
export function fmtRange(v, spec = G, unit = "") {
  if (isList(v)) {
    const nums = v.map(asNumber).filter((n) => n !== null);
    if (!nums.length) return null;
    if (nums.length >= 2 && nums[0] !== nums[1]) return `${spec(nums[0])}–${spec(nums[1])}${unit}`;
    return spec(nums[0]) + unit;
  }
  const n = asNumber(v);
  return n !== null ? spec(n) + unit : null;
}

function fmtPsd(r) {
  const v = r.psd_um;
  if (!truthy(v) || !isList(v)) return "—";
  const nums = v.map(asNumber).filter((n) => n !== null);
  if (!nums.length) return "—";
  if (nums.length === 2) return `${G(nums[0])}–${G(nums[1])}`;
  return nums.map(G).join("/");
}

function psdSort(r) {
  const v = r.psd_um;
  if (isList(v) && v.length) {
    const n = asNumber(v[0]);
    if (n !== null) return n;
  }
  return 1e9;          // unknown PSD sorts last ascending
}

const gatesOf = (r) => r._gates || new Set();
const fmtGates = (r) => ["A", "B", "C"].map((x) => (gatesOf(r).has(x) ? x : "·")).join("");
// C is worth most - it is the only gate backed by a real machine.
const gatesSort = (r) => (gatesOf(r).has("C") ? 4 : 0) + (gatesOf(r).has("B") ? 2 : 0) + (gatesOf(r).has("A") ? 1 : 0);
const fmtLpbf = (r) => (r.psd_pbf_suitable === true ? "● LPBF" : r.psd_pbf_suitable === false ? "○ coarse" : "? n/a");
const lpbfSort = (r) => (r.psd_pbf_suitable === true ? 2 : r.psd_pbf_suitable === false ? 0 : 1);
const fmtProc = (r) => (truthy(r.process_targets) ? r.process_targets.map((t) => strValue(t)).join(", ") : "—");
const fmtAtom = (r) => (truthy(r.atomization) ? rstr(r, "atomization") : "—");
const lenOf = (v) => (truthy(v) ? v.length : 0);

function fmtNum(key, spec = G) {
  return (r) => fmtRange(r[key], spec) || "—";
}

function numSort(key) {
  return (r) => {
    const n = asNumber(r[key]);
    return n !== null ? n : -1;
  };
}

function fmtOem(r) {
  const n = lenOf(r.oem_machines_tested);
  if (n) return String(n);
  const n2 = lenOf(r._supplier_oem);
  return n2 ? `(${n2})` : "—";
}

// powder-level evidence outranks supplier-level
const oemSort = (r) => lenOf(r.oem_machines_tested) * 100 + lenOf(r._supplier_oem);

function tagged(r, k, dflt) {
  const v = Object.hasOwn(r, k) ? r[k] : dflt;
  if (v === null || v === undefined) return null;
  if (typeof v === "string") return S(v);
  if (typeof v === "number") return isFloat(r._src, k) ? D(v) : I(v);
  return S(strValue(v));
}

// (header, display, sort role)
export const COLUMNS = [
  ["Supplier", (r) => (Object.hasOwn(r, "_supplier") ? r._supplier : "—"), (r) => tagged(r, "_supplier", "")],
  ["Region", (r) => (Object.hasOwn(r, "_region") ? r._region : "—"), (r) => tagged(r, "_region", "")],
  ["Alloy", (r) => (Object.hasOwn(r, "alloy") ? r.alloy : "—"), (r) => tagged(r, "alloy", "")],
  ["PSD µm", fmtPsd, (r) => D(psdSort(r))],
  ["Fit", fmtLpbf, (r) => I(lpbfSort(r))],
  ["Gates", fmtGates, (r) => I(gatesSort(r))],
  ["OEM", fmtOem, (r) => D(oemSort(r))],
  ["Process", fmtProc, (r) => S((truthy(r.process_targets) ? r.process_targets : []).map((t) => strValue(t)).join(","))],
  ["Atomization", fmtAtom, (r) => S(truthy(r.atomization) ? rstr(r, "atomization") : "")],
  ["App. dens", fmtNum("apparent_density_g_cm3", F2), (r) => D(numSort("apparent_density_g_cm3")(r))],
  ["Flow s/50g", fmtNum("flow_s_50g"), (r) => D(numSort("flow_s_50g")(r))],
  ["O ppm", fmtNum("oxygen_ppm", F0), (r) => D(numSort("oxygen_ppm")(r))],
];
const NUMERIC_COLS = [3, 6, 9, 10, 11];

export function displayText(r, col) {
  let v;
  try {
    v = COLUMNS[col][1](r);
  } catch {
    return "—";
  }
  return v === null || v === undefined ? "" : typeof v === "string" ? v : strValue(v);
}

export function sortValue(r, col) {
  try {
    return COLUMNS[col][2](r);
  } catch {
    return null;
  }
}

// PowderFilter.filterAcceptsRow
export function accepts(r, f) {
  if (f.supplier && r._supplier_slug !== f.supplier) return false;
  if (f.alloy && r.alloy !== f.alloy) return false;
  if (f.lpbfOnly && r.psd_pbf_suitable !== true) return false;
  if (f.gateCOnly && !gatesOf(r).has("C")) return false;
  if (f.text) {
    const join = (v) => (truthy(v) ? v.map((x) => strValue(x)).join(" ") : "");
    const hay = [rstr(r, "_supplier", ""), rstr(r, "alloy", ""), rstr(r, "designation", ""), rstr(r, "notes", ""),
      join(r.process_targets), join(r.oem_machines_tested)].join(" ").toLowerCase();
    if (!hay.includes(f.text)) return false;
  }
  return true;
}

// The alloy combo: by how many suppliers carry it, then by name.
export function alloyItems(doc) {
  const alloys = isDict(doc._alloys) ? doc._alloys : {};
  const count = (rec, k) => (isDict(rec) && Object.hasOwn(rec, k) ? rec[k] : 0);
  const items = Object.entries(alloys).sort(([a, ra], [b, rb]) =>
    (count(rb, "supplier_count") - count(ra, "supplier_count")) || pyCmp(a.toLowerCase(), b.toLowerCase()));
  return [[`All alloys (${items.length})`, null],
    ...items.map(([name, rec]) => [`${name}   (${strValue(count(rec, "supplier_count"))} sup · `
      + `${strValue(count(rec, "lpbf"))} LPBF)`, name])];
}

export function supplierItems(doc) {
  const sup = isDict(doc._suppliers) ? doc._suppliers : {};
  return [["All suppliers", null],
    ...Object.entries(sup).sort(([, a], [, b]) => pyCmp(String(a), String(b))).map(([slug, name]) => [strValue(name), slug])];
}

// ---- the detail pane (_render) ----
const span = (style, ...kids) => h("span", { style }, ...kids);
const link = (url) => h("a", { href: String(url), target: "_blank", rel: "noopener noreferrer" }, String(url));

function chemText(ch) {
  if (!isDict(ch) || !Object.keys(ch).length) return null;
  return Object.entries(ch).map(([el, v]) => (isDict(v)
    ? `${el} (${Object.keys(v).map((k) => `${k} ${pyStr(v, k)}`).join(", ")})`
    : `${el} ${pyStr(ch, el)}`)).join(" · ");
}

const GATE_DESC = [["A", "marketed for AM/PBF"], ["B", "PSD suits LPBF"], ["C", "validated on named OEM machine"]];

export function detailRows(r) {
  const fit = r.psd_pbf_suitable === true ? span("color:#1a6a3a;font-weight:bold", "● LPBF-suitable cut")
    : r.psd_pbf_suitable === false ? span("color:#b03030;font-weight:bold", "○ coarse — EBM / DED / binder-jet, not LPBF")
      : span("color:#888", "? PSD not published");
  const oemPw = truthy(r.oem_machines_tested) ? r.oem_machines_tested.map((x) => strValue(x)) : [];
  const oemSup = truthy(r._supplier_oem) ? r._supplier_oem.map((x) => strValue(x)) : [];
  const oem = oemPw.length
    ? [h("b", {}, oemPw.join(", ")), h("br"), span("color:#888;font-size:11px", "cited for this powder")]
    : oemSup.length ? [oemSup.join(", "), h("br"),
      span("color:#888;font-size:11px", "cited at supplier level, not for this specific powder")] : null;
  // The vendor's own product name, when it differs from the canonical one.
  const vendorName = truthy(r.alloy_vendor) && r.alloy_vendor !== r.alloy ? rstr(r, "alloy_vendor") : null;
  const val = (k) => (r[k] === null || r[k] === undefined ? null : rstr(r, k));
  return [
    ["Supplier", val("_supplier")],
    ["Region", val("_region")],
    ["Vendor product name", vendorName],
    ["Designation", val("designation")],
    ["PSD", fmtRange(r.psd_um, G, " µm")],
    ["Fit", fit],
    ["Process targets", truthy(r.process_targets) ? r.process_targets.map((t) => strValue(t)).join(", ") : ""],
    ["Atomization", val("atomization")],
    ["Sphericity", fmtRange(r.sphericity, G)],
    ["Apparent density", fmtRange(r.apparent_density_g_cm3, G, " g/cm³")],
    ["Tap density", fmtRange(r.tap_density_g_cm3, G, " g/cm³")],
    ["Flow (Hall)", fmtRange(r.flow_s_50g, G, " s/50 g")],
    ["Oxygen", fmtRange(r.oxygen_ppm, G, " ppm")],
    ["Nitrogen", fmtRange(r.nitrogen_ppm, G, " ppm")],
    ["Chemistry", chemText(r.chemistry)],
    ["OEM machines", oem],
    ["Datasheet", truthy(r.datasheet_url) ? link(r.datasheet_url) : null],
    ["Homepage", truthy(r._homepage) ? link(r._homepage) : null],
  ].filter(([, v]) => !(v === null || v === "" || v === "—"));
}

export function detailNode(r) {
  const gates = GATE_DESC.map(([gate, desc], i) => [i ? h("br") : null, gatesOf(r).has(gate)
    ? [h("span", { class: "gate on" }, gate), " ", span("color:#555;font-size:11px", desc)]
    : [h("span", { class: "gate" }, gate), " ", span("color:#aaa;font-size:11px", desc)]]);
  const rows = detailRows(r).map(([label, v]) => h("tr", {}, h("td", { class: "dt-label" }, label),
                                                   h("td", { class: "dt-value" }, v)));
  const notes = [["PSD note", "psd_note"], ["Notes", "notes"], ["Atomization note", "atomization_note"],
    ["Supplier note", "_supplier_notes"]]
    .filter(([, k]) => truthy(r[k]))
    .map(([label, k]) => h("div", { class: "dt-note" }, h("b", {}, `${label}:`), ` ${rstr(r, k)}`));
  return h("div", { class: "detail-doc" },
    h("div", { class: "dt-title" }, rstr(r, "alloy", "")),
    h("div", { class: "dt-gates" }, gates),
    h("table", { class: "dt-specs" }, h("tbody", {}, rows)),
    notes,
    h("div", { class: "dt-disclaimer" }, "O/N figures derived from a wt% specification are maxima, not typical "
      + "assays. Some vendors publish densities as minima. Verify against the vendor's current datasheet."));
}

export function openPowdersWindow(cat, { isMobile }) {
  const doc = cat.doc;
  const rows = flatten(doc);
  const filter = { supplier: null, alloy: null, lpbfOnly: true, gateCOnly: false, text: "" };

  return openWindow("MDS Viewer — Third-party Powder Suppliers", () => {
    const proxy = new SortFilterProxy(rows.length, (s, c) => sortValue(rows[s], c), (s) => accepts(rows[s], filter));
    const alloyCombo = h("select", { class: "combo alloy", "aria-label": "Alloy",
                                     tip: "Vendor branding (forAM, MetcoAdd, Osprey, TEKMAT…), the PSD cut\n"
                                       + "and the atomisation code are stripped, so the same alloy from\n"
                                       + "different suppliers lands on one entry. The vendor's own wording\n"
                                       + "is kept and shown in the detail pane." },
      alloyItems(doc).map(([label, name], i) => h("option", { value: i ? name : "" }, label)));
    const supCombo = h("select", { class: "combo supplier", "aria-label": "Supplier" },
      supplierItems(doc).map(([label, slug], i) => h("option", { value: i ? slug : "" }, label)));
    const lpbf = h("input", { type: "checkbox", checked: true });
    const gateC = h("input", { type: "checkbox" });
    const search = h("input", { type: "search", class: "combo search", placeholder: "alloy, supplier, standard, machine…",
                                "aria-label": "Search", autocomplete: "off" });
    const count = h("span", { class: "cat-count" });
    const detailTxt = h("div", { class: "detail-txt" });

    const table = catalogTable({
      columns: COLUMNS.map(([label], ci) => ({ label, cls: NUMERIC_COLS.includes(ci) ? "num" : null })),
      proxy,
      rowKey: (s) => String(s),
      initialSort: 2,       // by alloy: competing suppliers side by side
      cell(s, ci) {
        const r = rows[s];
        const cls = [NUMERIC_COLS.includes(ci) ? "num" : "", ci === 5 ? "mono" : "",
          r.psd_pbf_suitable === false ? "coarse" : ci === 5 && gatesOf(r).has("C") ? "ok" : ""].filter(Boolean).join(" ");
        const tip = truthy(r.psd_note) ? rstr(r, "psd_note") : truthy(r.notes) ? rstr(r, "notes") : null;
        return { text: displayText(r, ci), cls, tip };
      },
      onSelect({ selected }) {
        if (!selected.length) return;
        detailTxt.replaceChildren(detailNode(rows[selected[0]]));
        detailTxt.scrollTop = 0;
      },
      onActivate(s) {
        const r = rows[s];
        const url = truthy(r.datasheet_url) ? r.datasheet_url : r._homepage;
        if (truthy(url)) openExternal(String(url));
      },
      onTap(s) {
        if (!isMobile()) return false;
        openWindow(rstr(rows[s], "alloy", ""), () => h("div", { class: "detail-txt" }, detailNode(rows[s])),
                   { className: "sheet" });
        return true;
      },
    });

    const upd = () => { count.textContent = `${proxy.rows.length} / ${rows.length} powders`; };
    const set = (k, v) => { filter[k] = v; table.refilter(); upd(); };
    alloyCombo.addEventListener("change", () => set("alloy", alloyCombo.value || null));
    supCombo.addEventListener("change", () => set("supplier", supCombo.value || null));
    lpbf.addEventListener("change", () => set("lpbfOnly", lpbf.checked));
    gateC.addEventListener("change", () => set("gateCOnly", gateC.checked));
    search.addEventListener("input", () => set("text", search.value.trim().toLowerCase()));

    upd();
    if (!isMobile()) table.selectFirst();

    const st = isDict(doc._stats) ? doc._stats : {};
    const stat = (k) => (Object.hasOwn(st, k) ? pyStr(st, k) : "?");
    const bar = h("div", { class: "cat-bar" },
      h("span", { class: "cat-title" }, "⚗ Third-party Powder Suppliers"),
      h("label", { class: "field" }, h("span", { class: "lbl" }, "Alloy:"), alloyCombo),
      h("label", { class: "field" }, h("span", { class: "lbl" }, "Supplier:"), supCombo),
      h("label", { class: "check", tip: "Hide coarse cuts (45-106 / 45-150 µm), which are EBM / DED /\n"
        + "binder-jet feedstock rather than laser powder bed fusion." }, lpbf, "LPBF-suitable only"),
      h("label", { class: "check", tip: "Only powders whose supplier cites validation on a NAMED OEM\n"
        + "machine — the strongest evidence in the rubric." }, gateC, "Gate C only"),
      h("label", { class: "field" }, h("span", { class: "lbl" }, "Search:"), search),
      h("span", { class: "stretch" }), count);
    const foot = h("div", { class: "cat-foot" }, "Gates — ", h("b", {}, "A"), " vendor markets it for AM/PBF · ",
      h("b", {}, "B"), " PSD suits LPBF · ", h("b", {}, "C"), " validated on a named OEM machine (strongest). "
      + `Gates are independent. ${stat("lpbf_suitable")} LPBF-suitable of ${stat("powders")} records. `,
      h("span", { class: "dim" }, pyStr(doc, "_updated", "")));
    return [bar, catSplit(table.el, h("div", { class: "cat-detail" }, detailTxt), "powders"), foot];
  }, { className: "catalog powders" });
}
