"""Run Mass Collection Exporter through every export-mode permutation of the Export Lab scene.

    blender --background --factory-startup --python run_matrix.py -- <addon __init__.py> <lab.blend> <out_dir> [case_filter]

Writes into <out_dir>:
    scene.json      what the oracle needs to know about the source scene
    manifest.json   one entry per case: settings, files written, source-untouched diff, log
    cases/<id>/     the exported files, one folder per collection row (as the exporter wrote them)
    blobs/          each distinct file once; manifest file entries point at them ("blob")
    index.html ...  the Export Lab viewer, copied from ./viewer

Then:  python serve.py <out_dir> 8000   and open http://localhost:8000

Matrix A ("modes"): the six mode switches (Whole, Suffix, Sub-Collections, Empties, Join, Merge),
all 64 combinations x 3 formats x 2 row layouts. Matrix B ("options"): one option flipped at a
time on top of each distinct mode, glTF only. SPEC.md defines the expected result of each.
"""
import bpy
import contextlib
import hashlib
import importlib.util
import io
import itertools
import json
import os
import shutil
import sys
import time

argv = sys.argv[sys.argv.index("--") + 1:]
ADDON, LAB, OUT = argv[0], argv[1], os.path.abspath(argv[2])
FILTER = argv[3] if len(argv) > 3 else ""
HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("mass_collection_exporter", ADDON)
mx = importlib.util.module_from_spec(spec)
sys.modules["mass_collection_exporter"] = mx
spec.loader.exec_module(mx)
mx.register()
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(LAB), load_ui=False)

FLAGS = ("whole", "suffix", "subcoll", "empties", "join", "merge")
FORMATS = ("FBX", "OBJ", "GLTF")
LAYOUTS = {
    # one row: the parent collection into one folder
    "parent": ("Nature",),
    # the house setup: one row per asset, each into its own folder
    "assets": ("Stone", "Plant", "Tree"),
}
BASE_MODES = {
    "individual": "000000", "merge": "000001", "suffix": "010000", "subcoll": "001000",
    "empties": "000100", "join": "000110", "whole": "100000", "subcoll_join": "001110",
}
OPTIONS = {
    # name: (applies to modes, {global prop: value}, {row prop: value}, extra)
    "apply_modifiers_off": (None, {"apply_modifiers": False}, {}, None),
    "only_visible_off": (None, {"apply_only_visible_modifiers": False}, {}, None),
    "move_to_center_off": (None, {}, {"move_to_center": False}, None),
    "apply_transforms_on": (None, {"apply_transforms": True}, {}, None),
    "m_prefix_on": (None, {"add_m_prefix": True}, {}, None),
    "materials_overwrite": (None, {"material_mode": "OVERWRITE"}, {}, "override"),
    "materials_fill_empty": (None, {"material_mode": "FILL"}, {}, "override"),
    "export_hidden_off": (None, {"export_hidden_collections": False}, {}, None),
    "suffixes_all_disabled": (("suffix",), {}, {}, "suffix_off"),
    "custom_name": (("whole",), {}, {"single_fbx_custom_name": "Nature_Pack"}, None),
    "relative_path": (("individual", "whole"), {}, {}, "relative"),
    "fbx_apply_transform_on": (None, {}, {}, None),
    "fbx_apply_transform_off": (None, {"bake_space_transform": False}, {}, None),
}
# FBX settings sweep: Apply Transform x Apply Scalings x axis preset, on the hierarchy modes.
# Unity: -Z forward / Y up. Blender default (Unreal, Godot): Y forward / Z up.
FBX_AXES = {"unity": ("-Z", "Y"), "blender": ("Y", "Z")}
for _bake in (True, False):
    for _scale in ("FBX_SCALE_NONE", "FBX_SCALE_UNITS", "FBX_SCALE_ALL"):
        for _axes, (_fwd, _up) in FBX_AXES.items():
            OPTIONS[f"fbx_{'bake' if _bake else 'nobake'}_{_scale[10:].lower()}_{_axes}"] = (
                ("whole", "suffix", "empties"),
                {"bake_space_transform": _bake, "apply_scaling": _scale, "axis_forward": _fwd, "axis_up": _up},
                {}, None)
