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
// Release keys live in one cookie, as {key_id: passphrase}, the same
// mapping the desktop keeps in ~/.mds_viewer_keys.

const KDF_ITERATIONS = 200000;
const COOKIE = "mds_keys";
const REMEMBER_SECONDS = 90 * 24 * 3600;

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

// Throws (OperationError) when the passphrase is wrong: the GCM tag fails.
export async function decryptPayload(u8, passphrase) {
  const { salt, nonce, body } = parseHeader(u8);
  const base = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations: KDF_ITERATIONS },
    base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  return new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: nonce }, key, body));
}

export async function sha256Hex(u8) {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", u8));
  return Array.from(d, (b) => b.toString(16).padStart(2, "0")).join("");
}

// The cookie is scoped to the viewer's own folder (/<repo>/ on Pages).
function cookiePath() {
  return new URL(".", location.href).pathname;
}

export function readKeystore() {
  const m = document.cookie.match(new RegExp(`(?:^|;\\s*)${COOKIE}=([^;]*)`));
  if (!m) return {};
  try {
    const ks = JSON.parse(decodeURIComponent(m[1]));
    return ks && typeof ks === "object" && !Array.isArray(ks) ? ks : {};
  } catch {
    return {};
  }
}

// remember=false gives a session cookie: gone when the browser closes.
export function writeKeystore(ks, remember) {
  const attrs = [`Path=${cookiePath()}`, "SameSite=Strict"];
  if (location.protocol === "https:") attrs.push("Secure");
  if (remember) attrs.push(`Max-Age=${REMEMBER_SECONDS}`);
  document.cookie = `${COOKIE}=${encodeURIComponent(JSON.stringify(ks))}; ${attrs.join("; ")}`;
}

export function clearKeystore() {
  document.cookie = `${COOKIE}=; Path=${cookiePath()}; Max-Age=0; SameSite=Strict`;
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
