// Minimal ZIP reader for the machines / powders payloads, which
// _pack_data_enc.py writes with Python's zipfile (DEFLATE, no ZIP64).
// Inflating uses the browser's own DecompressionStream, so no library.

const EOCD = 0x06054b50, CDH = 0x02014b50, LFH = 0x04034b50;

// -> Map(name -> {method, offset, csize, size})
export function readZip(u8) {
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  let eocd = -1;
  for (let i = u8.length - 22; i >= Math.max(0, u8.length - 22 - 65535); i--) {
    if (dv.getUint32(i, true) === EOCD) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error("ZIP end record not found");
  const count = dv.getUint16(eocd + 10, true);
  let p = dv.getUint32(eocd + 16, true);
  const entries = new Map();
  const utf8 = new TextDecoder();
  for (let k = 0; k < count; k++) {
    if (dv.getUint32(p, true) !== CDH) throw new Error("bad ZIP central directory");
    const method = dv.getUint16(p + 10, true);
    const csize = dv.getUint32(p + 20, true);
    const size = dv.getUint32(p + 24, true);
    const nlen = dv.getUint16(p + 28, true);
    const xlen = dv.getUint16(p + 30, true);
    const clen = dv.getUint16(p + 32, true);
    const lho = dv.getUint32(p + 42, true);
    const name = utf8.decode(u8.subarray(p + 46, p + 46 + nlen));
    if (dv.getUint32(lho, true) !== LFH) throw new Error(`bad local header for ${name}`);
    const offset = lho + 30 + dv.getUint16(lho + 26, true) + dv.getUint16(lho + 28, true);
    entries.set(name, { method, offset, csize, size });
    p += 46 + nlen + xlen + clen;
  }
  return entries;
}

export async function extract(u8, entry) {
  const data = u8.subarray(entry.offset, entry.offset + entry.csize);
  if (entry.method === 0) return data;
  if (entry.method !== 8) throw new Error(`unsupported ZIP method ${entry.method}`);
  const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
  const out = new Uint8Array(await new Response(stream).arrayBuffer());
  if (out.length !== entry.size) throw new Error("ZIP member size mismatch");
  return out;
}
