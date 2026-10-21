"""Headless behaviour tests for Mass Collection Exporter.

Run from the repo root:
    blender --background --factory-startup --python Blender/Addons/MassExporter/source/tests/headless_export_test.py -- Blender/Addons/MassExporter/source/__init__.py <out_dir> [test_prefix,...]

Each test builds a small scene, runs an operator, re-imports the files and checks the
result plus that the source scene is unchanged. Prints PASS/FAIL and a summary.
"""
import bpy, sys, os, shutil, importlib.util, traceback, hashlib

argv = sys.argv[sys.argv.index("--") + 1:]
ADDON, OUT = argv[0], argv[1]
ONLY = argv[2].split(",") if len(argv) > 2 else None

spec = importlib.util.spec_from_file_location("mass_collection_exporter", ADDON)
mx = importlib.util.module_from_spec(spec)
sys.modules["mass_collection_exporter"] = mx
spec.loader.exec_module(mx)
mx.register()

RESULTS = []


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures):
        for b in list(blocks):
            blocks.remove(b)
    p = bpy.context.scene.mass_exporter_props
    p.collection_items.clear()
    p.suffix_items.clear()
    # reset every scene prop to its default
    for k in p.bl_rna.properties.keys():
        if k in ("rna_type", "name", "collection_items", "suffix_items"):
            continue
        try:
            p.property_unset(k)
        except Exception:
            pass
    bpy.context.view_layer.update()


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def cube(name, c, loc=(0, 0, 0), size=1.0):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = loc
    c.objects.link(o)
    return o


def empty(name, c, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    c.objects.link(o)
    return o


def parent(child, par):
    bpy.context.view_layer.update()
    child.parent = par
    child.matrix_parent_inverse = par.matrix_world.inverted()


def item(c, path, **kw):
    p = bpy.context.scene.mass_exporter_props
    it = p.collection_items.add()
    it.collection = c
    it.export_enabled = True
    it.export_path = path
    for k, v in kw.items():
        setattr(it, k, v)
    return it


def snapshot():
    """Everything an exporter must leave untouched."""
    bpy.context.view_layer.update()
    s = {}
    for o in bpy.data.objects:
        d = {
            "type": o.type,
            "loc": tuple(round(v, 5) for v in o.location),
            "mw": tuple(round(v, 5) for row in o.matrix_world for v in row),
            "parent": o.parent.name if o.parent else None,
            "data": o.data.name if o.data else None,
            "mods": [(m.name, m.show_viewport) for m in o.modifiers],
            "colls": sorted(c.name for c in o.users_collection),
            "hide": (o.hide_viewport, o.hide_get(), o.hide_select),
        }
        if o.type == "MESH":
            h = hashlib.md5()
            for v in o.data.vertices:
                h.update(repr(tuple(round(x, 5) for x in v.co)).encode())
            d["verts"] = h.hexdigest()
            d["mats"] = [m.name if m else None for m in o.data.materials]
        s["obj:" + o.name] = d
    s["materials"] = sorted(m.name for m in bpy.data.materials)
    s["meshes_with_users"] = sorted(m.name for m in bpy.data.meshes if m.users)

    def walk(lc, acc):
        acc[lc.name] = (lc.exclude, lc.hide_viewport)
        for ch in lc.children:
            walk(ch, acc)
        return acc
    s["layer"] = walk(bpy.context.view_layer.layer_collection, {})
    s["collflags"] = {c.name: (c.hide_viewport, c.hide_render) for c in bpy.data.collections}
    return s


def diff(a, b):
    out = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            out.append(f"{k}: {a.get(k)} -> {b.get(k)}")
    return out


def inspect(path):
    """Import an exported file, return {name: info}, then delete what it brought in."""
    before = set(bpy.data.objects)
    before_me = set(bpy.data.meshes)
    before_mat = set(bpy.data.materials)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    info = {}
    for o in new:
        info[o.name] = {
            "type": o.type,
            "parent": o.parent.name if o.parent else None,
            "verts": len(o.data.vertices) if o.type == "MESH" else None,
            "world": tuple(round(v, 3) for v in o.matrix_world.translation),
            "mods": [m.type for m in o.modifiers],
            "mats": [m.name for m in o.data.materials] if o.type == "MESH" else None,
            "center": tuple(round(x, 3) for x in (sum(((o.matrix_world @ v.co) for v in o.data.vertices), __import__("mathutils").Vector()) / len(o.data.vertices))) if o.type == "MESH" and len(o.data.vertices) else None,
        }
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    for m in [m for m in bpy.data.meshes if m not in before_me]:
        bpy.data.meshes.remove(m)
    for m in [m for m in bpy.data.materials if m not in before_mat]:
        bpy.data.materials.remove(m)
    for a in [a for a in bpy.data.armatures if a.users == 0]:
        bpy.data.armatures.remove(a)
    return info


def files(d):
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def run_export(op="export_all"):
    try:
        r = getattr(bpy.ops.massexporter, op)()
        return r
    except Exception as e:
        return f"EXC {e}"


TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + ("  | " + str(detail) if detail else ""))


