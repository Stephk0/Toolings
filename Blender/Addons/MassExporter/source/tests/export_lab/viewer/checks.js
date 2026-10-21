// Export Lab checks: load an exported file with three.js, describe it, and compare it with the
// oracle's expectation. three.js and its loaders are passed in, so this runs in the page and in
// Node alike.

// Distance unit of node positions per format, as three's loaders return them (metres for all
// three with the exporter's default "FBX Units Scale").
export const UNIT = { glb: 1, obj: 1, fbx: 1 };

// The file's own top nodes: under the conversion group of the Unity import model, else the
// loader's identity group
function fileRoots(root) {
  return root.userData.unity ? root.children[0].children : root.children;
}

// opts.fbx: "unity" (unity-fbx.js, Unity's model importer) or "three" (stock FBXLoader);
// opts.bakeAxis: Unity's Bake Axis Conversion
export function makeInspector({ GLTFLoader, FBXLoader, OBJLoader, loadUnityFBX }) {
  const gltf = new GLTFLoader();
  const fbx = new FBXLoader();
  const obj = new OBJLoader();

  async function load(buffer, ext, opts = {}) {
    if (ext === "glb") return (await gltf.parseAsync(buffer, "")).scene;
    if (ext === "fbx" && opts.fbx === "unity" && loadUnityFBX) return loadUnityFBX(buffer, { bakeAxisConversion: !!opts.bakeAxis });
    if (ext === "fbx") return fbx.parse(buffer, "");
    if (ext === "obj") return obj.parse(new TextDecoder().decode(buffer));
    throw new Error(`no loader for .${ext}`);
  }

  // World-space box [min, max] of a named node's own geometry (child parts excluded), or null
  function boxOf(root, name, parts) {
    const node = root.getObjectByName(name);
    if (!node) return null;
    let lo = null, hi = null;
    node.updateWorldMatrix(true, true);
    const own = [];
    const walk = (o) => {
      if (o !== node && parts.has(o.name)) return;   // another part, measured on its own
      if (o.isMesh) own.push(o);
      o.children.forEach(walk);
    };
    walk(node);
    own.forEach((o) => {
      const pos = o.geometry.attributes.position;
      const e = o.matrixWorld.elements;
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
        const w = [e[0] * x + e[4] * y + e[8] * z + e[12], e[1] * x + e[5] * y + e[9] * z + e[13], e[2] * x + e[6] * y + e[10] * z + e[14]];
        if (!lo) { lo = [...w]; hi = [...w]; continue; }
        for (let k = 0; k < 3; k++) { if (w[k] < lo[k]) lo[k] = w[k]; if (w[k] > hi[k]) hi[k] = w[k]; }
      }
    });
    if (lo && root.userData.unity?.bakeAxisConversion) {
      // Bake Axis Conversion turns the whole file half a turn round Y: measure it unturned
      [lo, hi] = [[-hi[0], lo[1], -hi[2]], [-lo[0], hi[1], -lo[2]]];
    }
    return lo ? [lo, hi] : null;
  }

  function describe(root) {
    root.updateMatrixWorld(true);
    const names = new Set();
    const meshes = [];
    const materials = new Set();
    let tris = 0;
    root.traverse((o) => {
      if (o !== root && o.name) names.add(o.name);
      if (!o.isMesh) return;
      const g = o.geometry;
      const t = (g.index ? g.index.count : g.attributes.position.count) / 3;
      tris += t;
      const mats = (Array.isArray(o.material) ? o.material : [o.material]).map((m) => m?.name || "");
      // FBXLoader names its stand-in for "no material" __DEFAULT; that is not a file material
      mats.filter((m) => m && m !== "__DEFAULT").forEach((m) => materials.add(m));
      meshes.push({ name: o.name, tris: t, materials: mats });
    });
    const roots = fileRoots(root).map((c) => {
      const e = c.matrixWorld.elements;
      return { name: c.name, dist: Math.hypot(e[12], e[13], e[14]) };
    });
    return { names: [...names], meshes, tris, materials: [...materials].sort(), roots, box: (n, parts) => boxOf(root, n, parts) };
  }

  return { load, describe };
}

