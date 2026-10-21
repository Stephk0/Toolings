"""Headless Blender checks for the operators.

blender --background --factory-startup --python tests/headless/blender_checks.py
Exits 1 on any failure.
"""

import os
import sys
import traceback

import bpy

SOURCE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(SOURCE))
addon = __import__(os.path.basename(SOURCE))
addon.register()

from types import SimpleNamespace  # noqa: E402

failures = []


def check(label, cond):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def scene_with_stack():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = "Cube"
    mirror = obj.modifiers.new("Mirror", 'MIRROR')
    mirror.use_axis = (True, False, False)
    for v in obj.data.vertices:  # off the mirror plane so no verts merge: 8 -> 16
        v.co.x += 2.0
    obj.modifiers.new("Subdivision", 'SUBSURF').levels = 1
    bev = obj.modifiers.new("Bevel", 'BEVEL')
    bev.show_viewport = False  # user-disabled, must stay off after restore
    obj.modifiers.new("Array", 'ARRAY')
    return obj


def eval_verts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    return len(obj.evaluated_get(dg).data.vertices)


def flags(obj):
    return [m.show_viewport for m in obj.modifiers]


try:
    ui = sys.modules[addon.__name__ + ".blender.ui"]

    obj = scene_with_stack()
    full = eval_verts(obj)

    # -- Show Up To Here -------------------------------------------------
    bpy.ops.object.modifier_up_to_here(object_name="Cube", modifier_name="Mirror")
    check("hides only later visible modifiers", flags(obj) == [True, False, False, False])
    check("evaluated mesh = cube mirrored", eval_verts(obj) == 16)
    check("state stored", '"target": "Mirror"' in obj.modifier_stack_actions_state)

    bpy.ops.object.modifier_up_to_here(object_name="Cube", modifier_name="Subdivision")
    check("switching target restores then re-hides",
          flags(obj) == [True, True, False, False])

    bpy.ops.object.modifier_up_to_here(object_name="Cube", modifier_name="Subdivision")
    check("same target toggles back", flags(obj) == [True, True, False, True])
    check("state cleared", obj.modifier_stack_actions_state == "")
    check("evaluated mesh back to full", eval_verts(obj) == full)

    bpy.ops.object.modifier_up_to_here(object_name="Cube", modifier_name="Mirror")
    bpy.ops.object.modifier_up_to_here_restore(object_name="Cube")
    check("restore op", flags(obj) == [True, True, False, True])

    # -- Extract Up To Here ----------------------------------------------
    before = flags(obj)
    bpy.ops.object.modifier_extract_up_to_here(object_name="Cube", modifier_name="Mirror")
    new = bpy.data.objects.get("Cube_Mirror")
    check("extracted object exists", new is not None)
    check("extracted = mirror only (16 verts)", new is not None and len(new.data.vertices) == 16)
    check("extracted has no modifiers", new is not None and len(new.modifiers) == 0)
    check("source flags untouched", flags(obj) == before)
    check("source still full", eval_verts(obj) == full)
    check("result active", bpy.context.view_layer.objects.active == new)

    # disabled target is forced on for extraction
    obj.modifiers["Bevel"].show_viewport = False
    bpy.ops.object.modifier_extract_up_to_here(object_name="Cube", modifier_name="Bevel")
    bev_obj = bpy.data.objects.get("Cube_Bevel")
    sub_obj_verts = None
    bpy.ops.object.modifier_extract_up_to_here(object_name="Cube", modifier_name="Subdivision")
    sub_obj_verts = len(bpy.data.objects["Cube_Subdivision"].data.vertices)
    check("disabled target applied in extract",
          bev_obj is not None and len(bev_obj.data.vertices) > sub_obj_verts)
    check("disabled target still off on source", obj.modifiers["Bevel"].show_viewport is False)

    # edit mode extraction
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.modifier_extract_up_to_here(object_name="Cube", modifier_name="Mirror")
    em = bpy.data.objects.get("Cube_Mirror.001")
    check("edit mode extract", em is not None and len(em.data.vertices) == 16)
    check("edit mode kept active object", bpy.context.object == obj)
    bpy.ops.object.mode_set(mode='OBJECT')

    # custom name
    bpy.ops.object.modifier_extract_up_to_here(object_name="Cube", modifier_name="Mirror",
                                               new_name="  MirrorOnly ")
    custom = bpy.data.objects.get("MirrorOnly")
    check("custom name used (trimmed)", custom is not None and custom.data.name == "MirrorOnly")
    check("custom-name result = mirror only", custom is not None and len(custom.data.vertices) == 16)
    n_before = len(bpy.data.objects)
    bpy.ops.object.modifier_extract_up_to_here(object_name="Cube", modifier_name="Mirror",
                                               new_name="   ")
    check("blank name falls back to default",
          len(bpy.data.objects) == n_before + 1 and "Cube_Mirror.002" in bpy.data.objects)

    # active-modifier fallback (F3 / scripts)
    bpy.context.view_layer.objects.active = obj
    obj.modifiers.active = obj.modifiers["Mirror"]
    bpy.ops.object.modifier_up_to_here()
    check("fallback to active modifier", flags(obj) == [True, False, False, False])
    bpy.ops.object.modifier_up_to_here_restore()

    # context-menu modifier lookup
    m = obj.modifiers["Subdivision"]
    check("menu finds button_pointer", ui.context_modifier(SimpleNamespace(button_pointer=m)) == m)
    check("menu finds modifier pointer", ui.context_modifier(SimpleNamespace(modifier=m)) == m)
    check("menu ignores other buttons",
          ui.context_modifier(SimpleNamespace(button_pointer=obj)) is None)

    # -- Add Modifier Before / After -----------------------------------
    insert = sys.modules[addon.__name__ + ".blender.insert"]
    obj = scene_with_stack()  # Mirror, Subdivision, Bevel, Array

    def names():
        return [m.name for m in obj.modifiers]

    insert.arm(obj, "Mirror", 'AFTER')
    bpy.ops.object.modifier_add(type='WELD')
    check("add after Mirror", names() == ["Mirror", "Weld", "Subdivision", "Bevel", "Array"])
    check("inserted modifier is active", obj.modifiers.active.name == "Weld")
    check("disarmed after insert", insert._pending is None)

    insert.arm(obj, "Mirror", 'BEFORE')
    bpy.ops.object.modifier_add(type='TRIANGULATE')
    check("add before first", names()[0] == "Triangulate")

    insert.arm(obj, "Array", 'AFTER')
    bpy.ops.object.modifier_add(type='SMOOTH')
    check("add after last", names()[names().index("Array") + 1] == "Smooth")

    bpy.ops.object.modifier_add(type='DISPLACE')
    check("plain add (not armed) appends", names()[-1] == "Displace")

    insert.arm(obj, "Mirror", 'AFTER')
    bpy.context.view_layer.objects.active = None  # update that leaves the stack alone
    bpy.context.view_layer.objects.active = obj
    bpy.context.view_layer.update()
    check("non-stack update keeps armed", insert._pending is not None)
    obj.modifiers.remove(obj.modifiers["Displace"])
    bpy.context.view_layer.update()
    check("other stack edit disarms", insert._pending is None)
    bpy.ops.object.modifier_add(type='DECIMATE')
    check("...and the next add appends", names()[-1] == "Decimate")

    insert.arm(obj, "Mirror", 'AFTER')
    insert._pending["time"] -= insert.TIMEOUT + 1
    bpy.ops.object.modifier_add(type='CAST')
    check("timed-out insert appends", names()[-1] == "Cast")

    insert.arm(obj, "Mirror", 'AFTER')
    insert._disarm_on_native_menu(None, bpy.context)  # native menu opened elsewhere
    check("native menu disarms", insert._pending is None)
    insert._drawing_wrapper = True
    insert.arm(obj, "Mirror", 'AFTER')
    insert._disarm_on_native_menu(None, bpy.context)
    check("native menu inside wrapper keeps armed", insert._pending is not None)
    insert._drawing_wrapper = False
    insert.disarm()

    bpy.ops.object.modifier_add(type='NODES')
    insert.arm(obj, "Mirror", 'BEFORE')
    n_before = len(obj.modifiers)
    bpy.ops.object.modifier_add(type='NODES')
    gn = obj.modifiers.active
    check("geometry nodes insert", len(obj.modifiers) == n_before + 1 and gn.type == 'NODES'
          and names().index(gn.name) == names().index("Mirror") - 1)

    # -- Move to First / Last ------------------------------------------
    obj = scene_with_stack()  # Mirror, Subdivision, Bevel, Array
    bpy.ops.object.modifier_stack_move(object_name="Cube", modifier_name="Bevel", position='FIRST')
    check("move to first", names() == ["Bevel", "Mirror", "Subdivision", "Array"])
    check("moved modifier is active", obj.modifiers.active.name == "Bevel")
    bpy.ops.object.modifier_stack_move(object_name="Cube", modifier_name="Mirror", position='LAST')
    check("move to last", names() == ["Bevel", "Subdivision", "Array", "Mirror"])
    res = bpy.ops.object.modifier_stack_move(object_name="Cube", modifier_name="Bevel", position='FIRST')
    check("already first is a no-op", res == {'CANCELLED'} and names()[0] == "Bevel")
    obj.modifiers.new("Hook", 'HOOK')  # needs original data: can't sit below generators
    bpy.ops.object.modifier_stack_move(object_name="Cube", modifier_name="Hook", position='FIRST')
    check("hook to first", names()[0] == "Hook")
    bpy.ops.object.modifier_stack_move(object_name="Cube", modifier_name="Hook", position='LAST')
    check("hook to last (allowed, same as header Move to Last)", names()[-1] == "Hook")

    addon.unregister()
    check("unregister clean", not hasattr(bpy.types.Object, "modifier_stack_actions_state"))
except Exception:
    traceback.print_exc()
    failures.append("exception")

print(f"\n{len(failures)} failure(s)")
sys.stdout.flush()
os._exit(1 if failures else 0)
