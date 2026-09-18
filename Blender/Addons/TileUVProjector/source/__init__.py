# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Stephan Viranyi

bl_info = {
    "name": "Tile UV Projector",
    "author": "Stephan Viranyi",
    "version": (1, 8, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Tile UV",
    "description": "Tile-based UV projection and placement on texture atlas grids",
    "category": "UV",
}

import math
import os

import bpy
import bmesh
import gpu
import blf
from gpu.types import Buffer, GPUTexture
from gpu_extras.batch import batch_for_shader
from bpy.types import Operator, Panel, PropertyGroup, UIList
from bpy.app.handlers import persistent
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    EnumProperty,
    BoolProperty,
    PointerProperty,
    CollectionProperty,
    FloatVectorProperty,
)
from mathutils import Vector


# Snap increments. A move snaps to a fraction of a TILE rather than to a fixed
# UV step: on a 4x4 grid the tiles sit at 0.125, 0.375, ... which no round UV
# increment can express, so a fixed grid would drag every tile off the tile it
# was just placed on. Eighths keep tile centres and tile edges on the grid.
_SNAP_TILE_FRACTION = 8.0
_SNAP_SCALE = 0.1
_SNAP_ANGLE_DEG = 5.0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_tile_bounds(col_index, row_index, cols, rows):
    """Compute tile UV bounds for a uniform grid cell."""
    tw = 1.0 / cols
    th = 1.0 / rows
    tile_min = Vector((col_index * tw, row_index * th))
    tile_max = Vector(((col_index + 1) * tw, (row_index + 1) * th))
    return tile_min, tile_max


def get_selected_face_uv_loops(bm, uv_layer):
    """Return list of BMLoopUV references for all selected faces."""
    loops = []
    for face in bm.faces:
        if face.select:
            for loop in face.loops:
                loops.append(loop[uv_layer])
    return loops


def compute_uv_bounds(uv_loops):
    """Compute bounding box of UV coordinates. Returns (min_uv, max_uv) or None."""
    if not uv_loops:
        return None

    min_u = min_v = float('inf')
    max_u = max_v = float('-inf')

    for luv in uv_loops:
        u, v = luv.uv
        min_u = min(min_u, u)
        min_v = min(min_v, v)
        max_u = max(max_u, u)
        max_v = max(max_v, v)

    return Vector((min_u, min_v)), Vector((max_u, max_v))


def normalize_and_place_uvs(uv_loops, uv_min, uv_max, target_min, target_max):
    """Normalize UVs to 0-1, then scale and translate into target rect.

    An island that is degenerate along one axis (all UVs collinear, which an
    edge-on Project From View produces readily) is CENTRED on that axis rather
    than divided by a 1.0 fallback, which used to pin every coordinate to the
    tile's left or bottom padded edge with no warning.
    """
    extent = uv_max - uv_min
    flat_u = extent.x < 1e-8
    flat_v = extent.y < 1e-8
    sx = 1.0 if flat_u else extent.x
    sy = 1.0 if flat_v else extent.y

    target_size = target_max - target_min

    for luv in uv_loops:
        u, v = luv.uv
        # Normalize to 0-1
        nu = 0.5 if flat_u else (u - uv_min.x) / sx
        nv = 0.5 if flat_v else (v - uv_min.y) / sy
        # Scale + translate into target tile
        luv.uv = Vector((
            nu * target_size.x + target_min.x,
            nv * target_size.y + target_min.y,
        ))


