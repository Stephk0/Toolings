"""UI panel and plan list for Library Relink."""

from bpy.types import Panel, UIList

STATUS_ICONS = {
    'RELINK': 'FILE_REFRESH',
    'MISSING': 'ERROR',
    'FILTERED': 'FILTER',
    'SAME': 'CHECKMARK',
}


class LIBRELINK_UL_plan(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_property, index=0, flt_flag=0):
        row = layout.row(align=True)
        if item.status == 'RELINK':
            row.prop(item, "enabled", text="")
        else:
            row.label(icon='BLANK1')
        row.label(text=item.lib_name, icon=STATUS_ICONS.get(item.status, 'QUESTION'))


class LIBRELINK_PT_panel(Panel):
    bl_label = "Library Relink"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Relink"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.library_relink

        col = layout.column(align=True)
        col.prop(settings, "new_dir")
        col.prop(settings, "old_dir_filter")
        layout.prop(settings, "make_relative")

        row = layout.row(align=True)
        row.operator("librelink.scan", icon='VIEWZOOM')
        row.operator("librelink.apply", icon='FILE_REFRESH')

        if not settings.plan:
            layout.label(text="Run Preview to build the plan", icon='INFO')
            return

        counts = {key: 0 for key in STATUS_ICONS}
        for item in settings.plan:
            counts[item.status] += 1
        layout.label(
            text=f"{counts['RELINK']} to relink · {counts['MISSING']} missing · "
                 f"{counts['FILTERED'] + counts['SAME']} skipped")

        row = layout.row()
        row.template_list("LIBRELINK_UL_plan", "", settings, "plan",
                          settings, "plan_index", rows=6)
        col = row.column(align=True)
        col.operator("librelink.set_all", text="", icon='CHECKBOX_HLT').enable = True
        col.operator("librelink.set_all", text="", icon='CHECKBOX_DEHLT').enable = False

        if 0 <= settings.plan_index < len(settings.plan):
            item = settings.plan[settings.plan_index]
            box = layout.box()
            box.label(text=item.lib_name, icon=STATUS_ICONS.get(item.status, 'QUESTION'))
            box.label(text=f"From: {item.current_path}")
            if item.status in {'RELINK', 'MISSING'}:
                box.label(text=f"To: {item.target_path}")


classes = (
    LIBRELINK_UL_plan,
    LIBRELINK_PT_panel,
)
