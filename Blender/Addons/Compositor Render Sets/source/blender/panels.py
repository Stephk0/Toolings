"""UI lists and panels for Compositor Render Sets."""

from bpy.types import Panel, UIList

from ..core import logbuf
from .visibility import get_active_render_set

LOG_LINES_SHOWN = 10


# ============================================================================
# UI Lists
# ============================================================================

class COMPRS_UL_CollectionList(UIList):
    """UIList for displaying collections in a render set"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        if item.collection:
            row.label(text=item.collection.name, icon='OUTLINER_COLLECTION')
            row.prop(item, "render_visibility", text="",
                     icon='RESTRICT_RENDER_OFF' if item.render_visibility else 'RESTRICT_RENDER_ON',
                     emboss=False)
        else:
            row.label(text="<Missing Collection>", icon='ERROR')
        op = row.operator("comprs.remove_collection", text="", icon='X', emboss=False)
        op.index = index


class COMPRS_UL_ConstantCollectionList(UIList):
    """UIList for displaying constant render set collections"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        render_set = get_active_render_set(context)
        is_override = bool(render_set and render_set.override_constant_collections
                           and data == render_set)

        row = layout.row(align=True)
        if item.collection:
            row.label(text=item.collection.name, icon='LIGHT')
            row.prop(item, "render_visibility", text="",
                     icon='RESTRICT_RENDER_OFF' if item.render_visibility else 'RESTRICT_RENDER_ON',
                     emboss=False)
        else:
            row.label(text="<Missing Collection>", icon='ERROR')
        op = row.operator("comprs.remove_constant_collection", text="", icon='X', emboss=False)
        op.index = index
        op.use_override = is_override


# ============================================================================
# Main Panel
# ============================================================================

