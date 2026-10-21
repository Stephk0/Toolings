// Export Lab oracle: the expected result of a case, written from SPEC.md section 3.
// Pure functions over scene.json and one manifest case. No three.js, no DOM, no addon code.

export const FLAGS = ["whole", "suffix", "subcoll", "empties", "join", "merge"];
export const FLAG_LETTERS = { whole: "W", suffix: "S", subcoll: "C", empties: "E", join: "J", merge: "M" };
export const EXT = { FBX: "fbx", OBJ: "obj", GLTF: "glb" };
export const SUFFIXES = ["_COL", "_LOD1"];
const SEPARATORS = "_-. ";

export const MODES = {
  whole: "Whole collection",
  suffix: "Group by suffix",
  subcoll: "Sub-collections",
  subcoll_join: "Sub-collections + join",
  empties: "Parent empties",
  join: "Join empties",
  merge: "Merge",
  individual: "Individual",
};

// Settings a case runs with: exporter defaults, the lab's baseline, then the case's own flips.
export function settingsOf(c) {
  const g = {
    apply_modifiers: true, apply_only_visible_modifiers: true, apply_transforms: false,
    add_m_prefix: false, material_mode: "KEEP",
    export_hidden_collections: true, ...c.global,
  };
  const row = {
    move_to_center: true, apply_modifiers_before_join: false,
    apply_only_visible: false, single_fbx_custom_name: "", ...c.row,
  };
  const suffixesOn = c.extra !== "suffix_off";
  return { g, row, flags: c.flags, suffixesOn, format: c.format, ext: EXT[c.format] };
}

// R-PRIORITY
export function effectiveMode(flags, suffixesOn = true) {
  if (flags.whole) return "whole";
  if (flags.suffix && suffixesOn) return "suffix";
  if (flags.subcoll) return flags.empties && flags.join ? "subcoll_join" : "subcoll";
  if (flags.empties) return flags.join ? "join" : "empties";
  return flags.merge ? "merge" : "individual";
}

function baseName(name, suffixesOn) {
  if (!suffixesOn) return name;
  const lower = name.toLowerCase();
  for (const s of [...SUFFIXES].sort((a, b) => b.length - a.length)) {
    if (lower.endsWith(s.toLowerCase())) {
      let base = name.slice(0, -s.length);
      if (base && SEPARATORS.includes(base[base.length - 1])) base = base.slice(0, -1);
      return base;
    }
  }
  return name;
}

class SceneModel {
  constructor(scene, s) {
    this.scene = scene;
    this.s = s;
    this.obj = scene.objects;
    this.colls = {};
    const walk = (c) => { this.colls[c.name] = c; c.children.forEach(walk); };
    walk(scene.root);
    this.children = {};
    for (const [name, o] of Object.entries(this.obj)) {
      if (o.parent) (this.children[o.parent] ??= []).push(name);
    }
  }

  // R-HIDDEN-SUB: with the toggle off, hidden sub-collections are left out
  skipHidden(coll) {
    return !this.s.g.export_hidden_collections && coll.hidden;
  }

  meshes(coll, isRow = false) {
    const out = [];
    const seen = new Set();
    const walk = (c, root) => {
      if (this.skipHidden(c)) return;
      for (const n of c.objects) {
        if (this.obj[n].type === "MESH" && !seen.has(n)) { seen.add(n); out.push(n); }
      }
      c.children.forEach((ch) => walk(ch, false));
    };
    walk(coll, isRow);
    return out;
  }

  directMeshes(coll) {
    return coll.objects.filter((n) => this.obj[n].type === "MESH");
  }

