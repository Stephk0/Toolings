"""
Paste this ENTIRE file into Blender's Scripting tab → Text Editor → New → paste
→ Run Script (Alt+P). It prints a full diagnostic trace of the Mass Collection
Exporter into the System Console (Window → Toggle System Console on Windows).

What it does (no destructive operations — all in a try/finally, no files
written unless the real export actually fires):

  1. Prints the loaded addon's VERSION + bl_info.
  2. Dumps every collection_items row (collection, path, flags, hide state).
  3. Monkey-patches _unhide_collection_for_export / _restore / perform_export
     so every call is logged with selection counts and return values.
  4. Runs bpy.ops.massexporter.export_all() exactly like the button does.
  5. Prints everything captured and restores the originals.

Copy the entire console output and paste it back to me.
"""
import bpy
import sys
import os
import importlib
import traceback

print("=" * 78)
print("MASS EXPORTER DIAGNOSTIC")
print("=" * 78)

# --- 1. Which module is loaded? ---
mod = None
for name, m in list(sys.modules.items()):
    if m is None:
        continue
    bl_info = getattr(m, "bl_info", None)
    if isinstance(bl_info, dict) and bl_info.get("name") == "Mass Collection Exporter":
        mod = m
        print(f"\n[module] sys.modules key: {name}")
        print(f"[module] file: {getattr(m, '__file__', '<unknown>')}")
        print(f"[module] VERSION constant: {getattr(m, 'VERSION', '<missing>')}")
        print(f"[module] bl_info['version']: {bl_info.get('version')}")
        break

if mod is None:
    print("\n[FATAL] Mass Collection Exporter module not found in sys.modules.")
    print("        The addon either isn't installed or isn't enabled.")
    raise SystemExit

# --- 2. Scene props + collection_items ---
print("\n" + "-" * 78)
print("SCENE STATE")
print("-" * 78)
scene = bpy.context.scene
props = getattr(scene, "mass_exporter_props", None)
if props is None:
    print("[FATAL] scene.mass_exporter_props is None — PropertyGroup not registered.")
    raise SystemExit

print(f"export_hidden_collections = {props.export_hidden_collections}")
print(f"export_rig_with_mesh      = {getattr(props, 'export_rig_with_mesh', '<n/a>')}")
print(f"apply_modifiers           = {getattr(props, 'apply_modifiers', '<n/a>')}")
print(f"export_format             = {getattr(props, 'export_format', '<n/a>')}")
print(f"debug_mode                = {props.debug_mode}")
print(f"collection_items          = {len(props.collection_items)} rows")

def _walk_lc(lc, depth=0, out=None):
    out = out if out is not None else []
    out.append(("  " * depth + f"LC '{lc.name}' exclude={lc.exclude} hide_vp={lc.hide_viewport}"))
    for child in lc.children:
        _walk_lc(child, depth + 1, out)
    return out

for i, item in enumerate(props.collection_items):
    coll = item.collection
    coll_name = getattr(coll, "name", "<None>")
    print(f"\n  [{i}] collection='{coll_name}' enabled={item.export_enabled} path='{item.export_path}'")
    if coll:
        print(f"       Collection.hide_viewport={coll.hide_viewport} hide_render={coll.hide_render}")
        root_lc = bpy.context.view_layer.layer_collection
        # locate layer collection
        def _find(lc, target):
            if lc.collection == target:
                return lc
            for c in lc.children:
                r = _find(c, target)
                if r:
                    return r
            return None
        target_lc = _find(root_lc, coll)
        if target_lc is not None:
            print(f"       LayerCollection.exclude={target_lc.exclude} hide_viewport={target_lc.hide_viewport}")
        else:
            print(f"       LayerCollection: NOT FOUND in active view_layer")
        print(f"       all_objects={len(coll.all_objects)} direct_objects={len(coll.objects)}")
        for obj in list(coll.all_objects)[:10]:
            print(f"         * {obj.name} ({obj.type}) hv={obj.hide_viewport} hg={obj.hide_get()} hs={obj.hide_select}")

# --- 3. Install trace hooks ---
print("\n" + "-" * 78)
print("INSTALLING TRACE HOOKS")
print("-" * 78)

try:
    op_class = mod.MASSEXPORTER_OT_export_all
except AttributeError:
    print("[FATAL] MASSEXPORTER_OT_export_all class not found on module")
    raise SystemExit

orig_unhide = op_class._unhide_collection_for_export
orig_restore = op_class._restore_collection_for_export
orig_perform = op_class.perform_export
orig_get_objects = op_class.get_collection_objects
orig_export_collection = op_class.export_collection
orig_export_as_single = op_class.export_objects_as_single
orig_export_single = op_class.export_single_object

events = []


def _log(msg):
    events.append(msg)
    print(f"[TRACE] {msg}")