# Options judged in another format than glTF
OPTION_FORMAT = {k: "FBX" for k in OPTIONS if k.startswith("fbx_")}
EXT = {"FBX": "fbx", "OBJ": "obj", "GLTF": "glb"}


# --------------------------------------------------------------------------- scene facts

def _with_modifiers(obj, mode, fn):
    """Call fn(mesh, matrix_world) on obj's mesh as 'raw', 'visible' or 'all' modifiers."""
    if mode == "raw":
        return fn(obj.data, obj.matrix_world)
    saved = [(m, m.show_viewport) for m in obj.modifiers]
    if mode == "all":
        for m in obj.modifiers:
            m.show_viewport = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    try:
        return fn(me, obj.matrix_world)
    finally:
        bpy.data.meshes.remove(me)
        for m, v in saved:
            m.show_viewport = v
        bpy.context.view_layer.update()


def world_bbox(obj, mode):
    """World-space [min, max] of obj's geometry, rounded."""
    def fn(me, mw):
        pts = [mw @ v.co for v in me.vertices]
        return [[round(min(p[i] for p in pts), 4) for i in range(3)],
                [round(max(p[i] for p in pts), 4) for i in range(3)]]
    return _with_modifiers(obj, mode, fn)


def tri_count(obj, mode):
    """Triangles of obj: 'raw' base mesh, 'visible' with viewport-enabled modifiers,
    'all' with every modifier switched on."""
    if obj.type != 'MESH':
        return None
    if mode == "raw":
        me = obj.data
        me.calc_loop_triangles()
        return len(me.loop_triangles)
    saved = [(m, m.show_viewport) for m in obj.modifiers]
    if mode == "all":
        for m in obj.modifiers:
            m.show_viewport = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    bpy.data.meshes.remove(me)
    for m, v in saved:
        m.show_viewport = v
    bpy.context.view_layer.update()
    return n


def scene_facts():
    vl = bpy.context.view_layer
    Op = mx.MASSEXPORTER_OT_export_all

    def lc_of(c):
        path = Op._get_layer_collection_path(vl.layer_collection, c)
        return path[-1] if path else None

    def walk(c):
        lc = lc_of(c)
        return {
            "name": c.name,
            "objects": [o.name for o in c.objects],
            "children": [walk(ch) for ch in c.children],
            "hidden_self": bool(c.hide_viewport or (lc and (lc.exclude or lc.hide_viewport))),
            "hidden": Op._collection_is_hidden(c),
        }

    objs = {}
    for o in bpy.data.objects:
        objs[o.name] = {
            "type": o.type,
            "parent": o.parent.name if o.parent else None,
            "collections": [c.name for c in o.users_collection],
            "world": [round(v, 4) for v in o.matrix_world.translation],
            "materials": [s.material.name if s.material else None for s in o.material_slots],
            "modifiers": [{"name": m.name, "type": m.type, "visible": m.show_viewport} for m in o.modifiers],
            "tris": {k: tri_count(o, k) for k in ("raw", "visible", "all")} if o.type == 'MESH' else None,
            "bbox": {k: world_bbox(o, k) for k in ("raw", "visible", "all")} if o.type == 'MESH' else None,
        }
    return {"blend": os.path.basename(LAB), "blender": bpy.app.version_string,
            "addon_version": ".".join(map(str, mx.VERSION)),
            "root": walk(bpy.context.scene.collection), "objects": objs}


# --------------------------------------------------------------------------- source snapshot

