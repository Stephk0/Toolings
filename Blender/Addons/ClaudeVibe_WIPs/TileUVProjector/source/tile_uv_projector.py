bl_info = {
    "name": "Tile UV Projector",
    "author": "Stephan Viranyi",
    "version": (1, 2, 1),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Tile UV",
    "description": "Tile-based UV projection and placement on texture atlas grids",
    "category": "UV",
}

import bpy
import bmesh
import gpu
import blf
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
    """Normalize UVs to 0-1, then scale and translate into target rect."""
    extent = uv_max - uv_min
    sx = extent.x
    sy = extent.y

    # Guard against zero-area
    if sx < 1e-8:
        sx = 1.0
    if sy < 1e-8:
        sy = 1.0

    target_size = target_max - target_min

    for luv in uv_loops:
        u, v = luv.uv
        # Normalize to 0-1
        nu = (u - uv_min.x) / sx
        nv = (v - uv_min.y) / sy
        # Scale + translate into target tile
        luv.uv = Vector((
            nu * target_size.x + target_min.x,
            nv * target_size.y + target_min.y,
        ))


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
    name: StringProperty(name="Name", default="Tile")
    min_u: FloatProperty(name="Min U", default=0.0, min=0.0, max=1.0)
    min_v: FloatProperty(name="Min V", default=0.0, min=0.0, max=1.0)
    max_u: FloatProperty(name="Max U", default=0.25, min=0.0, max=1.0)
    max_v: FloatProperty(name="Max V", default=0.25, min=0.0, max=1.0)



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

    # Advanced grid
    use_advanced_grid: BoolProperty(
        name="Advanced Grid", default=False,
        description="Use custom atlas tiles instead of uniform grid",
    )
    custom_tiles: CollectionProperty(type=TILEUV_CustomTile)
    active_custom_tile: IntProperty(name="Active Tile", default=0)

    # Split direction for advanced grid
    split_direction: EnumProperty(
        name="Split",
        items=[
            ('HORIZONTAL', "Horizontal", "Split tile horizontally"),
            ('VERTICAL', "Vertical", "Split tile vertically"),
        ],
        default='HORIZONTAL',
    )


# ============================================================================
# OPERATORS
# ============================================================================

class TILEUV_OT_apply_to_tile(Operator):
    """Project and place selected face UVs into a grid tile"""
    bl_idname = "uv.tileuv_apply_to_tile"
    bl_label = "Apply to Tile"
    bl_options = {'REGISTER', 'UNDO'}

    col_index: IntProperty()
    row_index: IntProperty()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT')

    def execute(self, context):
        grid, settings = get_grid_settings(context)
        obj = context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        # Check selection
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        # Check transforms
        scale = obj.scale
        if abs(scale.x - 1.0) > 0.001 or abs(scale.y - 1.0) > 0.001 or abs(scale.z - 1.0) > 0.001:
            self.report({'WARNING'}, "Object has non-uniform scale. Consider applying transforms (Ctrl+A).")

        # Ensure UV map exists
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        uv_layer = bm.loops.layers.uv.verify()

        # Compute tile bounds
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

        # Clear seams
        if settings.clear_seams:
            clear_seams_on_selected(bm)

        # Auto seams
        if settings.auto_seams:
            mark_boundary_seams(bm)

        if settings.clear_seams or settings.auto_seams:
            bmesh.update_edit_mesh(me)

        # Projection (project from view)
        if settings.projection_method in {'PROJECT_AND_UNWRAP', 'PROJECT_ONLY'}:
            bpy.ops.uv.project_from_view(
                camera_bounds=False,
                correct_aspect=True,
                scale_to_bounds=False,
            )

        # Unwrap
        if settings.projection_method in {'PROJECT_AND_UNWRAP', 'UNWRAP_ONLY'}:
            bpy.ops.uv.unwrap(method=settings.unwrap_method, margin=0.0)

        # Relax
        if settings.do_relax and settings.projection_method != 'PROJECT_ONLY':
            for _ in range(settings.relax_iterations):
                bpy.ops.uv.minimize_stretch(iterations=1)

        # Re-acquire bmesh after operator calls
        bm = bmesh.from_edit_mesh(me)
        uv_layer = bm.loops.layers.uv.verify()

        # Gather UVs of selected faces
        uv_loops = get_selected_face_uv_loops(bm, uv_layer)
        if not uv_loops:
            self.report({'WARNING'}, "No UV data found")
            return {'CANCELLED'}

        # Compute bounds
        bounds = compute_uv_bounds(uv_loops)
        if bounds is None:
            self.report({'WARNING'}, "Could not compute UV bounds")
            return {'CANCELLED'}

        uv_min, uv_max = bounds
        extent = uv_max - uv_min
        if extent.x < 1e-8 and extent.y < 1e-8:
            self.report({'WARNING'}, "Zero-area UV selection, skipping normalization")
            return {'CANCELLED'}

        # Normalize and place
        normalize_and_place_uvs(uv_loops, uv_min, uv_max, usable_min, usable_max)

        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, f"UVs placed in tile ({self.col_index}, {self.row_index})")
        return {'FINISHED'}


