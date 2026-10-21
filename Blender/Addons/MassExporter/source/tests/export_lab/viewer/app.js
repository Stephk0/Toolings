import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { MTLLoader } from "three/addons/loaders/MTLLoader.js";
import { expect, effectiveMode, settingsOf, outputSignature, FLAGS, FLAG_LETTERS, MODES } from "./oracle.js";
import { makeInspector, compareFile, compareCase, compareUnity } from "./checks.js";
import { loadUnityFBX } from "./unity-fbx.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem("mxlab:" + k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem("mxlab:" + k, JSON.stringify(v)); } catch { /* storage off */ } },
};

const RULES = [
  ["R-RUN", "The operator finishes and logs no export error."],
  ["R-SOURCE", "The scene is identical before and after the export."],
  ["R-SELECTION", "The selection after the export is the selection before it, hidden objects included."],
  ["R-FOLDER", "Exactly the expected files, in the folder of the row that wrote them. The mode rule that predicts the files is shown as the cause."],
  ["R-HIDDEN-SUB", "Export Hidden Collections off skips hidden sub-collections too."],
  ["R-EMPTIES", "Use Parent Empties writes one file per empty, named after it, with all its members; Join makes them one mesh."],
  ["R-JOIN", "Join: one mesh per empty named after it, origin at the empty (per sub-collection with Sub-Collections on)."],
  ["R-RELATIVE", "A // export path is relative to the .blend."],
  ["R-NODES", "Each file holds a node for every expected mesh and none for other scene meshes."],
  ["R-TRIS", "Triangle count matches the modifier settings (Apply Modifiers, Only Visible Modifiers, Join)."],
  ["R-CENTER", "Move to Center puts each asset's pivot (its parent empty, else the root) at the origin; off, roots keep their distance."],
  ["R-PLACEMENT", "Every part of a multi-mesh file sits where it sits in Blender, relative to the other parts."],
  ["R-MATERIALS", "Material names follow Materials (Keep / Fill Empty / Overwrite) and Add M_ Prefix."],
  ["R-LOAD", "three.js can load the file."],
  ["R-UNITY", "FBX with the Unity importer: the page's Unity import model matches what Unity itself imported (unity.json), per mesh within 1 cm."],
];

const state = {
  manifest: null, scene: null, meshNames: null,
  results: new Map(),      // case id -> { checks, content: bool }
  exp: new Map(),          // case id -> oracle expectation
  selected: null, selectedFile: null,
  tab: store.get("tab", "lineup"),
  filters: store.get("filters", { q: "", matrix: "", layout: "", format: "", mode: "", status: "", sort: "id", flags: {} }),
};

const inspector = makeInspector({ GLTFLoader, FBXLoader, OBJLoader, loadUnityFBX });
const bufferCache = new Map();

function fileUrl(c, f) {
  return f.blob ? `blobs/${f.blob}` : `cases/${c.id}/${f.path}`;
}

const packCache = new Map();