  // Nearest-empty membership over every empty in coll's tree, walk order kept.
  emptyGroups(coll, directOnly = false) {
    const empties = [];
    const seen = new Set();
    const walk = (c) => {
      if (this.skipHidden(c)) return;
      for (const n of c.objects) {
        if (this.obj[n].type === "EMPTY" && !seen.has(n)) { seen.add(n); empties.push(n); }
      }
      c.children.forEach(walk);
    };
    walk(coll);
    const groups = [];
    for (const e of empties) {
      const members = [];
      const stack = [...(this.children[e] || [])];
      while (stack.length) {
        const d = stack.shift();
        stack.push(...(this.children[d] || []));
        if (this.obj[d].type !== "MESH") continue;
        let owner = this.obj[d].parent;
        while (owner && !seen.has(owner)) owner = this.obj[owner].parent;
        if (owner === e) members.push(d);
      }
      if (members.length && (!directOnly || coll.objects.includes(e))) groups.push([e, members]);
    }
    return groups;
  }

  tris(name, bake = this.s.g.apply_modifiers, onlyVisible = this.s.g.apply_only_visible_modifiers) {
    const t = this.obj[name].tris;
    return bake ? (onlyVisible ? t.visible : t.all) : t.raw;
  }

  // Which evaluated version of a mesh lands in the file: raw, visible modifiers, or all
  geoMode(bake = this.s.g.apply_modifiers, onlyVisible = this.s.g.apply_only_visible_modifiers) {
    return bake ? (onlyVisible ? "visible" : "all") : "raw";
  }

  // World-space box of a mesh converted to the files' Y-up axes: Blender (x, y, z) -> (x, z, -y)
  box(name) {
    const [lo, hi] = this.obj[name].bbox[this.geoMode()];
    return [[lo[0], lo[2], -hi[1]], [hi[0], hi[2], -lo[1]]];
  }

  materials(name) {
    const g = this.s.g;
    let mats = this.obj[name].materials.filter(Boolean);
    // R-MATERIALS: Fill Empty fills per part, so a joined mesh keeps both
    if (g.material_mode === "OVERWRITE") mats = ["M_Override"];
    else if (g.material_mode === "FILL" && mats.length === 0) mats = ["M_Override"];
    if (g.add_m_prefix) mats = mats.map((m) => (m.startsWith("M_") ? m : "M_" + m));
    return mats;
  }

  dist(name) {
    const w = this.obj[name].world;
    return Math.hypot(w[0], w[1], w[2]);
  }

  distBetween(a, b) {
    const p = this.obj[a].world, q = this.obj[b].world;
    return Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
  }

  // Roots of an export set: members whose parent is outside the set.
  roots(names) {
    const set = new Set(names);
    return names.filter((n) => !this.obj[n].parent || !set.has(this.obj[n].parent));
  }
}

// One expected file. `meshes` are the scene meshes it carries; `joined` makes it a single node.
function file(m, folder, name, meshes, rule, opts = {}) {
  const s = m.s;
  const joined = opts.joined || null;
  const tris = joined
    ? meshes.reduce((a, n) => a + m.tris(n, joined.bake, joined.onlyVisible), 0)
    : meshes.reduce((a, n) => a + m.tris(n), 0);
  const materials = [...new Set(meshes.flatMap((n) => m.materials(n)))].sort();
  // R-CENTER: Move to Center puts each pivot at the origin. A root's pivot is its parent
  // when that parent is an empty outside the export set (the asset's origin), else itself.
  const set = new Set(opts.exportSet || meshes);
  const rootOf = (n) => { while (m.obj[n].parent && set.has(m.obj[n].parent)) n = m.obj[n].parent; return n; };
  const pivotOf = (root) => {
    const p = m.obj[root]?.parent;
    return p && !set.has(p) && m.obj[p].type === "EMPTY" ? p : root;
  };
  let roots = null;
  if (opts.center === "origin") {
    roots = Object.fromEntries((opts.rootNames || m.roots(meshes)).map((n) => [n, opts.joined || !m.obj[n] ? 0 : m.distBetween(n, pivotOf(n))]));
  } else if (opts.center === "keep") {
    roots = Object.fromEntries((opts.rootNames || m.roots(meshes)).map((n) => [n, opts.distOf ? opts.distOf(n) : m.dist(n)]));
  }
  if (roots && s.g.apply_transforms) for (const k in roots) roots[k] = 0;
  // R-PLACEMENT: each part's box centre relative to the centre of all parts (translation-free).
  // Several pivots stack at the origin, so each part moves by its pivot's world position.
  const shifted = (n) => {
    const b = m.box(n);
    if (opts.center !== "origin") return b;
    const w = m.obj[pivotOf(rootOf(n))].world;
    const t = [w[0], w[2], -w[1]];
    return b.map((p) => p.map((v, k) => v - t[k]));
  };
  const parts = joined || meshes.length < 2 ? null : Object.fromEntries(meshes.map((n) => [n, shifted(n)]));
  return {
    path: `${folder}/${name}.${s.ext}`, folder, name, rule, parts,
    meshes: joined ? [] : meshes, nodeNames: joined ? [name] : meshes,
    joinedFrom: joined ? meshes : null, tris, materials, roots,
  };
}