class TILEUV_OT_apply_to_custom_tile(Operator):
    """Project and place selected face UVs into a custom atlas tile"""
    bl_idname = "uv.tileuv_apply_to_custom_tile"
    bl_label = "Apply to Custom Tile"
    bl_options = {'REGISTER', 'UNDO'}

    tile_index: IntProperty()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT')

    def execute(self, context):
        settings = context.scene.tileuv_settings

        if self.tile_index < 0 or self.tile_index >= len(settings.custom_tiles):
            self.report({'ERROR'}, "Invalid tile index")
            return {'CANCELLED'}

        tile = settings.custom_tiles[self.tile_index]
        obj = context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        # Check transforms
        scale = obj.scale
        if abs(scale.x - 1.0) > 0.001 or abs(scale.y - 1.0) > 0.001 or abs(scale.z - 1.0) > 0.001:
            self.report({'WARNING'}, "Object has non-uniform scale. Consider applying transforms (Ctrl+A).")

        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        uv_layer = bm.loops.layers.uv.verify()

        pad = settings.padding
        usable_min = Vector((tile.min_u + pad, tile.min_v + pad))
        usable_max = Vector((tile.max_u - pad, tile.max_v - pad))

        if usable_min.x >= usable_max.x or usable_min.y >= usable_max.y:
            self.report({'ERROR'}, "Padding too large for tile size")
            return {'CANCELLED'}

        # Clear seams
        if settings.clear_seams:
            clear_seams_on_selected(bm)

        if settings.auto_seams:
            mark_boundary_seams(bm)

        if settings.clear_seams or settings.auto_seams:
            bmesh.update_edit_mesh(me)

        # Projection (project from view)
        if settings.projection_method in {'PROJECT_AND_UNWRAP', 'PROJECT_ONLY'}:
            bpy.ops.uv.project_from_view(
                camera_bounds=False,
                correct_aspect=True,
                scale_to_bounds=False,
            )

        # Unwrap
        if settings.projection_method in {'PROJECT_AND_UNWRAP', 'UNWRAP_ONLY'}:
            bpy.ops.uv.unwrap(method=settings.unwrap_method, margin=0.0)

        # Relax
        if settings.do_relax and settings.projection_method != 'PROJECT_ONLY':
            for _ in range(settings.relax_iterations):
                bpy.ops.uv.minimize_stretch(iterations=1)

        bm = bmesh.from_edit_mesh(me)
        uv_layer = bm.loops.layers.uv.verify()

        uv_loops = get_selected_face_uv_loops(bm, uv_layer)
        if not uv_loops:
            self.report({'WARNING'}, "No UV data found")
            return {'CANCELLED'}

        bounds = compute_uv_bounds(uv_loops)
        if bounds is None:
            self.report({'WARNING'}, "Could not compute UV bounds")
            return {'CANCELLED'}

        uv_min, uv_max = bounds
        extent = uv_max - uv_min
        if extent.x < 1e-8 and extent.y < 1e-8:
            self.report({'WARNING'}, "Zero-area UV selection")
            return {'CANCELLED'}

        normalize_and_place_uvs(uv_loops, uv_min, uv_max, usable_min, usable_max)
        bmesh.update_edit_mesh(me)

        self.report({'INFO'}, f"UVs placed in custom tile '{tile.name}'")
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
        settings.active_custom_tile = min(idx, len(settings.custom_tiles) - 1)
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
            src.name = src.name + " (bottom)"
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
            src.name = src.name + " (left)"
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
        settings = context.scene.tileuv_settings
        settings.custom_tiles.clear()

        cols = settings.grid_cols
        rows = settings.grid_rows

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

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and obj.mode == 'EDIT'
                and not cls._is_active)

    def invoke(self, context, event):
        cls = self.__class__
        grid, settings = get_grid_settings(context)

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
        cls._is_active = True

        cls._handle = bpy.types.SpaceView3D.draw_handler_add(
            cls._draw_callback,
            (cls, context),
            'UI', 'POST_PIXEL',
        )

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        cls = self.__class__
        context.area.tag_redraw()
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

        if event.type == 'MOUSEMOVE':
            cls._hover_col, cls._hover_row = self._tile_at_scrolled(
                ui_mx, ui_my, adj_oy, grid,
            )
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            col, row = self._tile_at_scrolled(ui_mx, ui_my, adj_oy, grid)
            if col >= 0 and row >= 0:
                cls._last_click_col = col
                cls._last_click_row = row
                # Apply UV to tile and close picker
                bpy.ops.uv.tileuv_apply_to_tile(col_index=col, row_index=row)
                self._cleanup(context)
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

    def _cleanup(self, context):
        cls = self.__class__
        if cls._handle:
            bpy.types.SpaceView3D.draw_handler_remove(cls._handle, 'UI')
            cls._handle = None
        cls._is_active = False
        cls._should_close = False
        context.area.tag_redraw()

    @staticmethod
    def _draw_callback(cls, context):
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
        img = grid.atlas_image
        drew_image = False
        if img:
            try:
                texture = gpu.texture.from_image(img)
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
        font_id = 0
        blf.size(font_id, 10)
        blf.color(font_id, 1.0, 1.0, 1.0, 0.45)
        for r in range(rows):
            for c in range(cols):
                blf.position(font_id, ox + c * tw + 3, oy + r * th + 3, 0)
                blf.draw(font_id, f"{c},{r}")

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
        TILEUV_OT_pick_tile._should_close = True
        return {'FINISHED'}


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

        # Show which source is active
        if settings.use_per_object:
            layout.label(text=f"Object: {context.active_object.name}", icon='OBJECT_DATA')

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

        # Atlas image preview — full width, using template_icon
        if grid.atlas_image:
            try:
                preview = grid.atlas_image.preview_ensure()
                if preview and preview.icon_id > 0:
                    prop_x = grid.proportion_x
                    prop_y = grid.proportion_y
                    icon_scale = max(3.0, min(16.0, 12.0 * (prop_y / prop_x)))
                    layout.template_icon(icon_value=preview.icon_id, scale=icon_scale)
                    refresh_row = layout.row()
                    refresh_row.alignment = 'CENTER'
                    refresh_row.operator(
                        "uv.tileuv_refresh_atlas_preview",
                        text="Refresh Preview",
                        icon='FILE_REFRESH',
                    )
            except Exception:
                pass

        # Open / Close picker button
        pick_row = layout.row(align=True)
        pick_row.scale_y = 1.2
        if TILEUV_OT_pick_tile._is_active:
            pick_row.operator("uv.tileuv_close_picker",
                              text="Close Picker", icon='CANCEL',
                              depress=True)
        elif grid.atlas_image:
            pick_row.operator("uv.tileuv_pick_tile",
                              text="Pick Tile", icon='IMAGE_DATA')
        else:
            pick_row.operator("uv.tileuv_pick_tile",
                              text="Pick Tile", icon='MESH_GRID')

        layout.separator()

        # Button grid (always visible)
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

