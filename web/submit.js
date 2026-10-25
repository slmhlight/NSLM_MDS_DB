// Submit TDS data (contribution_dialog), sent as a GitHub issue. The entry
// is the contribution JSON 15_merge_contributions.py takes (see
// contributions/SCHEMA.md), encrypted with the release key so the public
// issue shows nothing readable. _import_contributions.py turns the open
// issues back into contributions/pending/*.json for the maintainer.
import { h, modal, messageBox, toast } from "./util.js";
import { encryptPayload } from "./crypto.js";
import { pyFloat, strValue } from "./py.js";

export const ISSUE_REPO = "slmhlight/NSLM_MDS_DB";
const CATEGORY_TOPS = ["Aluminium", "Cobalt", "Copper", "Nickel", "Steel", "Titanium", "Niobium", "Other"];
// Canonical post-treatments observed across the DB; any other text is fine too.
const POST_TREATMENTS_COMMON = ["as-built", "stress-relieved", "annealed", "solution-annealed", "solution+age",
  "HIP", "HT_HIP", "HT_HIP_age", "T6", "T4", "aged", "DA", "tempered", "hardened", "heat-treated"];
const URL_RE = /^https?:\/\/[^\s]+$/;
const MAX_ISSUE_URL = 8000;          // GitHub refuses much longer prefilled links

// ---- validation: the desktop dialog's rules ----
function vUrl(s) {
  return !s || !URL_RE.test(s.trim()) ? "Source URL must start with http:// or https://" : null;
}

function vRange(name, val, lo, hi) {
  if (val === null || val === undefined || val === "") return null;
  const v = pyFloat(val);
  if (v === null) return `${name}: not a number`;
  if (v < lo || v > hi) return `${name}: ${strValue(v, true)} outside [${lo}, ${hi}]`;
  return null;
}

function vPairLe(loName, loVal, hiName, hiVal) {
  if ([null, undefined, ""].includes(loVal) || [null, undefined, ""].includes(hiVal)) return null;
  const l = pyFloat(loVal), u = pyFloat(hiVal);
  if (l === null || u === null) return null;
  return l > u ? `${loName} (${strValue(l, true)}) must be ≤ ${hiName} (${strValue(u, true)})` : null;
}

const NUMERIC = [["yield_MPa", 0, 5000], ["yield_z_MPa", 0, 5000], ["uts_xy_MPa", 0, 5000], ["uts_z_MPa", 0, 5000],
  ["elongation_xy_pct", 0, 100], ["elongation_z_pct", 0, 100], ["hardness_HV", 10, 1000]];

export function validateVendorEntry(d) {
  const errs = [];
  for (const k of ["manufacturer", "machine", "post_treatment", "source"]) {
    if (!String(d[k] ?? "").trim()) errs.push(`${k} is required`);
  }
  const u = vUrl(d.source ?? "");
  if (u) errs.push(u);
  const lt = vRange("layer_thickness_um", d.layer_thickness_um, 5, 500);
  if (lt) errs.push(lt);
  else if (!Number.isInteger(pyFloat(d.layer_thickness_um))) errs.push("layer_thickness_um: not a whole number");
  // A 0 is a blank here, as on the desktop's spin boxes.
  const opt = (k) => {
    const raw = String(d[k] ?? "").trim();
    return raw && pyFloat(raw) === 0 ? "" : raw;
  };
  for (const [k, lo, hi] of NUMERIC) {
    const e = vRange(k, opt(k), lo, hi);
    if (e) errs.push(e);
  }
  for (const [lo, hi] of [["yield_MPa", "uts_xy_MPa"], ["yield_z_MPa", "uts_z_MPa"]]) {
    const e = vPairLe(lo, opt(lo), hi, opt(hi));
    if (e) errs.push(e);
  }
  return errs;
}

export function validateNewMaterial(d) {
  const errs = [];
  for (const k of ["name", "category_top", "composition", "source"]) {
    if (!String(d[k] ?? "").trim()) errs.push(`${k} is required`);
  }
  if (d.category_top && !CATEGORY_TOPS.includes(d.category_top)) {
    errs.push(`category_top must be one of (${CATEGORY_TOPS.map((c) => `'${c}'`).join(", ")})`);
  }
  const u = vUrl(d.source ?? "");
  if (u) errs.push(u);
  return errs;
}