function centerMode(s) {
  return s.row.move_to_center ? "origin" : "keep";
}

function exportObjectsAsSingle(m, folder, name, meshes, rule, extraRoots) {
  return file(m, folder, name, meshes, rule, { center: centerMode(m.s), rootNames: extraRoots });
}

function individual(m, folder, meshes, rule = "R-INDIVIDUAL") {
  return meshes.map((n) => exportObjectsAsSingle(m, folder, n, [n], rule));
}

function joinAll(m, folder, coll, rule = "R-JOIN") {
  const s = m.s;
  const groups = m.emptyGroups(coll);
  if (!groups.length) {
    const meshes = m.meshes(coll);
    if (!meshes.length) return [];
    return s.flags.merge
      ? [exportObjectsAsSingle(m, folder, coll.name, meshes, rule + " (fallback: merge)")]
      : individual(m, folder, meshes, rule + " (fallback: individual)");
  }
  const claimed = new Set(groups.flatMap(([, mem]) => mem));
  const sources = [...groups.flatMap(([, mem]) => mem), ...m.meshes(coll).filter((n) => !claimed.has(n))];
  const firstEmpty = groups[0][0];
  return [file(m, folder, coll.name, sources, rule, {
    joined: joinOpts(s),
    center: centerMode(s), rootNames: [coll.name], distOf: () => m.dist(firstEmpty),
  })];
}

function joinOpts(s) {
  return {
    bake: s.row.apply_modifiers_before_join || s.g.apply_modifiers,
    onlyVisible: s.row.apply_only_visible || s.g.apply_only_visible_modifiers,
  };
}

// R-EMPTIES / R-JOIN: one file per parent empty, named after it. Without Join the members are
// elements of the file; with Join they are one mesh named after the empty, origin at the empty.
function empties(m, folder, coll) {
  const s = m.s;
  const groups = m.emptyGroups(coll);
  const out = [];
  for (const [e, members] of groups) {
    if (s.flags.join) {
      out.push(file(m, folder, e, members, "R-JOIN", {
        joined: joinOpts(s), center: centerMode(s), rootNames: [e], distOf: () => m.dist(e),
      }));
    } else {
      out.push(file(m, folder, e, members, "R-EMPTIES", { center: centerMode(s) }));
    }
  }
  const claimed = new Set(groups.flatMap(([, mem]) => mem));
  const loose = m.meshes(coll).filter((n) => !claimed.has(n));
  if (loose.length) {
    if (s.flags.merge) out.push(exportObjectsAsSingle(m, folder, coll.name, loose, "R-EMPTIES (loose, merged)"));
    else out.push(...individual(m, folder, loose, "R-EMPTIES (loose)"));
  }
  return out;
}

