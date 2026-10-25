// The material window (mds_dialog.open_mds_qt), as a page. Kept in the
// desktop's order and naming so the two can be read side by side.
import { T, trDb, plain, padEnd, padStart, h, openExternal, isHttpUrl, toast,
         messageBox, storageGet, storageSet, hideTip } from "./util.js";
import { fmtCell, fmtNum, pyFloat, pyOr, pySlice, pyStr, safeNum, strValue, truthy } from "./py.js";
import { drawChart } from "./chart.js";
import { buildReportHtml, reportFilename } from "./report.js";

const DEFAULT_CATS = ["Aluminium", "Cobalt", "Copper", "Nickel", "Steel", "Titanium", "Niobium", "Other"];
const DEFAULT_4 = ["Nikon SLM Solutions", "EOS", "Renishaw", "TRUMPF"];
// Nikon SLM Solutions → Major 4 (EOS/Renishaw/3D Systems/SLM Solutions) → the rest
const MAJOR_ORDER = { "Nikon SLM Solutions": 0, EOS: 1, Renishaw: 2, "3D Systems": 3, "SLM Solutions": 4 };

const VENDOR_COLS = [T("MD_COL_MFG"), T("MD_COL_MACHINE"), T("MD_COL_POST"), "Layer\nμm",
                     "YS XY\nMPa", "YS Z\nMPa", "UTS XY\nMPa", "UTS Z\nMPa",
                     T("MD_COL_ELONG"), T("MD_COL_HARD"), "Ra\nμm", T("MD_COL_TDS")];
const COL_PCTS = [13, 13, 9, 6, 7, 7, 7, 7, 7, 7, 11, 6];

const METRICS = [["UTS XY (MPa)", "uts"], ["UTS Z (MPa)", "uts_z"], ["YS XY (MPa)", "ys"],
                 ["YS Z (MPa)", "ys_z"], [T("MD_RADIO_ELONG_XY"), "elong_xy"],
                 [T("MD_RADIO_ELONG_Z"), "elong_z"], [T("MD_RADIO_HARD"), "hardness_HV"],
                 [T("MD_RADIO_RA"), "surface_ra_hi"]];
const METRIC_FIELD = { uts: "uts_xy_MPa", uts_z: "uts_z_MPa", ys: "yield_MPa", ys_z: "yield_z_MPa",
                       elong_xy: "elongation_xy_pct", elong_z: "elongation_z_pct",
                       hardness_HV: "hardness_HV", surface_ra_hi: "surface_ra_hi" };
// metric → keys to try inside _value_ranges: direction-specific first,
// then the generic range BLT publishes for both directions.
const RANGE_KEYS = { uts: ["tensile_MPa_xy", "tensile_MPa"], uts_z: ["tensile_MPa_z", "tensile_MPa"],
                     ys: ["yield_MPa_xy", "yield_MPa"], ys_z: ["yield_MPa_z", "yield_MPa"],
                     elong_xy: ["elongation_pct_xy", "elongation_pct"],
                     elong_z: ["elongation_pct_z", "elongation_pct"] };

const LAST_KEY = "mds_last";

// tr_db(c.get(k, dflt)) as printed by an f-string.
function trv(c, k, dflt) {
  const v = c && Object.hasOwn(c, k) ? c[k] : dflt;
  return typeof v === "string" ? trDb(v) : pyStr(c, k, dflt);
}

const isDict = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

// Supporting manufacturers, derived from the vendor entries.
function extractManufacturers(props) {
  const vendors = props.vendors;
  if (!isDict(vendors)) return [];
  const out = [];
  for (const [vkey, vdata] of Object.entries(vendors)) {
    let name = isDict(vdata) && truthy(vdata.manufacturer) ? vdata.manufacturer : null;
    if (!name) name = vkey.split("[", 1)[0].split("@", 1)[0].trim() || null;
    if (name && !out.includes(name)) out.push(name);
  }
  return out;
}

function group(title, ...body) {
  return h("fieldset", { class: "group" }, h("legend", {}, title), ...body);
}

function hsep() {
  return h("hr", { class: "hsep" });
}

// Qt's _SortableItem.__lt__: numbers compare as numbers and sort before
// blanks; anything else compares as lower-cased text.
function lessThan(a, b, col) {
  const x = a.sort[col], y = b.sort[col];
  if (x !== null && y !== null) return x < y;
  if (x !== null) return true;
  if (y !== null) return false;
  return a.cells[col].toLowerCase() < b.cells[col].toLowerCase();
}