def snapshot():
    bpy.context.view_layer.update()
    s = {}
    for o in bpy.data.objects:
        d = {"mw": tuple(round(v, 5) for row in o.matrix_world for v in row),
             "parent": o.parent.name if o.parent else None,
             "data": o.data.name if o.data else None,
             "mods": [(m.name, m.show_viewport) for m in o.modifiers],
             "colls": sorted(c.name for c in o.users_collection),
             "hide": (o.hide_viewport, o.hide_get(), o.hide_select)}
        if o.type == "MESH":
            h = hashlib.md5()
            for v in o.data.vertices:
                h.update(repr(tuple(round(x, 5) for x in v.co)).encode())
            d["verts"] = h.hexdigest()
            d["mats"] = [m.name if m else None for m in o.data.materials]
        s["obj:" + o.name] = d
    s["materials"] = sorted(m.name for m in bpy.data.materials)
    s["objects"] = sorted(o.name for o in bpy.data.objects)

    def walk(lc, acc):
        acc[lc.name] = (lc.exclude, lc.hide_viewport)
        for ch in lc.children:
            walk(ch, acc)
        return acc
    s["layer"] = walk(bpy.context.view_layer.layer_collection, {})
    return s


def diff(a, b):
    return [f"{k}: {a.get(k)} -> {b.get(k)}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


# --------------------------------------------------------------------------- cases

def bits_to_flags(bits):
    return {f: b == "1" for f, b in zip(FLAGS, bits)}


def build_cases():
    cases = []
    for layout, fmt, combo in itertools.product(LAYOUTS, FORMATS, itertools.product("01", repeat=6)):
        bits = "".join(combo)
        cases.append({"id": f"{layout}-{EXT[fmt]}-{bits}", "matrix": "modes", "layout": layout,
                      "rows": list(LAYOUTS[layout]),
                      "format": fmt, "flags": bits_to_flags(bits), "bits": bits,
                      "option": None, "global": {}, "row": {}, "extra": None})
    for mode, bits in BASE_MODES.items():
        for opt, (modes, g, r, extra) in OPTIONS.items():
            if modes and mode not in modes:
                continue
            cases.append({"id": f"opt-{opt}-{mode}", "matrix": "options", "layout": "parent",
                          "rows": list(LAYOUTS["parent"]),
                          "format": OPTION_FORMAT.get(opt, "GLTF"), "flags": bits_to_flags(bits), "bits": bits,
                          "base_mode": mode, "option": opt, "global": g, "row": r, "extra": extra})
    return cases


def configure(case, case_dir):
    p = bpy.context.scene.mass_exporter_props
    for k in p.bl_rna.properties.keys():
        if k in ("rna_type", "name", "collection_items", "suffix_items", "override_material"):
            continue
        try:
            p.property_unset(k)
        except Exception:
            pass
    p.apply_modifiers = True
    p.apply_only_visible_modifiers = True
    p.export_format = case["format"]
    p.override_material = bpy.data.materials["M_Override"]
    p.suffix_items.clear()
    for suffix, desc in (("_COL", "Collision"), ("_LOD1", "LOD Level 1")):
        s = p.suffix_items.add()
        s.suffix, s.description = suffix, desc
        s.enabled = case["extra"] != "suffix_off"
    for k, v in case["global"].items():
        setattr(p, k, v)

    p.collection_items.clear()
    for name in LAYOUTS[case["layout"]]:
        row = p.collection_items.add()
        row.collection = bpy.data.collections[name]
        row.export_enabled = True
        if case["extra"] == "relative":
            row.export_path = f"//ExportLab_relative_{case['id']}/{name}/"
        else:
            row.export_path = os.path.join(case_dir, name) + os.sep
        f = case["flags"]
        row.export_as_single_fbx = f["whole"]
        row.use_suffix_grouping = f["suffix"]
        row.export_subcollections_as_single = f["subcoll"]
        row.use_empty_origins = f["empties"]
        row.join_empty_children = f["join"]
        row.merge_to_single = f["merge"]
        for k, v in case["row"].items():
            setattr(row, k, v)


def list_files(root):
    out = []
    for d, _dirs, names in os.walk(root):
        for n in sorted(names):
            full = os.path.join(d, n)
            out.append({"path": os.path.relpath(full, root).replace(os.sep, "/"),
                        "size": os.path.getsize(full)})
    return sorted(out, key=lambda f: f["path"])


def run_case(case):
    case_dir = os.path.join(OUT, "cases", case["id"])
    shutil.rmtree(case_dir, ignore_errors=True)
    os.makedirs(case_dir)
    configure(case, case_dir)
    # Start every case from an empty selection, hidden objects included, so a selection one
    # case leaves behind cannot leak into the next one's files (it is reported as its own check)
    for o in bpy.data.objects:
        o.select_set(False)
    before = snapshot()
    log = io.StringIO()
    t0 = time.time()
    result, error = None, None
    with contextlib.redirect_stdout(log):
        try:
            result = sorted(bpy.ops.massexporter.export_all())
        except Exception as e:      # the operator returns CANCELLED for a failed run
            error = str(e)
    elapsed = time.time() - t0
    after = snapshot()
    changed = diff(before, after)
    left_selected = sorted(o.name for o in bpy.data.objects if o.select_get())
    files = list_files(case_dir)
    if not files:
        shutil.rmtree(case_dir, ignore_errors=True)
    if case["extra"] == "relative":
        # where did '//' go? Record and remove anything written next to the .blend or the cwd
        hits = []
        for base in (os.path.dirname(bpy.data.filepath), os.getcwd(), "\\\\"):
            cand = os.path.join(base, f"ExportLab_relative_{case['id']}")
            if base != "\\\\" and os.path.isdir(cand):
                hits.append(cand)
                shutil.rmtree(cand, ignore_errors=True)
        case["relative_written_to"] = hits
    case.update({
        "result": result, "error": error, "seconds": round(elapsed, 3),
        "files": files, "source_changed": changed[:20], "source_changed_count": len(changed),
        "left_selected": left_selected,
        "log": [l for l in log.getvalue().splitlines() if l.strip()][-30:],
    })
    return case


def write_blobs(cases):
    """Store each distinct file once under blobs/<hash>.<ext> and point every case file at it.

    Most switch combinations produce byte-identical files, so this shrinks 1900 files to a
    few hundred - small enough to publish the whole run. FBX hashes skip the creation
    timestamp, the only difference between two identical FBX exports."""
    blob_dir = os.path.join(OUT, "blobs")
    shutil.rmtree(blob_dir, ignore_errors=True)
    os.makedirs(blob_dir)
    names = set()
    for case in cases:
        for f in case["files"]:
            data = open(os.path.join(OUT, "cases", case["id"], f["path"]), "rb").read()
            ext = f["path"].rsplit(".", 1)[-1]
            key = data
            if ext == "fbx":
                i = data.find(b"CreationTimeStamp")
                j = data.find(b"Creator", i)
                if 0 < i < j:
                    key = data[:i] + data[j:]
            name = f"{hashlib.sha1(key).hexdigest()[:16]}.{ext}"
            if name not in names:
                names.add(name)
                open(os.path.join(blob_dir, name), "wb").write(data)
            f["blob"] = name
    return len(names)


def main():
    os.makedirs(OUT, exist_ok=True)
    if "M_Override" not in bpy.data.materials:
        m = bpy.data.materials.new("M_Override")
        m.diffuse_color = (1.0, 0.0, 1.0, 1.0)
    facts = scene_facts()
    json.dump(facts, open(os.path.join(OUT, "scene.json"), "w"), indent=1)

    cases = [c for c in build_cases() if FILTER in c["id"]]
    t0 = time.time()
    done = []
    for i, case in enumerate(cases):
        done.append(run_case(case))
        if i % 25 == 0:
            print(f"[{i + 1}/{len(cases)}] {case['id']} files={len(case['files'])}", file=sys.__stdout__)
    blob_count = write_blobs(done)
    manifest = {"generated": time.strftime("%Y-%m-%d %H:%M"), "blender": bpy.app.version_string,
                "blobs": blob_count,
                "addon_version": facts["addon_version"], "flags": FLAGS, "layouts": LAYOUTS,
                "seconds": round(time.time() - t0, 1), "cases": done}
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)

    viewer = os.path.join(HERE, "viewer")
    for n in os.listdir(viewer):
        shutil.copy2(os.path.join(viewer, n), os.path.join(OUT, n))
    print(f"{len(done)} cases in {manifest['seconds']}s -> {OUT}", file=sys.__stdout__)


main()