// "Ni balance, Cr 22, Co 19" -> [["Ni", "balance"], ["Cr", "22"], ["Co", "19"]]
export function parseComposition(text) {
  return String(text).split(/[,;\n]+/).map((s) => s.trim()).filter(Boolean).map((part) => {
    const m = /^(\S+?)\s*[:=]?\s+(.+)$/.exec(part) || /^(\S+?)[:=](.+)$/.exec(part);
    return m ? [m[1], m[2].trim()] : [part, "?"];
  });
}

// ---- the contribution JSON (contributions/SCHEMA.md) ----
const num = (s) => {
  const t = String(s ?? "").trim();
  if (!t) return null;
  const v = pyFloat(t);
  return v === 0 ? null : v;              // the desktop's spin boxes read 0 as "(blank)"
};

function entryOf(f, source) {
  return {
    manufacturer: f.manufacturer.trim(),
    machine: f.machine.trim(),
    post_treatment: f.post_treatment.trim(),
    layer_thickness_um: pyFloat(f.layer_thickness_um),
    yield_MPa: num(f.yield_MPa),
    yield_z_MPa: num(f.yield_z_MPa),
    uts_xy_MPa: num(f.uts_xy_MPa),
    uts_z_MPa: num(f.uts_z_MPa),
    elongation_xy_pct: num(f.elongation_xy_pct),
    elongation_z_pct: num(f.elongation_z_pct),
    hardness_HV: num(f.hardness_HV),
    surface_ra_lo: null,
    surface_ra_hi: null,
    tds_link: source,
  };
}

function envelope(type, source, notes, payload, now = new Date()) {
  return {
    schema_version: 1,
    type,
    submitted_by: "",              // filled in from the GitHub account on import
    submitted_at: now.toISOString().replace(/\.\d{3}Z$/, "Z"),
    source,
    rationale: notes || "(none given)",
    payload,
    submitted_via: "web viewer",
  };
}

export function buildVendorContribution(f, now) {
  const source = f.source.trim();
  return envelope("add_vendor_entry", source, f.notes.trim(),
                  { target_material: f.target_material, entry: entryOf(f, source) }, now);
}

export function buildMaterialContribution(f, now) {
  const source = f.source.trim();
  const name = f.name.trim();
  return envelope("add_material", source, f.notes.trim(), {
    name,
    category: f.category_top,
    category_top: f.category_top,
    density: null, melt: null, thermal_k: null, cp: null, cte: null, E: null, poisson: null,
    magnetic: "-",
    composition: parseComposition(f.composition),
    composition_text: f.composition.trim(),
    applications: "-",
    ref_urls: [[`${name} reference`, source]],
    first_vendor_entry: entryOf(f, source),
  }, now);
}

function base64(u8) {
  let s = "";
  for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode(...u8.subarray(i, i + 0x8000));
  return btoa(s);
}