def traced_unhide(collection):
    _log(f"_unhide_collection_for_export('{collection.name}')")
    try:
        backup = orig_unhide(collection)
        _log(f"  returned backup with coll_flags={len(backup.get('coll_flags', []))} "
             f"layer_coll={len(backup.get('layer_coll', []))} "
             f"objects={len(backup.get('objects', []))} "
             f"hide_select={len(backup.get('hide_select', []))} "
             f"local_view={len(backup.get('local_view', []))}")
        # Report actual state AFTER unhide
        root_lc = bpy.context.view_layer.layer_collection
        def _find(lc, t):
            if lc.collection == t:
                return lc
            for c in lc.children:
                r = _find(c, t)
                if r:
                    return r
            return None
        tlc = _find(root_lc, collection)
        _log(f"  after-unhide: Collection.hv={collection.hide_viewport} "
             f"LayerCollection.exclude={getattr(tlc,'exclude','?')} "
             f"LayerCollection.hv={getattr(tlc,'hide_viewport','?')}")
        # Check object state
        sel_ready = 0
        for o in collection.all_objects:
            try:
                # Object must be in view layer for select_set to succeed
                in_vl = o in bpy.context.view_layer.objects.values()
                if in_vl and not o.hide_get():
                    sel_ready += 1
            except Exception:
                pass
        _log(f"  selectable objects (in view_layer & not hide_get): {sel_ready}/{len(list(collection.all_objects))}")
        return backup
    except Exception as e:
        _log(f"  RAISED: {e!r}")
        traceback.print_exc()
        raise


def traced_restore(backup):
    _log(f"_restore_collection_for_export (backup objs={len(backup.get('objects', []))})")
    try:
        orig_restore(backup)
    except Exception as e:
        _log(f"  RAISED: {e!r}")
        traceback.print_exc()
        raise


def traced_get_objects(self, collection):
    objs = orig_get_objects(self, collection)
    _log(f"get_collection_objects('{collection.name}') -> {len(objs)} objects: "
         f"{[o.name for o in objs[:5]]}{'...' if len(objs)>5 else ''}")
    return objs


def traced_export_collection(self, context, props, item):
    _log(f"export_collection(item.collection='{getattr(item.collection,'name','<None>')}' "
         f"path='{item.export_path}')")
    try:
        r = orig_export_collection(self, context, props, item)
        _log(f"  export_collection returned: {r}")
        return r
    except Exception as e:
        _log(f"  RAISED: {e!r}")
        traceback.print_exc()
        raise


def traced_perform_export(self, props, filepath):
    sel = [o.name for o in bpy.context.selected_objects]
    _log(f"perform_export(filepath='{filepath}') "
         f"selected_count={len(sel)} selected={sel[:6]}{'...' if len(sel)>6 else ''}")
    try:
        r = orig_perform(self, props, filepath)
        _log(f"  perform_export returned: {r}")
        exists = os.path.exists(filepath)
        size = os.path.getsize(filepath) if exists else -1
        _log(f"  file_written={exists} size={size}")
        return r
    except Exception as e:
        _log(f"  RAISED: {e!r}")
        traceback.print_exc()
        raise


def traced_export_as_single(self, context, props, objects, collection_name, export_path):
    _log(f"export_objects_as_single(name='{collection_name}' "
         f"objects={[o.name for o in objects[:5]]}{'...' if len(objects)>5 else ''} "
         f"to='{export_path}')")
    return orig_export_as_single(self, context, props, objects, collection_name, export_path)


def traced_export_single(self, context, props, obj, export_path):
    _log(f"export_single_object(obj='{obj.name}' to='{export_path}')")
    return orig_export_single(self, context, props, obj, export_path)


op_class._unhide_collection_for_export = staticmethod(traced_unhide)
op_class._restore_collection_for_export = staticmethod(traced_restore)
op_class.perform_export = traced_perform_export
op_class.get_collection_objects = traced_get_objects
op_class.export_collection = traced_export_collection
op_class.export_objects_as_single = traced_export_as_single
op_class.export_single_object = traced_export_single

# --- 4. Snapshot filesystem state per export path, then run export ---
fs_before = {}
for item in props.collection_items:
    if item.export_enabled and item.export_path and os.path.isdir(item.export_path):
        try:
            fs_before[item.export_path] = set(os.listdir(item.export_path))
        except OSError:
            fs_before[item.export_path] = set()

print("\n" + "-" * 78)
print("RUNNING bpy.ops.massexporter.export_all()")
print("-" * 78)

try:
    res = bpy.ops.massexporter.export_all()
    print(f"\n[operator] returned: {res}")
except Exception as e:
    print(f"\n[operator] RAISED: {e!r}")
    traceback.print_exc()
finally:
    # --- 5. Restore patches ---
    op_class._unhide_collection_for_export = orig_unhide
    op_class._restore_collection_for_export = orig_restore
    op_class.perform_export = orig_perform
    op_class.get_collection_objects = orig_get_objects
    op_class.export_collection = orig_export_collection
    op_class.export_objects_as_single = orig_export_as_single
    op_class.export_single_object = orig_export_single

# --- 6. Filesystem diff ---
print("\n" + "-" * 78)
print("FILESYSTEM DIFF (after − before)")
print("-" * 78)
for path, before in fs_before.items():
    try:
        after = set(os.listdir(path))
    except OSError:
        after = set()
    added = sorted(after - before)
    print(f"  {path}")
    print(f"    added files: {added if added else '<none>'}")

print("\n" + "=" * 78)
print(f"END DIAGNOSTIC — {len(events)} trace events")
print("=" * 78)
