// MDS Viewer, web edition. Finds the newest material release this browser
// holds a key for (data/archive/manifest.json lists them, newest first),
// decrypts it in the page and shows the material window. The key is asked
// for once and kept in this browser's storage; nothing here or in the repo
// contains one.
import { readKeystore, writeKeystore, clearKeystore, decryptPayload, parseKeyLine } from "./crypto.js";
import { parsePyJson } from "./py.js";
import { h, modal, messageBox, progressDialog, installTooltips, setDbTranslations, storageGet, storageSet } from "./util.js";
import { mountMaterialView } from "./material.js";
import { RefStore } from "./refs.js";
import { createCatalogs } from "./catalog.js";
import { openMachinesWindow } from "./machines.js";
import { openPowdersWindow } from "./powders.js";
import { openSubmitDialog } from "./submit.js";
import { resetWindowHistory } from "./window.js";

const root = document.getElementById("app");
const mq = matchMedia("(max-width: 959px)");   // below this the two columns get too narrow
const LAYOUT_KEY = "mds_layout";

let manifest = null;
let keystore = readKeystore();
let loaded = null;                    // {payload, db}
let view = null;
const refs = new RefStore(fetchBytes);
const catalogs = createCatalogs({ fetchBytes, manifest: () => manifest, keystore: () => keystore });

// ---- fetching: payloads are immutable per ?v=, the manifest is not ----
const fetched = new Map();

// onProgress(bytesSoFar) follows a download the first time it is fetched.
function fetchBytes(path, v, onProgress) {
  const url = new URL(path, document.baseURI);
  if (v) url.searchParams.set("v", v);
  if (!fetched.has(url.href)) {
    // credentials: "omit": no cookie or other credential goes with these.
    const p = fetch(url, { credentials: "omit" }).then(async (r) => {
      if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
      if (!onProgress || !r.body) return new Uint8Array(await r.arrayBuffer());
      const chunks = [];
      let got = 0;
      for (const reader = r.body.getReader(); ;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        got += value.length;
        onProgress(got);
      }
      const out = new Uint8Array(got);
      let at = 0;
      for (const c of chunks) { out.set(c, at); at += c.length; }
      return out;
    });
    p.catch(() => fetched.delete(url.href));
    fetched.set(url.href, p);
  }
  return fetched.get(url.href);
}

async function fetchManifest() {
  const r = await fetch(new URL("data/archive/manifest.json", document.baseURI),
                        { credentials: "omit", cache: "no-cache" });
  if (!r.ok) throw new Error(`manifest.json: HTTP ${r.status}`);
  const doc = await r.json();
  if (!doc || doc.format !== 1 || !Array.isArray(doc.payloads)) throw new Error("manifest.json: unknown format");
  return doc;
}

const payloadsOf = (kind) => manifest.payloads.filter((p) => p.kind === kind);   // newest first

// db_crypto.find_accessible_archive: the newest material release whose key
// this browser holds. A release the saved key fails on is skipped.
async function openNewest() {
  for (const p of payloadsOf("material_db")) {
    const pw = keystore[p.key_id];
    if (pw === undefined) continue;
    status(`Opening release ${p.date}…`);
    try {
      // The release, its translations and the reference index decrypt in
      // parallel, so the first screen already lists the published PDFs.
      const [plain] = await Promise.all([
        fetchBytes(`data/archive/${p.file}`, p.v).then((b) => decryptPayload(b, pw)),
        loadTranslations(p.key_id, pw),
        refs.load(manifest, keystore),
      ]);
      return { payload: p, db: parsePyJson(new TextDecoder().decode(plain)) };
    } catch (e) {
      console.warn(`${p.file} did not open with the saved key ${p.key_id}:`, e);
    }
  }
  return null;
}

// The DB-value translations (lang.tr_db) published under the same key.
// Without them the page still works, showing those values untranslated.
async function loadTranslations(keyId, pw) {
  const row = payloadsOf("tr").find((r) => r.key_id === keyId);
  try {
    if (!row) throw new Error(`no translation payload for key ${keyId}`);
    const doc = JSON.parse(new TextDecoder().decode(
      await decryptPayload(await fetchBytes(`data/archive/${row.file}`, row.v), pw)));
    setDbTranslations(doc.exact, doc.patterns);
  } catch (e) {
    console.warn("DB translations unavailable:", e);
    setDbTranslations({}, []);
  }
}

// ---- layout: desktop window or single-column mobile page ----
function layoutMode() {
  const pref = storageGet(LAYOUT_KEY);
  if (pref === "desktop" || pref === "mobile") return pref;
  return mq.matches ? "mobile" : "desktop";
}