// Packed runs (pack.py) carry the files as base64 in packs/pack-<n>.json
async function packedBuffer(blob) {
  const id = state.manifest.packed[blob];
  if (!packCache.has(id)) packCache.set(id, fetch(`packs/pack-${id}.json`).then((r) => r.json()));
  const b64 = (await packCache.get(id))[blob];
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

async function fetchBuffer(url) {
  const blob = url.startsWith("blobs/") && state.manifest.packed ? url.slice(6) : null;
  if (blob) {
    if (!bufferCache.has(url)) bufferCache.set(url, packedBuffer(blob));
    return bufferCache.get(url);
  }
  if (!bufferCache.has(url)) {
    bufferCache.set(url, fetch(url).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ${url}`);
      return r.arrayBuffer();
    }));
  }
  return bufferCache.get(url);
}

function expOf(c) {
  if (!state.exp.has(c.id)) state.exp.set(c.id, expect(state.scene, c));
  return state.exp.get(c.id);
}

function modeOf(c) {
  return effectiveMode(c.flags, c.extra !== "suffix_off");
}

// Case-level checks need no file loading, so every case gets a status on page load.
function structuralChecks(c) {
  return compareCase(c, expOf(c));
}

function statusOf(c) {
  const r = state.results.get(c.id);
  const checks = r ? r.checks : structuralChecks(c);
  if (checks.some((k) => !k.ok)) return "fail";
  return r?.content ? "pass" : "pending";
}

async function runCase(c) {
  const exp = expOf(c);
  const checks = structuralChecks(c);
  for (const f of exp.files.filter((x) => !x.sidecar)) {
    const actual = c.files.find((x) => x.path === f.path);
    if (!actual) continue;
    const ext = f.path.split(".").pop();
    try {
      const buf = await fetchBuffer(fileUrl(c, actual));
      const obj = await inspector.load(buf.slice(0), ext, importOpts());
      for (const k of compareFile(f, inspector.describe(obj), ext, state.meshNames)) checks.push({ ...k, file: f.path });
      // The Unity import model against Unity's own import of this very file
      const id = (actual.blob || "").replace(/\.fbx$/, "");
      const nodes = ext === "fbx" && view.importer === "unity" && state.unity?.variants[view.bakeAxis ? "bake_axis" : "default"]?.[id];
      if (nodes) checks.push({ ...compareUnity(obj, nodes, id, state.unity.unity), file: f.path });
    } catch (e) {
      checks.push({ rule: "R-LOAD", ok: false, file: f.path, expected: "loads", found: String(e.message || e) });
    }
  }
  state.results.set(c.id, { checks, content: true });
  return checks;
}

// ------------------------------------------------------------------------- list + filters

function filtered() {
  const f = state.filters;
  const q = f.q.trim().toLowerCase();
  let list = state.manifest.cases.filter((c) => {
    if (f.matrix && c.matrix !== f.matrix) return false;
    if (f.layout && c.layout !== f.layout) return false;
    if (f.format && c.format !== f.format) return false;
    if (f.mode && modeOf(c) !== f.mode) return false;
    for (const flag of FLAGS) {
      const v = f.flags[flag];
      if (v === "on" && !c.flags[flag]) return false;
      if (v === "off" && c.flags[flag]) return false;
    }
    if (f.status && statusOf(c) !== f.status) return false;
    if (q && !c.id.toLowerCase().includes(q) && !c.files.some((x) => x.path.toLowerCase().includes(q))) return false;
    return true;
  });
  const modeOrder = Object.keys(MODES);
  const fails = (c) => { const r = state.results.get(c.id); return (r ? r.checks : structuralChecks(c)).filter((k) => !k.ok).length; };
  const sorters = {
    id: (a, b) => a.id.localeCompare(b.id),
    mode: (a, b) => modeOrder.indexOf(modeOf(a)) - modeOrder.indexOf(modeOf(b)) || a.id.localeCompare(b.id),
    files: (a, b) => b.files.length - a.files.length || a.id.localeCompare(b.id),
    fails: (a, b) => fails(b) - fails(a) || a.id.localeCompare(b.id),
  };
  return list.sort(sorters[f.sort] || sorters.id);
}

function bitsHtml(c) {
  return `<span class="bits" aria-label="switches">${FLAGS.map((k) => `<b class="${c.flags[k] ? "on" : ""}">${c.flags[k] ? FLAG_LETTERS[k] : "·"}</b>`).join("")}</span>`;
}

function modeHtml(mode) {
  return `<span class="mode" style="--mc: var(--m-${mode})">${esc(MODES[mode] || mode)}</span>`;
}

function renderList() {
  const list = filtered();
  $("count").textContent = `${list.length} of ${state.manifest.cases.length} cases`;
  $("cases").innerHTML = list.map((c) => {
    const st = statusOf(c);
    const sub = c.option ? `<span class="chip alt">${esc(c.option)}</span>` : "";
    return `<li class="case" data-id="${esc(c.id)}" aria-current="${c.id === state.selected?.id}">
      <span class="dot ${st === "pending" ? "part" : st}" title="${st}"></span>
      <span class="id">${esc(c.id)}</span>${bitsHtml(c)}
      <span class="meta">${modeHtml(modeOf(c))}<span>${c.format}</span><span>${c.files.length} file${c.files.length === 1 ? "" : "s"}</span>${sub}</span>
    </li>`;
  }).join("") || `<li class="empty" style="padding:12px">No case matches these filters.</li>`;
}

function renderFlagFilter() {
  $("flagfilter").innerHTML = FLAGS.map((k) => {
    const v = state.filters.flags[k] || "any";
    const label = { any: `${FLAG_LETTERS[k]} any`, on: `${FLAG_LETTERS[k]} on`, off: `${FLAG_LETTERS[k]} off` }[v];
    return `<button type="button" class="flagbtn" data-flag="${k}" data-v="${v}" title="${k}: ${v}">${label}</button>`;
  }).join("");
}

function renderStats() {
  const cases = state.manifest.cases;
  const st = cases.map(statusOf);
  const fail = st.filter((s) => s === "fail").length;
  const pass = st.filter((s) => s === "pass").length;
  const loaded = cases.filter((c) => state.results.get(c.id)?.content).length;
  const failingRules = new Set();
  for (const c of cases) {
    const r = state.results.get(c.id);
    (r ? r.checks : structuralChecks(c)).filter((k) => !k.ok).forEach((k) => failingRules.add(k.rule));
  }
  $("stats").innerHTML = `
    <div class="stat"><b>${cases.length}</b><span>cases</span></div>
    <div class="stat fail"><b>${fail}</b><span>failing</span></div>
    <div class="stat pass"><b>${pass}</b><span>passing</span></div>
    <div class="stat"><b>${loaded}</b><span>cases loaded</span></div>
    <div class="stat fail"><b>${failingRules.size}</b><span>rules failing</span></div>`;
}

// ------------------------------------------------------------------------- case detail

function renderCaseHead(c) {
  const s = settingsOf(c);
  $("c-id").textContent = c.id;
  $("c-mode").outerHTML = `<span class="mode" id="c-mode" style="--mc: var(--m-${modeOf(c)})">${esc(MODES[modeOf(c)])}</span>`;
  const on = FLAGS.filter((k) => c.flags[k]).map((k) => `${FLAG_LETTERS[k]} ${k}`);
  const chips = [
    `<span class="chip">${c.format === "GLTF" ? "glTF (.glb)" : c.format}</span>`,
    `<span class="chip">rows: ${c.rows.join(", ")}</span>`,
    `<span class="chip">${on.length ? on.join(" + ") : "no mode switch"}</span>`,
  ];
  if (c.option) chips.push(`<span class="chip alt">${esc(c.option)}</span>`);
  if (!s.g.apply_modifiers) chips.push(`<span class="chip">modifiers not applied</span>`);
  chips.push(`<span class="chip">${c.seconds}s</span>`);
  $("c-settings").innerHTML = chips.join("");
}

function renderTree(c) {
  const exp = expOf(c);
  const want = new Set(exp.files.map((f) => f.path));
  const got = new Map(c.files.map((f) => [f.path, f]));
  const all = [...new Set([...want, ...got.keys()])].sort();
  const folders = {};
  for (const p of all) {
    const [folder, ...rest] = p.split("/");
    (folders[folder] ??= []).push([p, rest.join("/")]);
  }
  const rows = [];
  if (exp.relative) rows.push(`<li class="muted">Export path <span class="mono">//ExportLab_relative_…</span> — ${c.relative_written_to?.length ? "written next to the .blend" : "nothing written"}</li>`);
  for (const [folder, files] of Object.entries(folders)) {
    rows.push(`<li>📁 ${esc(folder)}/</li>`);
    for (const [p, name] of files) {
      const cls = !got.has(p) ? "miss" : !want.has(p) ? "extra" : "";
      const tag = cls === "miss" ? `<span class="tag">missing</span>` : cls === "extra" ? `<span class="tag">unexpected</span>` : "";
      const size = got.has(p) ? `<span class="size">${(got.get(p).size / 1024).toFixed(1)} KB</span>` : "";
      rows.push(`<li class="file ${cls}" data-path="${esc(p)}" title="${esc(p)}">${esc(name)} ${tag}${size}</li>`);
    }
  }
  if (!all.length) rows.push(`<li class="muted">Nothing was written${exp.rows.some((r) => r.mode === "skipped") ? " (row skipped: hidden collection)" : ""}.</li>`);
  $("tree").innerHTML = rows.join("");
}

function renderChecks(c) {
  const r = state.results.get(c.id);
  const checks = r ? r.checks : structuralChecks(c);
  const sel = state.selectedFile;
  $("checks-title").textContent = sel ? `Checks — ${sel.split("/").pop()}` : "Checks";
  const rows = checks
    .filter((k) => !sel || !k.file || k.file === sel)
    .map((k) => `<tr class="${k.file && k.file === sel ? "focus" : ""}">
      <td class="st ${k.ok ? "pass" : "fail"}">${k.ok ? "pass" : "fail"}</td>
      <td class="rule">${esc(k.rule)}${k.cause && !k.ok ? `<div class="muted">${esc(k.cause)}</div>` : ""}</td>
      <td>${k.file ? `<div class="mono">${esc(k.file.split("/").pop())}</div>` : ""}<div class="muted">want ${esc(k.expected)}</div><div>${esc(k.found)}</div></td>
    </tr>`).join("");
  const pending = r?.content ? "" : `<tr><td colspan="3" class="empty">Loading files for the content checks…</td></tr>`;
  $("checks").innerHTML = `<thead><tr><th>State</th><th>Rule</th><th>Detail</th></tr></thead><tbody>${rows}${pending}</tbody>`;
}

async function selectCase(c, { scroll = false } = {}) {
  state.selected = c;
  state.selectedFile = null;
  store.set("case", c.id);
  try { history.replaceState(null, "", "#" + c.id); } catch { /* sandboxed */ }
  document.querySelectorAll(".case").forEach((el) => el.setAttribute("aria-current", String(el.dataset.id === c.id)));
  if (scroll) document.querySelector(`.case[data-id="${CSS.escape(c.id)}"]`)?.scrollIntoView({ block: "nearest" });
  renderCaseHead(c);
  renderTree(c);
  renderChecks(c);
  renderExportPanel();
  if (state.tab === "matrix") renderMatrix();
  const token = Symbol();
  state.loadToken = token;
  if (!state.results.get(c.id)?.content) {
    await runCase(c);
    if (state.loadToken !== token) return;
    renderChecks(c);
    renderStats();
    renderList();
    renderExportPanel();
  }
  await stage.show(c);
}

// ------------------------------------------------------------------------- 3D line-up

// Viewport settings, kept per viewer
const view = Object.assign({
  importer: "unity", bakeAxis: false, spacing: "lineup",
  grid: true, world: true, origins: true, pivots: false, arrows: false, gizmo: 1,
  bounds: false, labels: true, names: false, col: true, wire: false, expected: false,
  exportOpen: true, viewOpen: true,
}, store.get("view", {}));

const importOpts = () => ({ fbx: view.importer, bakeAxis: view.bakeAxis });

const stage = (() => {
  const wrap = $("stage");
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  wrap.prepend(renderer.domElement);
  const labels = new CSS2DRenderer();
  labels.domElement.style.cssText = "position:absolute;inset:0;pointer-events:none";
  wrap.appendChild(labels.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 500);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  // The geonode icon rig, in three.js terms: warm key, cool fill, hard cyan rim from behind-left
  scene.add(new THREE.HemisphereLight(0xdfe6ee, 0x3a3833, 0.9));
  const rig = [[0xfff4e0, 2.2, [4, 5, 5]], [0xd0e0ff, 0.8, [-5, 2.5, 4]], [0xe6f6ff, 1.6, [-5, 3, -6]]];
  for (const [col, i, p] of rig) {
    const l = new THREE.DirectionalLight(col, i);
    l.position.set(...p);
    scene.add(l);
  }
  const grid = new THREE.GridHelper(40, 80, 0x888888, 0x888888);
  grid.material.transparent = true;
  grid.material.opacity = 0.18;
  scene.add(grid);

  // World origin: long axes, a ring and a tag
  const world = new THREE.Group();
  world.add(new THREE.AxesHelper(0.8));
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.05, 0.065, 32), new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide, depthTest: false }));
  ring.rotation.x = -Math.PI / 2;
  world.add(ring);
  const worldTag = document.createElement("div");
  worldTag.className = "tag3d";
  worldTag.textContent = "world 0,0,0";
  const wt = new CSS2DObject(worldTag);
  wt.position.set(0, -0.02, 0.12);
  world.add(wt);
  scene.add(world);

  const content = new THREE.Group();
  scene.add(content);
  const pickBox = new THREE.BoxHelper(undefined, 0xffc233);
  pickBox.visible = false;
  scene.add(pickBox);

  let records = [];   // one per file: { f, slot, space, obj, origin, pivots, arrows, bounds, ghosts, names, label }
  let picked = null;

  function themeColours() {
    const cs = getComputedStyle(document.documentElement);
    scene.background = new THREE.Color(cs.getPropertyValue("--stage").trim() || "#d9dcd6");
  }
  themeColours();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", themeColours);
  new MutationObserver(themeColours).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  function resize() {
    const w = wrap.clientWidth, h = wrap.clientHeight;
    renderer.setSize(w, h);
    labels.setSize(w, h);
    camera.aspect = w / Math.max(h, 1);
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(wrap);
  resize();
  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
    labels.render(scene, camera);
  });

  function clear() {
    for (const o of [...content.children]) {
      o.traverse((n) => { if (n.isCSS2DObject) n.element.remove(); });
      content.remove(o);
    }
    records = [];
    unpick();
  }

  async function loadDisplay(c, f) {
    const ext = f.path.split(".").pop();
    const buf = await fetchBuffer(fileUrl(c, f));
    if (ext !== "obj") return inspector.load(buf.slice(0), ext, importOpts());
    const loader = new OBJLoader();
    const mtl = c.files.find((x) => x.path === f.path.replace(/\.obj$/, ".mtl"));
    if (mtl) {
      const text = new TextDecoder().decode(await fetchBuffer(fileUrl(c, mtl)));
      const mats = new MTLLoader().parse(text, "");
      mats.preload();
      loader.setMaterials(mats);
    }
    return loader.parse(new TextDecoder().decode(buf));
  }

  const isCol = (n) => /_COL$/.test(n.name) || /_COL$/.test(n.parent?.name || "");

  function dress(obj) {
    obj.traverse((n) => {
      if (!n.isMesh) return;
      const col = isCol(n);
      n.userData.isCol = col;
      const mats = Array.isArray(n.material) ? n.material : [n.material];
      n.material = mats.map((m) => {
        if (col || !m || m.name === "__DEFAULT" || !m.name) {
          return new THREE.MeshStandardMaterial({ color: col ? 0x2a8fa8 : 0xbdbdbd, wireframe: col, transparent: col, opacity: col ? 0.6 : 1, name: m?.name || "" });
        }
        m.side = THREE.DoubleSide;
        return m;
      });
      if (n.material.length === 1) n.material = n.material[0];
    });
  }

  // The file's own nodes: everything under the loader's container groups
  function fileNodes(obj) {
    const skip = new Set([obj]);
    if (obj.userData.unity) skip.add(obj.children[0]);
    const out = [];
    obj.traverse((o) => { if (!skip.has(o) && o.name && !o.isCSS2DObject) out.push(o); });
    return out;
  }

  // A helper parented to a node, kept at a fixed on-screen size whatever the node's scale
  function gizmo(node, helper, base) {
    helper.userData.base = base;
    helper.userData.node = node;
    node.add(helper);
    return helper;
  }

  function sizeGizmos() {
    const s = new THREE.Vector3();
    for (const r of records) {
      for (const h of [...r.pivots, ...r.arrows]) {
        h.userData.node.getWorldScale(s);
        const k = view.gizmo * h.userData.base;
        h.scale.set(k / (s.x || 1), k / (s.y || 1), k / (s.z || 1));
      }
      r.origin.scale.setScalar(view.gizmo);
    }
  }

  function edgeBox(lo, hi, color, dashed) {
    const g = new THREE.BoxGeometry(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]);
    const e = new THREE.EdgesGeometry(g);
    const m = dashed
      ? new THREE.LineDashedMaterial({ color, dashSize: 0.04, gapSize: 0.03, depthTest: false, transparent: true, opacity: 0.9 })
      : new THREE.LineBasicMaterial({ color, depthTest: false, transparent: true, opacity: 0.7 });
    const line = new THREE.LineSegments(e, m);
    line.position.set((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2);
    if (dashed) line.computeLineDistances();
    return line;
  }

  async function show(c) {
    const token = Symbol();
    show.token = token;
    const exp = expOf(c);
    const files = c.files.filter((f) => !f.path.endsWith(".mtl"));
    const r = state.results.get(c.id);
    const loaded = [];
    for (const f of files) {
      try { loaded.push([f, await loadDisplay(c, f)]); } catch (e) { loaded.push([f, null]); }
      if (show.token !== token) return;
    }
    clear();
    let cursor = 0, slotIndex = 0, lastFolder = null;
    const all = new THREE.Box3();
    const turn = view.importer === "unity" && view.bakeAxis;
    for (const [f, obj] of loaded) {
      const folder = f.path.split("/")[0];
      const lineup = view.spacing === "lineup";
      if (lineup && lastFolder !== null && folder !== lastFolder) cursor += 0.9;
      if (folder !== lastFolder) {
        const el = document.createElement("div");
        el.className = "folder3d";
        el.textContent = folder + "/";
        const tag = new CSS2DObject(el);
        tag.position.set(lineup ? cursor : 0, 0, 1 + (lineup ? 0 : slotIndex * 0.25));
        tag.center.set(0, 0);
        content.add(tag);
        lastFolder = folder;
      }
      const slot = new THREE.Group();
      const space = new THREE.Group();   // the file's own coordinate system
      space.userData.filePath = f.path;
      slot.add(space);
      content.add(slot);
      const rec = { f, slot, space, obj, pivots: [], arrows: [], bounds: [], ghosts: [], names: [] };
      rec.origin = new THREE.AxesHelper(0.25);
      rec.origin.position.y = 0.002;
      space.add(rec.origin);
      let box = new THREE.Box3(new THREE.Vector3(-0.35, 0, -0.35), new THREE.Vector3(0.35, 0.4, 0.35));
      if (obj) {
        dress(obj);
        space.add(obj);
        obj.updateMatrixWorld(true);
        const b = new THREE.Box3().setFromObject(obj);
        if (!b.isEmpty()) box = b;
        for (const node of fileNodes(obj)) {
          rec.pivots.push(gizmo(node, new THREE.AxesHelper(1), 0.15));
          const fwd = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(), 1, 0x3b82f6, 0.22, 0.12);
          const up = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(), 1, 0x22c55e, 0.22, 0.12);
          for (const a of [fwd, up]) {
            a.traverse((m) => { if (m.material) { m.material.depthTest = false; m.material.transparent = true; } });
            a.renderOrder = 10;
            rec.arrows.push(gizmo(node, a, 0.3));
          }
          if (node.isMesh) rec.bounds.push(node);
          const el = document.createElement("div");
          el.className = "tag3d";
          el.textContent = node.name;
          const nt = new CSS2DObject(el);
          nt.userData.node = node;
          node.add(nt);
          rec.names.push(nt);
        }
        // Where the oracle expects every part (Blender, converted to Y-up)
        const parts = exp.files.find((e) => e.path === f.path)?.parts;
        for (const [, [lo, hi]] of Object.entries(parts || {})) {
          const [l, h] = turn ? [[-hi[0], lo[1], -hi[2]], [-lo[0], hi[1], -lo[2]]] : [lo, hi];
          const g = edgeBox(l, h, 0xc026d3, true);
          space.add(g);
          rec.ghosts.push(g);
        }
      }
      if (lineup) {
        slot.position.x = cursor - box.min.x;
        cursor += Math.max(box.max.x - box.min.x, 0.7) + 0.45;
      }
      const checks = (r?.checks || []).filter((k) => k.file === f.path);
      const failed = checks.some((k) => !k.ok);
      const tris = exp.files.find((e) => e.path === f.path)?.tris;
      const el = document.createElement("div");
      el.className = `label3d ${checks.length ? (failed ? "fail" : "pass") : ""}`;
      el.style.pointerEvents = "auto";
      el.innerHTML = `<div class="fn">${esc(f.path.split("/").pop())}</div>
        <div class="sub">${esc(folder)}/ · ${(f.size / 1024).toFixed(0)} KB${tris != null ? ` · ${tris} tris` : ""}${obj ? "" : " · could not load"}</div>`;
      el.addEventListener("click", () => selectFile(f.path));
      el.dataset.path = f.path;
      const tag = new CSS2DObject(el);
      // alternate label heights so neighbouring (or, as exported, overlapping) labels stay apart
      const rows = lineup ? 2 : Math.max(loaded.length, 1);
      tag.position.set((box.min.x + box.max.x) / 2, Math.max(box.max.y, 0.3) + 0.12 + (slotIndex++ % rows) * 0.28, (box.min.z + box.max.z) / 2);
      space.add(tag);
      rec.label = tag;
      records.push(rec);
      content.updateMatrixWorld(true);
      all.expandByObject(slot);
    }
    if (!loaded.length) {
      const el = document.createElement("div");
      el.className = "label3d";
      el.textContent = "No files written for this case";
      content.add(new CSS2DObject(el));
      all.setFromCenterAndSize(new THREE.Vector3(), new THREE.Vector3(2, 1, 1));
    }
    state.frameBox = all;
    applyView();
    // Keep the camera while switching cases, so outcomes compare in place; Frame re-fits
    if (!show.framed) frame("persp");
    show.framed = true;
    highlight();
  }

  // Each mesh's own bounds (children and gizmos excluded), drawn in world space
  function drawBounds(r) {
    r.boundLines?.forEach((l) => { content.remove(l); l.geometry.dispose(); });
    r.boundLines = [];
    if (!view.bounds) return;
    for (const mesh of r.bounds) {
      if (mesh.userData.isCol && !view.col) continue;
      mesh.updateWorldMatrix(true, false);
      mesh.geometry.computeBoundingBox();
      const b = mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld);
      const l = edgeBox(b.min.toArray(), b.max.toArray(), mesh.userData.isCol ? 0x2a8fa8 : 0xd2601a, false);
      content.add(l);
      r.boundLines.push(l);
    }
  }

  // Show / hide every helper from the view settings; no reload needed
  function applyView() {
    grid.visible = view.grid;
    world.visible = view.world;
    worldTag.style.display = view.world ? "" : "none";
    for (const r of records) {
      r.origin.visible = view.origins;
      r.pivots.forEach((h) => (h.visible = view.pivots));
      r.arrows.forEach((h) => (h.visible = view.arrows));
      drawBounds(r);
      r.ghosts.forEach((h) => (h.visible = view.expected));
      r.names.forEach((t) => { t.visible = view.names; t.element.style.display = view.names ? "" : "none"; });
      r.label.visible = view.labels;
      r.label.element.style.display = view.labels ? "" : "none";
      r.obj?.traverse((n) => {
        if (!n.isMesh) return;
        n.visible = view.col || !n.userData.isCol;
        (Array.isArray(n.material) ? n.material : [n.material]).forEach((m) => { if (!n.userData.isCol) m.wireframe = view.wire; });
      });
    }
    sizeGizmos();
  }

  const DIRS = { persp: [0.15, 0.42, 1], front: [0, 0, 1], back: [0, 0, -1], top: [0, 1, 0.0001], side: [1, 0, 0] };

  function frame(dirName = "persp") {
    const b = state.frameBox || new THREE.Box3(new THREE.Vector3(-1, 0, -1), new THREE.Vector3(1, 1, 1));
    const size = b.getSize(new THREE.Vector3());
    const centre = b.getCenter(new THREE.Vector3());
    const tan = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const dir = new THREE.Vector3(...DIRS[dirName]).normalize();
    const across = dirName === "top" ? Math.max(size.x / camera.aspect, size.z) : dirName === "side" ? Math.max(size.z / camera.aspect, size.y) : Math.max(size.x / camera.aspect, size.y);
    const fit = Math.max(across, 1.2) / tan;
    camera.position.copy(centre).addScaledVector(dir, fit * 1.15 + size.length() * 0.3);
    controls.target.copy(centre);
    camera.far = fit * 20 + 50;
    camera.updateProjectionMatrix();
  }

  function highlight() {
    wrap.querySelectorAll(".label3d").forEach((el) => el.classList.toggle("sel", el.dataset.path === state.selectedFile));
  }

  // Click a part: select its file and read out the node
  const ray = new THREE.Raycaster();
  let down = null;
  renderer.domElement.addEventListener("pointerdown", (e) => { down = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4) return;
    const rect = renderer.domElement.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1), camera);
    const meshes = [];
    for (const r of records) r.obj?.traverse((n) => { if (n.isMesh && n.visible) meshes.push(n); });
    const hit = ray.intersectObjects(meshes, false)[0];
    if (!hit) { unpick(); return; }
    pick(hit.object);
  });

  function unpick() {
    picked = null;
    pickBox.visible = false;
    $("vp-info").hidden = true;
  }

  function pick(mesh) {
    picked = mesh;
    pickBox.setFromObject(mesh);
    pickBox.visible = true;
    let space = mesh;
    while (space && !space.userData.filePath) space = space.parent;
    if (!space) return;
    if (state.selectedFile !== space.userData.filePath) selectFile(space.userData.filePath);
    const rel = new THREE.Matrix4().copy(space.matrixWorld).invert().multiply(mesh.matrixWorld);
    const p = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
    rel.decompose(p, q, s);
    const eu = new THREE.Euler().setFromQuaternion(q, "YXZ");
    const deg = (v) => THREE.MathUtils.radToDeg(v).toFixed(1);
    const g = mesh.geometry;
    const tris = (g.index ? g.index.count : g.attributes.position.count) / 3;
    const mats = (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).map((m) => m.name).filter(Boolean);
    const node = mesh.name || mesh.parent?.name || "(unnamed)";
    const unity = view.importer === "unity" && space.userData.filePath.endsWith(".fbx");
    const f3 = (a) => a.map((v) => v.toFixed(3)).join(", ");
    $("vp-info").innerHTML = `
      <div class="fn">${esc(node)}</div>
      <div class="muted">${esc(space.userData.filePath)}</div>
      <table>
        <tr><th>position</th><td>${f3([p.x, p.y, p.z])}</td></tr>
        ${unity ? `<tr><th>Unity</th><td>${f3([-p.x, p.y, p.z])}</td></tr>` : ""}
        <tr><th>rotation</th><td>${deg(eu.x)}°, ${deg(eu.y)}°, ${deg(eu.z)}°</td></tr>
        <tr><th>scale</th><td>${f3([s.x, s.y, s.z])}</td></tr>
        <tr><th>tris</th><td>${tris}</td></tr>
        <tr><th>materials</th><td>${esc(mats.join(", ") || "(none)")}</td></tr>
      </table>
      <div class="muted">World transform in the file's space${unity ? "; Unity is left-handed, so its x is mirrored" : ""}.</div>`;
    $("vp-info").hidden = false;
  }

  return { show, highlight, applyView, frame };
})();

