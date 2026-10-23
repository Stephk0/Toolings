"""Demo video, GIF and README stills, captured from the REAL Blender UI.

Three steps:

    blender --factory-startup --enable-event-simulate --window-geometry 0 0 1920 1080 \
        --python demo_media.py -- capture <shots_dir>
    python demo_media.py <shots_dir> <out_dir>                 # cursor, captions, stills, GIF
    blender -b --factory-startup --python demo_media.py -- encode <out_dir>/frames <out.mp4>

README stills for the 1.2.0 entries (Apply Modifiers Above, pinned moves) without the
video, full-window PNGs to crop:

    blender --factory-startup --enable-event-simulate --window-geometry 0 0 1920 1080         --python demo_media.py -- stills <shots_dir>

Step 1 opens a Blender window and drives it with simulated mouse and keys
(right-clicks on modifier headers, menu hovers, typing), taking a window
screenshot after each step. Windows only as written (screen.screenshot reads
the GPU framebuffer; under Xvfb it comes back black, see Knowledge).
Step 2 needs PIL; it draws the mouse cursor, which screenshots don't show.
"""

import json
import os
import sys

FPS = 25
SIZE = (1920, 1080)
GIF_WIDTH = 960
MOVE_FRAMES = 12

# Context-menu entries, in px below the first item ("Reset to Default Value").
# Measured at ui_scale 1.25, 1920x1080, right-click on a modifier header's name
# field, no other preview active; our items are 27 px apart, separators add 10. Blender opens a menu with the item clicked
# last time under the cursor (matched by label), else the first item, so the
# demo tracks that memory.
MENU_OFFSETS = {
    "reset": 0, "show": 140, "extract": 167, "extract_as": 194, "apply_above": 221,
    "add_before": 258, "add_after": 285,
    "duplicate": 322, "copy": 349, "paste_before": 376, "paste_after": 403,
    "move_first": 440, "move_up": 467, "move_down": 494, "move_last": 521,
    "move_5th": 548,  # Move After Pinned (normal modifier) / Move to Last (pinned one)
}
# A pinned modifier's 4th move entry is Move Before Pinned, at move_last's offset.


# ---------------------------------------------------------------------------
# Step 1: inside Blender, real UI
# ---------------------------------------------------------------------------