def outdir(name):
    d = os.path.join(OUT, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    return d


# --------------------------------------------------------------------------- tests

@test
def t01_default_per_object():
    d = outdir("t01")
    c = coll("Props")
    a = cube("propA", c, (3, 0, 0))
    b = cube("propB", c, (0, 5, 0))
    m = a.modifiers.new("Sub", "SUBSURF"); m.levels = 1
    item(c, d)
    s0 = snapshot()
    r = run_export()
    s1 = snapshot()
    check("t01 per-object files", files(d) == ["propA.fbx", "propB.fbx"], files(d))
    check("t01 source untouched", not diff(s0, s1), diff(s0, s1))
    ia = inspect(os.path.join(d, "propA.fbx"))
    va = [v["verts"] for v in ia.values() if v["type"] == "MESH"]
    check("t01 subsurf baked (26 verts)", va == [26], ia)
    check("t01 move_to_center default puts it at 0", all(v["world"] == (0, 0, 0) for v in ia.values()), ia)


@test
def t02_obj_default_axes():
    d = outdir("t02")
    c = coll("Props")
    cube("objA", c)
    item(c, d)
    bpy.context.scene.mass_exporter_props.export_format = "OBJ"
    r = run_export()
    check("t02 OBJ export with default axes writes a file", files(d) == ["objA.obj"] or "objA.obj" in files(d), files(d))


@test
def t03_dae_removed():
    ids = [i.identifier for i in bpy.context.scene.mass_exporter_props.bl_rna.properties["export_format"].enum_items]
    check("t03 DAE removed from Export Format", "DAE" not in ids, ids)


@test
def t04_gltf_extension():
    d = outdir("t04")
    c = coll("Props")
    cube("gA", c)
    item(c, d)
    bpy.context.scene.mass_exporter_props.export_format = "GLTF"
    run_export()
    check("t04 glTF output file name matches what is written (.glb)", files(d) == ["gA.glb"], files(d))


@test
def t05_override_materials_source():
    d = outdir("t05")
    c = coll("Props")
    a = cube("matA", c)
    orig = bpy.data.materials.new("Wood")
    a.data.materials.append(orig)
    ov = bpy.data.materials.new("Override")
    p = bpy.context.scene.mass_exporter_props
    p.material_mode = 'OVERWRITE'
    p.override_material = ov
    item(c, d)
    s0 = snapshot()
    run_export()
    s1 = snapshot()
    check("t05 override materials leaves source untouched", not diff(s0, s1), diff(s0, s1))
    info = inspect(os.path.join(d, "matA.fbx"))
    check("t05 exported file carries override", any(v["mats"] and v["mats"][0].startswith("Override") for v in info.values()), info)


@test
def t06_m_prefix_renames_all():
    d = outdir("t06")
    c = coll("Props")
    a = cube("mpA", c)
    a.data.materials.append(bpy.data.materials.new("Wood"))
    bpy.data.materials.new("UnrelatedMat").use_fake_user = True
    ov = bpy.data.materials.new("Override")
    p = bpy.context.scene.mass_exporter_props
    p.material_mode = 'OVERWRITE'
    p.override_material = ov
    p.add_m_prefix = True
    item(c, d)
    s0 = snapshot()
    run_export()
    s1 = snapshot()
    check("t06 M_ prefix does not rename source materials", s0["materials"] == s1["materials"],
          (s0["materials"], s1["materials"]))


@test
def t07_assign_if_no_material_alone():
    d = outdir("t07")
    c = coll("Props")
    cube("nomat", c)
    ov = bpy.data.materials.new("Fallback")
    p = bpy.context.scene.mass_exporter_props
    p.override_material = ov          # legacy pre-13.9 checkbox, read as Fill Empty
    p.assign_if_no_material = True
    item(c, d)
    run_export()
    info = inspect(os.path.join(d, "nomat.fbx"))
    check("t07 'assign if no material' works without override", any(v["mats"] and v["mats"][0].startswith("Fallback") for v in info.values()), info)


def _two_children_rig(c):
    e = empty("Root", c, (10, 0, 0))
    a = cube("partA", c, (10, 0, 0))
    b = cube("partB", c, (12, 0, 0))
    parent(a, e); parent(b, e)
    ma = a.modifiers.new("SubA", "SUBSURF"); ma.levels = 1   # 8 -> 26
    mb = b.modifiers.new("ArrB", "ARRAY"); mb.count = 3      # 8 -> 24
    return e, a, b


@test
def t08_join_keeps_each_childs_modifiers():
    d = outdir("t08")
    c = coll("Joined")
    _two_children_rig(c)
    item(c, d, use_empty_origins=True, join_empty_children=True)   # apply_modifiers_before_join default OFF
    s0 = snapshot()
    run_export()
    s1 = snapshot()
    check("t08 join source untouched", not diff(s0, s1), diff(s0, s1))
    info = inspect(os.path.join(d, "Root.fbx")) if "Root.fbx" in files(d) else {}
    verts = sum(v["verts"] or 0 for v in info.values())
    check("t08 joined mesh = 26 + 24 verts (each child's own modifiers)", verts == 50, f"files={files(d)} verts={verts} {info}")


@test
def t09_join_apply_bakes_hidden():
    d = outdir("t09")
    c = coll("Joined")
    e, a, b = _two_children_rig(c)
    b.modifiers["ArrB"].show_viewport = False                      # user hid it
    item(c, d, use_empty_origins=True, join_empty_children=True, apply_modifiers_before_join=True)
    run_export()
    info = inspect(os.path.join(d, "Root.fbx")) if "Root.fbx" in files(d) else {}
    verts = sum(v["verts"] or 0 for v in info.values())
    check("t09 join+apply skips viewport-hidden modifier (26 + 8)", verts == 34, f"verts={verts}")


@test
def t10_empty_individual_drops_loose():
    d = outdir("t10")
    c = coll("Mixed")
    e = empty("Holder", c, (4, 0, 0))
    ch = cube("child", c, (4, 0, 0)); parent(ch, e)
    cube("loose", c, (-4, 0, 0))
    item(c, d, use_empty_origins=True)
    run_export()
    fs = files(d)
    check("t10 loose mesh (no parent empty) still exported in empty mode", any("loose" in f for f in fs), fs)


@test
def t11_suffix_double_export():
    d = outdir("t11")
    c = coll("Suffix")
    e = empty("crate", c, (0, 0, 0))
    m = cube("crate_mesh", c); parent(m, e)
    cube("barrel", c)
    cube("barrel_COL", c)
    p = bpy.context.scene.mass_exporter_props
    s = p.suffix_items.add(); s.suffix = "_COL"
    item(c, d, use_suffix_grouping=True)
    run_export()
    fs = files(d)
    check("t11 suffix grouping: crate child exported once (crate.fbx only)",
          fs == ["barrel.fbx", "crate.fbx"], fs)
    if "barrel.fbx" in fs:
        info = inspect(os.path.join(d, "barrel.fbx"))
        check("t11 barrel.fbx contains barrel + barrel_COL", sorted(k.split(".")[0] for k in info) == ["barrel", "barrel_COL"], sorted(info))


@test
def t12_whole_collection_hierarchy_with_modifiers():
    d = outdir("t12")
    c = coll("Vehicle")
    body = cube("body", c, (0, 0, 0))
    wheel = cube("wheel", c, (2, 0, 0), size=0.5)
    parent(wheel, body)
    body.modifiers.new("Bev", "BEVEL")
    item(c, d, export_as_single_fbx=True)
    s0 = snapshot()
    run_export()
    s1 = snapshot()
    check("t12 whole-collection source untouched", not diff(s0, s1), diff(s0, s1))
    info = inspect(os.path.join(d, "Vehicle.fbx"))
    par = [v["parent"] for k, v in info.items() if k.startswith("wheel")]
    check("t12 wheel stays parented to body in FBX", par and par[0] and par[0].startswith("body"), info)


@test
def t12b_whole_collection_hierarchy_no_modifiers():
    d = outdir("t12b")
    c = coll("Vehicle")
    body = cube("body", c)
    wheel = cube("wheel", c, (2, 0, 0), size=0.5)
    parent(wheel, body)
    item(c, d, export_as_single_fbx=True)
    run_export()
    info = inspect(os.path.join(d, "Vehicle.fbx"))
    par = [v["parent"] for k, v in info.items() if k.startswith("wheel")]
    check("t12b control: hierarchy kept when no modifiers", par and par[0] and par[0].startswith("body"), info)


@test
def t13_move_to_center_is_per_row():
    d = outdir("t13")
    ca = coll("A_moves")
    cb = coll("B_stays")
    ea = empty("EA", ca, (5, 0, 0)); ma = cube("ma", ca, (5, 0, 0)); parent(ma, ea)
    eb = empty("EB", cb, (7, 0, 0)); mb = cube("mb", cb, (7, 0, 0)); parent(mb, eb)
    item(ca, os.path.join(d, "a"), use_empty_origins=True)
    item(cb, os.path.join(d, "b"), use_empty_origins=True, move_to_center=False)
    s0 = snapshot()
    run_export()
    s1 = snapshot()
    check("t13 source restored", not diff(s0, s1), diff(s0, s1))
    wa = [v["center"] for v in inspect(os.path.join(d, "a", "EA.fbx")).values() if v["type"] == "MESH"]
    wb = [v["center"] for v in inspect(os.path.join(d, "b", "EB.fbx")).values() if v["type"] == "MESH"]
    check("t13 row A (Move to Center) at 0, row B (off) keeps x=7", wa == [(0, 0, 0)] and wb == [(7, 0, 0)], (wa, wb))


@test
def t14_shape_keys_drop_modifier():
    d = outdir("t14")
    c = coll("SK")
    a = cube("skA", c)
    a.shape_key_add(name="Basis"); a.shape_key_add(name="K1")
    m = a.modifiers.new("Sub", "SUBSURF"); m.levels = 1
    item(c, d)
    run_export()
    info = inspect(os.path.join(d, "skA.fbx"))
    verts = [v["verts"] for v in info.values() if v["type"] == "MESH"]
    check("t14 mesh with shape keys still gets its modifier baked", verts == [26], verts)


@test
def t15_whole_collection_apply_transforms():
    d = outdir("t15")
    c = coll("Scaled")
    a = cube("big", c)
    a.scale = (3, 3, 3)
    bpy.context.scene.mass_exporter_props.apply_transforms = True
    item(c, d, export_as_single_fbx=True)
    run_export()
    info = inspect(os.path.join(d, "Scaled.fbx"))
    # with transforms applied the imported object has unit scale
    check("t15 Apply Transforms honoured in whole-collection mode", True, "see scale below")
    o = None
    bpy.ops.import_scene.fbx(filepath=os.path.join(d, "Scaled.fbx"))
    o = bpy.context.selected_objects[0]
    sc = tuple(round(v, 3) for v in o.scale)
    RESULTS.pop()
    check("t15 Apply Transforms honoured in whole-collection mode", sc == (1.0, 1.0, 1.0), sc)
    bpy.data.objects.remove(o, do_unlink=True)


@test
def t16_join_preview_operator():
    c = coll("Prev")
    _two_children_rig(c)
    item(c, OUT)
    n0 = len(bpy.data.objects)
    run_export("join_empties")
    joined = [o for o in bpy.data.objects if o.name.startswith("Prev_joined")]
    check("t16 Join Empties preview creates a joined copy", len(joined) == 1, [o.name for o in bpy.data.objects])
    if joined:
        check("t16 preview origin at empty (x=10)", round(joined[0].matrix_world.translation.x, 3) == 10.0,
              tuple(joined[0].matrix_world.translation))


@test
def t17_quick_export_inherits_mode():
    d = outdir("t17")
    parent_c = coll("Char")
    sub = coll("Char_Cloth", parent_c)
    a = cube("shirt", sub)
    cube("pants", sub, (2, 0, 0))
    item(parent_c, d, export_as_single_fbx=True, use_suffix_grouping=False)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    a.select_set(True)
    bpy.context.view_layer.objects.active = a
    run_export("export_selected_collection")
    fs = files(d)
    check("t17 quick 'Export Collection of Selected' uses parent's Whole-Collection mode",
          fs == ["Char_Cloth.fbx"], fs)


@test
def t18_stale_xform_recovery():
    c = coll("Stale")
    o = cube("rock", c)
    o.name = "__mexport_xform_rock"
    item(c, outdir("t18"))
    run_export()
    names = sorted(x.name for x in bpy.data.objects)
    check("t18 crashed apply-transforms copy recovered to original name", "rock" in names, names)


@test
def t19_hidden_nested_restore():
    d = outdir("t19")
    top = coll("Top")
    mid = coll("Mid", top)
    cube("hid", mid)
    lc_top = mx._find_layer_collection(bpy.context.view_layer.layer_collection, top)
    lc_top.hide_viewport = True
    other = coll("ExcludedOther")
    cube("x", other)
    mx._find_layer_collection(bpy.context.view_layer.layer_collection, other).exclude = True
    item(mid, d)
    s0 = snapshot()
    run_export()
    s1 = snapshot()
    check("t19 hidden nested collection exported", files(d) == ["hid.fbx"], files(d))
    check("t19 visibility fully restored", not diff(s0, s1), diff(s0, s1))


@test
def t20_subcollections_mode():
    d = outdir("t20")
    top = coll("Kit")
    cube("base", top)
    s1c = coll("Kit_Door", top); cube("door1", s1c); cube("door2", s1c, (2, 0, 0))
    item(top, d, export_subcollections_as_single=True)
    run_export()
    check("t20 subcollections files", files(d) == ["Kit_Door.fbx", "Kit_main.fbx"], files(d))


@test
def t21_suffix_only_disabled():
    d = outdir("t21")
    c = coll("SufOff")
    cube("wall", c); cube("wall_COL", c)
    p = bpy.context.scene.mass_exporter_props
    s = p.suffix_items.add(); s.suffix = "_COL"; s.enabled = False
    item(c, d, use_suffix_grouping=True, merge_to_single=True)
    run_export()
    check("t21 all suffixes disabled -> falls back to Merge (SufOff.fbx)", files(d) == ["SufOff.fbx"], files(d))


@test
def t22_rig_export_and_binding():
    d = outdir("t22")
    c = coll("Rigged")
    rigc = coll("Rigs")
    arm = bpy.data.armatures.new("ArmData")
    rig = bpy.data.objects.new("Rig", arm)
    rigc.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    b = arm.edit_bones.new("Bone"); b.head = (0, 0, 0); b.tail = (0, 0, 1)
    bpy.ops.object.mode_set(mode="OBJECT")
    m = cube("skin", c)
    m.modifiers.new("Arm", "ARMATURE").object = rig
    m.vertex_groups.new(name="Bone").add(range(8), 1.0, "REPLACE")
    m.modifiers.new("Sub", "SUBSURF").levels = 1
    p = bpy.context.scene.mass_exporter_props
    p.export_rig_with_mesh = True
    item(c, d, move_to_center=False)
    s0 = snapshot()
    run_export()
    s1 = snapshot()
    check("t22 rig export source untouched", not diff(s0, s1), diff(s0, s1))
    info = inspect(os.path.join(d, "skin.fbx"))
    types = sorted(v["type"] for v in info.values())
    sk = [v for v in info.values() if v["type"] == "MESH"]
    check("t22 rig shipped with mesh and binding kept", "ARMATURE" in types and sk and "ARMATURE" in sk[0]["mods"], info)


@test
def t23_join_per_empty_with_grandchildren():
    d = outdir("t23")
    c = coll("Deep")
    e = empty("Root", c, (1, 0, 0))
    a = cube("a", c, (1, 0, 0)); parent(a, e)
    b = cube("b", c, (3, 0, 0)); parent(b, a)       # grandchild
    cube("loose", c, (-3, 0, 0))
    item(c, d, use_empty_origins=True, join_empty_children=True)
    run_export()
    check("t23 one joined file per empty + loose mesh on its own", files(d) == ["Root.fbx", "loose.fbx"], files(d))
    info = inspect(os.path.join(d, "Root.fbx")) if "Root.fbx" in files(d) else {}
    meshes = {k: v for k, v in info.items() if v["type"] == "MESH"}
    check("t23 Root.fbx = one mesh 'Root' of a + grandchild b (16 verts)",
          len(meshes) == 1 and next(iter(meshes)).startswith("Root") and next(iter(meshes.values()))["verts"] == 16, info)
    check("t23 no temp objects left", sorted(o.name for o in bpy.data.objects) == ["Root", "a", "b", "loose"],
          sorted(o.name for o in bpy.data.objects))


@test
def t24_quick_selected_objects_respects_merge():
    d = outdir("t24")
    c = coll("Sel")
    a = cube("s1", c); b = cube("s2", c, (2, 0, 0))
    item(c, d)
    for o in bpy.data.objects:
        o.select_set(False)
    a.select_set(True); b.select_set(True)
    bpy.context.view_layer.objects.active = a
    run_export("export_selected_objects")
    check("t24 Export Selected Object(s), Merge off -> one file each", files(d) == ["s1.fbx", "s2.fbx"], files(d))


@test
def t25_duplicate_data_pref_off():
    d = outdir("t25")
    prefs = bpy.context.preferences.edit
    old = prefs.use_duplicate_mesh
    prefs.use_duplicate_mesh = False
    try:
        c = coll("Pref")
        a = cube("pa", c)
        a.modifiers.new("Sub", "SUBSURF").levels = 1
        item(c, d)
        s0 = snapshot()
        run_export()
        s1 = snapshot()
        info = inspect(os.path.join(d, "pa.fbx"))
        verts = [v["verts"] for v in info.values()]
        check("t25 'Duplicate Data: Mesh' off -> modifier still baked", verts == [26], verts)
        check("t25 'Duplicate Data: Mesh' off -> source untouched", not diff(s0, s1), diff(s0, s1))
    finally:
        prefs.use_duplicate_mesh = old


@test
def t26_object_linked_material_restore():
    d = outdir("t26")
    c = coll("ObjMat")
    a = cube("om", c)
    a.data.materials.append(bpy.data.materials.new("DataMat"))
    a.material_slots[0].link = "OBJECT"
    a.material_slots[0].material = bpy.data.materials.new("ObjMat")
    p = bpy.context.scene.mass_exporter_props
    p.material_mode = 'OVERWRITE'
    p.override_material = bpy.data.materials.new("Override")
    item(c, d)
    slot0 = (a.material_slots[0].link, a.material_slots[0].material.name, a.data.materials[0].name)
    run_export()
    slot1 = (a.material_slots[0].link, a.material_slots[0].material.name, a.data.materials[0].name)
    check("t26 object-linked material slot restored", slot0 == slot1, (slot0, slot1))


@test
def t27_whole_collection_xform_and_mods_hierarchy():
    d = outdir("t27")
    c = coll("Tank")
    body = cube("hull", c)
    body.scale = (2, 2, 2)
    body.modifiers.new("Bev", "BEVEL")
    turret = cube("turret", c, (0, 0, 3), size=0.5)
    parent(turret, body)
    bpy.context.scene.mass_exporter_props.apply_transforms = True
    item(c, d, export_as_single_fbx=True, move_to_center=False)
    s0 = snapshot()
    run_export()
    s1 = snapshot()
    check("t27 xform+mods whole collection: source untouched", not diff(s0, s1), diff(s0, s1))
    info = inspect(os.path.join(d, "Tank.fbx"))
    tur = [v for k, v in info.items() if k.startswith("turret")]
    ok = tur and tur[0]["parent"] and tur[0]["parent"].startswith("hull") and tur[0]["center"] == (0, 0, 3)
    check("t27 turret parented to hull and its geometry still at world z=3", ok, info)


@test
def t28_shape_keys_kept_on_source():
    d = outdir("t28")
    c = coll("SK2")
    a = cube("sk2", c)
    a.shape_key_add(name="Basis"); a.shape_key_add(name="K1")
    a.modifiers.new("Sub", "SUBSURF").levels = 1
    item(c, d)
    run_export()
    check("t28 source keeps its shape keys and modifier",
          a.data.shape_keys is not None and len(a.data.shape_keys.key_blocks) == 2 and len(a.modifiers) == 1,
          (a.data.shape_keys, len(a.modifiers)))


@test
def t29_center_each_empty_parented():
    d = outdir("t29")
    c = coll("Nest")
    holder = empty("Holder", c, (10, 0, 0))
    e = empty("Inner", c, (12, 0, 0)); parent(e, holder)
    m = cube("piece", c, (12, 0, 0)); parent(m, e)
    item(c, d, use_empty_origins=True)
    run_export()
    info = inspect(os.path.join(d, "Inner.fbx")) if "Inner.fbx" in files(d) else {}
    w = [v["world"] for v in info.values()]
    check("t29 Move to Center puts a parented empty's child at world 0", w == [(0, 0, 0)], f"{files(d)} {info}")


@test
def t30_empty_without_join_is_one_file():
    d = outdir("t30")
    c = coll("Assets")
    e = empty("Crate", c, (6, 0, 0))
    a = cube("lid", c, (6, 0, 1)); parent(a, e)
    b = cube("box", c, (6, 0, 0)); parent(b, e)
    item(c, d, use_empty_origins=True)
    run_export()
    check("t30 one file per empty, named after it", files(d) == ["Crate.fbx"], files(d))
    info = inspect(os.path.join(d, "Crate.fbx")) if "Crate.fbx" in files(d) else {}
    cen = sorted(v["center"] for v in info.values() if v["type"] == "MESH")
    check("t30 members kept as elements around the centred empty", cen == [(0, 0, 0), (0, 0, 1)], info)


@test
def t31_apply_transforms_keeps_center_of_parented_mesh():
    import math
    d = outdir("t31")
    c = coll("Pivot")
    e = empty("Asset", c, (4, 2, 0))
    e.rotation_euler = (0, 0, 0.5)
    bpy.context.view_layer.update()
    a = cube("part", c)
    a.matrix_world = e.matrix_world @ __import__("mathutils").Matrix.Translation((1, 0, 0))
    parent(a, e)
    bpy.context.scene.mass_exporter_props.apply_transforms = True
    item(c, d, use_empty_origins=True)
    s0 = snapshot()
    run_export()
    check("t31 source untouched", not diff(s0, snapshot()), diff(s0, snapshot()))
    info = inspect(os.path.join(d, "Asset.fbx")) if "Asset.fbx" in files(d) else {}
    v = [x for x in info.values() if x["type"] == "MESH"]
    want = (math.cos(0.5), math.sin(0.5), 0)
    ok = v and all(abs(p - q) < 0.002 for p, q in zip(v[0]["center"], want)) and v[0]["world"] == (0, 0, 0)
    check("t31 Apply Transforms + Move to Center: part 1 m from the centred empty, baked", ok, info)


@test
def t32_hidden_selection_does_not_leak():
    d = outdir("t32")
    c = coll("Row")
    cube("shown", c)
    sub = coll("HiddenSub", c)
    cube("ghost", sub, (3, 0, 0))
    bpy.context.view_layer.update()
    mx._find_layer_collection(bpy.context.view_layer.layer_collection, sub).hide_viewport = True
    item(c, d, merge_to_single=True)
    for o in bpy.data.objects:
        o.select_set(False)
    run_export()
    sel = [o.name for o in bpy.data.objects if o.select_get()]
    check("t32 nothing left selected after exporting a hidden sub-collection", sel == [], sel)


@test
def t33_hidden_sub_skipped_when_toggle_off():
    d = outdir("t33")
    c = coll("Row")
    cube("shown", c)
    sub = coll("HiddenSub", c)
    cube("ghost", sub, (3, 0, 0))
    bpy.context.view_layer.update()
    mx._find_layer_collection(bpy.context.view_layer.layer_collection, sub).hide_viewport = True
    bpy.context.scene.mass_exporter_props.export_hidden_collections = False
    item(c, d)
    s0 = snapshot()
    run_export()
    check("t33 hidden sub-collection left out with the toggle off", files(d) == ["shown.fbx"], files(d))
    check("t33 visibility restored", not diff(s0, snapshot()), diff(s0, snapshot()))


@test
def t34_join_fill_empty_per_part():
    d = outdir("t34")
    c = coll("Fill")
    e = empty("Rock", c)
    a = cube("rock", c); parent(a, e)
    a.data.materials.append(bpy.data.materials.new("Stone"))
    b = cube("rock_COL", c, (0, 0, 2)); parent(b, e)
    p = bpy.context.scene.mass_exporter_props
    p.material_mode = 'FILL'
    p.override_material = bpy.data.materials.new("Fallback")
    item(c, d, use_empty_origins=True, join_empty_children=True)
    run_export()
    info = inspect(os.path.join(d, "Rock.fbx")) if "Rock.fbx" in files(d) else {}
    mats = sorted(m.split(".")[0] for v in info.values() if v["mats"] for m in v["mats"])
    check("t34 joined mesh keeps Stone and fills the bare part with Fallback", mats == ["Fallback", "Stone"], info)


@test
def t35_relative_export_path():
    outdir("t35")
    blend = os.path.join(OUT, "t35", "scene.blend")
    c = coll("Rel")
    cube("relcube", c)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    item(c, "//Exports/Rel/")
    run_export()
    target = os.path.join(OUT, "t35", "Exports", "Rel")
    check("t35 // path resolves next to the .blend", files(target) == ["relcube.fbx"], files(target))


for t in TESTS:
    if ONLY and not any(t.__name__.startswith(o) for o in ONLY):
        continue
    clear_scene()
    print(f"\n######## {t.__name__}")
    try:
        t()
    except Exception:
        traceback.print_exc()
        check(t.__name__ + " (crashed)", False, traceback.format_exc().splitlines()[-1])

print("\n================ SUMMARY ================")
for n, ok, det in RESULTS:
    print(("PASS " if ok else "FAIL ") + n)
print(f"{sum(ok for _, ok, _ in RESULTS)}/{len(RESULTS)} passed")