function selectFile(path) {
  state.selectedFile = state.selectedFile === path ? null : path;
  stage.highlight();
  renderChecks(state.selected);
}

// ------------------------------------------------------------------------- viewport panels

const BIT_EXT = { FBX: "fbx", OBJ: "obj", GLTF: "glb" };
const FLAG_NAMES = { whole: "Whole Collection", suffix: "Group by Suffix", subcoll: "Sub-Collections", empties: "Use Parent Empties", join: "Join Empty Children", merge: "Merge" };

function bitsOf(flags) {
  return FLAGS.map((k) => (flags[k] ? "1" : "0")).join("");
}

// The case a set of viewport choices points at, or null when the run has none
function findCase({ layout, format, flags, option }) {
  const cases = state.manifest.cases;
  if (option) return cases.find((c) => c.option === option && c.base_mode === effectiveMode(flags)) || null;
  return cases.find((c) => c.matrix === "modes" && c.id === `${layout}-${BIT_EXT[format]}-${bitsOf(flags)}`) || null;
}

function renderExportPanel() {
  const c = state.selected;
  if (!c) return;
  const options = [...new Set(state.manifest.cases.map((x) => x.option).filter(Boolean))];
  const seg = (k, items, cur, dis = false) => `<div class="seg">${items.map(([v, t]) => `<button type="button" data-k="${k}" data-v="${v}" aria-pressed="${v === cur}" ${dis ? "disabled" : ""}>${t}</button>`).join("")}</div>`;
  const byId = new Map(state.manifest.cases.map((x) => [x.id, x]));
  const cells = [];
  for (let r = 0; r < 8; r++) {
    for (let col = 0; col < 8; col++) {
      const bits = r.toString(2).padStart(3, "0") + col.toString(2).padStart(3, "0");
      const x = byId.get(`${c.layout}-${BIT_EXT[c.format]}-${bits}`);
      cells.push(x ? `<button class="mcell" type="button" data-id="${x.id}" data-s="${statusOf(x)}" aria-current="${x.id === c.id}" style="--mc: var(--m-${modeOf(x)})" title="${x.id} · ${MODES[modeOf(x)]}"></button>` : "<i></i>");
    }
  }
  $("vp-export").innerHTML = `
    <button type="button" class="vp-head" data-k="exportOpen" aria-expanded="${view.exportOpen}">Export settings <span>${view.exportOpen ? "▾" : "▸"}</span></button>
    <div class="vp-body" ${view.exportOpen ? "" : "hidden"}>
      <label>Rows</label>${seg("layout", [["assets", "Stone · Plant · Tree"], ["parent", "Nature"]], c.layout, !!c.option)}
      <label>Format</label>${seg("format", [["FBX", "FBX"], ["OBJ", "OBJ"], ["GLTF", "glTF"]], c.format, !!c.option)}
      <label>Mode switches <span class="mode" style="--mc: var(--m-${modeOf(c)})">${esc(MODES[modeOf(c)])}</span></label>
      <div class="sw">${FLAGS.map((k) => `<button type="button" data-flag="${k}" aria-pressed="${!!c.flags[k]}" title="${FLAG_NAMES[k]}">${FLAG_LETTERS[k]}<small>${FLAG_NAMES[k]}</small></button>`).join("")}</div>
      <label for="vp-option">Option</label>
      <select id="vp-option"><option value="">none (mode matrix)</option>${options.map((o) => `<option value="${o}" ${o === c.option ? "selected" : ""}>${esc(o.replace(/_/g, " "))}</option>`).join("")}</select>
      ${c.option ? "" : `<label>All 64 combinations <span class="muted">rows W S C · columns E J M</span></label><div class="mini">${cells.join("")}</div>`}
      <div class="vp-msg" id="vp-msg">${esc(c.id)} · ${c.files.length} file${c.files.length === 1 ? "" : "s"} · ${statusOf(c)}</div>
    </div>`;
}

