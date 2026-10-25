// Reference PDFs, published encrypted and opened with the release key.
//
// _pack_refs_enc.py turns data/refs/<Material_Name>/*.pdf (the folder the
// desktop's "Attach local PDF" button copies into) into
//
//   data/archive/refs/<random id>.enc     one MDSE payload per PDF
//   data/archive/refs/index_<date>.enc    {"refs": {material: [entry]}}
//
// The ids mean nothing and only the encrypted index ties a file to a
// material, so the repo listing says nothing about what the files are.
// An entry is {id, name, size, sha256 (of the PDF), v (of the .enc)}.
import { decryptPayload, parseHeader, sha256Hex } from "./crypto.js";

export class RefStore {
  constructor(fetchBytes) {
    this.fetchBytes = fetchBytes;
    this.index = null;
    this.opened = new Map();          // id -> object URL, for this page's life
  }

  // The newest index this browser holds a key for; false if there is none.
  async load(manifest, keystore) {
    this.index = null;
    for (const p of manifest.payloads.filter((r) => r.kind === "refs")) {
      const pw = keystore[p.key_id];
      if (pw === undefined) continue;
      try {
        const plain = await decryptPayload(await this.fetchBytes(`data/archive/${p.file}`, p.v), pw);
        const doc = JSON.parse(new TextDecoder().decode(plain));
        this.index = doc && typeof doc.refs === "object" ? doc.refs : {};
        return true;
      } catch (e) {
        console.warn(`reference index ${p.file} did not open:`, e);
      }
    }
    return false;
  }

  list(material) {
    const rows = this.index && this.index[material];
    return Array.isArray(rows) ? rows : [];
  }

  url(entry) {
    return `data/archive/refs/${entry.id}.enc`;
  }

  // Whether the published file is there, without downloading it.
  async exists(entry) {
    try {
      const r = await fetch(new URL(this.url(entry), document.baseURI),
                            { method: "HEAD", credentials: "omit", cache: "no-cache" });
      return r.ok;
    } catch {
      return false;
    }
  }

  // -> object URL of the decrypted PDF. Throws with a readable message.
  async open(entry, keystore) {
    const hit = this.opened.get(entry.id);
    if (hit) return hit;
    const blob = await this.fetchBytes(this.url(entry), entry.v);
    const { keyId } = parseHeader(blob);
    const pw = keystore[keyId];
    if (pw === undefined) throw new Error(`This file needs the release key ${keyId}.`);
    let plain;
    try {
      plain = await decryptPayload(blob, pw);
    } catch {
      throw new Error(`The saved key ${keyId} does not open this file.`);
    }
    if (entry.sha256 && (await sha256Hex(plain)) !== entry.sha256)
      throw new Error("The file does not match the reference index.");
    const url = URL.createObjectURL(new Blob([plain], { type: "application/pdf" }));
    this.opened.set(entry.id, url);
    return url;
  }
}