def capture(shots_dir):
    import math

    import bmesh
    import bpy
    from mathutils import Euler, Vector

    sys.path.insert(0, os.path.dirname(__file__))
    import ui_driver as U

    os.makedirs(shots_dir, exist_ok=True)
    U.load_addon()
    bpy.context.preferences.view.show_tooltips = False

    hits = {}

    def recorder(_self, context):
        ptr = getattr(context, "button_pointer", None)
        if isinstance(ptr, bpy.types.Modifier):
            hits["last"] = ptr.name

    bpy.types.UI_MT_button_context_menu.append(recorder)

    meta = []
    H = SIZE[1]

    def shot(title, sub="", hold=1.5, click=False, still=None):
        name = f"s{len(meta):03d}.png"
        U.screenshot(os.path.join(shots_dir, name))
        x, y = U.cursor()
        meta.append({"file": name, "cursor": [x, H - y], "hold": hold, "click": click,
                     "title": title, "subtitle": sub, "still": still})

    def setup_scene():
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        me = bpy.data.meshes.new("Suzanne")
        bm = bmesh.new()
        bmesh.ops.create_monkey(bm)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < -1e-4], context='VERTS')
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        ob = bpy.data.objects.new("Suzanne", me)
        bpy.context.scene.collection.objects.link(ob)
        ob.rotation_euler = (0, 0, math.radians(-25))
        mirror = ob.modifiers.new("Mirror", 'MIRROR')
        mirror.use_clip = True
        ob.modifiers.new("Subdivision", 'SUBSURF').levels = 2
        cast = ob.modifiers.new("Cast", 'CAST')  # the middle one: every action targets it
        cast.factor = 0.6
        arr = ob.modifiers.new("Array", 'ARRAY')
        arr.count = 3
        arr.relative_offset_displace = (0, 0, 1.05)
        bend = ob.modifiers.new("SimpleDeform", 'SIMPLE_DEFORM')
        bend.deform_method = 'BEND'
        bend.deform_axis = 'Y'
        bend.angle = math.radians(90)
        for m in ob.modifiers:
            m.show_expanded = False
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        return ob

    def frame_view():
        a = U.area('VIEW_3D')
        sp = a.spaces.active
        sp.shading.show_cavity = True
        sp.overlay.show_floor = True
        r3d = sp.region_3d
        r3d.view_perspective = 'PERSP'
        r3d.view_rotation = Euler((math.radians(72), 0, math.radians(28))).to_quaternion()
        r3d.view_location = Vector((1.8, 0, 2.4))
        r3d.view_distance = 10.5

    def headers():
        """Right-click down the modifier list; returns {modifier name: y}.

        Clicks in the name field, 380 px from the editor's right edge: the menu
        then opens right of the modifier's icon and name, which stay visible,
        and the Add submenu still fits to its right.
        """
        back = U.cursor()
        props = U.region(U.area('PROPERTIES'))
        x = props.x + props.width - 380
        found = {}
        for y in range(props.y + props.height - 60, props.y + props.height - 330, -6):
            hits.pop("last", None)
            U.mouse(x, y)
            yield 0.03
            U.click('RIGHTMOUSE')
            yield 0.15
            name = hits.get("last")
            U.key('ESC')
            yield 0.05
            if name:
                found.setdefault(name, []).append(y)
        headers.result = {n: sum(ys) // len(ys) for n, ys in found.items()}
        headers.x = x
        headers.icon_x = props.x + int(U.ui_unit() * 1.7)  # modifier type icon
        U.mouse(*back)  # the scan is not filmed; don't let the cursor jump
        print("HEADERS", headers.result, flush=True)

    MID = "Cast"
    menu = {"memory": None, "base": 0, "anchor": 0}

    def show_label(mod_name):
        state = bpy.context.object.modifier_stack_actions_state
        return "restore" if f'"target": "{mod_name}"' in state else "show"

    def right_click(mod_name):
        # Left-click the header first: Blender outlines the active modifier.
        U.mouse(headers.icon_x, headers.result[mod_name])
        yield 0.2
        U.click()
        yield 0.3
        print("ACTIVE", bpy.context.object.modifiers.active.name, flush=True)
        U.mouse(headers.x, headers.result[mod_name])
        yield 0.3
        mem = menu["memory"]
        valid = mem is not None and (mem[0] != "show" or mem[1] == show_label(mod_name))
        menu["base"] = MENU_OFFSETS[mem[0]] if valid else 0
        menu["anchor"] = headers.result[mod_name]
        menu["mod"] = mod_name
        U.click('RIGHTMOUSE')
        yield 0.5

    def hover_item(entry):
        U.mouse(headers.x - 120, menu["anchor"] - (MENU_OFFSETS[entry] - menu["base"]))
        menu["hover"] = entry
        yield 0.4

    def click_item():
        entry = menu["hover"]
        menu["memory"] = (entry, show_label(menu["mod"]) if entry == "show" else None)
        U.click()

    def type_text(text):
        for ch in text:  # text field in edit mode: TEXTINPUT events
            x, y = U.cursor()
            U.ev('TEXTINPUT', 'PRESS', x=x, y=y, unicode=ch)
        yield 0.3

    def type_keys(text):
        for ch in text:  # menu search opens on a letter key press
            x, y = U.cursor()
            U.ev(ch.upper(), 'PRESS', x=x, y=y, unicode=ch)
            U.ev(ch.upper(), 'RELEASE', x=x, y=y)
            yield 0.05
        yield 0.3

    def steps():
        w = U.win()
        props = U.area('PROPERTIES')
        with bpy.context.temp_override(window=w, screen=w.screen):
            bpy.ops.screen.area_move(x=props.x - 1, y=props.y + 100, delta=-530)
        props.spaces.active.context = 'MODIFIER'
        ob = setup_scene()
        frame_view()
        U.mouse(600, 500)
        U.key('ESC')  # splash
        yield 1.0
        yield from headers()

        # -- intro ---------------------------------------------------------
        U.mouse(700, 600)
        yield 0.5
        shot("Modifier Stack Actions",
             "Mirror > Subdivision > Cast > Array > Simple Deform: everything happens on Cast",
             hold=3.0, still="intro")

        # -- Show Up To Here -------------------------------------------------
        title = "Show Up To Here"
        yield from right_click(MID)
        shot(title, "Right-click Cast, the middle modifier", click=True, still="context_menu")
        yield from hover_item("show")
        shot(title, "Hides everything after Cast")
        click_item()
        yield 0.8
        yield from headers()  # the banner moved the panels down
        shot(title, "Mirror, Subdivision and Cast only: no Array, no Bend", click=True, hold=2.5,
             still="show_up_to_here")

        yield from right_click(MID)
        yield from hover_item("show")
        shot(title, "Same modifier again: Restore Modifier Stack")
        click_item()
        yield 0.8
        yield from headers()
        shot(title, "Everything back, as it was", click=True, hold=1.5)

        # -- Extract Up To Here As... ----------------------------------------
        title = "Extract Up To Here As..."
        yield from right_click(MID)
        yield from hover_item("extract_as")
        shot(title, "New object from the stack up to Cast")
        click_item()
        yield 0.8
        shot(title, "Default name <Object>_<Modifier>, change it if you like", click=True,
             hold=1.5, still="extract_dialog")
        yield from type_text("Suzanne_Round")
        shot(title, "Type a new name", hold=1.2)
        U.key('RET')
        yield 0.3
        U.key('RET')
        yield 1.0
        new = bpy.data.objects.get("Suzanne_Round")
        print("EXTRACTED", new and new.name, new and len(new.data.vertices), flush=True)
        if new:
            new.location.x += 3.6
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        yield 0.8
        shot(title, "Suzanne_Round: plain mesh, moved aside. The source is untouched", hold=2.5,
             still="extract_result")
        yield from headers()

        # -- Add Modifier After ------------------------------------------------
        title = "Add Modifier After"
        yield from right_click(MID)
        yield from hover_item("add_after")
        yield 0.6
        x, y = U.cursor()
        for i in range(1, 6):  # along the row into the submenu, so it stays open
            U.mouse(x + i * 50, y)
            yield 0.05
        yield 1.5  # asset catalogs load
        shot(title, "Blender's own Add Modifier menu, asset catalogs included",
             hold=2.5, still="add_after_menu")
        yield from type_keys("wire")
        yield 0.5
        shot(title, "Type to search, like the normal menu", hold=1.5, still="add_after_search")
        U.key('RET')
        menu["memory"] = ("add_after", None)  # submenu pick sets the parent's memory
        yield 1.0
        wire = next((m for m in ob.modifiers if m.type == 'WIREFRAME'), None)
        print("STACK", [m.name for m in ob.modifiers], flush=True)
        if wire:
            wire.show_expanded = False
            wire.thickness = 0.04
        yield 0.8
        shot(title, "Wireframe lands right after Cast, still before Array and Bend", hold=3.0,
             still="add_after_result")
        yield from headers()

        # -- Apply Modifiers Above ---------------------------------------------
        title = "Apply Modifiers Above"
        yield from right_click(MID)
        yield from hover_item("apply_above")
        shot(title, "Bake everything above Cast into the mesh")
        click_item()
        yield 1.0
        print("STACK", [m.name for m in ob.modifiers], len(ob.data.vertices), flush=True)
        yield from headers()  # Cast is the first modifier now
        shot(title, "Mirror and Subdivision applied; Cast and below stay live", click=True,
             hold=3.0, still="apply_above")

        json.dump(meta, open(os.path.join(shots_dir, "shots.json"), "w"), indent=1)

    U.run(steps)


def capture_stills(shots_dir):
    """Full-window PNGs of the 1.2.0 menu entries; no item is clicked until the
    last shot, so every menu opens with its first item under the cursor."""
    import math

    import bpy

    sys.path.insert(0, os.path.dirname(__file__))
    import ui_driver as U

    os.makedirs(shots_dir, exist_ok=True)
    U.load_addon()
    bpy.context.preferences.view.show_tooltips = False
    hits = {}

    def recorder(_self, context):
        ptr = getattr(context, "button_pointer", None)
        if isinstance(ptr, bpy.types.Modifier):
            hits["last"] = ptr.name

    bpy.types.UI_MT_button_context_menu.append(recorder)
    pos = {}

    def headers():
        props = U.region(U.area('PROPERTIES'))
        x = props.x + props.width - 380  # same click spot as the video
        found = {}
        for y in range(props.y + props.height - 60, props.y + props.height - 360, -6):
            hits.pop("last", None)
            U.mouse(x, y)
            yield 0.03
            U.click('RIGHTMOUSE')
            yield 0.15
            name = hits.get("last")
            U.key('ESC')
            yield 0.05
            if name:
                found.setdefault(name, []).append(y)
        pos.clear()
        pos.update({n: sum(ys) // len(ys) for n, ys in found.items()})
        pos["x"] = x
        pos["icon_x"] = props.x + int(U.ui_unit() * 1.7)
        print("HEADERS", pos, flush=True)

    def open_menu(mod_name, entry=None):
        U.mouse(pos["icon_x"], pos[mod_name])  # left-click first: active outline
        yield 0.2
        U.click()
        yield 0.3
        U.mouse(pos["x"], pos[mod_name])
        yield 0.3
        U.click('RIGHTMOUSE')
        yield 0.5
        if entry:
            U.mouse(pos["x"] - 120, pos[mod_name] - MENU_OFFSETS[entry])
            yield 0.4

    def shot(name):
        U.screenshot(os.path.join(shots_dir, name + ".png"))
        print("SHOT", name, U.cursor(), flush=True)

    def steps():
        w = U.win()
        props = U.area('PROPERTIES')
        with bpy.context.temp_override(window=w, screen=w.screen):
            bpy.ops.screen.area_move(x=props.x - 1, y=props.y + 100, delta=-530)
        props.spaces.active.context = 'MODIFIER'
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        bpy.ops.mesh.primitive_monkey_add()
        ob = bpy.context.object
        ob.name = "Suzanne"
        bpy.ops.object.shade_smooth()
        ob.modifiers.new("Mirror", 'MIRROR')
        ob.modifiers.new("Subdivision", 'SUBSURF').levels = 2
        arr = ob.modifiers.new("Array", 'ARRAY')
        arr.count = 3
        arr.relative_offset_displace = (0, 0, 1.05)
        for m in ob.modifiers:
            m.show_expanded = False
        ob.rotation_euler = (0, 0, math.radians(-25))
        U.mouse(600, 500)
        U.key('ESC')  # splash
        yield 1.0
        yield from headers()

        yield from open_menu("Subdivision")
        shot("context_menu")
        U.key('ESC')
        yield 0.3

        wn = ob.modifiers.new("WeightedNormal", 'WEIGHTED_NORMAL')
        wn.show_expanded = False
        wn.use_pin_to_last = True
        yield 0.5
        yield from headers()
        yield from open_menu("Subdivision", "move_5th")
        shot("pinned_menu_normal")
        U.key('ESC')
        yield 0.3
        yield from open_menu("WeightedNormal", "move_last")
        shot("pinned_menu_pinned")
        U.key('ESC')
        yield 0.3
        ob.modifiers.remove(wn)
        yield 0.5
        yield from headers()

        yield from open_menu("Array", "apply_above")
        shot("apply_above_menu")
        U.click()
        yield 1.0
        print("STACK", [m.name for m in ob.modifiers], len(ob.data.vertices), flush=True)
        shot("apply_above_result")

    U.run(steps)


# ---------------------------------------------------------------------------
# Step 2: plain Python + PIL
# ---------------------------------------------------------------------------

def assemble(shots_dir, out_dir):
    from PIL import Image, ImageDraw, ImageFont

    meta = json.load(open(os.path.join(shots_dir, "shots.json")))
    frames_dir = os.path.join(out_dir, "frames")
    still_dir = os.path.join(out_dir, "stills")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(still_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))

    def font(size, bold=False):
        for name in (("segoeuib.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf")):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
        return ImageFont.load_default()

    f_title, f_sub, f_tag = font(44, True), font(28), font(22)
    arrow = [(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 18), (21, 18)]

    def draw_cursor(im, pos, ring=0.0):
        d = ImageDraw.Draw(im, "RGBA")
        x, y = pos
        if ring:
            r = 10 + 26 * ring
            d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 170, 40, int(255 * (1 - ring))), width=4)
        pts = [(x + px, y + py) for px, py in arrow]
        d.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))
        return im

    def caption(im, entry):
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, SIZE[1] - 150, 1246, SIZE[1] - 30), fill=(20, 20, 20, 215))
        d.text((32, SIZE[1] - 140), entry["title"], font=f_title, fill=(240, 240, 240))
        d.text((32, SIZE[1] - 82), entry["subtitle"], font=f_sub, fill=(185, 185, 185))
        tag = "Modifier Stack Actions"
        d.text((1246 - 32 - d.textlength(tag, font=f_tag), SIZE[1] - 132), tag,
               font=f_tag, fill=(130, 130, 130))
        return im

    n = 0
    gif = []
    gif_size = (GIF_WIDTH, round(GIF_WIDTH * SIZE[1] / SIZE[0]))
    prev_img, prev_cur = None, None

    def emit(im):
        nonlocal n
        im.save(os.path.join(frames_dir, f"f{n:05d}.png"))
        if n % 2 == 0:
            gif.append(im.resize(gif_size, Image.LANCZOS)
                       .quantize(colors=128, method=Image.Quantize.MEDIANCUT))
        n += 1

    for entry in meta:
        img = Image.open(os.path.join(shots_dir, entry["file"])).convert("RGB")
        cur = tuple(entry["cursor"])
        if prev_img is not None and cur != prev_cur:
            for i in range(1, MOVE_FRAMES + 1):
                t = i / MOVE_FRAMES
                t = t * t * (3 - 2 * t)
                pos = (prev_cur[0] + (cur[0] - prev_cur[0]) * t, prev_cur[1] + (cur[1] - prev_cur[1]) * t)
                emit(draw_cursor(caption(prev_img.copy(), entry), pos))
        hold = max(1, int(entry["hold"] * FPS))
        for i in range(hold):
            ring = (i + 1) / 8 if entry["click"] and i < 8 else 0.0
            emit(draw_cursor(caption(img.copy(), entry), cur, ring))
        if entry.get("still"):
            img.save(os.path.join(still_dir, f"{entry['still']}.png"))
            draw_cursor(img.copy(), cur).save(os.path.join(still_dir, f"{entry['still']}_cursor.png"))
        prev_img, prev_cur = img, cur

    out_gif = os.path.join(out_dir, "modifier_stack_actions_demo.gif")
    gif[0].save(out_gif, save_all=True, append_images=gif[1:], loop=0,
                duration=int(2000 / FPS), optimize=True, disposal=1)
    print(f"wrote {n} frames, {still_dir}, {out_gif} ({os.path.getsize(out_gif) / 1e6:.1f} MB)")