function renderViewPanel() {
  const chk = (k, t) => `<label class="ck"><input type="checkbox" data-k="${k}" ${view[k] ? "checked" : ""}> ${t}</label>`;
  const seg = (k, items) => `<div class="seg">${items.map(([v, t]) => `<button type="button" data-k="${k}" data-v="${v}" aria-pressed="${view[k] === v}">${t}</button>`).join("")}</div>`;
  const unity = state.unity ? `Unity ${state.unity.unity}` : "Unity";
  $("vp-view").innerHTML = `
    <button type="button" class="vp-head" data-k="viewOpen" aria-expanded="${view.viewOpen}">View <span>${view.viewOpen ? "▾" : "▸"}</span></button>
    <div class="vp-body" ${view.viewOpen ? "" : "hidden"}>
      <label>FBX importer</label>${seg("importer", [["unity", unity], ["three", "three.js FBXLoader"]])}
      ${view.importer === "unity" ? chk("bakeAxis", "Bake Axis Conversion") : ""}
      <label>Placement</label>${seg("spacing", [["lineup", "Line-up"], ["exported", "As exported"]])}
      <div class="cks">
        ${chk("grid", "Grid")}${chk("world", "World origin")}${chk("origins", "File origins")}
        ${chk("pivots", "Node pivots")}${chk("arrows", "Orientation arrows")}${chk("bounds", "Bounds")}
        ${chk("labels", "File labels")}${chk("names", "Node names")}${chk("col", "Collision (_COL)")}
        ${chk("wire", "Wireframe")}${chk("expected", "Expected parts")}
      </div>
      <label for="vp-gizmo">Gizmo size <span class="muted" id="vp-gizmo-v">${view.gizmo.toFixed(2)}×</span></label>
      <input type="range" id="vp-gizmo" min="0.25" max="5" step="0.25" value="${view.gizmo}">
      <div class="legend3d"><span style="--c:#e5484d">X</span><span style="--c:#22c55e">Y / up</span><span style="--c:#3b82f6">Z / forward</span><span style="--c:#c026d3">expected</span></div>
      <label>Camera</label>
      <div class="seg">${[["persp", "Frame"], ["front", "Front"], ["back", "Back"], ["top", "Top"], ["side", "Side"]].map(([v, t]) => `<button type="button" data-cam="${v}">${t}</button>`).join("")}</div>
    </div>`;
}