class COMPRS_PT_MainPanel(Panel):
    """Main panel for Compositor Render Sets"""
    bl_label = "Compositor Render Sets"
    bl_idname = "COMPRS_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render Sets'

    def draw(self, context):
        layout = self.layout
        props = context.scene.compositor_render_sets

        # ====================================================================
        # Render Set Setup Section
        # ====================================================================

        box = layout.box()
        row = box.row()
        row.prop(props.settings, "expand_render_set_setup",
                 text="Render Set Setup",
                 icon='TRIA_DOWN' if props.settings.expand_render_set_setup else 'TRIA_RIGHT',
                 icon_only=False,
                 emboss=False)

        if props.settings.expand_render_set_setup:
            # Tabs for render sets with row wrapping
            if len(props.render_sets) > 0:
                max_tabs_per_row = props.settings.max_tabs_per_row

                for row_start in range(0, len(props.render_sets), max_tabs_per_row):
                    row = box.row(align=True)
                    row_end = min(row_start + max_tabs_per_row, len(props.render_sets))

                    for i in range(row_start, row_end):
                        render_set = props.render_sets[i]
                        icon = ('RESTRICT_RENDER_OFF' if render_set.enabled_for_batch_render
                                else 'RESTRICT_RENDER_ON')
                        op = row.operator("comprs.toggle_batch_render", text="", icon=icon, emboss=False)
                        op.index = i
                        row.operator("comprs.select_set", text=render_set.name,
                                     depress=(i == props.active_set_index)).index = i

                # Add/Remove buttons right under tabs
                row = box.row(align=True)
                row.operator("comprs.add_render_set", text="Add Set", icon='ADD')
                row.operator("comprs.remove_render_set", text="Remove Set", icon='REMOVE')

                box.separator()

                # Active render set details
                render_set = props.render_sets[props.active_set_index]

                col = box.column(align=True)
                col.prop(render_set, "enabled_for_batch_render", text="Enable for Batch Render")
                col.prop(render_set, "name", text="Name")
                col.prop(render_set, "output_path", text="Output")

                box.separator()

                # Output Node Settings override
                col = box.column(align=True)
                col.prop(render_set, "override_output_settings",
                         text="Override Output Node Settings", toggle=True)

                if render_set.override_output_settings:
                    sub = col.box().column(align=True)
                    sub.prop(render_set, "output_node_name_override", text="Output Node")
                    sub.prop(render_set, "name_prefix_override", text="Name Prefix")

                    sub.separator()
                    row = sub.row(align=True)
                    op = row.operator("comprs.create_node_setup", text="Create Node Setup", icon='ADD')
                    op.use_override = True
                    op = row.operator("comprs.test_node_setup", text="Test Node Setup", icon='VIEWZOOM')
                    op.use_override = True

                box.separator()

                # Render Set Collection list
                box.label(text="Render Set Collection:", icon='OUTLINER_COLLECTION')
                box.template_list(
                    "COMPRS_UL_CollectionList",
                    "",
                    render_set,
                    "collections",
                    render_set,
                    "active_collection_index",
                    rows=4
                )

                col = box.column(align=True)
                col.operator("comprs.add_collection", text="Add Collection", icon='ADD')
                col.operator("comprs.add_visible_collections",
                             text="Add Currently Visible Collections", icon='RESTRICT_VIEW_OFF')
                col.operator("comprs.clear_all_collections", text="Clear All Collections", icon='TRASH')

                if len(render_set.collections) > 0:
                    box.label(text=f"{len(render_set.collections)} collection(s) in set", icon='INFO')

                box.separator()

                # Visibility controls
                col = box.column(align=True)
                visibility_text = "Hide Set" if render_set.is_visible else "Show Set"
                col.operator("comprs.toggle_set_visibility", text=visibility_text,
                             icon='HIDE_OFF' if render_set.is_visible else 'HIDE_ON')

                hide_other_text = "Show Other Sets" if props.other_sets_hidden else "Hide Other Sets"
                hide_other_icon = 'RESTRICT_VIEW_OFF' if props.other_sets_hidden else 'RESTRICT_VIEW_ON'
                col.operator("comprs.hide_other_sets", text=hide_other_text, icon=hide_other_icon)

                solo_text = "Un-Solo Set" if props.solo_active else "Solo Set"
                col.operator("comprs.solo_set", text=solo_text,
                             icon='SOLO_ON' if props.solo_active else 'SOLO_OFF')

                box.separator()

                # Constant Render Set Collections (per-set override)
                col = box.column(align=True)
                col.prop(render_set, "override_constant_collections",
                         text="Override Constant Render Set Collections", toggle=True)

                if render_set.override_constant_collections:
                    sub = box.box()
                    sub.label(text="Constant Render Set Collections (Override):", icon='LIGHT')
                    sub.template_list(
                        "COMPRS_UL_ConstantCollectionList",
                        "",
                        render_set,
                        "constant_collections",
                        render_set,
                        "active_constant_collection_index",
                        rows=3
                    )

                    col2 = sub.column(align=True)
                    op = col2.operator("comprs.add_constant_collection",
                                       text="Add Constant Render Set Collection", icon='ADD')
                    op.use_override = True

                    if len(render_set.constant_collections) > 0:
                        sub.label(text=f"{len(render_set.constant_collections)} constant collection(s) in override",
                                  icon='INFO')
                        sub.separator()
                        const_vis_text = ("Hide Constant Render Set Collections"
                                          if props.constant_collections_visible
                                          else "Show Constant Render Set Collections")
                        const_vis_icon = 'HIDE_OFF' if props.constant_collections_visible else 'HIDE_ON'
                        col2.operator("comprs.toggle_constant_collections",
                                      text=const_vis_text, icon=const_vis_icon)

            else:
                box.label(text="No render sets. Add one below.", icon='INFO')
                row = box.row(align=True)
                row.operator("comprs.add_render_set", text="Add Set", icon='ADD')
                row.operator("comprs.remove_render_set", text="Remove Set", icon='REMOVE')

        layout.separator()

        # ====================================================================
        # Global Constant Render Set Collections Section
        # ====================================================================

        box = layout.box()
        row = box.row()
        row.prop(props.settings, "expand_constant_collections",
                 text="Constant Render Set Collections (Global)",
                 icon='TRIA_DOWN' if props.settings.expand_constant_collections else 'TRIA_RIGHT',
                 icon_only=False,
                 emboss=False)

        if props.settings.expand_constant_collections:
            box.template_list(
                "COMPRS_UL_ConstantCollectionList",
                "",
                props,
                "constant_collections",
                props,
                "active_constant_collection_index",
                rows=3
            )

            col = box.column(align=True)
            op = col.operator("comprs.add_constant_collection",
                              text="Add Constant Render Set Collection", icon='ADD')
            op.use_override = False

            if len(props.constant_collections) > 0:
                box.label(text=f"{len(props.constant_collections)} global constant collection(s)",
                          icon='INFO')
                box.separator()
                col = box.column(align=True)
                const_vis_text = ("Hide Constant Render Set Collections"
                                  if props.constant_collections_visible
                                  else "Show Constant Render Set Collections")
                const_vis_icon = 'HIDE_OFF' if props.constant_collections_visible else 'HIDE_ON'
                col.operator("comprs.toggle_constant_collections",
                             text=const_vis_text, icon=const_vis_icon)

        layout.separator()

        # ====================================================================
        # Render Section
        # ====================================================================

        box = layout.box()
        row = box.row()
        row.prop(props.settings, "expand_render",
                 text="Render",
                 icon='TRIA_DOWN' if props.settings.expand_render else 'TRIA_RIGHT',
                 icon_only=False,
                 emboss=False)

        if props.settings.expand_render:
            col = box.column(align=True)
            col.scale_y = 1.3

            op = col.operator("comprs.render_set", text="Render Current Set", icon='RENDER_STILL')
            op.mode = 'current'

            op = col.operator("comprs.render_set", text="Batch Render Sets", icon='RENDER_ANIMATION')
            op.mode = 'all'

            box.separator()

            col = box.column(align=True)
            col.enabled = props.is_rendering
            col.operator("comprs.abort_render", text="Abort Render", icon='CANCEL')

        layout.separator()

        # ====================================================================
        # Settings Section
        # ====================================================================

        box = layout.box()
        row = box.row()
        row.prop(props.settings, "expand_settings",
                 text="Settings",
                 icon='TRIA_DOWN' if props.settings.expand_settings else 'TRIA_RIGHT',
                 icon_only=False,
                 emboss=False)

        if props.settings.expand_settings:
            settings = props.settings

            # Output Node Settings (Global)
            col = box.column(align=True)
            col.label(text="Output Node Settings (Global):", icon='NODE')
            col.prop(settings, "output_node_name", text="Output Node Name")
            col.prop(settings, "name_prefix", text="Name Prefix")
            col.prop(settings, "mute_unused_output_nodes")

            col.separator()
            row = col.row(align=True)
            op = row.operator("comprs.create_node_setup", text="Create Node Setup", icon='ADD')
            op.use_override = False
            op = row.operator("comprs.test_node_setup", text="Test Node Setup", icon='VIEWZOOM')
            op.use_override = False

            box.separator()

            # Render Settings
            col = box.column(align=True)
            col.label(text="Render Settings:", icon='RENDER_STILL')
            col.prop(settings, "sync_visibility")
            col.prop(settings, "sync_modifiers")

            if settings.sync_modifiers:
                sub = col.column(align=True)
                sub.prop(settings, "only_sync_modifiers_in_renderset")

            col.prop(settings, "sync_objects")
            col.prop(settings, "hide_undefined_collections")
            col.prop(settings, "render_constant_collections")

            box.separator()

            # UI Settings
            col = box.column(align=True)
            col.label(text="UI Settings:", icon='WINDOW')
            col.prop(settings, "max_tabs_per_row", text="Max Tabs Per Row")
            col.prop(settings, "only_show_renderable")

            box.separator()
            col = box.column(align=True)
            col.prop(settings, "enable_log", text="Enable Log")
            col.prop(settings, "enable_debug", text="Debug Console Output")

        layout.separator()

        # ====================================================================
        # Log Section
        # ====================================================================

        box = layout.box()
        row = box.row()
        row.prop(props.settings, "expand_log",
                 text="Log",
                 icon='TRIA_DOWN' if props.settings.expand_log else 'TRIA_RIGHT',
                 icon_only=False,
                 emboss=False)
        row.operator("comprs.clear_log", text="", icon='X')

        if props.settings.expand_log:
            lines = logbuf.tail(props.log_text, LOG_LINES_SHOWN)
            if lines:
                col = box.column(align=True)
                for line in lines:
                    col.label(text=line[:80])  # Truncate long lines
            else:
                box.label(text="No log entries yet")


