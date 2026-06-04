bl_info = {
    "name": "Edit Mode Overlay",
    "author": "Assistant",
    "version": (1, 1, 0),
    "blender": (2, 80, 0),
    "location": "3D Viewport > Sidebar > View Tab",
    "description": "Shows a customizable overlay when in edit mode",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader


class EditModeOverlay:
    def __init__(self):
        self.draw_handler = None
        self.shader = None
        self.batch = None
        
    def setup_shader(self):
        """Setup shader for drawing the rectangle"""
        if gpu.platform.backend_type_get() == 'OPENGL':
            self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        else:
            # For newer Blender versions with different backends
            self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        
    def create_rectangle_batch(self, x, y, width, height):
        """Create batch for rectangle drawing"""
        vertices = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height)
        ]
        
        indices = [(0, 1, 2), (0, 2, 3)]
        
        return batch_for_shader(
            self.shader, 'TRIS',
            {"pos": vertices},
            indices=indices
        )
    
    def draw_callback(self):
        """Draw callback function"""
        context = bpy.context
        
        # Check if we're in any edit mode
        edit_modes = {
            'EDIT_MESH', 'EDIT_CURVE', 'EDIT_ARMATURE', 
            'EDIT_METABALL', 'EDIT_LATTICE', 'EDIT_SURFACE',
            'EDIT_TEXT', 'EDIT_GPENCIL'
        }
        
        if context.mode not in edit_modes:
            return
            
        # Get viewport dimensions
        area = context.area
        if not area or area.type != 'VIEW_3D':
            return
            
        region = context.region
        if not region:
            return
            
        # Get addon preferences
        addon_prefs = context.preferences.addons[__name__].preferences
        if not addon_prefs.show_overlay:
            return
            
        viewport_width = region.width
        viewport_height = region.height
        
        # Get customizable values from preferences
        rect_width = addon_prefs.overlay_width
        rect_height = addon_prefs.overlay_height
        distance_from_top = addon_prefs.distance_from_top
        
        # Calculate position based on alignment
        if addon_prefs.horizontal_alignment == 'LEFT':
            rect_x = addon_prefs.horizontal_offset
        elif addon_prefs.horizontal_alignment == 'RIGHT':
            rect_x = viewport_width - rect_width - addon_prefs.horizontal_offset
        else:  # CENTER
            rect_x = (viewport_width - rect_width) // 2 + addon_prefs.horizontal_offset
            
        rect_y = viewport_height - distance_from_top - rect_height
        
        # Setup shader if not done
        if not self.shader:
            self.setup_shader()
            
        # Create rectangle batch
        self.batch = self.create_rectangle_batch(rect_x, rect_y, rect_width, rect_height)
        
        # Enable blending for transparency
        gpu.state.blend_set('ALPHA')
        
        # Draw rectangle with custom color
        self.shader.bind()
        self.shader.uniform_float("color", (
            addon_prefs.overlay_color[0],
            addon_prefs.overlay_color[1],
            addon_prefs.overlay_color[2],
            addon_prefs.overlay_alpha
        ))
        self.batch.draw(self.shader)
        
        # Draw text
        font_id = 0
        text = addon_prefs.overlay_text
        
        # Calculate text size relative to rectangle height
        # Use a factor that ensures text fits nicely within the rectangle
        text_size = int(rect_height * addon_prefs.text_size_factor)
        text_size = max(text_size, 10)  # Minimum text size
        
        blf.size(font_id, text_size)
        text_width, text_height = blf.dimensions(font_id, text)
        
        # Center text on rectangle
        text_x = rect_x + (rect_width - text_width) // 2
        text_y = rect_y + (rect_height - text_height) // 2
        
        # Set text color
        blf.color(font_id, 
                 addon_prefs.text_color[0],
                 addon_prefs.text_color[1],
                 addon_prefs.text_color[2],
                 1.0)
        blf.position(font_id, text_x, text_y, 0)
        blf.draw(font_id, text)
        
        # Restore GPU state
        gpu.state.blend_set('NONE')


class EDITMODE_OT_toggle_overlay(bpy.types.Operator):
    """Toggle Edit Mode Overlay"""
    bl_idname = "editmode.toggle_overlay"
    bl_label = "Toggle Edit Mode Overlay"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        addon_prefs = context.preferences.addons[__name__].preferences
        addon_prefs.show_overlay = not addon_prefs.show_overlay
        
        if addon_prefs.show_overlay:
            register_draw_handler()
            self.report({'INFO'}, "Edit Mode Overlay enabled")
        else:
            unregister_draw_handler()
            self.report({'INFO'}, "Edit Mode Overlay disabled")
            
        # Force viewport redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
                
        return {'FINISHED'}


class EDITMODE_PT_overlay_panel(bpy.types.Panel):
    """Creates a Panel in the 3D viewport sidebar"""
    bl_label = "Edit Mode Overlay"
    bl_idname = "EDITMODE_PT_overlay_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "View"
    
    def draw(self, context):
        layout = self.layout
        addon_prefs = context.preferences.addons[__name__].preferences
        
        # Toggle button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("editmode.toggle_overlay", 
                    text="Disable Overlay" if addon_prefs.show_overlay else "Enable Overlay",
                    icon='HIDE_OFF' if addon_prefs.show_overlay else 'HIDE_ON')
        
        layout.separator()
        
        # Quick access to preferences
        col = layout.column(align=True)
        col.label(text="Quick Settings:")
        col.prop(addon_prefs, "overlay_text")
        col.prop(addon_prefs, "overlay_width")
        col.prop(addon_prefs, "overlay_height")
        
        layout.separator()
        
        # Button to open full preferences
        layout.operator("preferences.addon_show", 
                       text="More Settings",
                       icon='PREFERENCES').module = __name__


class EditModeOverlayPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    show_overlay: bpy.props.BoolProperty(
        name="Show Overlay",
        description="Show edit mode overlay",
        default=True,
        update=lambda self, context: toggle_overlay_update(self, context)
    )
    
    overlay_text: bpy.props.StringProperty(
        name="Overlay Text",
        description="Text to display in the overlay",
        default=">>> IN EDIT MODE <<<",
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    overlay_width: bpy.props.IntProperty(
        name="Width",
        description="Width of the overlay rectangle",
        default=512,
        min=100,
        max=2000,
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    overlay_height: bpy.props.IntProperty(
        name="Height",
        description="Height of the overlay rectangle",
        default=64,
        min=30,
        max=300,
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    distance_from_top: bpy.props.IntProperty(
        name="Distance from Top",
        description="Distance from the top of the viewport",
        default=64,
        min=0,
        max=500,
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    horizontal_alignment: bpy.props.EnumProperty(
        name="Horizontal Alignment",
        description="Horizontal alignment of the overlay",
        items=[
            ('LEFT', "Left", "Align to left"),
            ('CENTER', "Center", "Center horizontally"),
            ('RIGHT', "Right", "Align to right")
        ],
        default='CENTER',
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    horizontal_offset: bpy.props.IntProperty(
        name="Horizontal Offset",
        description="Additional horizontal offset",
        default=0,
        min=-500,
        max=500,
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    overlay_color: bpy.props.FloatVectorProperty(
        name="Overlay Color",
        description="Color of the overlay rectangle",
        default=(1.0, 0.5, 0.0),
        min=0.0,
        max=1.0,
        subtype='COLOR',
        size=3,
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    overlay_alpha: bpy.props.FloatProperty(
        name="Overlay Opacity",
        description="Opacity of the overlay rectangle",
        default=0.8,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    text_color: bpy.props.FloatVectorProperty(
        name="Text Color",
        description="Color of the overlay text",
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        subtype='COLOR',
        size=3,
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    text_size_factor: bpy.props.FloatProperty(
        name="Text Size Factor",
        description="Text size relative to rectangle height (0.1 = 10%, 0.5 = 50%)",
        default=0.4,
        min=0.1,
        max=0.9,
        subtype='FACTOR',
        update=lambda self, context: force_viewport_redraw(context)
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Main toggle
        row = layout.row()
        row.scale_y = 1.5
        row.prop(self, "show_overlay", toggle=True)
        
        # Settings grouped in boxes
        if self.show_overlay:
            # Text settings
            box = layout.box()
            box.label(text="Text Settings", icon='FONT_DATA')
            col = box.column(align=True)
            col.prop(self, "overlay_text")
            col.prop(self, "text_color")
            col.prop(self, "text_size_factor", slider=True)
            
            # Rectangle settings
            box = layout.box()
            box.label(text="Rectangle Settings", icon='MESH_PLANE')
            col = box.column(align=True)
            
            row = col.row(align=True)
            row.prop(self, "overlay_width")
            row.prop(self, "overlay_height")
            
            col.separator()
            col.prop(self, "overlay_color")
            col.prop(self, "overlay_alpha", slider=True)
            
            # Position settings
            box = layout.box()
            box.label(text="Position Settings", icon='ORIENTATION_VIEW')
            col = box.column(align=True)
            col.prop(self, "distance_from_top")
            col.prop(self, "horizontal_alignment")
            if self.horizontal_alignment != 'CENTER':
                col.prop(self, "horizontal_offset")
            
        # Info
        layout.separator()
        col = layout.column()
        col.scale_y = 0.7
        col.label(text="Tip: Access quick settings from 3D Viewport > Sidebar > View Tab", icon='INFO')


# Global instance
overlay_instance = EditModeOverlay()


def toggle_overlay_update(self, context):
    """Update function for show_overlay property"""
    if self.show_overlay:
        register_draw_handler()
    else:
        unregister_draw_handler()
    force_viewport_redraw(context)


def force_viewport_redraw(context):
    """Force all 3D viewports to redraw"""
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def register_draw_handler():
    """Register the draw handler"""
    if overlay_instance.draw_handler is None:
        overlay_instance.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            overlay_instance.draw_callback,
            (),
            'WINDOW',
            'POST_PIXEL'
        )


def unregister_draw_handler():
    """Unregister the draw handler"""
    if overlay_instance.draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(overlay_instance.draw_handler, 'WINDOW')
        overlay_instance.draw_handler = None


classes = (
    EDITMODE_OT_toggle_overlay,
    EDITMODE_PT_overlay_panel,
    EditModeOverlayPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Auto-enable overlay on registration if preference is set
    addon_prefs = bpy.context.preferences.addons[__name__].preferences
    if addon_prefs.show_overlay:
        register_draw_handler()


def unregister():
    unregister_draw_handler()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()