function bindViewport() {
  $("vp-export").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const c = state.selected;
    if (b.dataset.k === "exportOpen") {
      view.exportOpen = !view.exportOpen;
      store.set("view", view);
      renderExportPanel();
      return;
    }
    if (b.dataset.id) {
      const x = state.manifest.cases.find((y) => y.id === b.dataset.id);
      if (x) selectCase(x, { scroll: true });
      return;
    }
    const want = { layout: c.layout, format: c.format, flags: { ...c.flags }, option: c.option || "" };
    if (b.dataset.flag) want.flags[b.dataset.flag] = !want.flags[b.dataset.flag];
    else if (b.dataset.k === "layout" || b.dataset.k === "format") want[b.dataset.k] = b.dataset.v;
    else return;
    const target = findCase(want);
    if (target) selectCase(target, { scroll: true });
    else $("vp-msg").textContent = `Not in this run: ${want.option ? `${want.option} with ${MODES[effectiveMode(want.flags)]}` : `${want.layout}-${BIT_EXT[want.format]}-${bitsOf(want.flags)}`}`;
  });
  $("vp-export").addEventListener("change", (e) => {
    if (e.target.id !== "vp-option") return;
    const c = state.selected;
    const option = e.target.value;
    let target;
    if (option) {
      target = findCase({ flags: c.flags, option })
        || state.manifest.cases.find((x) => x.option === option);   // the option does not apply to this mode: its first one
    } else {
      target = findCase({ layout: "parent", format: c.format, flags: c.flags, option: "" });
    }
    if (target) selectCase(target, { scroll: true });
  });
  $("vp-view").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.cam) return stage.frame(b.dataset.cam);
    const k = b.dataset.k;
    if (k === "viewOpen") view.viewOpen = !view.viewOpen;
    else if (k === "importer" || k === "spacing") {
      if (view[k] === b.dataset.v) return;
      view[k] = b.dataset.v;
    } else return;
    store.set("view", view);
    renderViewPanel();
    if (k === "importer") importerChanged();
    else if (k === "spacing") stage.show(state.selected);
  });
  $("vp-view").addEventListener("change", (e) => {
    const k = e.target.dataset.k;
    if (!k) return;
    view[k] = e.target.checked;
    store.set("view", view);
    if (k === "bakeAxis") importerChanged();
    else stage.applyView();
  });
  $("vp-view").addEventListener("input", (e) => {
    if (e.target.id !== "vp-gizmo") return;
    view.gizmo = +e.target.value;
    $("vp-gizmo-v").textContent = `${view.gizmo.toFixed(2)}×`;
    store.set("view", view);
    stage.applyView();
  });
}

