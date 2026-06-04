"""
This operator is inspired by Modifier Tools add-on, thanks for the authors
meta-androcto, saidenka and lijenstina.
https://wiki.blender.org/wiki/Extensions:2.6/Py/Scripts/3D_interaction/modifier_tools
"""

import bpy
from bpy.props import *
from bpy.types import Operator
from ... import __package__ as base_package

from ..utils import get_ml_active_object

visibility_modifer_list = {}
visibility_modifier_dict = {}

def get_ml_active_object():
    return bpy.context.view_layer.objects.active


class VIEW3D_OT_ml_toggle_all_modifiers(Operator):
    bl_idname = "view3d.ml_toggle_all_modifiers"
    bl_label = "Toggle Visibility Of All Modifiers"
    bl_description = """Toggle the visibility of all modifiers of the selected object(s). 
The active object must have modifiers."

Hold Shift to toggle modifiers based on current viewport on state.
"""
    bl_options = {'REGISTER', 'UNDO'}

    only_toggle_visible: BoolProperty(name="Only Toggle Visible", options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, event):
        if event.shift:
            self.only_toggle_visible = True

        return self.execute(context)


    @classmethod
    def poll(cls, context):
        ml_act_ob = get_ml_active_object()
        return ml_act_ob is not None and bool(ml_act_ob.modifiers)

    def execute(self, context):
        global visibility_modifer_list 
        global visibility_modifier_dict

        if self.only_toggle_visible == False:
            ml_act_ob = get_ml_active_object()
            sel_obs = context.selected_objects
            obs = sel_obs.copy()

            if ml_act_ob not in obs:
                obs.append(ml_act_ob)

            ml_act_ob_all_mods_vis = [mod.show_viewport for mod in ml_act_ob.modifiers]
            show_mods = not any(ml_act_ob_all_mods_vis)
            skipped_linked_obs = False

            for ob in obs:
                # Skip linked objects if they don't have a library override
                if ob.library and not ob.override_library:
                    skipped_linked_obs = True
                    continue

                for mod in ob.modifiers:
                    # Dont toggle the visibility of collision modifiers as that
                    # can apparently cause problems in some scenes.
                    if not mod.type == 'COLLISION':
                        mod.show_viewport = show_mods

            prefs = bpy.context.preferences.addons[base_package].preferences

            if 'TOGGLE_VISIBILITY' in prefs.batch_ops_reports:
                skipped_linked_obs_message = (" (skipped linked objects with no override)"
                                            if skipped_linked_obs else "")
                message = "Displaying all modifiers" if show_mods else "Hiding all modifiers"
                self.report({'INFO'}, message + skipped_linked_obs_message)

        else:
            if bpy.context.active_object is not None:
                    active_object_name = bpy.context.view_layer.objects.active.name

                    if active_object_name not in visibility_modifier_dict:
                        visibility_modifier_dict[active_object_name] = []

                    visibility_modifier_list = visibility_modifier_dict[active_object_name]

                    if len(visibility_modifier_list) <= 0:
                        ml_act_ob = get_ml_active_object()
                        for mod in ml_act_ob.modifiers:
                            if mod.show_viewport:
                                visibility_modifier_list.append(mod)
                                mod.show_viewport = False
                    else:
                        ml_act_ob = get_ml_active_object()
                        hidden_modifiers = []
                        for mod in ml_act_ob.modifiers:
                            if mod in visibility_modifier_list:
                                mod.show_viewport = True
                                hidden_modifiers.append(mod)
                        visibility_modifier_list = [mod for mod in visibility_modifier_list if mod not in hidden_modifiers]
                        visibility_modifier_dict[active_object_name] = visibility_modifier_list
        return {'FINISHED'}
            