// QTreeModel.sort: a stable sort; descending uses "greater than", so rows
// that tie keep their current order either way.
function sortRows(rows, col, desc) {
  rows.sort(desc
    ? (a, b) => (lessThan(b, a, col) ? -1 : lessThan(a, b, col) ? 1 : 0)
    : (a, b) => (lessThan(a, b, col) ? -1 : lessThan(b, a, col) ? 1 : 0));
}

const cmpText = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

export function mountMaterialView(host, ctx) {
  const db = ctx.db;
  const mats = isDict(db.materials) ? db.materials : {};
  const names = Object.keys(mats);
  const ALL = T("MD_CAT_ALL");
  const catOrder = truthy(db._category_top_order) ? db._category_top_order : DEFAULT_CATS;
  const matToCat = Object.fromEntries(names.map((m) => [m, truthy(mats[m].category_top) ? mats[m].category_top : "Other"]));

  // ---- Top: category filter + material selector ----
  const catSel = h("select", { class: "combo cat", "aria-label": "Category",
                               tip: "Filter the material list by Nikon-style top-level category.\n"
                                 + "Categories follow https://nikon-slm-solutions.com/materials/\n"
                                 + "(refractory metals not listed by Nikon → 'Other')." },
    [ALL, ...catOrder].map((c) => h("option", { value: c }, c)));
  const matSel = h("select", { class: "combo mat", "aria-label": "Material" });
  const catLbl = h("span", { class: "catlbl" });

  const toolBtn = (label, tip, onclick) => h("button", { class: "tool", type: "button", tip, onclick }, label);
  const tools = h("div", { class: "tools" },
    toolBtn("Submit TDS data…", "Submit a new vendor entry (or new material) based on a published TDS.\n"
      + "It goes to the maintainer as a GitHub issue, encrypted with your release key.", ctx.onSubmit),
    toolBtn("🔧 Machines…", "Open the LPBF/AM machine hardware catalog: build volumes,\n"
      + "laser configs, layer ranges, approximate prices, product\nimages, and links to each "
      + "manufacturer's page.", ctx.onMachines),
    toolBtn("⚗ Powders…", "Third-party LPBF powder suppliers: alloy, particle size,\natomization, "
      + "flow/density, and whether the vendor has\nvalidated the powder on a named OEM machine.", ctx.onPowders),
    toolBtn("Add release key…", "Paste a new release key you received from the maintainer.\n"
      + "It is saved in this browser, and a newer release it unlocks loads right away.", ctx.onAddKey),
    h("button", { class: "tool layout", type: "button", "aria-label": "Switch layout",
                  tip: "Switch between the desktop and the mobile layout", onclick: ctx.onToggleLayout }));

  const top = h("header", { class: "topbar" },
    h("div", { class: "pick" },
      h("label", { class: "field" }, h("span", { class: "lbl" }, plain(T("MD_CAT_FILTER"))), catSel),
      h("label", { class: "field" }, h("span", { class: "lbl" }, plain(T("MD_MAT"))), matSel),
      catLbl),
    tools);
  const banner = h("div", { class: "banner", hidden: true });
  const bodyHost = h("main", { class: "body" });
  host.replaceChildren(top, hsep(), banner, bodyHost);

  let current = null;
  let currentCat = ALL;

  function populate(cat, keep) {
    const shown = cat === ALL ? names : names.filter((m) => matToCat[m] === cat);
    matSel.replaceChildren(...shown.map((m) => h("option", { value: m }, m)));
    // Keep the current material selected if it survives the filter
    if (keep && shown.includes(keep)) matSel.value = keep;
    return shown;
  }

  function show(name) {
    current = name;
    hideTip();
    buildBody(name, mats[name] || {});
    storageSet(LAST_KEY, JSON.stringify({ cat: currentCat, mat: name }));
  }

  catSel.addEventListener("change", () => {
    currentCat = catSel.value;
    const shown = populate(currentCat, current);
    if (shown.length) show(matSel.value);
  });
  matSel.addEventListener("change", () => show(matSel.value));

  // ---- body ----
  function buildBody(matName, props) {
    catLbl.textContent = T("MD_CATEGORY").replace("{cat}", () => trv(props, "category", "-"));

    // Left col: basic physical / thermal
    const lbl = (key, w = 14) => {
      const t = T(key);
      return t + " ".repeat(Math.max(2, w - t.length));
    };
    const basicLines = [
      `  ${lbl("MD_BASIC_DENSITY")}: ${padStart(fmtNum(props.density, 3), 10)} g/cm3`,
      `  ${lbl("MD_BASIC_MELT")}: ${padStart(fmtNum(props.melt, 0), 10)} C`,
      `  ${lbl("MD_BASIC_MAG")}: ${trv(props, "magnetic", "-")}`,
      `  ${lbl("MD_BASIC_YOUNGS")}: ${padStart(fmtNum(props.E, 0), 10)} GPa`,
      `  ${lbl("MD_BASIC_POISSON")}: ${padStart(fmtNum(props.poisson, 3), 10)}`,
      `  ${lbl("MD_BASIC_THERMK")}: ${padStart(fmtNum(props.thermal_k, 1), 10)} W/m K`,
      `  ${lbl("MD_BASIC_CP")}: ${padStart(fmtNum(props.cp, 0), 10)} J/kg K`,
      `  ${lbl("MD_BASIC_CTE")}: ${padStart(fmtNum(props.cte, 1), 10)} 10-6/K`,
    ];
    const basicBox = group(T("MD_BASIC_PHYS"), h("pre", { class: "textbox mono basic" }, basicLines.join("\n")));

    const tabs = tabWidget();
    const ht = isDict(props.heat_treatments) ? props.heat_treatments : {};
    if (Object.keys(ht).length) {
      for (const [htKey, d] of Object.entries(ht)) {
        if (!isDict(d)) continue;
        const hard = [];
        if (truthy(d.hardness_HV)) hard.push(`${pyStr(d, "hardness_HV")} HV`);
        if (![undefined, null, 0, "", false].includes(d.hardness_HRC)) hard.push(`${pyStr(d, "hardness_HRC")} HRC`);
        if (truthy(d.hardness_HB)) hard.push(`${pyStr(d, "hardness_HB")} HB`);
        const ra = truthy(d.surface_ra_um) ? pyStr(d, "surface_ra_um") : "-";
        const notes = truthy(d.notes) ? trv(d, "notes") : "-";
        const htl = (key) => lbl(key, 22);
        const content = [
          `${htl("MD_HT_UTS")}: ${padStart(fmtNum(d.uts, 0), 8)} MPa`,
          `${htl("MD_HT_YS")}: ${padStart(fmtNum(d.ys, 0), 8)} MPa`,
          `${htl("MD_HT_ELONG")}: ${padStart(fmtNum(d.elong, 1), 8)} %`,
          `${htl("MD_HT_HARD")}: ${hard.join(" / ") || "-"}`,
          `${htl("MD_HT_RA")}: ${ra}  (SLM as-built, side wall)`,
          "",
          T("MD_HT_STD"),
          `  ${notes}`,
        ];
        tabs.add(trDb(htKey), h("pre", { class: "textbox mono ht" }, content.join("\n")));
      }
    } else {
      tabs.add(T("MD_NO_DATA_TAB"), h("div", { class: "placeholder" }, T("MD_NO_HEAT")));
    }

    const vendors = isDict(props.vendors) ? props.vendors : {};
    if (Object.keys(vendors).length) tabs.add(T("MD_TAB_VENDOR"), vendorTab(matName, props, vendors));
    tabs.select(0);

    const left = h("section", { class: "left" },
      basicBox, h("div", { class: "htlbl" }, T("MD_HEAT_TREAT")), tabs.el);

    // Right col: official vendors, composition, applications
    const d4 = truthy(db._default_4) ? db._default_4 : DEFAULT_4;
    const derived = extractManufacturers(props);
    const vendBox = group(T("MD_VENDORS_OFFICIAL"),
      d4.map((v) => derived.includes(v)
        ? h("div", { class: "vend on" }, `☑  ${v}`)
        : h("div", { class: "vend off" }, `☐  ${v}`)));
    const extras = derived.filter((v) => !d4.includes(v));
    if (extras.length) {
      vendBox.append(hsep(), h("div", { class: "vend-extra" }, plain(T("MD_VENDORS_EXTRA"))),
        ...extras.map((v) => h("div", { class: "vend extra" }, `  ☑  ${v}`)));
    }

    const comp = Array.isArray(props.composition) ? props.composition : [];
    const compBox = group(T("MD_COMP"), h("div", { class: "comp-wrap" }, h("table", { class: "comp" },
      h("thead", {}, h("tr", {}, h("th", {}, "Element"), h("th", {}, "wt %"))),
      h("tbody", {}, comp.map((c) => {
        let el, pct;
        if (isDict(c)) [el, pct] = [pyStr(c, "element", "?"), pyStr(c, "pct", "-")];
        else if (Array.isArray(c) && c.length >= 2) [el, pct] = [pyStr(c, 0), pyStr(c, 1)];
        else [el, pct] = [strValue(c), "-"];
        return h("tr", {}, h("td", { class: "el" }, el), h("td", {}, pct));
      })))));
    compBox.classList.add("comp-box");

    const appsBox = group(T("MD_APP"),
      h("div", { class: "textbox apps" }, trDb(pyOr(props, "applications", "-"))));

    const right = h("aside", { class: "right" }, vendBox, compBox, appsBox);
    const splitter = h("div", { class: "splitter", role: "separator", "aria-orientation": "vertical",
                                tip: "Drag to resize" });
    enableSplitter(splitter);
    const split = h("div", { class: "split" }, left, splitter, right);

    bodyHost.replaceChildren(split, hsep(), referenceBox(matName, props));
  }

  // ---- vendor tab: tree + chart + report button ----
  function vendorTab(matName, props, vendors) {
    const rows = [];
    for (const [key, vd] of Object.entries(vendors)) {
      if (!isDict(vd)) continue;
      const tds = truthy(vd.tds_link) ? vd.tds_link : null;
      const fmtElong = () => {
        const xy = vd.elongation_xy_pct ?? null, z = vd.elongation_z_pct ?? null;
        if (xy === null && z === null) return fmtCell(vd.elongation_pct);
        if (xy !== null && z !== null && xy !== z) return `${fmtCell(xy)} / ${fmtCell(z)}`;
        return fmtCell(xy !== null ? xy : z);
      };
      const fmtRa = () => {
        const lo = vd.surface_ra_lo ?? null, hi = vd.surface_ra_hi ?? null;
        if (lo === null && hi === null) return "-";
        if (lo === null) return fmtCell(hi);
        if (hi === null || lo === hi) return fmtCell(lo);
        return `${fmtCell(lo)}~${fmtCell(hi)}`;
      };
      const cells = [
        pyStr(vd, "manufacturer", key),
        pyOr(vd, "machine", "-"),
        pyOr(vd, "post_treatment", "-"),
        fmtCell(vd.layer_thickness_um),
        fmtCell(vd.yield_MPa),
        fmtCell(vd.yield_z_MPa),
        fmtCell(vd.uts_xy_MPa),
        fmtCell(vd.uts_z_MPa),
        fmtElong(),
        fmtCell(vd.hardness_HV),
        fmtRa(),
        tds ? "📄" : "-",
      ];
      const sortVal = (v) => safeNum(v, null);
      const sort = new Array(12).fill(null);
      Object.assign(sort, {
        3: sortVal(vd.layer_thickness_um), 4: sortVal(vd.yield_MPa), 5: sortVal(vd.yield_z_MPa),
        6: sortVal(vd.uts_xy_MPa), 7: sortVal(vd.uts_z_MPa),
        8: sortVal(vd.elongation_xy_pct ?? vd.elongation_z_pct ?? vd.elongation_pct),
        9: sortVal(vd.hardness_HV), 10: sortVal(vd.surface_ra_lo ?? vd.surface_ra_hi),
        11: tds ? 1 : 0,
      });
      rows.push({ key, vd, cells, sort, tds, tip: rowTooltip(vd, tds), checked: false, tr: null });
    }

    // Pre-sort as the desktop does, then the tree's own initial sort:
    // column 0 (Mfg) descending, a stable sort over that order.
    rows.sort((a, b) => ((MAJOR_ORDER[a.cells[0]] ?? 99) - (MAJOR_ORDER[b.cells[0]] ?? 99))
      || cmpText(a.cells[0], b.cells[0]) || cmpText(a.cells[1], b.cells[1]) || cmpText(a.cells[2], b.cells[2]));
    let sortCol = 0, sortDesc = true;
    sortRows(rows, sortCol, sortDesc);

    // tree
    const ths = VENDOR_COLS.map((label, ci) => h("th", { scope: "col", onclick: () => onHeader(ci) },
      h("span", { class: "th-label" }, label), h("span", { class: "sort-ind" })));
    const tbody = h("tbody", {});
    const table = h("table", { class: "vtree" },
      h("colgroup", {}, COL_PCTS.map((p) => h("col", { style: { width: `${p}%` } }))),
      h("thead", {}, h("tr", {}, ths)), tbody);
    const treeWrap = h("div", { class: "vtree-wrap" }, table);
    let selected = null;

    function renderRows() {
      ths.forEach((th, ci) => {
        th.classList.toggle("sorted", ci === sortCol);
        th.querySelector(".sort-ind").textContent = ci === sortCol ? (sortDesc ? "▼" : "▲") : "";
        th.setAttribute("aria-sort", ci === sortCol ? (sortDesc ? "descending" : "ascending") : "none");
      });
      tbody.replaceChildren(...rows.map((r) => {
        if (!r.tr) r.tr = rowElement(r);
        return r.tr;
      }));
    }

    function rowElement(r) {
      const box = h("input", { type: "checkbox", "aria-label": `Compare ${r.cells[0]} ${r.cells[1]}` });
      box.addEventListener("change", () => { r.checked = box.checked; redraw(); });
      const tds = r.cells.map((text, ci) => {
        if (ci === 0) return h("td", { class: "c0", tip: r.tip || null }, h("label", { class: "cb" }, box), h("span", {}, text));
        if (ci === 11 && r.tds) {
          return h("td", { class: "c11 link", tip: `Click — open TDS\n${r.tds}`,
                           onclick: (e) => { e.stopPropagation(); openTds(r.tds); } }, text);
        }
        return h("td", { class: `c${ci}` }, text);
      });
      const tr = h("tr", { dataset: { key: r.key } }, tds);
      tr.addEventListener("click", () => {
        selected?.classList.remove("selected");
        selected = tr;
        tr.classList.add("selected");
      });
      return tr;
    }

    function onHeader(ci) {
      // QHeaderView: the sorted column flips; a new column starts ascending.
      if (ci === sortCol) sortDesc = !sortDesc;
      else { sortCol = ci; sortDesc = false; }
      sortRows(rows, sortCol, sortDesc);
      renderRows();
      redraw();
    }

    // chart
    let metric = "uts";
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "chart-svg");
    svg.setAttribute("role", "img");
    const canvas = h("div", { class: "chart-canvas" }, svg);
    const radios = METRICS.map(([label, key]) => {
      const input = h("input", { type: "radio", name: `metric-${matName}`, value: key, checked: key === metric });
      input.addEventListener("change", () => { if (input.checked) setMetric(key); });
      return { key, input, el: h("label", { class: "radio" }, input, h("span", {}, label)) };
    });
    const chips = METRICS.map(([label, key]) =>
      h("button", { type: "button", class: "chip", dataset: { metric: key }, onclick: () => setMetric(key) }, label));
    const chipBar = h("div", { class: "chips", role: "group", "aria-label": plain(T("MD_CMP_ITEM")) }, chips);
    const metricBox = h("div", { class: "metric-box" },
      h("div", { class: "metric-title" }, plain(T("MD_CMP_ITEM"))), radios.map((r) => r.el));

    function setMetric(key) {
      metric = key;
      for (const r of radios) r.input.checked = r.key === key;
      for (const c of chips) {
        c.classList.toggle("on", c.dataset.metric === key);
        if (c.dataset.metric === key && chipBar.clientWidth) {
          const { offsetLeft: x, offsetWidth: w } = c;
          if (x < chipBar.scrollLeft) chipBar.scrollLeft = x;
          else if (x + w > chipBar.scrollLeft + chipBar.clientWidth) chipBar.scrollLeft = x + w - chipBar.clientWidth;
        }
      }
      redraw();
    }

    let size = [0, 0];
    function redraw() {
      const [w, hgt] = size;
      if (w > 0 && hgt > 0) drawChart(svg, chartData(rows.filter((r) => r.checked).map((r) => r.vd), metric), metric, w, hgt);
    }
    new ResizeObserver(([entry]) => {
      const r = entry.contentRect;
      const next = [Math.floor(r.width), Math.floor(r.height)];
      if (next[0] !== size[0] || next[1] !== size[1]) { size = next; redraw(); }
    }).observe(canvas);

    const reportBtn = h("button", { type: "button", class: "btn report",
                                    tip: "Generate a standalone HTML report with tables\n"
                                      + "and charts for every checked vendor entry.",
                                    onclick: () => makeReport(matName, props, rows) }, T("MD_REPORT_BTN"));

    renderRows();
    setMetric(metric);
    return h("div", { class: "vendor-tab" },
      treeWrap,
      h("div", { class: "chart-row" }, h("div", { class: "chart-col" }, chipBar, canvas), metricBox),
      h("div", { class: "report-row" }, reportBtn));
  }

  function openTds(url) {
    if (openExternal(url)) return;
    navigator.clipboard?.writeText(String(url)).catch(() => {});
    messageBox("TDS URL copied", `Browser could not open; URL copied to clipboard.\n\n${url}`);
  }

  async function makeReport(matName, props, rows) {
    const selected = rows.filter((r) => r.checked).map((r) => [r.key, r.vd]);
    if (!selected.length) {
      await messageBox(T("MD_REPORT_NONE"), T("MD_REPORT_NONE_MSG"));
      return;
    }
    const now = new Date();
    const name = reportFilename(matName, now);
    const url = URL.createObjectURL(new Blob([buildReportHtml(matName, props, selected, now)],
                                             { type: "text/html;charset=utf-8" }));
    if (matchMedia("(pointer: coarse)").matches) {
      // Phones: one tap to view, one to keep -- a download plus a new tab at once is too much.
      await messageBox("Report generated", h("div", {},
        `Generated report from ${selected.length} entries.`,
        h("div", { class: "pdf-ready" },
          h("a", { class: "btn default", href: url, target: "_blank" }, "Open report"),
          h("a", { class: "btn", href: url, download: name }, "Save"))));
      return;
    }
    const a = h("a", { href: url, download: name });
    document.body.append(a);
    a.click();
    a.remove();
    window.open(url, "_blank");
    toast(`Generated report from ${selected.length} entries.\n${name}`);
  }

  // ---- reference / MDS: collapsible, default closed. The maintainer's
  // reference PDFs arrive encrypted (data/archive/refs/); there is no
  // attaching here, a browser has nowhere to keep the file.
  function referenceBox(matName, props) {
    const urls = Array.isArray(props.ref_urls) ? props.ref_urls : [];
    const published = ctx.refs.list(matName);
    const content = h("div", { class: "ref-content", hidden: true });
    const arrow = h("span", { class: "arrow" }, "▶");
    const toggle = h("button", { type: "button", class: "ref-toggle", "aria-expanded": "false" },
      arrow, `  ◆ Reference / MDS (${urls.length + published.length})  `);
    let checked = false;
    toggle.addEventListener("click", () => {
      const open = content.hidden;
      content.hidden = !open;
      arrow.textContent = open ? "▼" : "▶";
      toggle.setAttribute("aria-expanded", String(open));
      if (open && !checked) {
        checked = true;
        for (const job of pendingChecks) job();
      }
    });

    const pendingChecks = [];
    const row = (vendor, target, kind, opener) => {
      const disp = Array.from(target).length <= 80 ? target : `${pySlice(target, 77)}...`;
      const status = h("span", { class: "ref-status" }, T("MD_UNVERIFIED"));
      const link = kind === "url" && isHttpUrl(target)
        ? h("a", { class: "ref-target", href: target.trim(), target: "_blank", rel: "noopener noreferrer", tip: target }, disp)
        : h("span", { class: "ref-target", tip: target }, disp);
      let btn;
      if (kind === "url") {
        status.textContent = T("MD_EXTERNAL_URL");
        status.classList.add("ext");
        btn = h("button", { type: "button", class: "btn small", onclick: async () => {
          try {
            await navigator.clipboard.writeText(target);
            toast(`${strValue(vendor)} URL copied to clipboard`);
          } catch {
            messageBox("Copy failed", `The browser did not allow copying.\n\n${target}`, "warn");
          }
        } }, T("MD_BTN_COPY"));
      } else {
        btn = h("button", { type: "button", class: "btn small", disabled: !opener, onclick: opener }, T("MD_BTN_OPEN"));
      }
      const setOk = (ok) => {
        status.textContent = ok ? T("MD_LOCAL_OK") : T("MD_FILE_MISSING");
        status.className = `ref-status ${ok ? "ok" : "missing"}`;
      };
      return { el: h("div", { class: "ref-row" }, h("span", { class: "ref-vendor" }, `  • ${vendor}`), link, status, btn), setOk };
    };

    for (const entry of urls) {
      let vName, target;
      if (Array.isArray(entry) && entry.length >= 2) [vName, target] = [trv(entry, 0), entry[1]];
      else [vName, target] = ["Reference", strValue(entry)];
      if (typeof target !== "string") continue;
      const isLocal = target.toLowerCase().endsWith(".pdf") && !target.startsWith("http");
      if (isLocal) {
        // A path on the maintainer's PC: there is nothing to open in a browser.
        const r = row(vName, target, "local", null);
        r.setOk(false);
        content.append(r.el);
      } else {
        content.append(row(vName, target, "url").el);
      }
    }
    for (const entry of published) {
      const r = row("Local PDF (attached)", String(entry.name), "local", (e) => openPublished(entry, e.currentTarget, r));
      pendingChecks.push(() => ctx.refs.exists(entry).then(r.setOk));
      content.append(r.el);
    }
    if (!urls.length && !published.length) content.append(h("div", { class: "ref-none" }, T("MD_NO_REF")));

    return h("fieldset", { class: "refbox" }, h("div", { class: "ref-header" }, toggle), content);
  }

  async function openPublished(entry, button, r) {
    // A window opened before the decrypt keeps the click's permission to
    // open one; touch browsers get a link to tap instead.
    const touch = matchMedia("(pointer: coarse)").matches;
    const win = touch ? null : window.open("", "_blank");
    if (win) win.document.title = "Opening…";
    button.disabled = true;
    const label = button.textContent;
    button.textContent = "Decrypting…";
    try {
      const url = await ctx.refs.open(entry, ctx.keystore());
      r.setOk(true);
      if (win) {
        win.location.href = url;
      } else {
        await pdfReady(entry.name, url);
      }
    } catch (e) {
      win?.close();
      if (/HTTP 404/.test(String(e.message))) r.setOk(false);
      messageBox("Could not open the PDF", String(e.message || e), "warn");
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  }

  function pdfReady(name, url) {
    return messageBox(name, h("div", { class: "pdf-ready" },
      h("a", { class: "btn default", href: url, target: "_blank" }, "Open PDF"),
      h("a", { class: "btn", href: url, download: name }, "Save")));
  }

  // ---- startup selection: the last material this browser showed ----
  let last = {};
  try { last = JSON.parse(storageGet(LAST_KEY) || "{}") || {}; } catch { last = {}; }
  currentCat = [ALL, ...catOrder].includes(last.cat) ? last.cat : ALL;
  catSel.value = currentCat;
  const shown = populate(currentCat, last.mat);
  if (!shown.length) { currentCat = ALL; catSel.value = ALL; populate(ALL, last.mat); }
  if (matSel.value) show(matSel.value);

  return {
    banner,
    currentMaterial: () => current,
    select(name) {
      if (!Object.hasOwn(mats, name)) return;
      if (!populate(currentCat, name).includes(name)) {
        currentCat = ALL;
        catSel.value = ALL;
        populate(ALL, name);
      }
      matSel.value = name;
      show(name);
    },
    // After a key change: the published PDFs may differ. An open list stays open.
    refreshReferences() {
      const old = bodyHost.querySelector(".refbox");
      if (!old || !current) return;
      const box = referenceBox(current, mats[current] || {});
      old.replaceWith(box);
      if (!old.querySelector(".ref-content").hidden) box.querySelector(".ref-toggle").click();
    },
  };
}