const sameSet = (a, b) => a.length === b.length && a.every((x) => b.includes(x));

// Per-file checks: R-NODES, R-TRIS, R-CENTER, R-MATERIALS
export function compareFile(exp, info, ext, sceneMeshNames) {
  const out = [];
  const missing = exp.nodeNames.filter((n) => !info.names.includes(n));
  const extra = info.names.filter((n) => sceneMeshNames.has(n) && !exp.nodeNames.includes(n));
  out.push({
    rule: "R-NODES", ok: !missing.length && !extra.length,
    expected: exp.nodeNames.join(", "),
    found: missing.length || extra.length
      ? [missing.length && `missing ${missing.join(", ")}`, extra.length && `unexpected ${extra.join(", ")}`].filter(Boolean).join("; ")
      : "all present",
  });
  out.push({ rule: "R-TRIS", ok: info.tris === exp.tris, expected: exp.tris, found: info.tris });
  if (exp.roots) {
    const unit = UNIT[ext] ?? 1;
    const bad = [];
    for (const [name, d] of Object.entries(exp.roots)) {
      const r = info.roots.find((x) => x.name === name);
      if (!r) continue;   // a missing node is R-NODES' failure, not this one's
      const want = d * unit;
      if (Math.abs(r.dist - want) > 1e-3 * unit + 0.01 * want) bad.push(`${name} ${(r.dist / unit).toFixed(3)} m, want ${d.toFixed(3)} m`);
    }
    out.push({
      rule: "R-CENTER", ok: !bad.length,
      expected: Object.values(exp.roots).every((d) => d === 0) ? "roots at origin" : "roots keep their distance",
      found: bad.length ? bad.join("; ") : "as expected",
    });
  }
  if (exp.parts) {
    const unit = UNIT[ext] ?? 1;
    const centre = (b) => [0, 1, 2].map((k) => (b[0][k] + b[1][k]) / 2);
    const union = (bs) => [[0, 1, 2].map((k) => Math.min(...bs.map((b) => b[0][k]))), [0, 1, 2].map((k) => Math.max(...bs.map((b) => b[1][k])))];
    const names = Object.keys(exp.parts).filter((n) => info.names.includes(n));
    const partSet = new Set(Object.keys(exp.parts));
    const found = Object.fromEntries(names.map((n) => [n, info.box(n, partSet)]).filter(([, b]) => b));
    const fk = Object.keys(found);
    if (fk.length > 1) {
      const ec = centre(union(fk.map((n) => exp.parts[n])));
      const fc = centre(union(fk.map((n) => found[n].map((p) => p.map((v) => v / unit)))));
      const size = Math.max(...[0, 1, 2].map((k) => union(fk.map((n) => exp.parts[n]))[1][k] - union(fk.map((n) => exp.parts[n]))[0][k]));
      const bad = [];
      for (const n of fk) {
        const e = centre(exp.parts[n]).map((v, k) => v - ec[k]);
        const f = centre(found[n].map((p) => p.map((v) => v / unit))).map((v, k) => v - fc[k]);
        const d = Math.hypot(e[0] - f[0], e[1] - f[1], e[2] - f[2]);
        if (d > 0.01 + 0.02 * size) bad.push(`${n} off by ${d.toFixed(2)} m`);
      }
      out.push({ rule: "R-PLACEMENT", ok: !bad.length, expected: "parts where they sit in Blender", found: bad.length ? bad.join("; ") : "as expected" });
    }
  }
  out.push({
    rule: "R-MATERIALS", ok: sameSet(exp.materials, info.materials),
    expected: exp.materials.join(", ") || "(none)", found: info.materials.join(", ") || "(none)",
  });
  return out;
}