// The importer decides what the FBX content checks see: drop their results and check again
function importerChanged() {
  for (const c of state.manifest.cases) {
    if (c.files.some((f) => f.path.endsWith(".fbx"))) state.results.delete(c.id);
  }
  refreshAll();
  if (state.selected) selectCase(state.selected);
}

// ------------------------------------------------------------------------- matrix / outcomes / rules

function renderMatrix() {
  $("legend").innerHTML = Object.entries(MODES).map(([k, v]) => `<span class="mode" style="--mc: var(--m-${k})">${esc(v)}</span>`).join("");
  const byId = new Map(state.manifest.cases.map((c) => [c.id, c]));
  const ext = { FBX: "fbx", OBJ: "obj", GLTF: "glb" };
  const html = [];
  for (const layout of ["assets", "parent"]) {
    for (const fmt of ["FBX", "OBJ", "GLTF"]) {
      const head = `<div class="ax"></div>` + [...Array(8)].map((_, i) => `<div class="ax">${i.toString(2).padStart(3, "0").replace(/./g, (b, j) => (b === "1" ? "EJM"[j] : "·"))}</div>`).join("");
      const rows = [...Array(8)].map((_, r) => {
        const wsc = r.toString(2).padStart(3, "0");
        const cells = [...Array(8)].map((_, col) => {
          const ejm = col.toString(2).padStart(3, "0");
          const c = byId.get(`${layout}-${ext[fmt]}-${wsc}${ejm}`);
          if (!c) return `<div></div>`;
          return `<button class="cell" type="button" data-id="${c.id}" data-s="${statusOf(c)}" aria-current="${c.id === state.selected?.id}" style="--mc: var(--m-${modeOf(c)})" title="${c.id} · ${MODES[modeOf(c)]} · ${c.files.length} files · ${statusOf(c)}"></button>`;
        }).join("");
        return `<div class="ax">${wsc.replace(/./g, (b, j) => (b === "1" ? "WSC"[j] : "·"))}</div>${cells}`;
      }).join("");
      const outcomes = new Set(state.manifest.cases.filter((c) => c.layout === layout && c.format === fmt && c.matrix === "modes").map(outputSignature)).size;
      html.push(`<div class="card"><h2>${layout} · ${fmt === "GLTF" ? "glTF" : fmt}</h2><p class="muted" style="margin:2px 0 8px">${outcomes} distinct outcomes from 64 combinations</p><div class="grid8">${head}${rows}</div></div>`);
    }
  }
  $("grids").innerHTML = html.join("");
}