// _VendorBarChart.collect_data: [label, value, lo, hi] for the checked
// entries (in tree order) that have the metric; lo/hi is the published
// range when the vendor gives one, else null.
export function chartData(entries, metric) {
  const data = [];
  for (const vd of entries) {
    const v = vd[METRIC_FIELD[metric]];
    if (v === null || v === undefined || v === 0 || v === false) continue;
    const manuf = pySlice(pyOr(vd, "manufacturer", "?"), 12);
    const machine = pyOr(vd, "machine", "");
    const post = pyOr(vd, "post_treatment", "");
    // No layer -> no layer text (it used to read "Noneμm"), and no empty line.
    const lt = truthy(vd.layer_thickness_um) ? ` ${pyStr(vd, "layer_thickness_um")}μm` : "";
    const lbl2 = (pySlice(machine, 10) + lt).trim();
    const parts = lbl2 ? [manuf, lbl2] : [manuf];
    if (post && post.toLowerCase() !== "as-built") parts.push(`(${pySlice(post, 8)})`);
    let lo = null, hi = null, bad = false;
    const vr = isDict(vd._value_ranges) ? vd._value_ranges : {};
    for (const rk of RANGE_KEYS[metric] || []) {
      const rng = vr[rk];
      if (Array.isArray(rng) && rng.length === 2 && rng[0] !== null && rng[1] !== null) {
        [lo, hi] = [pyFloat(rng[0]), pyFloat(rng[1])];
        bad = lo === null || hi === null;          // float() raised: the desktop drops the row
        break;
      }
    }
    if (!bad) data.push([parts.join("\n"), safeNum(v, 0), lo, hi]);
  }
  return data;
}