// -> {title, body, url}: the issue text, and a link that opens it prefilled
export async function issueFor(contribution, keyId, passphrase, now = new Date()) {
  const plain = new TextEncoder().encode(JSON.stringify(contribution, null, 2));
  const b64 = base64(await encryptPayload(plain, keyId, passphrase));
  const title = `Submission ${now.toISOString().slice(0, 16).replace("T", " ")}Z`;
  const body = ["Encrypted with the viewer's release key: only the maintainer can read it.",
    "Please submit it as it is; an edited block cannot be opened.", "", "```mdse",
    ...b64.match(/.{1,76}/g), "```", ""].join("\n");
  const base = `https://github.com/${ISSUE_REPO}/issues/new`;
  const full = `${base}?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
  return { title, body, url: full.length <= MAX_ISSUE_URL ? full : null, plainUrl: base };
}

// ---- the dialog ----
function field(label, input, { req = false, unit = null } = {}) {
  return [h("label", { class: "flabel" }, `${label}${req ? " *" : ""}:`),
    unit ? h("span", { class: "with-unit" }, input, h("span", { class: "unit" }, unit)) : input];
}

const text = (attrs = {}) => h("input", { type: "text", autocomplete: "off", spellcheck: "false", ...attrs });
const number = (attrs = {}) => h("input", { type: "text", inputmode: "decimal", autocomplete: "off",
                                            placeholder: "(blank)", ...attrs });

// The vendor-entry fields; fields() reads them as the contribution's names.
function vendorFields(idPrefix) {
  const datalist = h("datalist", { id: `${idPrefix}-posts` }, POST_TREATMENTS_COMMON.map((p) => h("option", { value: p })));
  const w = {
    manufacturer: text({ placeholder: "e.g. EOS, Nikon SLM Solutions" }),
    machine: text({ placeholder: "e.g. EOS M 290" }),
    layer_thickness_um: h("input", { type: "number", min: "5", max: "500", step: "1", value: "30", inputmode: "numeric" }),
    post_treatment: text({ list: `${idPrefix}-posts`, value: "as-built" }),
    yield_MPa: number(), yield_z_MPa: number(), uts_xy_MPa: number(), uts_z_MPa: number(),
    elongation_xy_pct: number(), elongation_z_pct: number(), hardness_HV: number(),
  };
  const group = (title, xy, z, unit) => h("fieldset", { class: "ngroup" }, h("legend", {}, title),
    h("div", { class: "nrow" }, h("span", {}, "XY:"), h("span", { class: "with-unit" }, w[xy], h("span", { class: "unit" }, unit))),
    h("div", { class: "nrow" }, h("span", {}, "Z:"), h("span", { class: "with-unit" }, w[z], h("span", { class: "unit" }, unit))));
  const nodes = [
    ...field("Manufacturer", w.manufacturer, { req: true }),
    ...field("Machine", w.machine, { req: true }),
    ...field("Layer thickness", w.layer_thickness_um, { req: true, unit: "μm" }),
    ...field("Post-treatment", w.post_treatment, { req: true }), datalist,
    h("div", { class: "ngroups" }, group("Yield strength (0.2 %)", "yield_MPa", "yield_z_MPa", "MPa"),
      group("Ultimate tensile strength", "uts_xy_MPa", "uts_z_MPa", "MPa"),
      group("Elongation", "elongation_xy_pct", "elongation_z_pct", "%")),
    ...field("Hardness", w.hardness_HV, { unit: "HV" }),
  ];
  return { w, nodes, read: () => Object.fromEntries(Object.entries(w).map(([k, el]) => [k, el.value])) };
}

// ctx: {db, keyId, passphrase}
export function openSubmitDialog(ctx) {
  const materials = Object.keys(ctx.db?.materials || {}).sort();
  return modal("MDS Viewer — Submit TDS contribution", (close) => {
    // Tab 1: add a vendor entry to an existing material
    const target = h("select", {}, materials.map((m) => h("option", { value: m }, m)));
    const v = vendorFields("sv");
    const vSrc = text({ placeholder: "https://vendor.com/path/to/datasheet.pdf", inputmode: "url" });
    const vNotes = h("textarea", { rows: "2" });
    const tab1 = h("div", { class: "form" }, ...field("Target material", target, { req: true }), ...v.nodes,
      ...field("Source URL", vSrc, { req: true }), ...field("Notes (optional)", vNotes));

    // Tab 2: a new material, with the first vendor entry from its TDS
    const mName = text({ placeholder: "e.g. Inconel 939" });
    const mCat = h("select", {}, CATEGORY_TOPS.map((c) => h("option", { value: c }, c)));
    const mComp = h("textarea", { rows: "3", placeholder: "e.g. Ni balance, Cr 22, Co 19, Al 1.9, Ti 3.7, W 2 ..." });
    const mSrc = text({ placeholder: "https://...  (ASTM/AMS/MMPDS or vendor source)", inputmode: "url" });
    const mNotes = h("textarea", { rows: "2" });
    const mv = vendorFields("sm");
    const tab2 = h("div", { class: "form" }, ...field("Material name", mName, { req: true }),
      ...field("Category", mCat, { req: true }), ...field("Composition", mComp, { req: true }),
      ...field("Source URL", mSrc, { req: true }), ...field("Notes (optional)", mNotes),
      h("div", { class: "fsub" }, "First vendor entry, from the same TDS"), ...mv.nodes);

    const tabs = [["Add vendor entry", tab1], ["Add new material", tab2]];
    let active = 0;
    const btns = tabs.map(([label], i) => h("button", { type: "button", class: "tab", role: "tab",
                                                       onclick: () => select(i) }, label));
    const select = (i) => {
      active = i;
      btns.forEach((b, j) => { b.classList.toggle("active", i === j); b.setAttribute("aria-selected", String(i === j)); });
      tabs.forEach(([, el], j) => { el.hidden = i !== j; });
    };
    select(0);

    const go = h("button", { type: "submit", class: "btn default" }, "Validate & prepare issue");
    const form = h("form", { class: "submit-form", onsubmit: async (e) => {
      e.preventDefault();
      let errs, contribution;
      if (active === 0) {
        const f = { ...v.read(), target_material: target.value, source: vSrc.value, notes: vNotes.value };
        errs = validateVendorEntry(f);
        if (!errs.length) contribution = buildVendorContribution(f);
      } else {
        const f = { ...mv.read(), name: mName.value, category_top: mCat.value, composition: mComp.value,
                    source: mSrc.value, notes: mNotes.value };
        errs = [...validateNewMaterial(f), ...validateVendorEntry(f).filter((x) => !x.startsWith("source")
          && !x.startsWith("Source")).map((x) => `vendor entry: ${x}`)];
        if (!errs.length) contribution = buildMaterialContribution(f);
      }
      if (errs.length) {
        await messageBox("Validation failed", errs.map((x) => `• ${x}`).join("\n"), "warn");
        return;
      }
      go.disabled = true;
      try {
        const issue = await issueFor(contribution, ctx.keyId, ctx.passphrase);
        if (await readyDialog(issue, ctx.keyId)) close(true);
      } catch (err) {
        messageBox("Could not prepare the issue", String(err.message || err), "warn");
      } finally {
        go.disabled = false;
      }
    } },
      h("div", { class: "key-intro" }, h("b", {}, "Submit a new TDS-sourced entry."), h("br"),
        "Fill in the form and press ", h("b", {}, "Validate & prepare issue"), ". The entry is encrypted with your "
        + "release key and opened as a new issue on GitHub; only the maintainer can read it.", h("br"),
        h("i", {}, "Source URL must be the actual published TDS (vendor's official data sheet PDF or page).")),
      h("div", { class: "tabbar form-tabs", role: "tablist" }, btns),
      h("div", { class: "form-pane" }, tab1, tab2),
      h("div", { class: "dialog-buttons" },
        h("button", { type: "button", class: "btn", onclick: () => close(false) }, "Cancel"), go));
    return form;
  }, { wide: true, backdrop: false });
}

// The hand-over: open the issue on GitHub, or copy the text for whoever
// has no GitHub account. Resolves true once the entry is on its way.
function readyDialog(issue, keyId) {
  return modal("Submit TDS contribution — ready", (close) => {
    const area = h("textarea", { class: "issue-text mono", rows: "5", readonly: true }, issue.body);
    const copy = h("button", { type: "button", class: "btn", onclick: async () => {
      try {
        await navigator.clipboard.writeText(issue.body);
        toast("Copied. Send it to your maintainer.");
      } catch {
        area.select();
        toast("Select-all is done: press Ctrl+C (or ⌘C) to copy.");
      }
    } }, "Copy text");
    const open = h("a", { class: "btn default", href: issue.url || issue.plainUrl, target: "_blank",
                          rel: "noopener noreferrer", onclick: () => {
                            toast("GitHub opened in a new tab: press “Submit new issue” there.", 5000);
                            setTimeout(() => close(true), 0);
                          } }, "Open GitHub issue");
    return [
      h("div", { class: "msg-text" },
        `Your entry is encrypted with release key ${keyId}.\n\n`
        + "1. Press “Open GitHub issue”. GitHub opens with the entry filled in (sign in if it asks).\n"
        + "2. Press “Submit new issue” there.\n\n"
        + (issue.url ? "" : "The entry is too long for a prefilled link: paste the text below into the new issue.\n\n")
        + "No GitHub account? Copy the text and send it to your maintainer instead."),
      area,
      h("div", { class: "dialog-buttons" },
        h("button", { type: "button", class: "btn", onclick: () => close(false) }, "Back"), copy, open),
    ];
  }, { wide: true });
}
