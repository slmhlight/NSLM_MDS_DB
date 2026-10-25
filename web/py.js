// Python semantics the desktop app's output depends on.
//
// The desktop formats every value with Python, and Python remembers what
// JSON.parse forgets: 191.0 is a float and prints as "191.0", 191 is an int
// and prints as "191". material_db.json holds ~3,000 integral floats, and
// the desktop prints some of them verbatim (heat-treatment hardness, the
// tooltip ranges, the report's Ra), so the payload is parsed here instead
// of with JSON.parse. Every object or array that held a float-typed number
// lists those keys in a Set under the FLOATS symbol, which Object.keys,
// for...in and JSON.stringify all ignore.

export const FLOATS = Symbol("floats");

const NUMBER = /-?(?:0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?/y;

export function parsePyJson(text) {
  let i = 0;
  let wasFloat = false;        // set by the last value() that was a number
  const fail = (what) => { throw new SyntaxError(`JSON: ${what} at offset ${i}`); };
  const ws = () => {
    for (;;) {
      const c = text.charCodeAt(i);
      if (c === 32 || c === 10 || c === 13 || c === 9) i++;
      else return;
    }
  };

  function string() {
    const start = i++;
    for (;;) {
      const j = text.indexOf('"', i);
      if (j < 0) fail("unterminated string");
      let k = j - 1;
      while (text.charCodeAt(k) === 92) k--;           // backslashes before the quote
      i = j + 1;
      if ((j - 1 - k) % 2 === 0) break;
    }
    const raw = text.slice(start, i);
    return raw.includes("\\") ? JSON.parse(raw) : raw.slice(1, -1);
  }

  function object() {
    i++;
    const o = {};
    let floats = null;
    ws();
    if (text.charCodeAt(i) === 125) { i++; return o; }
    for (;;) {
      ws();
      if (text.charCodeAt(i) !== 34) fail("expected a key");
      const k = string();
      ws();
      if (text.charCodeAt(i++) !== 58) fail("expected ':'");
      const v = value();
      if (k === "__proto__") {
        Object.defineProperty(o, k, { value: v, writable: true, enumerable: true, configurable: true });
      } else {
        o[k] = v;
      }
      if (wasFloat) (floats ??= new Set()).add(k);
      else floats?.delete(k);                            // a repeated key: last one wins
      ws();
      const c = text.charCodeAt(i++);
      if (c === 125) break;
      if (c !== 44) fail("expected ',' or '}'");
    }
    if (floats?.size) o[FLOATS] = floats;
    wasFloat = false;
    return o;
  }

  function array() {
    i++;
    const a = [];
    let floats = null;
    ws();
    if (text.charCodeAt(i) === 93) { i++; return a; }
    for (;;) {
      const v = value();
      if (wasFloat) (floats ??= new Set()).add(a.length);
      a.push(v);
      ws();
      const c = text.charCodeAt(i++);
      if (c === 93) break;
      if (c !== 44) fail("expected ',' or ']'");
    }
    if (floats) a[FLOATS] = floats;
    wasFloat = false;
    return a;
  }

  function value() {
    ws();
    wasFloat = false;
    const c = text.charCodeAt(i);
    if (c === 123) return object();
    if (c === 91) return array();
    if (c === 34) return string();
    for (const [word, v, isFloat] of LITERALS) {
      if (text.startsWith(word, i)) { i += word.length; wasFloat = isFloat; return v; }
    }
    NUMBER.lastIndex = i;
    const m = NUMBER.exec(text);
    if (!m) fail("unexpected character");
    i = NUMBER.lastIndex;
    wasFloat = m[1] !== undefined || m[2] !== undefined;
    return Number(m[0]);
  }

  const out = value();
  ws();
  if (i < text.length) fail("trailing data");
  return out;
}

// Python's json also reads NaN and the infinities (json.dump writes them).
const LITERALS = [["true", true, false], ["false", false, false], ["null", null, false],
                  ["NaN", NaN, true], ["Infinity", Infinity, true], ["-Infinity", -Infinity, true]];

export function isFloat(container, key) {
  return Boolean(container?.[FLOATS]?.has(key));
}

// repr(float): the shortest round-trip digits (JS finds the same ones),
// in exponent form below 1e-4 and from 1e16 up, with a two-digit exponent.
function floatRepr(x) {
  if (Number.isNaN(x)) return "nan";
  if (!Number.isFinite(x)) return x > 0 ? "inf" : "-inf";
  if (x === 0) return Object.is(x, -0) ? "-0.0" : "0.0";
  const [mant, exp] = x.toExponential().split("e");
  const e = Number(exp);
  if (e < -4 || e >= 16) return `${mant}e${e < 0 ? "-" : "+"}${String(Math.abs(e)).padStart(2, "0")}`;
  const s = String(x);
  return s.includes(".") ? s : `${s}.0`;
}

function quote(s) {
  const q = s.includes("'") && !s.includes('"') ? '"' : "'";
  return q + s.replace(/\\/g, "\\\\").replace(new RegExp(q, "g"), `\\${q}`)
    .replace(/\n/g, "\\n").replace(/\r/g, "\\r").replace(/\t/g, "\\t") + q;
}

function reprItem(c, k) {
  const v = c[k];
  return typeof v === "string" ? quote(v) : strValue(v, isFloat(c, k));
}

// str(v), given whether the JSON wrote v as a float.
export function strValue(v, float = false) {
  if (v === null || v === undefined) return "None";
  if (v === true) return "True";
  if (v === false) return "False";
  if (typeof v === "number") return float || !Number.isInteger(v) ? floatRepr(v) : String(v);
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return `[${v.map((_, i) => reprItem(v, i)).join(", ")}]`;
  return `{${Object.keys(v).map((k) => `${quote(k)}: ${reprItem(v, k)}`).join(", ")}}`;
}

// str(c.get(k, dflt)) -- or str(c[i]) for an array.
export function pyStr(c, k, dflt = null) {
  if (c === null || c === undefined || !Object.hasOwn(c, k)) return strValue(dflt);
  return strValue(c[k], isFloat(c, k));
}

// str(c.get(k) or dflt)
export function pyOr(c, k, dflt) {
  return truthy(c?.[k]) ? pyStr(c, k) : dflt;
}

export function truthy(v) {
  if (v === null || v === undefined || v === false) return false;
  if (typeof v === "number") return v !== 0;         // NaN is truthy in Python
  if (typeof v === "string" || Array.isArray(v)) return v.length > 0;
  if (typeof v === "object") return Object.keys(v).length > 0;
  return true;
}

// float(v), or null where Python would raise.
export function pyFloat(v) {
  if (typeof v === "number") return v;
  if (typeof v === "boolean") return v ? 1 : 0;
  if (typeof v !== "string") return null;
  const s = v.trim();
  if (/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(s)) return Number(s);
  const m = /^([+-]?)(inf|infinity|nan)$/i.exec(s);
  if (!m) return null;
  if (m[2].toLowerCase() === "nan") return NaN;
  return m[1] === "-" ? -Infinity : Infinity;
}

// mds_dialog._safe_num: a number, or float() of the first word of str(v).
export function safeNum(v, dflt = 0) {
  if (v === null || v === undefined) return dflt;
  if (typeof v === "number" || typeof v === "boolean") return pyFloat(v);
  if (typeof v !== "string") return dflt;
  const word = v.trim().split(/\s+/)[0];
  const n = word ? pyFloat(word) : null;
  return n === null ? dflt : n;
}

// f"{x:.{d}f}". toFixed rounds an exact tie away from zero; Python rounds
// it to even. Ties are decided on the exact binary value, which toFixed(100)
// spells out in full for any magnitude this data holds.
export function pyFixed(x, d) {
  if (Number.isNaN(x)) return "nan";
  if (!Number.isFinite(x)) return x > 0 ? "inf" : "-inf";
  const out = x.toFixed(d);
  const ax = Math.abs(x);
  if (ax >= 1e21) return out;
  const full = ax.toFixed(100);
  const dot = full.indexOf(".");
  if (!/^50*$/.test(full.slice(dot + 1 + d))) return out;
  const kept = d ? full.slice(0, dot + 1 + d) : full.slice(0, dot);
  if (Number(kept[kept.length - 1]) % 2 !== 0) return out;        // odd: both round up
  return (x < 0 ? "-" : "") + kept;
}

// round(x) for an int result: halves go to the even neighbour.
export function pyRound(x) {
  const f = Math.floor(x);
  const r = x - f;
  if (r > 0.5) return f + 1;
  if (r < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

// mds_dialog._fmt_num(v, spec)
export function fmtNum(v, digits) {
  const n = safeNum(v, null);
  return n === null ? "-" : pyFixed(n, digits);
}

// The vendor tree's _fmt: whole numbers bare, others to one decimal, and a
// value float() cannot read shown as it is.
export function fmtCell(x) {
  if (x === null || x === undefined || x === "" || x === "-") return "-";
  const n = pyFloat(x);
  if (n === null) return strValue(x);
  if (Number.isInteger(n)) return String(n);
  return pyFixed(n, 1);
}

// Slicing and len() count code points, not UTF-16 units.
export function pySlice(s, n) {
  const cps = Array.from(s);
  return cps.length <= n ? s : cps.slice(0, n).join("");
}

export function pyLen(s) {
  return Array.from(s).length;
}