def get_edit_mesh_targets(context):
    """Every mesh currently open in Edit Mode, as (object, mesh) pairs.

    Blender's uv operators act on ALL objects in multi-object Edit Mode, so the
    placement pass has to cover them too. Collecting only the active object's
    loops left every other selected mesh projected and unwrapped but never
    placed — its old UVs destroyed and the new ones dumped wherever the
    projection happened to land.
    """
    objects = getattr(context, "objects_in_mode_unique_data", None)
    if not objects:
        active = getattr(context, "active_object", None)
        objects = [active] if active is not None else []
    return [(obj, obj.data) for obj in objects
            if obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT']


def collect_edit_uv_loops(targets):
    """Selected-face UV loops across every edit-mode mesh, plus those meshes.

    Returns (loops, meshes). The UV layer is created here via verify(), so call
    this only once the operation is known to be valid.
    """
    loops = []
    meshes = []
    for _obj, me in targets:
        bm = bmesh.from_edit_mesh(me)
        uv_layer = bm.loops.layers.uv.verify()
        found = get_selected_face_uv_loops(bm, uv_layer)
        if found:
            loops.extend(found)
            meshes.append(me)
    return loops, meshes


def count_selected_faces(targets):
    """Selected faces across every edit-mode mesh."""
    total = 0
    for _obj, me in targets:
        bm = bmesh.from_edit_mesh(me)
        total += sum(1 for f in bm.faces if f.select)
    return total


def warn_unapplied_scale(operator, targets):
    """Warn once if any edit-mode object carries a non-uniform object scale.

    Only non-uniformity distorts a view projection; a uniform 2.0 is harmless,
    so this deliberately does not fire on it.
    """
    for obj, _me in targets:
        scale = obj.scale
        if max(scale) - min(scale) > 1e-3:
            operator.report(
                {'WARNING'},
                f"{obj.name} has non-uniform scale — apply transforms (Ctrl+A) "
                f"for an undistorted projection")
            return


def has_view3d_context(context):
    """True when the operator is running somewhere uv projection can work."""
    space = getattr(context, "space_data", None)
    return space is not None and getattr(space, "type", "") == 'VIEW_3D'


def run_projection_ops(operator, context, settings):
    """Project / unwrap / relax. Returns False if it could not run."""
    method = settings.projection_method

    if method in {'PROJECT_AND_UNWRAP', 'PROJECT_ONLY'}:
        if not has_view3d_context(context):
            operator.report({'ERROR'},
                            "Project From View needs the 3D Viewport — run this "
                            "from the sidebar, or pick an Unwrap Only method")
            return False
        bpy.ops.uv.project_from_view(
            camera_bounds=False,
            correct_aspect=True,
            scale_to_bounds=False,
        )

    if method in {'PROJECT_AND_UNWRAP', 'UNWRAP_ONLY'}:
        bpy.ops.uv.unwrap(method=settings.unwrap_method, margin=0.0)

    if settings.do_relax and method != 'PROJECT_ONLY':
        # One call with N iterations, not N operator invocations — the loop
        # pushed an undo step and a mesh sync per iteration, up to 500 times.
        bpy.ops.uv.minimize_stretch(iterations=settings.relax_iterations)

    return True


def place_loops_in_tile(operator, settings, loops, meshes, usable_min, usable_max):
    """Fit collected loops into the tile rect and flush every mesh touched."""
    bounds = compute_uv_bounds(loops)
    if bounds is None:
        operator.report({'WARNING'}, "Could not compute UV bounds")
        return False

    uv_min, uv_max = bounds
    extent = uv_max - uv_min
    if extent.x < 1e-8 and extent.y < 1e-8:
        operator.report({'WARNING'}, "Zero-area UV selection, nothing to place")
        return False

    normalize_and_place_uvs(loops, uv_min, uv_max, usable_min, usable_max)

    if settings.use_tile_scale:
        scale_uvs_in_tile(loops, usable_min, usable_max,
                          settings.tile_scale, settings.tile_scale_pivot)

    for me in meshes:
        bmesh.update_edit_mesh(me)
    return True


def strip_split_suffix(name):
    """Drop a trailing split marker so repeated splits do not stack them up."""
    for suffix in (" (bottom)", " (top)", " (left)", " (right)"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def scale_uvs_in_tile(uv_loops, tile_min, tile_max, scale, pivot):
    """Scale already-placed UVs inside their tile about a normalised pivot.

    ``pivot`` is in 0..1 tile space: (0.5, 0.5) is the tile centre, (0, 0) the
    lower-left corner, (1, 1) the upper-right. So a scale of (0.5, 1.0) about
    (0.5, 0.5) leaves the UVs half as wide and still centred in the tile, while
    the same scale about (0, 0.5) pins them to the tile's left edge.

    The tile rect passed in is the *usable* rect, i.e. already inset by padding,
    so scaling stays inside the padded area.
    """
    size = tile_max - tile_min
    anchor_u = tile_min.x + size.x * pivot[0]
    anchor_v = tile_min.y + size.y * pivot[1]
    scale_u, scale_v = scale[0], scale[1]

    for luv in uv_loops:
        u, v = luv.uv
        luv.uv = Vector((anchor_u + (u - anchor_u) * scale_u,
                         anchor_v + (v - anchor_v) * scale_v))


def clear_seams_on_selected(bm):
    """Clear all seams on edges that touch selected faces."""
    for edge in bm.edges:
        if any(f.select for f in edge.link_faces):
            edge.seam = False


def mark_boundary_seams(bm):
    """Mark seams on boundary edges of selected faces."""
    for edge in bm.edges:
        sel_count = sum(1 for f in edge.link_faces if f.select)
        total = len(edge.link_faces)
        if sel_count > 0 and (sel_count < total or total == 1):
            edge.seam = True


# ============================================================================
# ATLAS IMAGE STATE
# ============================================================================
#
# The panel preview (template_icon) and the viewport picker overlay must always
# show the SAME picture. The panel draws Blender's cached Image preview, the
# overlay draws the live image pixels — either can go stale when a texture is
# reloaded, repathed or re-generated. Everything below exists to keep the two in
# sync and to never render Blender's magenta "missing image" placeholder as if
# it were the atlas.

# Bumped whenever the atlas pixel data may have changed. Used as the cache key
# for the overlay's GPU texture so a reload is picked up on the next redraw.
_atlas_refresh_token = 0

# image name -> (token, GPUTexture) for the preview-pixel fallback path.
_atlas_preview_tex_cache = {}

# abspath -> (token, exists) so the overlay does not stat the disk every frame.
_atlas_path_exists_cache = {}


def bump_atlas_refresh_token():
    """Invalidate every cached atlas GPU texture and path lookup."""
    global _atlas_refresh_token
    _atlas_refresh_token += 1
    _atlas_preview_tex_cache.clear()
    _atlas_path_exists_cache.clear()


def get_image_abspath(img):
    """Absolute on-disk path for a file-backed image, or "" if it has none.

    TILED (UDIM) images are excluded on purpose: their filepath carries a
    <UDIM> token that never exists on disk, so an existence check on it would
    mark every UDIM atlas as missing.
    """
    if img is None or img.source not in {'FILE', 'SEQUENCE', 'MOVIE'}:
        return ""
    raw = img.filepath_raw or img.filepath
    if not raw:
        return ""
    try:
        return bpy.path.abspath(raw, library=img.library)
    except Exception:
        return ""


def image_is_packed(img):
    """True if the image carries its own data inside the .blend."""
    if img is None:
        return False
    if getattr(img, "packed_file", None) is not None:
        return True
    return bool(getattr(img, "packed_files", None))


def image_file_missing(img):
    """True if the image points at a file path that does not exist on disk.

    This is the one condition that reliably produces Blender's magenta
    "missing image" texture, so it is the only thing treated as a hard error.
    """
    if img is None or image_is_packed(img):
        return False
    path = get_image_abspath(img)
    if not path:
        return False
    cached = _atlas_path_exists_cache.get(path)
    if cached is not None and cached[0] == _atlas_refresh_token:
        return not cached[1]
    exists = os.path.exists(path)
    _atlas_path_exists_cache[path] = (_atlas_refresh_token, exists)
    return not exists


def image_buffer_loaded(img):
    """True if the image's pixel buffer happens to be cached in memory *now*.

    NOT a health check. Blender loads image buffers lazily and frees them under
    its image cache limit, and ``Image.reload()`` deliberately drops the buffer
    so it is re-read on next use — so a perfectly good atlas reports False here
    most of the time, and ``Image.size`` reads (0, 0) alongside it. Only use this
    to decide whether a cheap shortcut is available, never to decide that an
    image is broken.
    """
    if img is None:
        return False
    try:
        return bool(img.has_data) and img.size[0] > 0 and img.size[1] > 0
    except Exception:
        return False


def image_is_resolvable(img):
    """True unless we can positively prove the image cannot supply pixels.

    Deliberately optimistic: requesting the GPU texture is what forces Blender to
    load the buffer, so anything that is packed, generated, or backed by a file
    that exists on disk gets the benefit of the doubt.
    """
    if img is None:
        return False
    if img.source in {'GENERATED', 'VIEWER'} or image_is_packed(img):
        return True
    if not get_image_abspath(img):
        # No usable path recorded — only trust it if pixels are already loaded.
        return image_buffer_loaded(img)
    return not image_file_missing(img)


def describe_atlas_image(img):
    """Return (ok, message, icon) summarising the atlas image's usability."""
    if img is None:
        return False, "No atlas texture set", 'ERROR'
    if image_file_missing(img):
        return False, f"File not found: {os.path.basename(get_image_abspath(img))}", 'ERROR'
    try:
        width, height = img.size[0], img.size[1]
    except Exception:
        width = height = 0
    if width > 0 and height > 0:
        return True, f"{width} x {height}", 'IMAGE_DATA'
    # Buffer not cached right now — normal for a lazily loaded or just-reloaded
    # image, and not a problem: it loads on the next draw.
    return True, f"{img.name} (loads on use)", 'IMAGE_DATA'


def refresh_atlas_image(img, reload_from_disk):
    """Re-read an atlas image and its preview thumbnail.

    Setting ``reload_from_disk`` re-reads the file (Image.reload), which also
    drops Blender's cached GPU texture. Without it only the preview thumbnail is
    regenerated from the pixel data already in memory.

    Returns (ok, message).
    """
    if img is None:
        return False, "No atlas image set"

    if reload_from_disk:
        try:
            img.reload()
        except Exception as exc:
            return False, f"Could not reload image: {exc}"

    # Regenerate the thumbnail the panel draws, so preview and overlay agree.
    try:
        img.preview_ensure()
        if img.preview is not None:
            img.preview.reload()
    except Exception as exc:
        bump_atlas_refresh_token()
        return False, f"Could not refresh preview: {exc}"

    bump_atlas_refresh_token()

    if image_file_missing(img):
        return False, f"File not found: {os.path.basename(get_image_abspath(img))}"

    # Deliberately NOT checking has_data/size here: Image.reload() drops the
    # pixel buffer so it is re-read lazily on next use, so a successful reload
    # legitimately reports "no data" until something draws the image.
    verb = "Reloaded" if reload_from_disk else "Refreshed"
    return True, f"{verb} {img.name}"


def _texture_from_preview_pixels(img):
    """Build a GPU texture from the *preview thumbnail* the panel displays.

    Fallback for images whose full-resolution buffer is unavailable (freed,
    unloaded, or file missing while a thumbnail survives in the .blend). Low
    resolution, but it is literally the picture shown in the preview window.
    """
    preview = getattr(img, "preview", None)
    if preview is None:
        return None
    try:
        width, height = preview.image_size[0], preview.image_size[1]
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None

    count = width * height * 4
    pixels = [0.0] * count
    try:
        preview.image_pixels_float.foreach_get(pixels)
    except Exception:
        try:
            pixels = list(preview.image_pixels_float)
        except Exception:
            return None
    if len(pixels) != count or not any(pixels):
        return None

    try:
        return GPUTexture(
            (width, height), format='RGBA16F',
            data=Buffer('FLOAT', count, pixels),
        )
    except Exception:
        return None


def get_atlas_gpu_texture(img):
    """Return (texture, source) for drawing the atlas behind the picker grid.

    source is 'IMAGE' (live full-resolution pixels), 'PREVIEW' (the panel's
    thumbnail) or '' when nothing drawable exists. Never returns Blender's
    magenta missing-image placeholder.
    """
    if img is None:
        return None, ""

    # Requesting the GPU texture is what forces Blender to load a lazily-loaded
    # or just-reloaded buffer, so ask for it unless the file is provably gone.
    if image_is_resolvable(img):
        try:
            texture = gpu.texture.from_image(img)
            if texture is not None:
                return texture, 'IMAGE'
        except Exception:
            pass

    cached = _atlas_preview_tex_cache.get(img.name)
    if cached and cached[0] == _atlas_refresh_token:
        return cached[1], ('PREVIEW' if cached[1] is not None else "")

    texture = _texture_from_preview_pixels(img)
    _atlas_preview_tex_cache[img.name] = (_atlas_refresh_token, texture)
    return texture, ('PREVIEW' if texture is not None else "")


# ============================================================================
# PROPERTY GROUPS
# ============================================================================


def get_grid_settings(context):
    """Return the active grid/atlas settings — per-object or global.

    Returns (grid_source, settings) where grid_source has: grid_cols, grid_rows,
    padding, proportion_x, proportion_y, atlas_image.
    settings is always the scene-level TILEUV_Settings (for unwrap/projection/etc).
    """
    settings = context.scene.tileuv_settings
    if settings.use_per_object and context.active_object:
        return context.active_object.tileuv_obj_settings, settings
    return settings, settings


class TILEUV_CustomTile(PropertyGroup):
    """A single custom atlas tile with arbitrary UV rect."""
    name: StringProperty(
        name="Name", default="Tile",
        description="Label for this tile in the list",
    )
    min_u: FloatProperty(
        name="Min U", default=0.0, min=0.0, max=1.0,
        description="Left edge of the tile in UV space",
    )
    min_v: FloatProperty(
        name="Min V", default=0.0, min=0.0, max=1.0,
        description="Bottom edge of the tile in UV space",
    )
    max_u: FloatProperty(
        name="Max U", default=0.25, min=0.0, max=1.0,
        description="Right edge of the tile in UV space",
    )
    max_v: FloatProperty(
        name="Max V", default=0.25, min=0.0, max=1.0,
        description="Top edge of the tile in UV space",
    )



class TILEUV_ObjectSettings(PropertyGroup):
    """Per-object grid and atlas settings."""
    grid_cols: IntProperty(
        name="Columns", default=4, min=1, max=64,
        description="Number of columns in the tile grid",
    )
    grid_rows: IntProperty(
        name="Rows", default=4, min=1, max=64,
        description="Number of rows in the tile grid",
    )
    padding: FloatProperty(
        name="Padding", default=0.005, min=0.0, max=0.1,
        precision=4, step=0.1,
        description="Padding inside each tile in UV space",
    )
    proportion_x: FloatProperty(
        name="W", default=1.0, min=0.1, max=10.0,
        description="Texture width proportion",
    )
    proportion_y: FloatProperty(
        name="H", default=1.0, min=0.1, max=10.0,
        description="Texture height proportion",
    )
    atlas_image: PointerProperty(
        type=bpy.types.Image,
        name="Atlas Texture",
        description="Texture image for this object",
    )


class TILEUV_Settings(PropertyGroup):
    """Main settings for Tile UV Projector."""

    # Per-object toggle
    use_per_object: BoolProperty(
        name="Per Object",
        default=False,
        description="Use per-object grid and atlas settings instead of global",
    )

    # Grid
    grid_cols: IntProperty(
        name="Columns", default=4, min=1, max=64,
        description="Number of columns in the tile grid",
    )
    grid_rows: IntProperty(
        name="Rows", default=4, min=1, max=64,
        description="Number of rows in the tile grid",
    )
    padding: FloatProperty(
        name="Padding", default=0.005, min=0.0, max=0.1,
        precision=4, step=0.1,
        description="Padding inside each tile in UV space",
    )

    # Grid proportion (width : height ratio for visual button sizing)
    proportion_x: FloatProperty(
        name="W", default=1.0, min=0.1, max=10.0,
        description="Texture width proportion (e.g. 2 for a 2:1 landscape texture)",
    )
    proportion_y: FloatProperty(
        name="H", default=1.0, min=0.1, max=10.0,
        description="Texture height proportion (e.g. 2 for a 1:2 portrait texture)",
    )

    # Atlas texture preview
    atlas_image: PointerProperty(
        type=bpy.types.Image,
        name="Atlas Texture",
        description="Texture image to display behind the grid for visual reference",
    )
    # Unwrap
    clear_seams: BoolProperty(
        name="Clear Seams", default=True,
        description="Clear existing seams on selected faces before unwrapping",
    )
    auto_seams: BoolProperty(
        name="Auto Seams", default=True,
        description="Automatically mark seams on selection boundary before unwrapping",
    )
    unwrap_method: EnumProperty(
        name="Method",
        items=[
            ('ANGLE_BASED', "Angle Based", "Angle-based flattening"),
            ('CONFORMAL', "Conformal", "Conformal mapping"),
        ],
        default='ANGLE_BASED',
        description="UV unwrap algorithm",
    )
    do_relax: BoolProperty(
        name="Relax", default=False,
        description="Run UV relaxation after unwrapping",
    )
    relax_iterations: IntProperty(
        name="Iterations", default=10, min=1, max=500,
        description="Number of relaxation iterations",
    )

    # Projection
    projection_method: EnumProperty(
        name="Projection",
        items=[
            ('PROJECT_AND_UNWRAP', "Project + Unwrap", "Project from view, then unwrap"),
            ('PROJECT_ONLY', "Project Only", "Project from view without unwrapping"),
            ('UNWRAP_ONLY', "Unwrap Only", "Skip projection, only unwrap"),
        ],
        default='PROJECT_AND_UNWRAP',
        description="UV projection method",
    )

    # Fine adjust
    fine_adjust_enabled: BoolProperty(
        name="Fine Adjust After Project",
        default=False,
        description="After placing UVs in a tile, enter an interactive transform "
                    "mode to nudge, scale and rotate them inside the tile",
    )
    fine_adjust_hide_overlays: BoolProperty(
        name="Hide Overlays & Gizmos",
        default=True,
        description="Temporarily switch off viewport overlays and gizmos for an "
                    "unobstructed view. The previous state is restored on exit",
    )
    fine_adjust_flat_shading: BoolProperty(
        name="Flat Textured Shading",
        default=True,
        description="Temporarily switch to Solid shading with flat lighting and "
                    "texture colour, so the atlas is seen unlit. The previous "
                    "shading is restored on exit",
    )

    # Tile scale, applied after projecting
    use_tile_scale: BoolProperty(
        name="Tile Scale",
        default=False,
        description="After fitting the UVs into a tile, scale them inside that "
                    "tile by a fixed amount",
    )
    tile_scale: FloatVectorProperty(
        name="Scale",
        size=2,
        default=(1.0, 1.0),
        min=0.001, max=10.0,
        precision=3,
        description="UV scale applied inside the tile after projecting. "
                    "(0.5, 1.0) is half as wide at full height",
    )
    tile_scale_pivot: FloatVectorProperty(
        name="Pivot",
        size=2,
        default=(0.5, 0.5),
        min=0.0, max=1.0,
        precision=3,
        description="Anchor for the default scale, in tile space. "
                    "(0.5, 0.5) is the tile centre, (0, 0) its lower-left corner",
    )

    # Fine adjust snap increments (Ctrl)
    snap_move_divisions: IntProperty(
        name="Move",
        default=int(_SNAP_TILE_FRACTION), min=1, max=64,
        description="Ctrl-snap step when moving: one Nth of a tile on each "
                    "axis. Divisions of a tile keep tile centres and edges on "
                    "the grid at any grid size",
    )
    snap_scale_step: FloatProperty(
        name="Scale",
        default=_SNAP_SCALE, min=0.001, max=1.0,
        precision=3, step=1,
        description="Ctrl-snap step when scaling",
    )
    snap_rotate_degrees: FloatProperty(
        name="Rotate",
        default=_SNAP_ANGLE_DEG, min=0.1, max=90.0,
        precision=2,
        description="Ctrl-snap step when rotating, in degrees",
    )

    # Advanced grid
    use_advanced_grid: BoolProperty(
        name="Advanced Grid", default=False,
        description="Use custom atlas tiles instead of uniform grid",
    )
    custom_tiles: CollectionProperty(
        type=TILEUV_CustomTile,
        description="Custom atlas tiles with arbitrary UV rectangles",
    )
    active_custom_tile: IntProperty(
        name="Active Tile", default=0, min=0,
        description="Index of the selected custom tile",
    )

    # Split direction for advanced grid
    split_direction: EnumProperty(
        name="Split",
        items=[
            ('HORIZONTAL', "Horizontal", "Split tile horizontally"),
            ('VERTICAL', "Vertical", "Split tile vertically"),
        ],
        default='HORIZONTAL',
        description="Direction to split the active custom tile in",
    )


# ============================================================================
# OPERATORS
# ============================================================================

class TILEUV_OT_apply_to_tile(Operator):
    """Project and place selected face UVs into a grid tile"""
    bl_idname = "uv.tileuv_apply_to_tile"
    bl_label = "Apply to Tile"
    bl_options = {'REGISTER', 'UNDO'}

    col_index: IntProperty(
        name="Column", default=0, min=0,
        description="Grid column of the target tile, counted from the left",
        options={'SKIP_SAVE'},
    )
    row_index: IntProperty(
        name="Row", default=0, min=0,
        description="Grid row of the target tile, counted from the bottom",
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT')

    def execute(self, context):
        grid, settings = get_grid_settings(context)

        targets = get_edit_mesh_targets(context)
        if not targets:
            self.report({'WARNING'}, "No mesh in Edit Mode")
            return {'CANCELLED'}

        if not count_selected_faces(targets):
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        # Validate the tile BEFORE touching any mesh, so a rejected apply
        # cannot leave a freshly created UV layer or modified seams behind.
        tile_min, tile_max = get_tile_bounds(
            self.col_index, self.row_index,
            grid.grid_cols, grid.grid_rows
        )
        pad = grid.padding
        usable_min = tile_min + Vector((pad, pad))
        usable_max = tile_max - Vector((pad, pad))

        if usable_min.x >= usable_max.x or usable_min.y >= usable_max.y:
            self.report({'ERROR'}, "Padding too large for tile size")
            return {'CANCELLED'}

        warn_unapplied_scale(self, targets)

        # Seams, on every mesh in Edit Mode
        if settings.clear_seams or settings.auto_seams:
            for _obj, me in targets:
                bm = bmesh.from_edit_mesh(me)
                if settings.clear_seams:
                    clear_seams_on_selected(bm)
                if settings.auto_seams:
                    mark_boundary_seams(bm)
                bmesh.update_edit_mesh(me)

        if not run_projection_ops(self, context, settings):
            return {'CANCELLED'}

        # Re-collect after the operator calls, across every edit-mode mesh.
        uv_loops, meshes = collect_edit_uv_loops(targets)
        if not uv_loops:
            self.report({'WARNING'}, "No UV data found")
            return {'CANCELLED'}

        if not place_loops_in_tile(self, settings, uv_loops, meshes,
                                   usable_min, usable_max):
            return {'CANCELLED'}

        self.report({'INFO'}, f"UVs placed in tile ({self.col_index}, {self.row_index})")
        maybe_start_fine_adjust(context, settings)
        return {'FINISHED'}


class TILEUV_OT_apply_to_custom_tile(Operator):
    """Project and place selected face UVs into a custom atlas tile"""
    bl_idname = "uv.tileuv_apply_to_custom_tile"
    bl_label = "Apply to Custom Tile"
    bl_options = {'REGISTER', 'UNDO'}

    tile_index: IntProperty(
        name="Tile", default=0, min=0,
        description="Index of the custom tile to place the UVs in",
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT')

    def execute(self, context):
        grid, settings = get_grid_settings(context)

        if self.tile_index < 0 or self.tile_index >= len(settings.custom_tiles):
            self.report({'ERROR'}, "Invalid tile index")
            return {'CANCELLED'}

        tile = settings.custom_tiles[self.tile_index]

        targets = get_edit_mesh_targets(context)
        if not targets:
            self.report({'WARNING'}, "No mesh in Edit Mode")
            return {'CANCELLED'}

        if not count_selected_faces(targets):
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        # An inverted or zero-size rect used to be diagnosed as "padding too
        # large", which fires even at zero padding and sends the user to the
        # wrong setting.
        if tile.max_u <= tile.min_u or tile.max_v <= tile.min_v:
            self.report({'ERROR'},
                        f"Tile '{tile.name}' has no area — Max U/V must be "
                        f"greater than Min U/V")
            return {'CANCELLED'}

        # Padding comes from the same source as the uniform grid, so Per Object
        # settings are honoured in both modes.
        pad = grid.padding
        usable_min = Vector((tile.min_u + pad, tile.min_v + pad))
        usable_max = Vector((tile.max_u - pad, tile.max_v - pad))

        if usable_min.x >= usable_max.x or usable_min.y >= usable_max.y:
            self.report({'ERROR'}, "Padding too large for tile size")
            return {'CANCELLED'}

        warn_unapplied_scale(self, targets)

        if settings.clear_seams or settings.auto_seams:
            for _obj, me in targets:
                bm = bmesh.from_edit_mesh(me)
                if settings.clear_seams:
                    clear_seams_on_selected(bm)
                if settings.auto_seams:
                    mark_boundary_seams(bm)
                bmesh.update_edit_mesh(me)

        if not run_projection_ops(self, context, settings):
            return {'CANCELLED'}

        uv_loops, meshes = collect_edit_uv_loops(targets)
        if not uv_loops:
            self.report({'WARNING'}, "No UV data found")
            return {'CANCELLED'}

        if not place_loops_in_tile(self, settings, uv_loops, meshes,
                                   usable_min, usable_max):
            return {'CANCELLED'}

        self.report({'INFO'}, f"UVs placed in custom tile '{tile.name}'")
        maybe_start_fine_adjust(context, settings)
        return {'FINISHED'}


class TILEUV_OT_add_custom_tile(Operator):
    """Add a new custom atlas tile"""
    bl_idname = "uv.tileuv_add_custom_tile"
    bl_label = "Add Tile"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.tileuv_settings
        tile = settings.custom_tiles.add()
        idx = len(settings.custom_tiles) - 1
        tile.name = f"Tile {idx}"
        settings.active_custom_tile = idx
        return {'FINISHED'}


class TILEUV_OT_remove_custom_tile(Operator):
    """Remove the active custom atlas tile"""
    bl_idname = "uv.tileuv_remove_custom_tile"
    bl_label = "Remove Tile"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.tileuv_settings
        return len(settings.custom_tiles) > 0

    def execute(self, context):
        settings = context.scene.tileuv_settings
        idx = settings.active_custom_tile
        settings.custom_tiles.remove(idx)
        settings.active_custom_tile = max(
            0, min(idx, len(settings.custom_tiles) - 1))
        return {'FINISHED'}


class TILEUV_OT_split_custom_tile(Operator):
    """Split the active custom tile in half"""
    bl_idname = "uv.tileuv_split_custom_tile"
    bl_label = "Split Tile"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.tileuv_settings
        return len(settings.custom_tiles) > 0

    def execute(self, context):
        settings = context.scene.tileuv_settings
        idx = settings.active_custom_tile

        if idx < 0 or idx >= len(settings.custom_tiles):
            self.report({'WARNING'}, "No tile selected")
            return {'CANCELLED'}

        src = settings.custom_tiles[idx]
        direction = settings.split_direction

        if direction == 'HORIZONTAL':
            mid_v = (src.min_v + src.max_v) / 2.0
            # Modify original to be bottom half
            orig_max_v = src.max_v
            src.max_v = mid_v
            src.name = strip_split_suffix(src.name) + " (bottom)"
            # Add top half
            new_tile = settings.custom_tiles.add()
            new_tile.name = src.name.replace("(bottom)", "(top)")
            new_tile.min_u = src.min_u
            new_tile.max_u = src.max_u
            new_tile.min_v = mid_v
            new_tile.max_v = orig_max_v
        else:  # VERTICAL
            mid_u = (src.min_u + src.max_u) / 2.0
            orig_max_u = src.max_u
            src.max_u = mid_u
            src.name = strip_split_suffix(src.name) + " (left)"
            new_tile = settings.custom_tiles.add()
            new_tile.name = src.name.replace("(left)", "(right)")
            new_tile.min_u = mid_u
            new_tile.max_u = orig_max_u
            new_tile.min_v = src.min_v
            new_tile.max_v = src.max_v

        return {'FINISHED'}


class TILEUV_OT_generate_grid_tiles(Operator):
    """Generate custom tiles from current uniform grid settings"""
    bl_idname = "uv.tileuv_generate_grid_tiles"
    bl_label = "Generate from Grid"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        grid, settings = get_grid_settings(context)
        settings.custom_tiles.clear()

        cols = grid.grid_cols
        rows = grid.grid_rows

        for row in range(rows):
            for col in range(cols):
                tile = settings.custom_tiles.add()
                tile.name = f"Tile ({col}, {row})"
                tile.min_u = col / cols
                tile.min_v = row / rows
                tile.max_u = (col + 1) / cols
                tile.max_v = (row + 1) / rows

        settings.active_custom_tile = 0
        self.report({'INFO'}, f"Generated {cols * rows} tiles")
        return {'FINISHED'}


class TILEUV_OT_pick_tile(Operator):
    """Open persistent atlas tile picker overlay in the viewport"""
    bl_idname = "uv.tileuv_pick_tile"
    bl_label = "Atlas Tile Picker"

    # Class-level state so panel can query and close operator can signal
    _handle = None
    _is_active: bool = False
    _should_close: bool = False
    _overlay_x: int = 0
    _overlay_y: int = 0
    _overlay_w: int = 0
    _overlay_h: int = 0
    _hover_col: int = -1
    _hover_row: int = -1
    _last_click_col: int = -1
    _last_click_row: int = -1
    _ui_region_x: int = 0
    _ui_region_y: int = 0
    _initial_scroll: float = 0.0
    # The viewport the picker was opened in. A SpaceView3D draw handler fires
    # for EVERY 3D view, so without this the overlay is painted into every open
    # viewport's sidebar at coordinates computed for a different one.
    _space = None

    @classmethod
    def is_running(cls):
        """True if the modal picker is genuinely still alive.

        Blender can tear a modal operator down without routing through modal()
        — file load, area close, script reload, an undo that swallows the modal.
        The draw handler is the reliable witness: if it is gone the operator is
        gone too, so clear the stale flag instead of blocking the picker from
        ever being opened again.
        """
        if cls._is_active and cls._handle is None:
            cls._is_active = False
            cls._should_close = False
        return cls._is_active

    @classmethod
    def force_reset(cls):
        """Drop a leaked draw handler and clear all picker state."""
        if cls._handle is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(cls._handle, 'UI')
            except Exception:
                pass
            cls._handle = None
        cls._space = None
        cls._is_active = False
        cls._should_close = False

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT'
                and not cls.is_running()
                # Two live modals fight over every event, and the older one
                # starves. Adjust mode also caches UVs that a re-project would
                # invalidate, so letting both run risks silent data loss.
                and not TILEUV_OT_fine_adjust.is_running())

    def invoke(self, context, event):
        cls = self.__class__
        grid, settings = get_grid_settings(context)

        # Warn about a genuinely broken atlas, but never block the picker: the
        # grid stays usable even with no texture behind it.
        img = grid.atlas_image
        if img is not None and image_file_missing(img):
            self.report(
                {'WARNING'},
                f"Atlas file not found: {os.path.basename(get_image_abspath(img))}",
            )

        # Find the UI region (N-panel)
        ui_region = None
        for reg in context.area.regions:
            if reg.type == 'UI':
                ui_region = reg
                break

        if not ui_region or ui_region.width < 20:
            self.report({'WARNING'}, "Open the N-panel first (press N)")
            return {'CANCELLED'}

        # Compute template_icon size to match exactly
        # template_icon(scale=S) produces a square of S * ui_unit pixels
        prop_x = grid.proportion_x
        prop_y = grid.proportion_y
        icon_scale = max(3.0, min(16.0, 12.0 * (prop_y / prop_x)))

        dpi_fac = context.preferences.system.dpi / 72.0
        ui_scale = context.preferences.view.ui_scale
        ui_unit = 20.0 * dpi_fac * ui_scale

        # template_icon is a square of this size
        preview_size = int(icon_scale * ui_unit)

        # But it can't exceed the panel content width (sidebar width minus padding)
        panel_content_w = ui_region.width - 12  # approximate panel margins
        preview_size = min(preview_size, panel_content_w)

        cls._overlay_w = preview_size
        cls._overlay_h = preview_size

        # Center horizontally in the region (same as template_icon)
        cls._overlay_x = (ui_region.width - cls._overlay_w) // 2

        # The "Pick Tile" button is directly below template_icon.
        # Click lands in center of button (height ~1.2 * ui_unit).
        # So template_icon bottom ≈ click_y + half_button_height
        click_ui_y = event.mouse_y - ui_region.y
        button_half_h = int(1.2 * ui_unit * 0.5)
        cls._overlay_y = click_ui_y + button_half_h

        # Clamp within region
        cls._overlay_y = max(4, min(cls._overlay_y,
                                     ui_region.height - cls._overlay_h - 4))

        # Store scroll and region position
        cls._ui_region_x = ui_region.x
        cls._ui_region_y = ui_region.y
        cls._initial_scroll = ui_region.view2d.region_to_view(0, 0)[1]

        cls._hover_col = -1
        cls._hover_row = -1
        cls._last_click_col = -1
        cls._last_click_row = -1
        cls._should_close = False
        cls._space = context.space_data
        cls._is_active = True

        cls._handle = bpy.types.SpaceView3D.draw_handler_add(
            cls._draw_callback,
            (cls, context),
            'UI', 'POST_PIXEL',
        )

        if not context.window_manager.modal_handler_add(self):
            # Without a handler no event arrives, so the draw handler added
            # above would linger with _is_active stuck True.
            cls.force_reset()
            self.report({'ERROR'}, "Could not start the tile picker")
            return {'CANCELLED'}
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        cls = self.__class__
        area = getattr(context, "area", None)
        grid, settings = get_grid_settings(context)

        # External close request (from panel toggle button)
        if cls._should_close:
            self._cleanup(context)
            return {'CANCELLED'}

        # Exit if user leaves edit mode
        obj = context.active_object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            self._cleanup(context)
            return {'CANCELLED'}

        # Update UI region screen position (handles panel resize)
        ui_region = None
        for reg in context.area.regions:
            if reg.type == 'UI':
                ui_region = reg
                cls._ui_region_x = reg.x
                cls._ui_region_y = reg.y
                break

        # Convert absolute mouse coords to UI region-relative
        ui_mx = event.mouse_x - cls._ui_region_x
        ui_my = event.mouse_y - cls._ui_region_y

        # Scroll-adjusted overlay Y for hit testing
        if ui_region:
            current_scroll = ui_region.view2d.region_to_view(0, 0)[1]
            scroll_delta = current_scroll - cls._initial_scroll
        else:
            scroll_delta = 0.0
        adj_oy = cls._overlay_y - int(scroll_delta)

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            col, row = self._tile_at_scrolled(ui_mx, ui_my, adj_oy, grid)
            if (col, row) != (cls._hover_col, cls._hover_row):
                cls._hover_col, cls._hover_row = col, row
                if area is not None:
                    area.tag_redraw()
            return {'RUNNING_MODAL'}

        if area is not None:
            area.tag_redraw()

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            col, row = self._tile_at_scrolled(ui_mx, ui_my, adj_oy, grid)
            if col >= 0 and row >= 0:
                cls._last_click_col = col
                cls._last_click_row = row
                # Close the picker *before* applying: the apply operator may
                # hand straight over to the fine adjust modal, and two of our
                # modals must never be live at the same time.
                self._cleanup(context)
                bpy.ops.uv.tileuv_apply_to_tile(col_index=col, row_index=row)
                return {'FINISHED'}
            # Click outside overlay — pass through to Blender
            return {'PASS_THROUGH'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self._cleanup(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def _tile_at_scrolled(self, mx, my, adj_oy, settings):
        """Convert UI-region mouse coords to (col, row), accounting for scroll."""
        cls = self.__class__
        ox = cls._overlay_x
        ow, oh = cls._overlay_w, cls._overlay_h

        if mx < ox or mx >= ox + ow or my < adj_oy or my >= adj_oy + oh:
            return -1, -1

        rx = (mx - ox) / ow
        ry = (my - adj_oy) / oh

        col = min(int(rx * settings.grid_cols), settings.grid_cols - 1)
        row = min(int(ry * settings.grid_rows), settings.grid_rows - 1)
        return col, row

    def cancel(self, context):
        """Called by Blender when the modal is torn down outside modal()."""
        self._cleanup(context)

    def _cleanup(self, context):
        self.__class__.force_reset()
        area = getattr(context, "area", None)
        if area is not None:
            area.tag_redraw()

    @staticmethod
    def _draw_callback(cls, context):
        # Only paint into the viewport this picker belongs to.
        if cls._space is not None and context.space_data != cls._space:
            return
        try:
            cls._draw_overlay(context)
        except Exception:
            # A raise here would repeat on every redraw forever. Drop the
            # overlay instead of wallpapering the console.
            import traceback
            traceback.print_exc()
            cls.force_reset()

    @staticmethod
    def _draw_overlay(context):
        cls = TILEUV_OT_pick_tile
        grid, settings = get_grid_settings(context)
        ow, oh = cls._overlay_w, cls._overlay_h
        cols = grid.grid_cols
        rows = grid.grid_rows

        # Compensate for N-panel scroll
        region = context.region
        current_scroll = region.view2d.region_to_view(0, 0)[1]
        scroll_delta = current_scroll - cls._initial_scroll
        ox = cls._overlay_x
        oy = cls._overlay_y - int(scroll_delta)

        gpu.state.blend_set('ALPHA')
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        # --- Atlas image ---
        # Resolve the texture first: an image with no pixel data would otherwise
        # be drawn as Blender's magenta "missing image" placeholder.
        img = grid.atlas_image
        texture, tex_source = get_atlas_gpu_texture(img)
        drew_image = False
        if texture is not None:
            try:
                shader_img = gpu.shader.from_builtin('IMAGE')
                batch_img = batch_for_shader(
                    shader_img, 'TRI_FAN',
                    {
                        "pos": [(ox, oy), (ox + ow, oy),
                                (ox + ow, oy + oh), (ox, oy + oh)],
                        "texCoord": [(0, 0), (1, 0), (1, 1), (0, 1)],
                    },
                )
                shader_img.bind()
                shader_img.uniform_sampler("image", texture)
                batch_img.draw(shader_img)
                drew_image = True
            except Exception:
                pass

        if not drew_image:
            batch_bg = batch_for_shader(
                shader, 'TRI_FAN',
                {"pos": [(ox, oy), (ox + ow, oy),
                         (ox + ow, oy + oh), (ox, oy + oh)]},
            )
            shader.bind()
            shader.uniform_float("color", (0.12, 0.12, 0.12, 0.92))
            batch_bg.draw(shader)

        tw = ow / cols
        th = oh / rows

        # --- Last-clicked tile (green) ---
        if cls._last_click_col >= 0 and cls._last_click_row >= 0:
            lx = ox + cls._last_click_col * tw
            ly = oy + cls._last_click_row * th
            batch_l = batch_for_shader(
                shader, 'TRI_FAN',
                {"pos": [(lx, ly), (lx + tw, ly),
                         (lx + tw, ly + th), (lx, ly + th)]},
            )
            shader.bind()
            shader.uniform_float("color", (0.1, 0.8, 0.2, 0.25))
            batch_l.draw(shader)

        # --- Hover highlight (orange) ---
        if cls._hover_col >= 0 and cls._hover_row >= 0:
            hx = ox + cls._hover_col * tw
            hy = oy + cls._hover_row * th
            batch_h = batch_for_shader(
                shader, 'TRI_FAN',
                {"pos": [(hx, hy), (hx + tw, hy),
                         (hx + tw, hy + th), (hx, hy + th)]},
            )
            shader.bind()
            shader.uniform_float("color", (1.0, 0.55, 0.0, 0.35))
            batch_h.draw(shader)

        # --- Grid lines ---
        lines = []
        for c in range(cols + 1):
            x = ox + c * tw
            lines.extend([(x, oy), (x, oy + oh)])
        for r in range(rows + 1):
            y = oy + r * th
            lines.extend([(ox, y), (ox + ow, y)])

        batch_lines = batch_for_shader(shader, 'LINES', {"pos": lines})
        shader.bind()
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.6))
        gpu.state.line_width_set(1.0)
        batch_lines.draw(shader)

        # --- Outer border ---
        border = [
            (ox, oy), (ox + ow, oy),
            (ox + ow, oy), (ox + ow, oy + oh),
            (ox + ow, oy + oh), (ox, oy + oh),
            (ox, oy + oh), (ox, oy),
        ]
        batch_b = batch_for_shader(shader, 'LINES', {"pos": border})
        shader.bind()
        shader.uniform_float("color", (1.0, 1.0, 1.0, 1.0))
        gpu.state.line_width_set(2.0)
        batch_b.draw(shader)
        gpu.state.line_width_set(1.0)

        # --- Tile labels ---
        # Skipped once a cell is too small to read them in: a 64x64 grid would
        # otherwise issue 4096 text draws on every single mouse move.
        font_id = 0
        blf.size(font_id, 10)
        blf.color(font_id, 1.0, 1.0, 1.0, 0.45)
        if tw >= 22 and th >= 14:
            for r in range(rows):
                for c in range(cols):
                    blf.position(font_id, ox + c * tw + 3, oy + r * th + 3, 0)
                    blf.draw(font_id, f"{c},{r}")

        # --- Texture-state notice (instead of a magenta placeholder) ---
        if not drew_image:
            _, state_msg, _ = describe_atlas_image(img)
            blf.size(font_id, 12)
            blf.color(font_id, 1.0, 0.35, 0.3, 1.0)
            msg_w = blf.dimensions(font_id, state_msg)[0]
            blf.position(font_id, ox + max(4, (ow - msg_w) / 2), oy + oh / 2, 0)
            blf.draw(font_id, state_msg)
        elif tex_source == 'PREVIEW':
            # Drawing the panel thumbnail, not the full-resolution image.
            note = "preview thumbnail — press Reload"
            blf.size(font_id, 10)
            blf.color(font_id, 1.0, 0.7, 0.2, 0.9)
            note_w = blf.dimensions(font_id, note)[0]
            blf.position(font_id, ox + max(2, (ow - note_w) / 2), oy + 4, 0)
            blf.draw(font_id, note)

        # --- Hover tooltip (inside overlay, top-center) ---
        if cls._hover_col >= 0 and cls._hover_row >= 0:
            blf.size(font_id, 12)
            blf.color(font_id, 1.0, 0.7, 0.2, 1.0)
            hover_text = f"({cls._hover_col}, {cls._hover_row})"
            htw = blf.dimensions(font_id, hover_text)[0]
            blf.position(font_id, ox + (ow - htw) / 2, oy + oh - 16, 0)
            blf.draw(font_id, hover_text)

        gpu.state.blend_set('NONE')


class TILEUV_OT_close_picker(Operator):
    """Close the atlas tile picker overlay"""
    bl_idname = "uv.tileuv_close_picker"
    bl_label = "Close Tile Picker"

    def execute(self, context):
        if TILEUV_OT_pick_tile.is_running() \
                and not TILEUV_OT_pick_tile._should_close:
            TILEUV_OT_pick_tile._should_close = True
        else:
            # Either the modal is already gone, or a previous request was never
            # consumed — which means it is not listening. Force the reset so the
            # panel button can never become permanently dead.
            TILEUV_OT_pick_tile.force_reset()
        _tag_ui_redraw(context)
        return {'FINISHED'}



# ============================================================================
# FINE ADJUST TRANSFORM MODE
# ============================================================================

# event.type -> character, for Blender-style numeric input during a transform.
_NUMERIC_KEYS = {
    'ZERO': '0', 'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4',
    'FIVE': '5', 'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9',
    'NUMPAD_0': '0', 'NUMPAD_1': '1', 'NUMPAD_2': '2', 'NUMPAD_3': '3',
    'NUMPAD_4': '4', 'NUMPAD_5': '5', 'NUMPAD_6': '6', 'NUMPAD_7': '7',
    'NUMPAD_8': '8', 'NUMPAD_9': '9',
    'PERIOD': '.', 'NUMPAD_PERIOD': '.',
}

# Added to both sides of the scale drag ratio so a transform started near the
# anchor still scales, while zero mouse movement still means a factor of 1.0.
_DRAG_SOFTEN_PX = 60.0

# Axis constraint keys -> the UV axis they lock to. Z is the V-axis key so an
# XZ modelling habit carries straight over; Y stays wired up as an alias.
_AXIS_KEYS = {'X': 'U', 'Z': 'V', 'Y': 'V'}

# What to call each axis in the header — matching the keys above, not U/V.
_AXIS_LABELS = {'U': 'X', 'V': 'Z'}

_CTRL_KEYS = {'LEFT_CTRL', 'RIGHT_CTRL'}
_SHIFT_KEYS = {'LEFT_SHIFT', 'RIGHT_SHIFT'}

# Passed through to the UI when the pointer is not over the 3D view, so the
# sidebar stays usable while the mode is running.
_MOUSE_BUTTONS = {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'}

# Above this many tiles the sidebar shows the picker hint instead of a button
# per tile — the buttons are rebuilt on every redraw.
_MAX_GRID_BUTTONS = 1024


# Events passed straight through so the user can still navigate the viewport
# while deciding what to adjust.
_NAV_EVENTS = {
    'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE',
    'WHEELINMOUSE', 'WHEELOUTMOUSE', 'TRACKPADPAN', 'TRACKPADZOOM',
    'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4', 'NUMPAD_5',
    'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 'NUMPAD_9', 'NUMPAD_0',
    'NUMPAD_PERIOD', 'NUMPAD_PLUS', 'NUMPAD_MINUS',
}


def space_is_open(space):
    """True if `space` is still present in some open area.

    SpaceView3D / View3DOverlay / ARegion are not ID datablocks, so Blender does
    not invalidate their Python wrappers when the area they belong to is closed
    or the file is replaced. Writing to a freed one is not catchable by
    try/except, so anything holding such a reference across events has to check
    it is still reachable first.
    """
    if space is None:
        return False
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                for candidate in area.spaces:
                    if candidate == space:
                        return True
    except Exception:
        return False
    return False


class ViewportStateSnapshot:
    """Records only the viewport properties we actually change, so they can be
    put back exactly as the user had them.

    Nothing is hard-coded on the way out: a property that already held the
    wanted value is neither recorded nor restored, and every restore writes back
    the value that was read at capture time. If the user had overlays off before
    entering fine adjust, they stay off afterwards.
    """

    def __init__(self):
        self._changes = []

    def set_tracked(self, owner, attr, value):
        """Set owner.attr, remembering the previous value for restore()."""
        if owner is None:
            return
        try:
            old = getattr(owner, attr)
        except Exception:
            return
        if old == value:
            # Already what we want — do not touch it, do not restore it.
            return
        try:
            setattr(owner, attr, value)
        except Exception:
            return
        self._changes.append((owner, attr, old))

    def restore(self):
        """Put every recorded property back, most recent change first."""
        while self._changes:
            owner, attr, old = self._changes.pop()
            try:
                setattr(owner, attr, old)
            except Exception:
                pass

    @property
    def is_empty(self):
        return not self._changes


class TILEUV_OT_fine_adjust(Operator):
    """Interactively move, scale and rotate the selected UVs

    Uses the familiar Blender transform keys: G/S/R to start, X or Y to
    constrain, type a number for an exact value, Ctrl to snap, Shift for
    precision. Enter confirms, Esc cancels
    """
    bl_idname = "uv.tileuv_fine_adjust"
    bl_label = "Fine Adjust UVs"
    bl_options = {'REGISTER'}

    _is_active: bool = False
    _should_close: bool = False
    _space = None
    # Kept on the class so a session that loses its events can still be undone
    # from the panel — otherwise a stuck modal leaves overlays off for good.
    _live_view_state = None

    @classmethod
    def is_running(cls):
        return cls._is_active

    @classmethod
    def force_reset(cls, restore_view=True):
        """Release the mode. `restore_view` False drops the recorded viewport
        state without writing it back — used on file load, where the spaces it
        refers to belong to the file being replaced."""
        if cls._live_view_state is not None:
            if restore_view:
                try:
                    cls._live_view_state.restore()
                except Exception:
                    pass
            cls._live_view_state = None
        cls._is_active = False
        cls._should_close = False
        cls._space = None

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT'
                and not cls._is_active
                and not TILEUV_OT_pick_tile.is_running())

    # -- lifecycle ---------------------------------------------------------

    def invoke(self, context, event):
        cls = self.__class__
        grid, settings = get_grid_settings(context)
        self._applies = 0
        self._mesh = None
        self._bm = None
        self._bm_id = None
        self._loops = None
        self._uv_base = None
        self._warned = False
        self._verified = False

        loops = self._fetch_loops(context)
        if loops is None:
            return {'CANCELLED'}

        self._uv_entry = [Vector(luv.uv) for luv in loops]
        if not self._uv_entry:
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        self._uv_base = list(self._uv_entry)

        # Aspect of the atlas, so rotation looks square on a non-square texture.
        try:
            self._aspect = max(1e-6, grid.proportion_x / grid.proportion_y)
        except Exception:
            self._aspect = 1.0

        # Snap increments, from the user's settings and the tile layout.
        try:
            cols = max(1, int(grid.grid_cols))
            rows = max(1, int(grid.grid_rows))
        except Exception:
            cols = rows = 4
        divisions = max(1, int(settings.snap_move_divisions))
        self._snap_u = 1.0 / (cols * divisions)
        self._snap_v = 1.0 / (rows * divisions)
        self._snap_scale = max(1e-4, float(settings.snap_scale_step))
        self._snap_angle = math.radians(
            max(0.01, float(settings.snap_rotate_degrees)))

        self._region = None
        for reg in context.area.regions:
            if reg.type == 'WINDOW':
                self._region = reg
                break
        if self._region is None:
            self.report({'WARNING'}, "No 3D viewport region found")
            return {'CANCELLED'}

        self._mode = 'NONE'
        self._axis = None
        self._numeric = ""
        self._snap = False
        self._precise = False
        self._start_mouse = (event.mouse_x, event.mouse_y)
        self._pivot = Vector((0.0, 0.0))
        self._finished = False
        self._dirty = False

        # View state is captured and applied only for the options the user
        # switched on; everything else is left untouched.
        self._view_state = ViewportStateSnapshot()
        space = context.space_data
        cls._space = space
        if space is not None and getattr(space, "type", "") == 'VIEW_3D':
            if settings.fine_adjust_hide_overlays:
                self._view_state.set_tracked(space.overlay, "show_overlays", False)
                self._view_state.set_tracked(space, "show_gizmo", False)
            if settings.fine_adjust_flat_shading:
                self._view_state.set_tracked(space.shading, "type", 'SOLID')
                self._view_state.set_tracked(space.shading, "light", 'FLAT')
                self._view_state.set_tracked(space.shading, "color_type", 'TEXTURE')

        cls._is_active = True
        cls._should_close = False
        cls._live_view_state = self._view_state
        self._update_status(context)
        added = context.window_manager.modal_handler_add(self)
        if not added:
            # Without a handler no event ever reaches modal(); bailing out beats
            # sitting there looking active while doing nothing.
            self.report({'ERROR'}, "Could not start the fine adjust modal")
            self._finish(context, revert=False)
            return {'CANCELLED'}
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        """Called by Blender when the modal is torn down outside modal()."""
        self._finish(context, revert=True)

    def _finish(self, context, revert):
        """Single exit path — idempotent, so a double teardown is harmless."""
        if self._finished:
            return
        self._finished = True

        if revert:
            self._write_uvs(context, self._uv_entry)
        elif self._dirty:
            try:
                bpy.ops.ed.undo_push(message="Fine Adjust UVs")
            except Exception:
                pass

        # Do not write viewport settings back into a space that has been
        # closed since the mode started — those structs are freed and the write
        # is not something try/except can save us from.
        if space_is_open(self.__class__._space):
            self._view_state.restore()
        self.__class__._live_view_state = None
        self.__class__._space = None
        self.__class__._is_active = False
        # Clear the request too, or the next session would close on its first
        # event.
        self.__class__._should_close = False

        area = getattr(context, "area", None)
        if area is not None:
            try:
                area.header_text_set(None)
            except Exception:
                pass
            area.tag_redraw()
        workspace = getattr(context, "workspace", None)
        if workspace is not None:
            try:
                workspace.status_text_set(None)
            except Exception:
                pass

    # -- modal -------------------------------------------------------------

    def modal(self, context, event):
        # Asked to stop from the panel. Checked before anything else so the
        # request is honoured even mid-transform.
        if self.__class__._should_close:
            self._finish(context, revert=False)
            return {'FINISHED'}

        obj = context.active_object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            self._finish(context, revert=False)
            return {'CANCELLED'}

        if self._mode == 'NONE':
            return self._modal_idle(context, event)
        return self._modal_transform(context, event)

    def _outside_viewport(self, event):
        """True when the pointer is off the 3D view, e.g. over the sidebar."""
        region = getattr(self, "_region", None)
        if region is None:
            return False
        return not (region.x <= event.mouse_x < region.x + region.width
                    and region.y <= event.mouse_y < region.y + region.height)

    def _modal_idle(self, context, event):
        # Clicks over the sidebar have to reach the buttons there — swallowing
        # them is what made Force Exit unclickable while adjusting.
        if event.type in _MOUSE_BUTTONS and self._outside_viewport(event):
            return {'PASS_THROUGH'}

        if event.value != 'PRESS':
            if event.type in _NAV_EVENTS:
                return {'PASS_THROUGH'}
            return {'RUNNING_MODAL'}

        if event.type in {'G', 'S', 'R'}:
            self._begin(context, event)
            return {'RUNNING_MODAL'}

        if event.type in {'RET', 'NUMPAD_ENTER', 'SPACE'}:
            self._finish(context, revert=False)
            self.report({'INFO'}, "Fine adjust applied")
            return {'FINISHED'}

        if event.type == 'ESC':
            self._finish(context, revert=True)
            self.report({'INFO'}, "Fine adjust cancelled")
            return {'CANCELLED'}

        if event.type in _NAV_EVENTS:
            return {'PASS_THROUGH'}

        # Swallow everything else so stray keys cannot edit the mesh.
        return {'RUNNING_MODAL'}

    def _sync_modifiers(self, event):
        """Track Ctrl/Shift from their own key events, not just event flags.

        Reading event.ctrl off whichever event happens to be in hand is not
        reliable — modifier flags on synthetic movement events can lag, which is
        why holding Ctrl appeared to do nothing while Shift worked. The dedicated
        modifier key events are authoritative for going down and coming back up;
        the flags on any other event are only ever used to turn a state on, never
        to clear one.
        """
        if event.type in _CTRL_KEYS:
            self._snap = event.value == 'PRESS'
        elif event.type in _SHIFT_KEYS:
            self._precise = event.value == 'PRESS'
        if getattr(event, "ctrl", False):
            self._snap = True
        if getattr(event, "shift", False):
            self._precise = True

    def _modal_transform(self, context, event):
        self._sync_modifiers(event)

        # Pressing or releasing a modifier has to take effect straight away,
        # otherwise snapping only appears once the mouse happens to move again
        # and reads as "Ctrl does nothing".
        if event.type in _CTRL_KEYS or event.type in _SHIFT_KEYS:
            if not self._numeric:
                self._apply(context, event)
            else:
                self._update_status(context)
            return {'RUNNING_MODAL'}

        # INBETWEEN_MOUSEMOVE is what a high-rate mouse or tablet mostly sends;
        # ignoring it makes the drag stutter.
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            if not self._numeric:
                self._apply(context, event)
            return {'RUNNING_MODAL'}

        if event.value == 'PRESS':
            # Switch transform type mid-flight, like Blender does.
            if event.type in {'G', 'S', 'R'}:
                self._write_uvs(context, self._uv_base)
                self._begin(context, event)
                return {'RUNNING_MODAL'}

            if event.type in _AXIS_KEYS:
                axis = _AXIS_KEYS[event.type]
                self._axis = None if self._axis == axis else axis
                self._apply(context, event)
                return {'RUNNING_MODAL'}

            if event.type == 'MIDDLEMOUSE':
                # Blender-style: the middle mouse picks the axis from the
                # direction dragged so far, and picking the current one drops
                # the constraint again.
                axis = self._axis_from_drag(event)
                self._axis = None if self._axis == axis else axis
                self._apply(context, event)
                return {'RUNNING_MODAL'}

            if event.type in _NUMERIC_KEYS:
                self._numeric += _NUMERIC_KEYS[event.type]
                self._apply(context, event)
                return {'RUNNING_MODAL'}

            if event.type in {'MINUS', 'NUMPAD_MINUS'}:
                if self._numeric.startswith('-'):
                    self._numeric = self._numeric[1:]
                else:
                    self._numeric = '-' + self._numeric
                self._apply(context, event)
                return {'RUNNING_MODAL'}

            if event.type == 'BACK_SPACE':
                self._numeric = self._numeric[:-1]
                self._apply(context, event)
                return {'RUNNING_MODAL'}

            if event.type in {'RET', 'NUMPAD_ENTER', 'LEFTMOUSE'}:
                self._dirty = True
                self._end_transform(context)
                return {'RUNNING_MODAL'}

            if event.type in {'ESC', 'RIGHTMOUSE'}:
                self._write_uvs(context, self._uv_base)
                self._end_transform(context)
                return {'RUNNING_MODAL'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    # -- transform helpers -------------------------------------------------

    def _begin(self, context, event):
        """Start a translate/scale/rotate from the current UV state."""
        self._mode = {'G': 'TRANSLATE', 'S': 'SCALE', 'R': 'ROTATE'}[event.type]
        self._axis = None
        self._numeric = ""
        self._snap = bool(getattr(event, "ctrl", False))
        self._precise = bool(getattr(event, "shift", False))
        self._start_mouse = (event.mouse_x, event.mouse_y)
        loops = self._fetch_loops(context)
        if loops is not None:
            self._uv_base = [Vector(luv.uv) for luv in loops]
        self._pivot = self._compute_pivot()
        self._update_status(context)

    def _axis_from_drag(self, event):
        """The axis the pointer has travelled furthest along since the start."""
        dx = abs(event.mouse_x - self._start_mouse[0])
        dy = abs(event.mouse_y - self._start_mouse[1])
        return 'U' if dx >= dy else 'V'

    def _end_transform(self, context):
        """Commit or discard the running transform and return to idle."""
        self._mode = 'NONE'
        self._axis = None
        self._numeric = ""
        self._snap = False
        self._precise = False
        self._update_status(context)

    def _compute_pivot(self):
        """Bounding-box centre of the selected UVs — i.e. the tile's centre."""
        if not self._uv_base:
            return Vector((0.0, 0.0))
        min_u = min(uv.x for uv in self._uv_base)
        max_u = max(uv.x for uv in self._uv_base)
        min_v = min(uv.y for uv in self._uv_base)
        max_v = max(uv.y for uv in self._uv_base)
        return Vector(((min_u + max_u) * 0.5, (min_v + max_v) * 0.5))

    def _numeric_value(self):
        try:
            return float(self._numeric)
        except (TypeError, ValueError):
            return None

    def _edit_mesh(self, context):
        """The mesh datablock currently open in Edit Mode, from live context.

        context.edit_object is the authority here. A Mesh reference captured in
        invoke() is not: resolving the BMesh through a stale datablock hands
        back a throwaway BMesh rebuilt from the stored mesh, so every write
        lands in a copy that is discarded before the next event — the edit
        appears to work and nothing ever changes.
        """
        obj = getattr(context, "edit_object", None)
        if obj is None:
            obj = getattr(context, "active_object", None)
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return None
        return obj.data

    @staticmethod
    def _bm_alive(bm):
        try:
            return bool(bm.is_valid)
        except Exception:
            return False

    def _get_bm(self, context):
        """The session BMesh, re-acquired only when Blender invalidates it.

        Holding one BMesh for the whole modal is what working UV modals do, and
        it means a write and the next read are guaranteed to hit the same data.
        Any change of identity here is logged, because a BMesh silently swapped
        between events is exactly the kind of thing that makes edits evaporate.
        """
        me = self._edit_mesh(context)
        if me is None:
            return self._fetch_failed("no mesh is in Edit Mode")

        bm = self._bm
        if bm is None or not self._bm_alive(bm) or me is not self._mesh:
            try:
                bm = bmesh.from_edit_mesh(me)
            except Exception as exc:
                return self._fetch_failed(f"could not open the mesh ({exc})")
            self._bm = bm
            self._mesh = me
            self._loops = None

        if id(bm) != self._bm_id:
            self._bm_id = id(bm)
            self._loops = None
        return bm

    def _fetch_loops(self, context):
        """The UV loops being transformed, from the session BMesh.

        Collected with the same helper and iteration order as the apply
        operators, so index N here is index N in _uv_base.

        Returns None if the mesh cannot supply the loops, after saying so once —
        a silent None here is what made this bug so hard to see.
        """
        bm = self._get_bm(context)
        if bm is None:
            return None

        if self._loops is None:
            try:
                uv_layer = bm.loops.layers.uv.active
                if uv_layer is None:
                    return self._fetch_failed("mesh has no active UV layer")
                self._loops = get_selected_face_uv_loops(bm, uv_layer)
            except Exception as exc:
                return self._fetch_failed(f"could not read the mesh ({exc})")

        if self._uv_base is not None and len(self._loops) != len(self._uv_base):
            return self._fetch_failed(
                f"selection changed ({len(self._loops)} loops, expected "
                f"{len(self._uv_base)})")
        return self._loops

    def _fetch_failed(self, reason):
        """Report once why the UVs cannot be reached, then stay quiet."""
        if not self._warned:
            self._warned = True
            self.report({'WARNING'}, f"Adjust: {reason}")
        return None

    def _flush(self):
        """Push UV edits to the mesh and force the viewport to repaint.

        Full default update on purpose. Skipping the loop-triangle rebuild is
        tempting for a per-mouse-move path, but the viewport draws textures from
        the tessellated loop data — without it the UVs change in the mesh and
        the screen keeps showing the old ones.
        """
        try:
            bmesh.update_edit_mesh(self._mesh)
        except Exception as exc:
            self._fetch_failed(f"could not update the mesh ({exc})")
            return
        for area in self._redraw_areas():
            area.tag_redraw()

    @staticmethod
    def _redraw_areas():
        """Every 3D view and UV editor, so both show the edit as it happens."""
        areas = []
        try:
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                        areas.append(area)
        except Exception:
            pass
        return areas

    def _write_uvs(self, context, values):
        """Write an absolute set of UVs — used to revert a cancelled step."""
        loops = self._fetch_loops(context)
        if loops is None:
            return
        try:
            for luv, uv in zip(loops, values):
                luv.uv = Vector(uv)
        except (ReferenceError, AttributeError, TypeError):
            return
        self._flush()

    def _apply(self, context, event):
        """Recompute the UVs from _uv_base and push them live to the viewport."""
        loops = self._fetch_loops(context)
        if loops is None:
            return

        try:
            if self._mode == 'TRANSLATE':
                self._apply_translate(loops, event)
            elif self._mode == 'SCALE':
                self._apply_scale(loops, event)
            elif self._mode == 'ROTATE':
                self._apply_rotate(loops, event)
        except Exception as exc:
            # Never silent: a swallowed write here is exactly what made this
            # look like "the modal runs but nothing happens".
            import traceback
            traceback.print_exc()
            self._fetch_failed(f"could not write the UVs ({exc})")
            return

        after = tuple(loops[0].uv)
        self._applies += 1
        self._flush()
        self._verify_persisted(context, after)
        self._update_status(context)

    def _verify_persisted(self, context, expected):
        """Confirm once that an edit survives to the next read.

        A write that lands in a discarded BMesh looks perfect from inside the
        transform — the value reads back correctly right after assignment — and
        is simply gone by the next event. Checking it once turns that from an
        invisible failure into a message.
        """
        if self._verified or self._applies < 2:
            return
        self._verified = True
        # Drop the cached loop list first: comparing the values we just wrote
        # against the very objects we wrote them to is a tautology, and would
        # pass even in the failure case this check exists for.
        self._loops = None
        loops = self._fetch_loops(context)
        if loops is None:
            return
        got = tuple(loops[0].uv)
        if abs(got[0] - expected[0]) > 1e-6 or abs(got[1] - expected[1]) > 1e-6:
            self.report({'ERROR'}, "Adjust: UV edits are not sticking")

    def _mouse_delta(self, event):
        """Mouse travel in UV units — one region width equals 1.0 UV."""
        ref = max(self._region.width, 1)
        return ((event.mouse_x - self._start_mouse[0]) / ref,
                (event.mouse_y - self._start_mouse[1]) / ref)

    def _region_center(self):
        return (self._region.x + self._region.width * 0.5,
                self._region.y + self._region.height * 0.5)

    def _apply_translate(self, loops, event):
        value = self._numeric_value()
        if value is not None:
            # Unconstrained numeric goes to U, matching Blender's first field.
            dx, dy = (0.0, value) if self._axis == 'V' else (value, 0.0)
        else:
            dx, dy = self._mouse_delta(event)
            if self._precise:
                dx *= 0.1
                dy *= 0.1
            if self._axis == 'U':
                dy = 0.0
            elif self._axis == 'V':
                dx = 0.0
            if self._snap:
                # Snap where the tile LANDS, not how far it moved. Rounding the
                # delta leaves the tile off-grid by whatever offset it started
                # with, which does not read as snapping at all.
                pivot = self._pivot
                if self._axis != 'V':
                    dx = (round((pivot.x + dx) / self._snap_u) * self._snap_u
                          - pivot.x)
                if self._axis != 'U':
                    dy = (round((pivot.y + dy) / self._snap_v) * self._snap_v
                          - pivot.y)

        offset = Vector((dx, dy))
        for luv, base in zip(loops, self._uv_base):
            luv.uv = base + offset

    def _apply_scale(self, loops, event):
        value = self._numeric_value()
        if value is not None:
            factor = value
        else:
            cx, cy = self._region_center()
            start_d = math.hypot(self._start_mouse[0] - cx,
                                 self._start_mouse[1] - cy)
            now_d = math.hypot(event.mouse_x - cx, event.mouse_y - cy)
            # Softened ratio. A plain now/start ratio is dead on arrival when
            # the transform starts near the anchor (start_d ~ 0 pinned the
            # factor at 1.0 and scaling did nothing). Adding the same constant
            # to both keeps factor == 1.0 for zero movement at any starting
            # distance, and approaches the plain ratio further out.
            factor = (now_d + _DRAG_SOFTEN_PX) / (start_d + _DRAG_SOFTEN_PX)
            if self._precise:
                factor = 1.0 + (factor - 1.0) * 0.1
            if self._snap:
                factor = round(factor / self._snap_scale) * self._snap_scale

        sx = sy = factor
        if self._axis == 'U':
            sy = 1.0
        elif self._axis == 'V':
            sx = 1.0

        pivot = self._pivot
        for luv, base in zip(loops, self._uv_base):
            luv.uv = Vector((pivot.x + (base.x - pivot.x) * sx,
                             pivot.y + (base.y - pivot.y) * sy))

    def _apply_rotate(self, loops, event):
        value = self._numeric_value()
        if value is not None:
            angle = math.radians(value)
        else:
            cx, cy = self._region_center()
            start_dx = self._start_mouse[0] - cx
            start_dy = self._start_mouse[1] - cy
            now_dx = event.mouse_x - cx
            now_dy = event.mouse_y - cy
            if math.hypot(start_dx, start_dy) < 1.0 or \
                    math.hypot(now_dx, now_dy) < 1.0:
                # Sitting exactly on the anchor — the angle is meaningless.
                return
            angle = math.atan2(now_dy, now_dx) - math.atan2(start_dy, start_dx)
            # Take the short way round so crossing the -pi/pi seam does not
            # snap the tile through a half turn.
            angle = (angle + math.pi) % (2.0 * math.pi) - math.pi
            if self._precise:
                angle *= 0.1
            if self._snap:
                step = self._snap_angle
                angle = round(angle / step) * step

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        pivot = self._pivot
        aspect = self._aspect
        for luv, base in zip(loops, self._uv_base):
            # Rotate in image-aspect space so a circle stays a circle on a
            # non-square atlas, then convert back to UV space.
            x = (base.x - pivot.x) * aspect
            y = base.y - pivot.y
            luv.uv = Vector((pivot.x + (x * cos_a - y * sin_a) / aspect,
                             pivot.y + (x * sin_a + y * cos_a)))

    # -- feedback ----------------------------------------------------------

    def _update_status(self, context):
        area = getattr(context, "area", None)
        if self._mode == 'NONE':
            header = "Fine Adjust UVs"
            keys = ("G Move   S Scale   R Rotate   |   "
                    "Enter Confirm   Esc Cancel")
        else:
            label = {'TRANSLATE': "Move", 'SCALE': "Scale",
                     'ROTATE': "Rotate"}[self._mode]
            shown = self._numeric if self._numeric else "drag"
            axis = f" {_AXIS_LABELS[self._axis]}" if self._axis else ""
            flags = []
            if self._snap:
                flags.append("snap")
            if self._precise:
                flags.append("precise")
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            header = f"Fine Adjust — {label}{axis}: {shown}{suffix}"
            keys = ("X / Z Constrain axis   MMB Pick axis   "
                    "Type a number for an exact value   "
                    "Ctrl Snap   Shift Precision   |   "
                    "Enter / LMB Confirm   Esc / RMB Cancel")
        if area is not None:
            try:
                area.header_text_set(header)
            except Exception:
                pass
            area.tag_redraw()
        workspace = getattr(context, "workspace", None)
        if workspace is not None:
            try:
                workspace.status_text_set(keys)
            except Exception:
                pass


class TILEUV_OT_fine_adjust_abort(Operator):
    """Leave adjust mode, keeping the changes made so far

    Restores the viewport overlays and shading that were recorded on entry
    """
    bl_idname = "uv.tileuv_fine_adjust_abort"
    bl_label = "Exit Adjust Mode"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if TILEUV_OT_fine_adjust.is_running() \
                and not TILEUV_OT_fine_adjust._should_close:
            # Ask the modal to wind itself up. Resetting the class state behind
            # its back would leave it running and eating every event.
            TILEUV_OT_fine_adjust._should_close = True
        else:
            # Either nothing is running, or a previous request went unanswered —
            # proof the modal is not listening. Force the release so the mode can
            # never strand the user with their overlays switched off.
            TILEUV_OT_fine_adjust.force_reset()
        area = getattr(context, "area", None)
        if area is not None:
            try:
                area.header_text_set(None)
            except Exception:
                pass
        workspace = getattr(context, "workspace", None)
        if workspace is not None:
            try:
                workspace.status_text_set(None)
            except Exception:
                pass
        _tag_ui_redraw(context)
        return {'FINISHED'}


def maybe_start_fine_adjust(context, settings):
    """Enter fine adjust after a tile was applied, if the user enabled it."""
    if not settings.fine_adjust_enabled:
        return
    if not TILEUV_OT_fine_adjust.poll(context):
        return
    try:
        bpy.ops.uv.tileuv_fine_adjust('INVOKE_DEFAULT')
    except Exception:
        pass


# ============================================================================
# UI LISTS
# ============================================================================

class TILEUV_UL_custom_tiles(UIList):
    bl_idname = "TILEUV_UL_custom_tiles"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False)
        row.label(text=f"[{item.min_u:.2f},{item.min_v:.2f}]-[{item.max_u:.2f},{item.max_v:.2f}]")


# ============================================================================
# PANELS
# ============================================================================

def compute_preview_scale(context, grid):
    """template_icon scale, clamped to what the sidebar can actually show.

    The picker overlay clamps its square to the sidebar width. If the thumbnail
    underneath is not clamped the same way it draws wider than the overlay, and
    the clickable columns stop lining up with the picture.
    """
    prop_x = max(1e-6, grid.proportion_x)
    prop_y = max(1e-6, grid.proportion_y)
    scale = max(3.0, min(16.0, 12.0 * (prop_y / prop_x)))

    region = getattr(context, "region", None)
    try:
        ui_unit = (20.0 * (context.preferences.system.dpi / 72.0)
                   * context.preferences.view.ui_scale)
    except Exception:
        return scale
    if region is not None and region.width > 0 and ui_unit > 0:
        scale = min(scale, max(3.0, (region.width - 12) / ui_unit))
    return scale


def draw_atlas_texture_controls(layout, img):
    """Status line plus the reload/refresh buttons for an atlas image.

    Shared by Grid Settings and the Grid panel so the texture can be updated
    from wherever the user happens to be looking.
    """
    if img is None:
        return

    ok, message, icon = describe_atlas_image(img)

    col = layout.column(align=True)
    col.alert = not ok
    col.label(text=message, icon=icon)
    col.alert = False

    row = col.row(align=True)
    row.operator("uv.tileuv_reload_atlas", text="Reload", icon='FILE_REFRESH')
    row.operator("uv.tileuv_refresh_atlas_preview",
                 text="Refresh Preview", icon='SEQ_PREVIEW')

    if image_file_missing(img):
        col.operator("file.find_missing_files",
                     text="Find Missing Files", icon='VIEWZOOM')

class TILEUV_PT_main(Panel):
    bl_label = "Tile UV Projector"
    bl_idname = "TILEUV_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tileuv_settings

        row = layout.row(align=True)
        row.prop(settings, "use_advanced_grid", toggle=True)
        row.prop(settings, "use_per_object", toggle=True, icon='OBJECT_DATA')

        # The Grid panel that normally carries this button is hidden in
        # Advanced Grid mode, which used to leave a running picker with no
        # visible way out.
        if TILEUV_OT_pick_tile.is_running():
            layout.operator("uv.tileuv_close_picker",
                            text="Close Picker", icon='CANCEL', depress=True)


class TILEUV_PT_grid_settings(Panel):
    bl_label = "Grid Settings"
    bl_idname = "TILEUV_PT_grid_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"
    bl_parent_id = "TILEUV_PT_main"

    @classmethod
    def poll(cls, context):
        return not context.scene.tileuv_settings.use_advanced_grid

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tileuv_settings
        grid, _ = get_grid_settings(context)

        # Show which source is active. get_grid_settings falls back to the
        # scene settings when there is no active object, so this has to as well
        # — dereferencing it unguarded threw on every redraw with nothing
        # selected.
        if settings.use_per_object:
            obj = context.active_object
            if obj is not None:
                layout.label(text=f"Object: {obj.name}", icon='OBJECT_DATA')
            else:
                row = layout.row()
                row.enabled = False
                row.label(text="No active object — using global settings",
                          icon='INFO')

        row = layout.row(align=True)
        row.prop(grid, "grid_cols", text="X")
        row.prop(grid, "grid_rows", text="Y")
        layout.prop(grid, "padding")

        layout.separator()
        layout.label(text="Proportion (W:H):")
        row = layout.row(align=True)
        row.prop(grid, "proportion_x", text="W")
        row.prop(grid, "proportion_y", text="H")

        layout.separator()
        layout.label(text="Atlas Texture:")
        layout.template_ID(grid, "atlas_image", open="image.open")
        draw_atlas_texture_controls(layout, grid.atlas_image)


class TILEUV_PT_unwrap_settings(Panel):
    bl_label = "Unwrap Settings"
    bl_idname = "TILEUV_PT_unwrap_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"
    bl_parent_id = "TILEUV_PT_main"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tileuv_settings

        layout.prop(settings, "clear_seams")
        layout.prop(settings, "auto_seams")

        # Unwrap method and relax only relevant when unwrapping
        is_unwrapping = settings.projection_method != 'PROJECT_ONLY'
        col = layout.column()
        col.enabled = is_unwrapping
        col.prop(settings, "unwrap_method")
        col.separator()
        col.prop(settings, "do_relax")
        if settings.do_relax:
            col.prop(settings, "relax_iterations")


class TILEUV_PT_projection(Panel):
    bl_label = "Projection"
    bl_idname = "TILEUV_PT_projection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"
    bl_parent_id = "TILEUV_PT_main"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tileuv_settings
        layout.prop(settings, "projection_method", expand=True)


class TILEUV_PT_fine_adjust(Panel):
    bl_label = "Adjust after Project"
    bl_idname = "TILEUV_PT_fine_adjust"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"
    bl_parent_id = "TILEUV_PT_main"

    def draw_header(self, context):
        self.layout.prop(context.scene.tileuv_settings,
                         "fine_adjust_enabled", text="")

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tileuv_settings

        col = layout.column()
        col.active = settings.fine_adjust_enabled
        col.prop(settings, "fine_adjust_hide_overlays")
        col.prop(settings, "fine_adjust_flat_shading")

        layout.separator()

        # Also usable on its own, without re-projecting.
        row = layout.row()
        row.scale_y = 1.2
        if TILEUV_OT_fine_adjust.is_running():
            row.operator("uv.tileuv_fine_adjust_abort",
                         text="Exit Adjust Mode", icon='CHECKMARK')
        else:
            row.operator("uv.tileuv_fine_adjust",
                         text="Adjust Current UVs", icon='MOD_MESHDEFORM')


class TILEUV_PT_snap_increments(Panel):
    bl_label = "Snap Increments"
    bl_idname = "TILEUV_PT_snap_increments"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"
    bl_parent_id = "TILEUV_PT_fine_adjust"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tileuv_settings

        col = layout.column(align=True)
        col.prop(settings, "snap_move_divisions")
        col.label(text=f"= 1/{max(1, settings.snap_move_divisions)} of a tile")
        col.prop(settings, "snap_scale_step")
        col.prop(settings, "snap_rotate_degrees")


class TILEUV_PT_tile_scale(Panel):
    bl_label = "Tile Scale"
    bl_idname = "TILEUV_PT_tile_scale"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"
    bl_parent_id = "TILEUV_PT_main"

    def draw_header(self, context):
        self.layout.prop(context.scene.tileuv_settings,
                         "use_tile_scale", text="")

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tileuv_settings

        col = layout.column(align=True)
        col.active = settings.use_tile_scale
        row = col.row(align=True)
        row.prop(settings, "tile_scale", index=0, text="Scale X")
        row.prop(settings, "tile_scale", index=1, text="Y")
        row = col.row(align=True)
        row.prop(settings, "tile_scale_pivot", index=0, text="Pivot X")
        row.prop(settings, "tile_scale_pivot", index=1, text="Y")


class TILEUV_PT_grid_ui(Panel):
    bl_label = "Grid"
    bl_idname = "TILEUV_PT_grid_ui"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"
    bl_parent_id = "TILEUV_PT_main"

    @classmethod
    def poll(cls, context):
        return not context.scene.tileuv_settings.use_advanced_grid

    def draw(self, context):
        layout = self.layout
        grid, settings = get_grid_settings(context)
        cols = grid.grid_cols
        rows = grid.grid_rows

        # Atlas image preview — full width, using template_icon. This is the
        # same picture the tile picker overlay draws behind its grid. It is
        # hidden only when the file is provably missing, which is the one case
        # that renders as Blender's magenta placeholder.
        img = grid.atlas_image
        if img:
            image_ok, _, _ = describe_atlas_image(img)
            if image_ok:
                try:
                    preview = img.preview_ensure()
                    if preview and preview.icon_id > 0:
                        layout.template_icon(
                            icon_value=preview.icon_id,
                            scale=compute_preview_scale(context, grid))
                except Exception:
                    pass
            draw_atlas_texture_controls(layout, img)

        # Open / Close picker button
        pick_row = layout.row(align=True)
        pick_row.scale_y = 1.2
        if TILEUV_OT_pick_tile.is_running():
            pick_row.operator("uv.tileuv_close_picker",
                              text="Close Picker", icon='CANCEL',
                              depress=True)
        elif grid.atlas_image:
            pick_row.operator("uv.tileuv_pick_tile",
                              text="Pick Tile", icon='IMAGE_DATA')
        else:
            pick_row.operator("uv.tileuv_pick_tile",
                              text="Pick Tile", icon='MESH_GRID')

        # The picker is a mesh Edit Mode tool — say so instead of just greying
        # the button out, which reads as "the button is broken".
        obj = context.active_object
        if not (obj and obj.type == 'MESH' and obj.mode == 'EDIT'):
            hint = layout.row()
            hint.enabled = False
            hint.label(text="Enter Edit Mode to pick tiles", icon='INFO')

        layout.separator()

        # Button grid. Capped: a 64x64 grid would rebuild 4096 operator buttons
        # on every single panel redraw, which locks the UI up.
        if cols * rows > _MAX_GRID_BUTTONS:
            box = layout.box()
            box.label(text=f"{cols} x {rows} is too dense for buttons",
                      icon='INFO')
            box.label(text="Use Pick Tile instead")
            return

        prop_x = grid.proportion_x
        prop_y = grid.proportion_y
        scale_y = (prop_y * cols) / (prop_x * rows)
        scale_y = max(0.15, min(scale_y, 4.0))

        for row in reversed(range(rows)):
            grid_row = layout.row(align=True)
            grid_row.scale_y = scale_y
            for col in range(cols):
                op = grid_row.operator(
                    "uv.tileuv_apply_to_tile",
                    text=f"{col},{row}",
                )
                op.col_index = col
                op.row_index = row


class TILEUV_PT_advanced_grid(Panel):
    bl_label = "Custom Atlas"
    bl_idname = "TILEUV_PT_advanced_grid"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tile UV"
    bl_parent_id = "TILEUV_PT_main"

    @classmethod
    def poll(cls, context):
        return context.scene.tileuv_settings.use_advanced_grid

    def draw(self, context):
        layout = self.layout
        settings = context.scene.tileuv_settings

        # Padding
        layout.prop(settings, "padding")

        layout.separator()

        # Tile list
        row = layout.row()
        row.template_list(
            "TILEUV_UL_custom_tiles", "",
            settings, "custom_tiles",
            settings, "active_custom_tile",
            rows=4,
        )

        col = row.column(align=True)
        col.operator("uv.tileuv_add_custom_tile", icon='ADD', text="")
        col.operator("uv.tileuv_remove_custom_tile", icon='REMOVE', text="")

        # Active tile properties
        if settings.custom_tiles and settings.active_custom_tile < len(settings.custom_tiles):
            tile = settings.custom_tiles[settings.active_custom_tile]
            box = layout.box()
            box.label(text="Tile Bounds:")
            row = box.row(align=True)
            row.prop(tile, "min_u", text="Min U")
            row.prop(tile, "min_v", text="Min V")
            row = box.row(align=True)
            row.prop(tile, "max_u", text="Max U")
            row.prop(tile, "max_v", text="Max V")

            # Apply button
            op = box.operator(
                "uv.tileuv_apply_to_custom_tile",
                text=f"Apply to '{tile.name}'",
                icon='UV',
            )
            op.tile_index = settings.active_custom_tile

        layout.separator()

        # Split controls
        row = layout.row(align=True)
        row.prop(settings, "split_direction", expand=True)
        layout.operator("uv.tileuv_split_custom_tile", icon='MOD_EDGESPLIT')

        layout.separator()
        layout.operator("uv.tileuv_generate_grid_tiles", icon='MESH_GRID')


# ============================================================================
# AUTO-REFRESH HANDLER
# ============================================================================

def collect_atlas_image_names(scene):
    """Names of every Image configured as an atlas, scene-wide or per-object."""
    names = set()
    settings = getattr(scene, "tileuv_settings", None)
    img = getattr(settings, "atlas_image", None) if settings else None
    if img is not None:
        names.add(img.name)
    try:
        for obj in bpy.data.objects:
            obj_settings = getattr(obj, "tileuv_obj_settings", None)
            img = getattr(obj_settings, "atlas_image", None) if obj_settings else None
            if img is not None:
                names.add(img.name)
    except Exception:
        pass
    return names


@persistent
def _tileuv_atlas_preview_handler(scene, depsgraph):
    """Invalidate atlas image previews when the source image data changes.

    Blender caches Image previews (the thumbnail used by template_icon), so a
    reload from disk or re-generation does not refresh the panel preview by
    itself. This handler clears the cached preview for any Image touched by the
    depsgraph, forcing it to regenerate from the current pixel data on next draw,
    and invalidates the picker overlay's cached GPU texture along with it so both
    keep showing the same picture.
    """
    atlas_names = None
    touched = False
    for update in depsgraph.updates:
        if not isinstance(update.id, bpy.types.Image):
            continue
        # Resolved lazily, and only when an image really did change: texture
        # painting and image-sequence playback would otherwise clear the atlas
        # caches on every frame.
        if atlas_names is None:
            atlas_names = collect_atlas_image_names(scene)
        img = update.id
        if img.name not in atlas_names:
            continue
        touched = True
        try:
            if img.preview is not None:
                img.preview.reload()
        except Exception:
            pass
    if touched:
        bump_atlas_refresh_token()


@persistent
def _tileuv_load_post_handler(dummy):
    """Clear modal/texture state that cannot survive a file load."""
    TILEUV_OT_pick_tile.force_reset()
    # The recorded spaces belong to the file being replaced — restoring onto
    # them would write to freed memory, and would stamp the old file's overlay
    # settings onto the new file's viewport even if it worked.
    TILEUV_OT_fine_adjust.force_reset(restore_view=False)
    bump_atlas_refresh_token()


class TILEUV_OT_refresh_atlas_preview(Operator):
    """Rebuild the atlas preview thumbnail from the image data currently in memory"""
    bl_idname = "uv.tileuv_refresh_atlas_preview"
    bl_label = "Refresh Atlas Preview"
    bl_options = {'REGISTER'}

    def execute(self, context):
        grid, _ = get_grid_settings(context)
        ok, msg = refresh_atlas_image(grid.atlas_image, reload_from_disk=False)
        _tag_ui_redraw(context)
        if not ok:
            self.report({'WARNING'}, msg)
            return {'CANCELLED'}
        return {'FINISHED'}


class TILEUV_OT_reload_atlas(Operator):
    """Re-read the atlas texture from disk and rebuild its preview

    Use after editing or re-exporting the texture outside Blender, or when the
    preview and the tile picker have gone out of sync
    """
    bl_idname = "uv.tileuv_reload_atlas"
    bl_label = "Reload Atlas Texture"
    bl_options = {'REGISTER'}

    all_images: BoolProperty(
        name="All Atlas Images",
        default=False,
        description="Reload every image used as an atlas in this file, "
                    "not just the active one",
    )

    def execute(self, context):
        grid, settings = get_grid_settings(context)

        images = []
        if self.all_images:
            seen = set()
            for src in (settings, *(o.tileuv_obj_settings for o in bpy.data.objects)):
                img = getattr(src, "atlas_image", None)
                if img is not None and img.name not in seen:
                    seen.add(img.name)
                    images.append(img)
        elif grid.atlas_image is not None:
            images.append(grid.atlas_image)

        if not images:
            self.report({'WARNING'}, "No atlas image set")
            return {'CANCELLED'}

        failures = []
        for img in images:
            ok, msg = refresh_atlas_image(img, reload_from_disk=True)
            if not ok:
                failures.append(f"{img.name}: {msg}")

        _tag_ui_redraw(context)

        if failures:
            self.report({'WARNING'}, "; ".join(failures))
            return {'CANCELLED'}
        self.report({'INFO'}, f"Reloaded {len(images)} atlas texture(s)")
        return {'FINISHED'}


def _tag_ui_redraw(context):
    """Redraw every area so panel preview and picker overlay update together."""
    screen = getattr(context, "screen", None)
    if screen is not None:
        for area in screen.areas:
            area.tag_redraw()
        return
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    TILEUV_CustomTile,
    TILEUV_ObjectSettings,
    TILEUV_Settings,
    TILEUV_OT_apply_to_tile,
    TILEUV_OT_apply_to_custom_tile,
    TILEUV_OT_add_custom_tile,
    TILEUV_OT_remove_custom_tile,
    TILEUV_OT_split_custom_tile,
    TILEUV_OT_generate_grid_tiles,
    TILEUV_OT_pick_tile,
    TILEUV_OT_close_picker,
    TILEUV_OT_fine_adjust,
    TILEUV_OT_fine_adjust_abort,
    TILEUV_OT_refresh_atlas_preview,
    TILEUV_OT_reload_atlas,
    TILEUV_UL_custom_tiles,
    TILEUV_PT_main,
    TILEUV_PT_grid_settings,
    TILEUV_PT_unwrap_settings,
    TILEUV_PT_projection,
    TILEUV_PT_tile_scale,
    TILEUV_PT_fine_adjust,
    TILEUV_PT_snap_increments,
    TILEUV_PT_grid_ui,
    TILEUV_PT_advanced_grid,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.tileuv_settings = PointerProperty(type=TILEUV_Settings)
    bpy.types.Object.tileuv_obj_settings = PointerProperty(type=TILEUV_ObjectSettings)
    if _tileuv_atlas_preview_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_tileuv_atlas_preview_handler)
    if _tileuv_load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_tileuv_load_post_handler)


def unregister():
    TILEUV_OT_pick_tile.force_reset()
    TILEUV_OT_fine_adjust.force_reset()
    bump_atlas_refresh_token()
    if _tileuv_load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_tileuv_load_post_handler)
    if _tileuv_atlas_preview_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_tileuv_atlas_preview_handler)
    del bpy.types.Object.tileuv_obj_settings
    del bpy.types.Scene.tileuv_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