@persistent
def _tileuv_atlas_preview_handler(scene, depsgraph):
    """Invalidate atlas image previews when the source image data changes.

    Blender caches Image previews (the thumbnail used by template_icon), so a
    reload from disk or re-generation does not refresh the panel preview by
    itself. This handler clears the cached preview for any Image touched by the
    depsgraph, forcing it to regenerate from the current pixel data on next draw.
    """
    for update in depsgraph.updates:
        if not isinstance(update.id, bpy.types.Image):
            continue
        img = update.id
        try:
            if img.preview is not None:
                img.preview.reload()
        except Exception:
            pass


class TILEUV_OT_refresh_atlas_preview(Operator):
    """Refresh the atlas texture preview to reflect changes in the source image"""
    bl_idname = "uv.tileuv_refresh_atlas_preview"
    bl_label = "Refresh Atlas Preview"
    bl_options = {'REGISTER'}

    def execute(self, context):
        grid, _ = get_grid_settings(context)
        img = grid.atlas_image
        if img is None:
            self.report({'WARNING'}, "No atlas image set")
            return {'CANCELLED'}
        try:
            img.preview_ensure()
            if img.preview is not None:
                img.preview.reload()
        except Exception as e:
            self.report({'WARNING'}, f"Could not refresh preview: {e}")
            return {'CANCELLED'}
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


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
    TILEUV_OT_refresh_atlas_preview,
    TILEUV_UL_custom_tiles,
    TILEUV_PT_main,
    TILEUV_PT_grid_settings,
    TILEUV_PT_unwrap_settings,
    TILEUV_PT_projection,
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


def unregister():
    if _tileuv_atlas_preview_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_tileuv_atlas_preview_handler)
    del bpy.types.Object.tileuv_obj_settings
    del bpy.types.Scene.tileuv_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
