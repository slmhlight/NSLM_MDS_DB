// catalog_store: the machine and powder catalogs. Each is the newest
// <kind>_<date>.enc this browser holds a key for -- a ZIP of <kind>.json
// plus, for machines, the product images. A catalog is fetched the first
// time its window opens (the machine payload is ~10 MB) and kept for the
// session; the images are unpacked one by one as rows come into view.
import { decryptPayload } from "./crypto.js";
import { parsePyJson } from "./py.js";
import { readZip, extract } from "./zip.js";

const MIME = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", gif: "image/gif" };

// fetchBytes(path, v, onProgress) as in app.js; manifest() and keystore()
// return the current ones.
export function createCatalogs({ fetchBytes, manifest, keystore }) {
  let cache = new Map();

  async function open(kind, onProgress) {
    const rows = manifest().payloads.filter((p) => p.kind === kind);       // newest first
    if (!rows.length) throw new Error(`no ${kind}_*.enc in data/archive`);
    const ks = keystore();
    if (!Object.keys(ks).length) throw new Error("no keystore — cannot open the catalog");
    for (const p of rows) {
      const pw = ks[p.key_id];
      if (pw === undefined) continue;
      // A download that fails is not a key problem: it ends the attempt.
      const bytes = await fetchBytes(`data/archive/${p.file}`, p.v,
                                     onProgress && ((got) => onProgress(got, p.size)));
      let plain;
      try {
        plain = await decryptPayload(bytes, pw);
      } catch (e) {
        console.warn(`catalog: decrypt failed for ${p.file}:`, e);
        continue;
      }
      try {
        const zip = readZip(plain);
        const member = zip.get(`${kind}.json`);
        if (!member) throw new Error(`no ${kind}.json inside`);
        const doc = parsePyJson(new TextDecoder().decode(await extract(plain, member)));
        return { doc, info: `${p.file} (key_id=${p.key_id})`, images: imageStore(plain, zip) };
      } catch (e) {
        console.warn(`catalog: ${p.file} is not a valid payload:`, e);
      }
    }
    const have = [...new Set(rows.map((p) => p.file))].sort();
    throw new Error(`no decryptable ${kind} payload among [${have.map((f) => `'${f}'`).join(", ")}]`);
  }

  return {
    // -> Promise<{doc, info, images}>; rejects with the reason it cannot open.
    load(kind, onProgress) {
      if (!cache.has(kind)) {
        const p = open(kind, onProgress);
        p.catch(() => cache.delete(kind));
        cache.set(kind, p);
      }
      return cache.get(kind);
    },
    // A new key may open a newer catalog: start over.
    reset() {
      for (const p of cache.values()) p.then((c) => c.images.revoke(), () => {});
      cache = new Map();
    },
  };
}

function imageStore(plain, zip) {
  const urls = new Map();
  return {
    // catalog_store.image_bytes: "machine_images/x.jpg" and the older
    // "data/machine_images/x.jpg" both resolve. -> Promise<object URL | null>
    url(relPath) {
      if (!relPath || typeof relPath !== "string") return Promise.resolve(null);
      const rel = relPath.replace(/\\/g, "/").replace(/^[./]+/, "");
      const name = [rel, rel.startsWith("data/") ? rel.slice(5) : `data/${rel}`].find((n) => zip.has(n));
      if (!name) return Promise.resolve(null);
      if (!urls.has(name)) {
        const type = MIME[name.split(".").pop().toLowerCase()] || "application/octet-stream";
        urls.set(name, extract(plain, zip.get(name)).then((b) => URL.createObjectURL(new Blob([b], { type }))));
      }
      return urls.get(name);
    },
    revoke() {
      for (const p of urls.values()) p.then((u) => URL.revokeObjectURL(u), () => {});
      urls.clear();
    },
  };
}