// Case-level checks: R-RUN, R-SOURCE, R-FOLDER (with R-PRIORITY / mode rules as the cause), R-RELATIVE
export function compareCase(c, exp) {
  const out = [];
  const errors = (c.log || []).filter((l) => /export (error|failed)|Traceback|Error/i.test(l));
  out.push({
    rule: "R-RUN", ok: !c.error && (c.result || []).includes("FINISHED") && !errors.length,
    expected: "FINISHED, no export errors",
    found: c.error || (errors[0] ?? (c.result || []).join(", ")),
  });
  const leaked = c.left_selected || [];
  out.push({
    rule: "R-SELECTION", ok: !leaked.length, expected: "selection restored",
    found: leaked.length ? `left selected: ${leaked.join(", ")}` : "restored",
  });
  out.push({
    rule: "R-SOURCE", ok: c.source_changed_count === 0, expected: "scene unchanged",
    found: c.source_changed_count ? `${c.source_changed_count} change(s): ${c.source_changed[0]}` : "unchanged",
  });
  if (exp.relative) {
    const hit = c.relative_written_to || [];
    out.push({
      rule: "R-RELATIVE", ok: hit.length > 0, expected: "files next to the .blend",
      found: hit.length ? hit.join(", ") : "nothing written (path not resolved)",
    });
    return out;
  }
  const want = exp.files.map((f) => f.path);
  const got = c.files.map((f) => f.path);
  const missing = want.filter((p) => !got.includes(p));
  const extra = got.filter((p) => !want.includes(p));
  const rules = [...new Set(exp.files.map((f) => f.rule.split(" ")[0]))];
  out.push({
    rule: "R-FOLDER", cause: rules.join(", ") || "R-HIDDEN-ROW", ok: !missing.length && !extra.length,
    expected: `${want.length} file(s)`,
    found: missing.length || extra.length
      ? [missing.length && `missing ${missing.join(", ")}`, extra.length && `unexpected ${extra.join(", ")}`].filter(Boolean).join("; ")
      : `${got.length} file(s), as expected`,
    missing, extra,
  });
  return out;
}

// R-UNITY: the Unity import model against what Unity really imported (unity.json). Each Unity
// node with a mesh is matched by name - a file with a single top node has its mesh on the root
// GameObject, named after the file - and its world bounds must agree within 1 cm. Unity is
// left-handed, so its x is mirrored into the page's right-handed space.
export function compareUnity(root, nodes, fileId, unityVersion) {
  root.updateMatrixWorld(true);
  const meshes = [];
  root.traverse((o) => { if (o.isMesh) meshes.push(o); });
  const bad = [];
  let n = 0;
  for (const u of nodes.filter((x) => x.box)) {
    let mesh = meshes.find((o) => o.name === u.name || o.parent?.name === u.name);
    if (!mesh && u.name === fileId && meshes.length === 1) mesh = meshes[0];
    n++;
    if (!mesh) { bad.push(`${u.name} not in the model`); continue; }
    // Like Unity's dump: the mesh's local bounding box, its 8 corners taken to world space
    mesh.geometry.computeBoundingBox();
    const bb = mesh.geometry.boundingBox;
    const e = mesh.matrixWorld.elements;
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < 8; i++) {
      const x = i & 1 ? bb.max.x : bb.min.x, y = i & 2 ? bb.max.y : bb.min.y, z = i & 4 ? bb.max.z : bb.min.z;
      const w = [e[0] * x + e[4] * y + e[8] * z + e[12], e[1] * x + e[5] * y + e[9] * z + e[13], e[2] * x + e[6] * y + e[10] * z + e[14]];
      for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], w[k]); hi[k] = Math.max(hi[k], w[k]); }
    }
    const ulo = [-u.box[1][0], u.box[0][1], u.box[0][2]], uhi = [-u.box[0][0], u.box[1][1], u.box[1][2]];
    const d = Math.max(...[0, 1, 2].map((k) => Math.max(Math.abs(lo[k] - ulo[k]), Math.abs(hi[k] - uhi[k]))));
    if (d > 0.01) bad.push(`${u.name} off by ${d.toFixed(3)} m`);
  }
  return {
    rule: "R-UNITY", ok: !bad.length, expected: `matches Unity ${unityVersion} (${n} mesh${n === 1 ? "" : "es"})`,
    found: bad.length ? bad.join("; ") : "within 1 cm",
  };
}