function renderOutcomes() {
  const html = [];
  for (const layout of ["assets", "parent"]) {
    const groups = new Map();
    for (const c of state.manifest.cases.filter((x) => x.matrix === "modes" && x.layout === layout && x.format === "GLTF")) {
      const sig = outputSignature(c);
      if (!groups.has(sig)) groups.set(sig, []);
      groups.get(sig).push(c);
    }
    html.push(`<h2 style="margin-top:8px">${layout} layout <span class="muted" style="font-weight:400">— ${groups.size} outcomes (glTF shown; FBX and OBJ write the same names)</span></h2>`);
    const sorted = [...groups.values()].sort((a, b) => b.length - a.length);
    for (const cases of sorted) {
      const c0 = cases[0];
      const modes = [...new Set(cases.map(modeOf))];
      html.push(`<div class="outcome">
        <div>${modes.map(modeHtml).join(" ")} <span class="muted">· ${cases.length} combination${cases.length === 1 ? "" : "s"} · ${c0.files.length} file${c0.files.length === 1 ? "" : "s"}</span></div>
        <div class="files">${c0.files.map((f) => `<span>${esc(f.path)}</span>`).join("") || "<span>(nothing)</span>"}</div>
        <div class="combos">${cases.map((c) => `<button type="button" data-id="${c.id}" title="${c.id}">${FLAGS.map((k) => (c.flags[k] ? FLAG_LETTERS[k] : "·")).join("")}</button>`).join("")}</div>
      </div>`);
    }
  }
  $("outcomes").innerHTML = html.join("");
}

function renderRules() {
  const fails = new Map(RULES.map(([id]) => [id, []]));
  // R-FOLDER failures also count against the mode rule that caused them
  const byCause = { "R-HIDDEN-SUB": [], "R-EMPTIES": [], "R-JOIN": [] };
  for (const c of state.manifest.cases) {
    const r = state.results.get(c.id);
    const checks = r ? r.checks : structuralChecks(c);
    for (const k of checks.filter((x) => !x.ok)) {
      if (!fails.has(k.rule)) fails.set(k.rule, []);
      fails.get(k.rule).push(c);
      if (k.rule === "R-FOLDER") {
        if (/R-EMPTIES/.test(k.cause)) byCause["R-EMPTIES"].push(c);
        if (/R-JOIN/.test(k.cause)) byCause["R-JOIN"].push(c);
        if (c.option === "export_hidden_off") byCause["R-HIDDEN-SUB"].push(c);
      }
    }
  }
  for (const [id, list] of Object.entries(byCause)) fails.set(id, [...(fails.get(id) || []), ...list]);
  $("rules").innerHTML = RULES.map(([id, text]) => {
    const list = [...new Set(fails.get(id) || [])];
    const content = ["R-NODES", "R-TRIS", "R-CENTER", "R-PLACEMENT", "R-MATERIALS", "R-LOAD", "R-UNITY"].includes(id);
    const checked = state.manifest.cases.filter((c) => state.results.get(c.id)?.content).length;
    const n = content && !checked ? "–" : list.length;
    return `<div class="rulecard">
      <span class="rid">${id}</span>
      <span>${esc(text)}</span>
      <span class="n ${n === "–" ? "" : list.length ? "fail" : "pass"}">${n === "–" ? "not run" : list.length ? `${list.length} failing` : "pass"}</span>
      ${list.length ? `<div class="ex combos">${list.slice(0, 40).map((c) => `<button type="button" data-id="${c.id}">${esc(c.id)}</button>`).join("")}${list.length > 40 ? `<span class="muted">+${list.length - 40} more</span>` : ""}</div>` : ""}
    </div>`;
  }).join("");
}

