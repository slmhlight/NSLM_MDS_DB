// Shared UI helpers: the desktop's text lookups, a small DOM builder,
// Qt-style tooltips, toasts and modal dialogs.
import { STR } from "./i18n.js";
import { pyLen } from "./py.js";

// mds_dialog._T: the English string for a lang.py key.
export function T(key, fallback = key) {
  return Object.hasOwn(STR, key) ? STR[key] : fallback;
}

// lang.tr_db's tables. They quote the database, so they arrive encrypted
// with each release (data/archive/ui/) rather than in this file.
let dbExact = {};
let dbPatterns = [];

export function setDbTranslations(exact, patterns) {
  dbExact = exact && typeof exact === "object" ? exact : {};
  dbPatterns = Array.isArray(patterns) ? patterns : [];
}

// lang.tr_db for English: whole-value match first, then substring fallbacks.
export function trDb(value) {
  if (typeof value !== "string" || !value) return value;
  if (Object.hasOwn(dbExact, value)) return dbExact[value];
  let out = value;
  for (const [ko, en] of dbPatterns) if (out.includes(ko)) out = out.split(ko).join(en);
  return out;
}

// "<b>Category:</b>" -> "Category:" (lang.py keeps Qt rich-text tags).
export function plain(s) {
  return String(s).replace(/<[^>]+>/g, "");
}

export function padEnd(s, w) { return s + " ".repeat(Math.max(0, w - pyLen(s))); }
export function padStart(s, w) { return " ".repeat(Math.max(0, w - pyLen(s))) + s; }

// html.escape(str(s)), quote=True
export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" }[c]));
}

export function isHttpUrl(u) {
  return typeof u === "string" && /^https?:\/\//i.test(u.trim());
}

// h("div", {class: "x", onclick: fn}, child, "text", ...)
export function h(tag, attrs, ...children) {
  const el = tag.startsWith("svg:")
    ? document.createElementNS("http://www.w3.org/2000/svg", tag.slice(4))
    : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "class") el.setAttribute("class", v);
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k === "tip") el.dataset.tip = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

// Open an external page without telling it where the click came from.
export function openExternal(url) {
  if (!isHttpUrl(url)) return false;
  const a = h("a", { href: url.trim(), target: "_blank", rel: "noopener noreferrer" });
  document.body.append(a);
  a.click();
  a.remove();
  return true;
}

export function storageGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

export function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch { /* private mode: not remembered */ }
}

// ---- tooltips: any element with data-tip. Hover on a mouse, long-press on
// touch, styled like the desktop's QToolTip.
let tipEl = null;
let tipTimer = 0;
let tipOwner = null;

function showTip(owner, x, y) {
  if (!tipEl) tipEl = h("div", { class: "tooltip", role: "tooltip" });
  tipEl.textContent = owner.dataset.tip;
  document.body.append(tipEl);
  tipOwner = owner;
  const pad = 8;
  const r = tipEl.getBoundingClientRect();
  let left = x + 14;
  let top = y + 18;
  if (left + r.width > innerWidth - pad) left = Math.max(pad, innerWidth - pad - r.width);
  if (top + r.height > innerHeight - pad) top = Math.max(pad, y - r.height - 10);
  tipEl.style.left = `${left}px`;
  tipEl.style.top = `${top}px`;
}

export function hideTip() {
  clearTimeout(tipTimer);
  tipEl?.remove();
  tipOwner = null;
}

export function installTooltips() {
  document.addEventListener("pointerover", (e) => {
    if (e.pointerType !== "mouse") return;
    const owner = e.target.closest?.("[data-tip]");
    if (owner === tipOwner) return;
    hideTip();
    if (!owner) return;
    const { clientX: x, clientY: y } = e;
    tipTimer = setTimeout(() => showTip(owner, x, y), 450);
  });
  document.addEventListener("pointerdown", (e) => {
    hideTip();
    if (e.pointerType === "mouse") return;
    const owner = e.target.closest?.("[data-tip]");
    if (!owner) return;
    const { clientX: x, clientY: y } = e;
    tipTimer = setTimeout(() => showTip(owner, x, y), 500);
  });
  for (const ev of ["pointerup", "pointercancel"]) {
    document.addEventListener(ev, (e) => { if (e.pointerType !== "mouse") clearTimeout(tipTimer); });
  }
  document.addEventListener("scroll", hideTip, true);
  // A long-press must not also open the browser's context menu.
  document.addEventListener("contextmenu", (e) => {
    if (tipOwner && e.target.closest?.("[data-tip]") === tipOwner) e.preventDefault();
  });
}

// ---- toast: a short confirmation that does not need an OK click.
export function toast(text, ms = 3200) {
  const el = h("div", { class: "toast", role: "status" }, text);
  document.body.append(el);
  requestAnimationFrame(() => el.classList.add("show"));
  setTimeout(() => { el.classList.remove("show"); setTimeout(() => el.remove(), 300); }, ms);
}

// ---- modal dialog. build(close) returns the body; resolves with close(value).
export function modal(title, build, { closable = true, wide = false } = {}) {
  return new Promise((resolve) => {
    const prevFocus = document.activeElement;
    let done = false;
    const close = (value) => {
      if (done) return;
      done = true;
      back.remove();
      document.removeEventListener("keydown", onKey, true);
      prevFocus?.focus?.();
      resolve(value);
    };
    const onKey = (e) => {
      if (e.key === "Escape" && closable) { e.stopPropagation(); close(undefined); }
    };
    const dlg = h("div", { class: `dialog${wide ? " wide" : ""}`, role: "dialog", "aria-modal": "true",
                           "aria-label": title },
      h("div", { class: "dialog-title" }, title),
      h("div", { class: "dialog-body" }, build(close)));
    const back = h("div", { class: "dialog-back" }, dlg);
    if (closable) back.addEventListener("mousedown", (e) => { if (e.target === back) close(undefined); });
    document.addEventListener("keydown", onKey, true);
    document.body.append(back);
    (dlg.querySelector("[autofocus]") || dlg.querySelector("button"))?.focus();
  });
}

// QMessageBox.information / .warning
export function messageBox(title, text, kind = "info") {
  return modal(title, (close) => [
    h("div", { class: `msg ${kind}` }, h("span", { class: "msg-icon" }, kind === "info" ? "i" : "!"),
      h("div", { class: "msg-text" }, text)),
    h("div", { class: "dialog-buttons" },
      h("button", { class: "btn default", autofocus: true, onclick: () => close(true) }, "OK")),
  ]);
}
