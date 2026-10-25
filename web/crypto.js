// Opens the MDSE v2 payloads the desktop app reads (db_crypto.py), with the
// browser's WebCrypto API: PBKDF2-HMAC-SHA256 (200k) -> AES-256-GCM.
//
//   offset  size  field
//    0       4    magic "MDSE"
//    4       1    version = 2
//    5       1    key_id length n
//    6       n    key_id (UTF-8)
//    6+n    16    salt
//   22+n    12    nonce
//   34+n   rest   ciphertext + 16-byte GCM tag (WebCrypto's layout too)
//
// Release keys are kept in this browser's storage as {key_id: passphrase},
// the same mapping the desktop keeps in ~/.mds_viewer_keys. Storage never
// leaves the browser (a cookie went to the server with every page request).
// "Remember" keeps them in localStorage for 90 days from the last save;
// otherwise they live in sessionStorage and go when the tab is closed.

const KDF_ITERATIONS = 200000;
const STORE = "mds_keys";
const REMEMBER_MS = 90 * 24 * 3600 * 1000;
const LEGACY_COOKIE = "mds_keys";       // where the first release kept them

export function parseHeader(u8) {
  if (u8.length < 50 || u8[0] !== 0x4d || u8[1] !== 0x44 || u8[2] !== 0x53 || u8[3] !== 0x45)
    throw new Error("not an MDSE payload");
  if (u8[4] !== 2) throw new Error(`unsupported payload version ${u8[4]}`);
  const n = u8[5];
  return {
    keyId: new TextDecoder().decode(u8.subarray(6, 6 + n)),
    salt: u8.slice(6 + n, 22 + n),
    nonce: u8.slice(22 + n, 34 + n),
    body: u8.subarray(34 + n),
  };
}

async function deriveKey(passphrase, salt, use) {
  const base = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations: KDF_ITERATIONS },
    base, { name: "AES-GCM", length: 256 }, false, [use]);
}

// Throws (OperationError) when the passphrase is wrong: the GCM tag fails.
export async function decryptPayload(u8, passphrase) {
  const { salt, nonce, body } = parseHeader(u8);
  const key = await deriveKey(passphrase, salt, "decrypt");
  return new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: nonce }, key, body));
}

// db_crypto.encrypt_bytes: a fresh salt and nonce, the same header.
export async function encryptPayload(u8, keyId, passphrase) {
  const kid = new TextEncoder().encode(keyId);
  if (kid.length > 255) throw new Error("key_id too long (max 255 bytes UTF-8)");
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(passphrase, salt, "encrypt");
  const body = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, key, u8));
  const out = new Uint8Array(34 + kid.length + body.length);
  out.set([0x4d, 0x44, 0x53, 0x45, 2, kid.length]);
  out.set(kid, 6);
  out.set(salt, 6 + kid.length);
  out.set(nonce, 22 + kid.length);
  out.set(body, 34 + kid.length);
  return out;
}

export async function sha256Hex(u8) {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", u8));
  return Array.from(d, (b) => b.toString(16).padStart(2, "0")).join("");
}

function storage(kind) {
  try {
    return kind === "local" ? localStorage : sessionStorage;
  } catch {
    return null;                            // storage disabled: keys last as long as the page
  }
}

const isKeys = (v) => v && typeof v === "object" && !Array.isArray(v)
  && Object.entries(v).every(([k, p]) => /^[A-Za-z0-9_.\-]+$/.test(k) && typeof p === "string");

function readFrom(kind) {
  const s = storage(kind);
  let doc = null;
  try {
    doc = JSON.parse(s?.getItem(STORE) || "null");
  } catch {
    doc = null;
  }
  if (!doc || !isKeys(doc.keys)) return {};
  if (kind === "local" && !(Date.now() - Number(doc.saved) < REMEMBER_MS)) {
    try { s.removeItem(STORE); } catch { /* nothing to clear */ }
    return {};
  }
  return doc.keys;
}

function writeTo(kind, keys) {
  try {
    storage(kind).setItem(STORE, JSON.stringify({ saved: Date.now(), keys }));
    return true;
  } catch {
    return false;
  }
}

// The cookie the first release used was scoped to the viewer's folder.
function cookiePath() {
  return new URL(".", location.href).pathname;
}

function dropCookie() {
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${LEGACY_COOKIE}=; Path=${cookiePath()}; Max-Age=0; SameSite=Strict${secure}`;
}

// Move keys out of that cookie, and delete it so it stops travelling.
function migrateCookie() {
  const m = document.cookie.match(new RegExp(`(?:^|;\\s*)${LEGACY_COOKIE}=([^;]*)`));
  if (!m) return;
  try {
    const ks = JSON.parse(decodeURIComponent(m[1]));
    if (isKeys(ks) && Object.keys(ks).length) writeTo("local", { ...readFrom("local"), ...ks });
  } catch { /* unreadable: just drop it */ }
  dropCookie();
}

export function readKeystore() {
  migrateCookie();
  return { ...readFrom("local"), ...readFrom("session") };
}

// remember=true: localStorage, 90 days. Otherwise this tab only; keys
// remembered earlier stay remembered.
export function writeKeystore(ks, remember) {
  if (remember && writeTo("local", ks)) {
    try { storage("session")?.removeItem(STORE); } catch { /* nothing to clear */ }
  } else {
    writeTo("session", ks);
  }
}

export function clearKeystore() {
  for (const kind of ["local", "session"]) {
    try { storage(kind)?.removeItem(STORE); } catch { /* nothing to clear */ }
  }
  dropCookie();
}

// key_dialog.parse_key_line: the first "<key_id> = <passphrase>" line,
// skipping blank lines, '#' comments and any prose around it.
const KEY_LINE = /^\s*([A-Za-z0-9_.\-]+)\s*=\s*(\S.*?)\s*$/;

export function parseKeyLine(text) {
  for (const raw of String(text || "").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const m = KEY_LINE.exec(line);
    if (m) return { keyId: m[1], passphrase: m[2] };
  }
  return null;
}