# ============================================================================
# Mirror panels in node editors
# ============================================================================

class COMPRS_PT_ShaderEditorPanel(Panel):
    """Panel in Shader Editor"""
    bl_label = "Compositor Render Sets"
    bl_idname = "COMPRS_PT_shader_editor_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Render Sets'

    @classmethod
    def poll(cls, context):
        return getattr(context.space_data, "tree_type", None) == 'ShaderNodeTree'

    def draw(self, context):
        COMPRS_PT_MainPanel.draw(self, context)


class COMPRS_PT_CompositorPanel(Panel):
    """Panel in Compositor"""
    bl_label = "Compositor Render Sets"
    bl_idname = "COMPRS_PT_compositor_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Render Sets'

    @classmethod
    def poll(cls, context):
        return getattr(context.space_data, "tree_type", None) == 'CompositorNodeTree'

    def draw(self, context):
        COMPRS_PT_MainPanel.draw(self, context)


class COMPRS_PT_GeometryNodesPanel(Panel):
    """Panel in Geometry Nodes Editor"""
    bl_label = "Compositor Render Sets"
    bl_idname = "COMPRS_PT_geometry_nodes_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Render Sets'

    @classmethod
    def poll(cls, context):
        return getattr(context.space_data, "tree_type", None) == 'GeometryNodeTree'

    def draw(self, context):
        COMPRS_PT_MainPanel.draw(self, context)


classes = (
    COMPRS_UL_CollectionList,
    COMPRS_UL_ConstantCollectionList,
    COMPRS_PT_MainPanel,
    COMPRS_PT_ShaderEditorPanel,
    COMPRS_PT_CompositorPanel,
    COMPRS_PT_GeometryNodesPanel,
)