function suffixGroups(m, folder, coll) {
  const groups = new Map();
  const claimed = new Set();
  const add = (base, n) => {
    if (claimed.has(n)) return;
    claimed.add(n);
    if (!groups.has(base)) groups.set(base, []);
    groups.get(base).push(n);
  };
  for (const [e, members] of m.emptyGroups(coll, true)) {
    for (const n of members) add(baseName(e, true), n);
  }
  for (const sub of coll.children) {
    if (m.skipHidden(sub)) continue;
    for (const n of m.meshes(sub)) add(baseName(sub.name, true), n);
  }
  for (const n of m.directMeshes(coll)) add(baseName(n, true), n);
  return [...groups].map(([base, meshes]) => exportObjectsAsSingle(m, folder, base, meshes, "R-SUFFIX"));
}

function subcollections(m, folder, coll) {
  const s = m.s;
  const out = [];
  const main = m.directMeshes(coll);
  if (main.length) out.push(exportObjectsAsSingle(m, folder, `${coll.name}_main`, main, "R-SUBCOLL"));
  for (const sub of coll.children) {
    if (s.flags.empties && s.flags.join) {
      out.push(...joinAll(m, folder, sub, "R-SUBCOLL + R-JOIN"));
    } else {
      const meshes = m.meshes(sub);
      if (meshes.length) out.push(exportObjectsAsSingle(m, folder, sub.name, meshes, "R-SUBCOLL"));
    }
  }
  return out;
}

function whole(m, folder, coll) {
  const s = m.s;
  const name = (s.row.single_fbx_custom_name || "").trim() || coll.name;
  const meshes = m.meshes(coll);
  // roots of the whole set include empties (they ship too)
  const all = [];
  const walk = (c, isRow) => {
    if (m.skipHidden(c)) return;
    c.objects.forEach((n) => { if (!all.includes(n)) all.push(n); });
    c.children.forEach((ch) => walk(ch, false));
  };
  walk(coll, true);
  const roots = m.roots(all.filter((n) => ["MESH", "EMPTY"].includes(m.obj[n].type)));
  const exportSet = all.filter((n) => ["MESH", "EMPTY"].includes(m.obj[n].type));
  return [file(m, folder, name, meshes, "R-WHOLE", { center: centerMode(s), rootNames: roots, exportSet })];
}

// The expected result of one case: { mode, rows: [{ row, folder, mode, files }], files, notes }
export function expect(scene, c) {
  const s = settingsOf(c);
  const m = new SceneModel(scene, s);
  const mode = effectiveMode(s.flags, s.suffixesOn);
  const rows = [];
  for (const rowName of c.rows) {
    const coll = m.colls[rowName];
    const folder = rowName;
    let files = [];
    let rowMode = mode;
    if (coll.hidden && !s.g.export_hidden_collections) {
      rowMode = "skipped";
    } else if (mode === "whole") files = whole(m, folder, coll);
    else if (mode === "suffix") files = suffixGroups(m, folder, coll);
    else if (mode === "subcoll" || mode === "subcoll_join") files = subcollections(m, folder, coll);
    else if (mode === "join") files = empties(m, folder, coll);
    else if (mode === "empties") files = empties(m, folder, coll);
    else if (mode === "merge") {
      const meshes = m.meshes(coll);
      if (meshes.length) files = [exportObjectsAsSingle(m, folder, coll.name, meshes, "R-MERGE")];
    } else files = individual(m, folder, m.meshes(coll));
    if (s.format === "OBJ") {
      files.forEach((f) => { f.roots = null; });
      // the OBJ exporter writes its material library beside every file
      files = files.concat(files.map((f) => ({ ...f, path: f.path.replace(/\.obj$/, ".mtl"), sidecar: true })));
    }
    rows.push({ row: rowName, folder, mode: rowMode, files });
  }
  return { mode, settings: s, rows, files: rows.flatMap((r) => r.files), relative: c.extra === "relative" };
}

// A short, stable signature of what a case wrote: used to group cases by identical output.
export function outputSignature(c) {
  return c.files.map((f) => f.path.replace(/\.(fbx|obj|glb)$/, "")).join("|") || "(nothing)";
}
