// Bundles `dist-portable/` into a versioned, share-ready zip.
// Usage: `npm run dist:zip` (after `npm run build:portable`).
//
// Zero-dependency: uses Node's built-in zlib + a small stored-zip writer.
// The output path is printed at the end.

import { readFileSync, writeFileSync, statSync, readdirSync, existsSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { deflateRawSync, crc32 } from 'node:zlib';

const here = fileURLToPath(new URL('.', import.meta.url));
const root = resolve(here, '..');
const distDir = join(root, 'dist-portable');
const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
const stamp = new Date().toISOString().slice(0, 10);
const outZip = join(root, `stephko-toolings-docs_v${pkg.version}_${stamp}.zip`);

if (!existsSync(distDir)) {
  console.error(`✗ ${distDir} does not exist. Run \`npm run build:portable\` first.`);
  process.exit(1);
}

function walk(dir, base = dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) walk(full, base, out);
    else out.push({ full, rel: relative(base, full).split('\\').join('/') });
  }
  return out;
}

function u16(n) { const b = Buffer.alloc(2); b.writeUInt16LE(n, 0); return b; }
function u32(n) { const b = Buffer.alloc(4); b.writeUInt32LE(n >>> 0, 0); return b; }

function buildZip(files) {
  const chunks = [];
  const central = [];
  let offset = 0;

  for (const f of files) {
    const data = readFileSync(f.full);
    const compressed = deflateRawSync(data);
    const useCompression = compressed.length < data.length;
    const finalData = useCompression ? compressed : data;
    const method = useCompression ? 8 : 0; // 8 = deflate, 0 = store
    const name = Buffer.from(f.rel, 'utf8');
    const crc = crc32(data);
    const mtime = 0;
    const mdate = 0;

    // Local file header
    const local = Buffer.concat([
      u32(0x04034b50),
      u16(20), u16(0), u16(method),
      u16(mtime), u16(mdate),
      u32(crc), u32(finalData.length), u32(data.length),
      u16(name.length), u16(0),
      name, finalData,
    ]);
    chunks.push(local);

    // Central directory entry
    central.push(Buffer.concat([
      u32(0x02014b50),
      u16(20), u16(20), u16(0), u16(method),
      u16(mtime), u16(mdate),
      u32(crc), u32(finalData.length), u32(data.length),
      u16(name.length), u16(0), u16(0), u16(0), u16(0),
      u32(0), u32(offset),
      name,
    ]));
    offset += local.length;
  }

  const centralBuf = Buffer.concat(central);
  const eocd = Buffer.concat([
    u32(0x06054b50),
    u16(0), u16(0),
    u16(files.length), u16(files.length),
    u32(centralBuf.length), u32(offset),
    u16(0),
  ]);

  return Buffer.concat([...chunks, centralBuf, eocd]);
}

const files = walk(distDir);
console.log(`Packing ${files.length} files from dist-portable/ …`);
const zipBuf = buildZip(files);
writeFileSync(outZip, zipBuf);

const sizeKB = (statSync(outZip).size / 1024).toFixed(1);
console.log(`\n✓ Wrote ${outZip}`);
console.log(`  ${sizeKB} KB · share this zip; recipient unzips and runs \`npx serve\` in the unzipped folder (or opens it via any static-site host).`);