function applyLayout() {
  const mode = layoutMode();
  root.classList.toggle("mobile", mode === "mobile");
  root.classList.toggle("desktop", mode === "desktop");
  document.documentElement.dataset.layout = mode;         // for the catalog windows
  const btn = root.querySelector(".tool.layout");
  if (btn) {
    btn.textContent = mode === "mobile" ? "Desktop view" : "Mobile view";
    btn.dataset.tip = mode === "mobile" ? "Switch to the desktop layout" : "Switch to the mobile layout";
  }
}

function toggleLayout() {
  const next = layoutMode() === "mobile" ? "desktop" : "mobile";
  storageSet(LAYOUT_KEY, next === (mq.matches ? "mobile" : "desktop") ? "auto" : next);
  applyLayout();
}

// ---- screens ----
function status(text) {
  if (view) return;
  root.replaceChildren(h("div", { class: "splash" }, h("div", { class: "splash-title" }, "MDS Viewer"),
    h("div", { class: "splash-text" }, text)));
}

function failure(text) {
  root.replaceChildren(h("div", { class: "splash" }, h("div", { class: "splash-title" }, "MDS Viewer"),
    h("div", { class: "splash-text error" }, text),
    h("button", { class: "btn", type: "button", onclick: () => location.reload() }, "Retry")));
}

// The key dialog was closed without a key: wait here until asked again.
function locked() {
  return new Promise((resolve) => {
    const again = h("button", { class: "btn default", type: "button", onclick: () => resolve() }, "Enter access key…");
    root.replaceChildren(h("div", { class: "splash" }, h("div", { class: "splash-title" }, "MDS Viewer"),
      h("div", { class: "splash-text" }, "Locked — the data opens with a release access key."), again));
    again.focus();
  });
}

// key_dialog.ask_user_for_key, with the key checked against a release
// before it is saved. Resolves with the key_id, or undefined if closed.
function keyDialog({ add = false, message = "" } = {}) {
  const title = add ? "MDS Viewer - Add release key" : "MDS Viewer - Enter access key";
  return modal(title, (close) => {
    const intro = add
      ? [h("b", {}, "Add a new release access key."), h("br"),
         "Paste the line your maintainer sent you below.", h("br"),
         "Format: ", h("code", {}, "YYYY-MM-DD = <your-key-here>"), h("br"), h("br"),
         "It is saved in this browser, and a newer release it unlocks loads right away. ",
         "Older keys stay valid — no harm in keeping them."]
      : [h("b", {}, "This release is encrypted."), h("br"),
         "Paste the access-key line your maintainer sent you below. The format is:", h("br"),
         h("code", {}, "YYYY-MM-DD = <your-key-here>"), h("br"), h("br"),
         "The pass-phrase part is masked. Once saved you won't be asked again on this device."];
    const input = h("input", { type: "password", class: "key-input mono", autocomplete: "off",
                               autocapitalize: "off", spellcheck: "false", autofocus: true,
                               placeholder: "paste the line: YYYY-MM-DD = <key>", "aria-label": "Release key" });
    const show = h("input", { type: "checkbox" });
    show.addEventListener("change", () => { input.type = show.checked ? "text" : "password"; });
    const idStatus = h("div", { class: "key-status" }, " ");
    input.addEventListener("input", () => {
      const parsed = parseKeyLine(input.value);
      idStatus.className = "key-status";
      if (!input.value.trim()) idStatus.textContent = " ";
      else if (!parsed) {
        idStatus.textContent = "✗  format not recognised — expected: YYYY-MM-DD = <key>";
        idStatus.classList.add("bad");
      } else {
        idStatus.textContent = `✓  detected key ID:  ${parsed.keyId}   (passphrase hidden)`;
        idStatus.classList.add("good");
      }
    });
    const remember = h("input", { type: "checkbox", checked: true });
    const error = h("div", { class: "key-error", hidden: true });
    const ok = h("button", { class: "btn default", type: "submit" }, "Save key & continue");

    const fail = (text) => { error.textContent = text; error.hidden = false; };
    const form = h("form", { class: "key-form", onsubmit: async (e) => {
      e.preventDefault();
      error.hidden = true;
      const parsed = parseKeyLine(input.value);
      if (!parsed) {
        fail("Couldn't recognise a key line in your input.\n\nExpected format:  <key_id> = <passphrase>\n"
             + "(e.g. YYYY-MM-DD = <key>)\n\nMake sure both sides of the '=' are present.");
        return;
      }
      const { keyId, passphrase } = parsed;
      const locked = manifest.payloads.filter((p) => p.key_id === keyId).sort((a, b) => a.size - b.size);
      if (!locked.length) {
        fail(`No release here is locked with the key ID "${keyId}". Check the date part of the line.`);
        return;
      }
      ok.disabled = true;
      ok.textContent = "Checking…";
      try {
        await decryptPayload(await fetchBytes(`data/archive/${locked[0].file}`, locked[0].v), passphrase);
      } catch {
        fail(`This key does not open the ${keyId} release — check it for typos.`);
        return;
      } finally {
        ok.disabled = false;
        ok.textContent = "Save key & continue";
      }
      keystore = { ...keystore, [keyId]: passphrase };
      writeKeystore(keystore, remember.checked);
      close(keyId);
    } },
      h("div", { class: "key-intro" }, intro),
      message ? h("div", { class: "key-warn" }, message) : null,
      h("div", { class: "key-row" }, input, h("label", { class: "check" }, show, "Show")),
      idStatus,
      h("label", { class: "check remember" }, remember, "Remember on this device (90 days)"),
      error,
      h("div", { class: "dialog-buttons" },
        h("button", { class: "btn", type: "button", onclick: () => close(undefined) }, add ? "Cancel" : "Close"),
        ok));

    const saved = Object.keys(keystore);
    const forget = add && saved.length
      ? h("div", { class: "key-saved" }, `Saved in this browser: ${saved.join(", ")}  `,
          h("button", { class: "linkish", type: "button", onclick: () => {
            if (!confirm("Forget every release key saved in this browser?\n\n"
                         + "The viewer locks until a key is entered again.")) return;
            clearKeystore();
            location.reload();
          } }, "Forget saved keys"))
      : null;
    return [form, forget];
  }, { backdrop: false });
}