function renderScene() {
  const sc = state.scene;
  $("scene-blend").textContent = `${sc.blend} · Blender ${sc.blender} · Mass Collection Exporter ${sc.addon_version}`;
  const rows = [];
  const walk = (c, depth) => {
    if (depth >= 0) rows.push(`<li style="padding-left:${depth * 16}px">📁 ${esc(c.name)}${c.hidden_self ? ` <span class="tag muted">hidden</span>` : ""}</li>`);
    const objs = c.objects.map((n) => [n, sc.objects[n]]);
    const depthOf = (n) => { let d = 0, p = sc.objects[n].parent; while (p && c.objects.includes(p)) { d++; p = sc.objects[p].parent; } return d; };
    const order = [];
    const visit = (n) => { order.push(n); objs.filter(([m, o]) => o.parent === n).forEach(([m]) => visit(m)); };
    objs.filter(([n, o]) => !o.parent || !c.objects.includes(o.parent)).forEach(([n]) => visit(n));
    for (const n of order) {
      const o = sc.objects[n];
      const mods = (o.modifiers || []).map((m) => (m.visible ? m.type.toLowerCase() : `<s>${m.type.toLowerCase()}</s>`)).join(", ");
      const info = o.type === "MESH" ? `${o.tris.raw}→${o.tris.visible} tris${mods ? " · " + mods : ""}` : o.type.toLowerCase();
      rows.push(`<li class="file" style="padding-left:${(depth + 1) * 16 + depthOf(n) * 14}px">${o.type === "EMPTY" ? "⌖" : "▪"} ${esc(n)} <span class="size">${info}</span></li>`);
    }
    c.children.forEach((ch) => walk(ch, depth + 1));
  };
  walk(sc.root, -1);
  $("scenetree").innerHTML = rows.join("");
  $("preview").addEventListener("error", () => { $("preview").hidden = true; }, { once: true });
}

// ------------------------------------------------------------------------- tabs, events, boot

function setTab(tab) {
  state.tab = tab;
  store.set("tab", tab);
  document.querySelectorAll(".tab").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
  for (const t of ["lineup", "matrix", "outcomes", "rules", "scene"]) $("tab-" + t).hidden = t !== tab;
  if (tab === "matrix") renderMatrix();
  if (tab === "outcomes") renderOutcomes();
  if (tab === "rules") renderRules();
  if (tab === "scene") renderScene();
}

function refreshAll() {
  renderStats();
  renderList();
  if (state.selected) { renderTree(state.selected); renderChecks(state.selected); }
  if (state.tab !== "lineup") setTab(state.tab);
}

async function runAll() {
  const btn = $("runall");
  btn.disabled = true;
  const bar = $("progress");
  bar.hidden = false;
  const cases = state.manifest.cases;
  let done = 0;
  const queue = [...cases];
  const worker = async () => {
    while (queue.length) {
      const c = queue.shift();
      if (!state.results.get(c.id)?.content) await runCase(c);
      done++;
      if (done % 10 === 0 || done === cases.length) {
        bar.firstElementChild.style.width = `${(100 * done) / cases.length}%`;
        btn.textContent = `Checking ${done}/${cases.length}`;
      }
    }
  };
  await Promise.all([worker(), worker(), worker(), worker()]);
  btn.textContent = "Run all checks";
  btn.disabled = false;
  bar.hidden = true;
  refreshAll();
  if (state.selected) stage.show(state.selected);
}

function resultsJson() {
  return JSON.stringify({
    addon: state.manifest.addon_version, generated: state.manifest.generated,
    cases: state.manifest.cases.map((c) => {
      const r = state.results.get(c.id);
      const checks = r ? r.checks : structuralChecks(c);
      return { id: c.id, status: statusOf(c), failing: checks.filter((k) => !k.ok).map((k) => ({ rule: k.rule, file: k.file, expected: k.expected, found: k.found })) };
    }),
  }, null, 1);
}

function bind() {
  const f = state.filters;
  const map = { q: "q", "f-matrix": "matrix", "f-layout": "layout", "f-format": "format", "f-mode": "mode", "f-status": "status", sort: "sort" };
  $("f-mode").innerHTML = `<option value="">Any mode</option>` + Object.entries(MODES).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");
  for (const [id, key] of Object.entries(map)) {
    $(id).value = f[key] || (key === "sort" ? "id" : "");
    $(id).addEventListener(id === "q" ? "input" : "change", (e) => { f[key] = e.target.value; store.set("filters", f); renderList(); });
  }
  $("flagfilter").addEventListener("click", (e) => {
    const b = e.target.closest(".flagbtn");
    if (!b) return;
    const next = { any: "on", on: "off", off: "any" }[b.dataset.v];
    f.flags[b.dataset.flag] = next;
    store.set("filters", f);
    renderFlagFilter();
    renderList();
  });
  const pick = (e) => {
    const el = e.target.closest("[data-id]");
    if (!el) return;
    const c = state.manifest.cases.find((x) => x.id === el.dataset.id);
    if (!c) return;
    if (state.tab !== "lineup" && !e.target.closest(".case")) setTab("lineup");
    selectCase(c, { scroll: true });
  };
  $("cases").addEventListener("click", pick);
  $("grids").addEventListener("click", pick);
  $("outcomes").addEventListener("click", pick);
  $("rules").addEventListener("click", pick);
  $("tree").addEventListener("click", (e) => { const li = e.target.closest("li.file"); if (li) selectFile(li.dataset.path); });
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));
  $("runall").addEventListener("click", runAll);
  $("copy").addEventListener("click", () => {
    const text = resultsJson();
    navigator.clipboard?.writeText(text).then(
      () => { $("copy").textContent = "Copied"; setTimeout(() => ($("copy").textContent = "Copy results"), 1500); },
      () => { $("copy").textContent = "Copy failed"; },
    );
  });
}

async function boot() {
  const [manifest, scene] = await Promise.all(["manifest.json", "scene.json"].map((u) => fetch(u).then((r) => r.json())));
  state.manifest = manifest;
  state.scene = scene;
  state.meshNames = new Set(Object.entries(scene.objects).filter(([, o]) => o.type === "MESH").map(([n]) => n));
  // Unity's own import of every FBX (unity_dump.py); optional
  state.unity = await fetch("unity.json").then((r) => (r.ok ? r.json() : null)).catch(() => null);
  $("ver").textContent = `Mass Collection Exporter ${manifest.addon_version} · Blender ${manifest.blender.split(" ")[0]} · run ${manifest.generated}`;
  bind();
  bindViewport();
  renderViewPanel();
  renderFlagFilter();
  renderStats();
  renderList();
  setTab(state.tab);
  const wanted = location.hash.slice(1) || store.get("case", "assets-glb-010000");
  const first = manifest.cases.find((c) => c.id === wanted) || manifest.cases.find((c) => c.id === "assets-glb-010000") || manifest.cases[0];
  selectCase(first, { scroll: true });
}

boot().catch((e) => {
  $("ver").textContent = `Could not load the run: ${e.message}. Serve this folder over http (python -m http.server) next to manifest.json.`;
});
