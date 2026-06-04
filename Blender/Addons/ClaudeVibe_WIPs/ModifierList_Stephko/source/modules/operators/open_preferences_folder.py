import bpy
from bpy.types import Operator
from ... import __package__ as base_package


class OpenMLPreferencesFolder(Operator):
    bl_idname = "ml.open_preferences_folder"
    bl_label = "Open Config Folder"
    bl_description = "Open the folder where the modifier list preferences are stored"
    bl_options = {'REGISTER'}

    def execute(self, context):
        import os
        import platform

        config_dir = bpy.utils.user_resource('CONFIG')
        ml_config_dir = os.path.join(config_dir, base_package)
        prefs_file = os.path.join(ml_config_dir, "preferences.json")

        if platform.system() == 'Windows':
            os.system(f'explorer /select,"{prefs_file}"')
        elif platform.system() == 'Darwin':
            os.system(f'open -R "{prefs_file}"')
        elif platform.system() == 'Linux':
            os.system(f'xdg-open "{prefs_file}"')
        return {'FINISHED'}