// The vendor tree's row tooltip: TDS link, notes, and the provenance fields
// some vendors carry (BLT lo-hi ranges, Velo3D modulus / source note, ...).
function rowTooltip(vd, tds) {
  const parts = [];
  if (tds) parts.push(`TDS: ${strValue(tds)}`);
  if (truthy(vd._tds_source)) parts.push(`Source: ${pyStr(vd, "_tds_source")}`);
  if (truthy(vd.notes)) parts.push(`Notes: ${trv(vd, "notes")}`);
  if (truthy(vd.test_standard)) parts.push(`Std: ${pyStr(vd, "test_standard")}`);
  const mod = vd._modulus_GPa_range;
  if (truthy(mod) && Array.isArray(mod) && mod.length === 2) parts.push(`Modulus: ${pyStr(mod, 0)}–${pyStr(mod, 1)} GPa`);
  if (vd._hardness_HRC !== undefined && vd._hardness_HRC !== null) parts.push(`Hardness: HRC ${pyStr(vd, "_hardness_HRC")}`);
  if (vd._hardness_HRBW !== undefined && vd._hardness_HRBW !== null) parts.push(`Hardness: HRBW ${pyStr(vd, "_hardness_HRBW")}`);
  const vr = truthy(vd._value_ranges) && isDict(vd._value_ranges) ? vd._value_ranges : null;
  if (vr) {
    const lines = [];
    for (const [k, label] of [["yield_MPa", "YS"], ["tensile_MPa", "UTS"], ["elongation_pct", "Elong"], ["hardness_HRC", "HRC"]]) {
      const v = vr[k];
      if (truthy(v) && Array.isArray(v) && v.length === 2) {
        const unit = k.includes("MPa") ? "MPa" : k.includes("pct") ? "%" : "";
        lines.push(`  ${label}: ${pyStr(v, 0)}–${pyStr(v, 1)} ${unit}`.trimEnd());
      }
    }
    if (lines.length) parts.push("Published ranges:", ...lines);
  }
  const pp = truthy(vd._powder_properties) && isDict(vd._powder_properties) ? vd._powder_properties : null;
  if (pp) {
    const lines = [];
    if (truthy(pp.flowability)) lines.push(`  Flow: ${pyStr(pp, "flowability")}`);
    if (pp.apparent_density_g_cm3 != null) lines.push(`  Apparent density: ≥${pyStr(pp, "apparent_density_g_cm3")} g/cm³`);
    if (pp.sphericity_min != null) lines.push(`  Sphericity: ≥${pyStr(pp, "sphericity_min")}`);
    if (pp.oxygen_ppm_max != null) lines.push(`  O: ≤${pyStr(pp, "oxygen_ppm_max")} ppm`);
    if (lines.length) parts.push("Powder:", ...lines);
  }
  if (truthy(vd._source_note)) {
    let sn = pyStr(vd, "_source_note");
    if (Array.from(sn).length > 200) sn = `${pySlice(sn, 197)}...`;
    parts.push(`\n${sn}`);
  }
  return parts.join("\n");
}

