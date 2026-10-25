// The desktop opens the catalogs as windows of their own. Here a window is
// a layer over the page with a title bar and ✕, closed by ✕, Escape or the
// browser's Back button: each window is one history entry, so Back on a
// phone closes it instead of leaving the viewer.
import { h, hideTip } from "./util.js";

const stack = [];
let wired = false;

function wire() {
  if (wired) return;
  wired = true;
  addEventListener("popstate", () => {
    const depth = Number(history.state?.mdsWin) || 0;
    while (stack.length > depth) stack.pop().destroy();
  });
  addEventListener("keydown", (e) => {
    // A dialog over the window takes Escape first.
    if (e.key !== "Escape" || !stack.length || document.querySelector(".dialog-back")) return;
    e.preventDefault();
    stack[stack.length - 1].close();
  });
}

// A reload keeps the history state but not the windows it belonged to.
export function resetWindowHistory() {
  if (history.state?.mdsWin) history.replaceState(null, "");
}

// build(win) returns the window's content; win.body is where it goes.
export function openWindow(title, build, { className = "" } = {}) {
  wire();
  hideTip();
  const prevFocus = document.activeElement;
  const titleEl = h("div", { class: "win-title" }, title);
  const closeBtn = h("button", { type: "button", class: "win-close", "aria-label": "Close", tip: "Close (Esc)" }, "✕");
  const body = h("div", { class: "win-body" });
  const frame = h("div", { class: `win ${className}`.trim(), role: "dialog", "aria-modal": "true", "aria-label": title },
    h("div", { class: "win-bar" }, titleEl, closeBtn), body);
  const layer = h("div", { class: "win-layer" }, frame);
  const win = {
    el: frame,
    body,
    onClose: null,
    close() {
      if (stack[stack.length - 1] === win) history.back();
    },
    destroy() {
      hideTip();
      layer.remove();
      win.onClose?.();
      prevFocus?.focus?.();
    },
  };
  closeBtn.addEventListener("click", () => win.close());
  stack.push(win);
  history.pushState({ mdsWin: stack.length }, "");
  document.body.append(layer);
  body.append(...[build(win)].flat().filter(Boolean));
  closeBtn.focus();
  return win;
}