function updateBanner() {
  if (!view || !loaded) return;
  const newest = payloadsOf("material_db")[0];
  const banner = view.banner;
  if (newest && newest.date > loaded.payload.date && !(newest.key_id in keystore)) {
    banner.replaceChildren(
      `A newer data release (${newest.date}) is available — add its release key to load it. `,
      h("button", { class: "linkish", type: "button", onclick: addKey }, "Add release key…"));
    banner.hidden = false;
  } else {
    banner.hidden = true;
  }
}

async function addKey() {
  const added = await keyDialog({ add: true });
  if (!added) return;
  catalogs.reset();                         // a newer catalog may open now
  const next = await openNewest();          // also reloads the translations and the PDF index
  if (next && next.payload.file !== loaded.payload.file) {
    const keep = view.currentMaterial();
    show(next);
    if (keep) view.select(keep);
    messageBox("Key saved", `Release ${next.payload.date} is now loaded.`);
  } else {
    view.refreshReferences();
    messageBox("Key saved", "The key was added to this browser. The release shown is still the newest one it opens.");
  }
  updateBanner();
}

// The machine / powder catalogs: fetched the first time, behind a progress
// dialog when that takes more than a moment.
async function openCatalog(kind) {
  const name = kind === "machines" ? "machine" : "powder";
  let dlg = null;
  const timer = setTimeout(() => { dlg = progressDialog(`Loading the ${name} catalog`); }, 250);
  let cat;
  try {
    cat = await catalogs.load(kind, (got, total) => dlg?.set(got, total));
  } catch (e) {
    clearTimeout(timer);
    dlg?.close();
    messageBox(`${name[0].toUpperCase()}${name.slice(1)} catalog unavailable`, String(e.message || e), "warn");
    return;
  }
  clearTimeout(timer);
  dlg?.close();
  const opts = { isMobile: () => layoutMode() === "mobile" };
  if (kind === "machines") openMachinesWindow(cat, opts);
  else openPowdersWindow(cat, opts);
}

function openSubmit() {
  const keyId = loaded.payload.key_id;
  openSubmitDialog({ db: loaded.db, keyId, passphrase: keystore[keyId] });
}

function show(result) {
  loaded = result;
  view = null;
  root.replaceChildren();
  view = mountMaterialView(root, {
    db: result.db,
    refs,
    keystore: () => keystore,
    onAddKey: addKey,
    onToggleLayout: toggleLayout,
    onSubmit: openSubmit,
    onMachines: () => openCatalog("machines"),
    onPowders: () => openCatalog("powders"),
  });
  applyLayout();
}

async function boot() {
  resetWindowHistory();
  installTooltips();
  applyLayout();
  mq.addEventListener("change", applyLayout);
  status("Loading…");
  try {
    manifest = await fetchManifest();
  } catch (e) {
    failure(`The data list could not be read (${e.message}).`);
    return;
  }
  if (!payloadsOf("material_db").length) {
    failure("No release has been published yet.");
    return;
  }
  let result = await openNewest();
  let message = Object.keys(keystore).length && !result
    ? "The key saved in this browser does not open any release here." : "";
  while (!result) {
    status("Locked");
    if ((await keyDialog({ message })) === undefined) {
      await locked();
      message = "";
      continue;
    }
    result = await openNewest();
    message = "That key did not open a release.";
  }
  show(result);
  updateBanner();
}

boot();