# ---------------------------------------------------------------------------
# Step 3: Blender's FFmpeg
# ---------------------------------------------------------------------------

def encode(png_dir, out_mp4):
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    files = sorted(f for f in os.listdir(png_dir) if f.endswith(".png"))
    scene.sequence_editor_create()
    strips = scene.sequence_editor.strips if hasattr(scene.sequence_editor, "strips") \
        else scene.sequence_editor.sequences
    strip = strips.new_image("frames", os.path.join(png_dir, files[0]), channel=1, frame_start=1)
    for f in files[1:]:
        strip.elements.append(f)
    r = scene.render
    r.resolution_x, r.resolution_y = SIZE
    r.resolution_percentage = 100
    r.fps = FPS
    scene.frame_start, scene.frame_end = 1, len(files)
    if hasattr(r.image_settings, "media_type"):
        r.image_settings.media_type = 'VIDEO'     # Blender 5.0: FFMPEG lives under VIDEO
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'
    r.ffmpeg.codec = 'H264'
    r.ffmpeg.constant_rate_factor = 'HIGH'
    r.ffmpeg.ffmpeg_preset = 'BEST'
    r.ffmpeg.gopsize = FPS
    r.filepath = out_mp4
    bpy.ops.render.render(animation=True)
    print(f"wrote {out_mp4}: {len(files)} frames at {FPS} fps", flush=True)


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ImportError:
        assemble(sys.argv[1], sys.argv[2])
    else:
        argv = sys.argv[sys.argv.index("--") + 1:]
        if argv[0] == "encode":
            encode(argv[1], argv[2])
        elif argv[0] == "stills":
            capture_stills(argv[1])
        else:
            capture(argv[1])