// A QTabWidget: a tab bar over one visible page.
function tabWidget() {
  const bar = h("div", { class: "tabbar", role: "tablist" });
  const panes = h("div", { class: "tabpanes" });
  const tabs = [];
  const select = (i) => tabs.forEach((t, j) => {
    t.btn.classList.toggle("active", i === j);
    t.btn.setAttribute("aria-selected", String(i === j));
    t.pane.hidden = i !== j;
    // Bring a half-hidden tab into the (scrolling) bar; never scroll the page.
    if (i === j) {
      const { offsetLeft: x, offsetWidth: w } = t.btn;
      if (x < bar.scrollLeft) bar.scrollLeft = x;
      else if (x + w > bar.scrollLeft + bar.clientWidth) bar.scrollLeft = x + w - bar.clientWidth;
    }
  });
  return {
    el: h("div", { class: "tabs" }, bar, panes),
    add(title, content) {
      const i = tabs.length;
      const btn = h("button", { type: "button", role: "tab", class: "tab", onclick: () => select(i) }, title);
      const pane = h("div", { class: "tabpane", role: "tabpanel" }, content);
      tabs.push({ btn, pane });
      bar.append(btn);
      panes.append(pane);
    },
    select,
  };
}

// The QSplitter between the columns (desktop layout only).
const SPLIT_KEY = "mds_split";
function enableSplitter(handle) {
  const apply = (f) => document.documentElement.style.setProperty("--split", String(f));
  const saved = Number(storageGet(SPLIT_KEY));
  if (saved > 0.3 && saved < 0.9) apply(saved);
  handle.addEventListener("pointerdown", (e) => {
    const split = handle.parentElement;
    const box = split.getBoundingClientRect();
    handle.setPointerCapture(e.pointerId);
    let f = null;
    const move = (ev) => {
      f = Math.min(0.85, Math.max(0.35, (ev.clientX - box.left) / box.width));
      apply(f);
    };
    const up = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", up);
      if (f !== null) storageSet(SPLIT_KEY, String(f));
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", up);
    e.preventDefault();
  });
}
