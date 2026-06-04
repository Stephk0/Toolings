bl_info = {
    "name": "Add Bounds To Name",
    "author": "Stephan Viranyi",
    "version": (1, 1, 3),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Bounds Name",
    "description": "Automatically add object bounding dimensions to object names with extensive formatting options",
    "category": "Object",
}

import bpy
from bpy.types import Operator, Panel, PropertyGroup, AddonPreferences
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    EnumProperty,
    BoolProperty,
    PointerProperty,
)
import os
import json
import math
import re


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def convert_to_unit(value_meters, target_unit):
    """Convert meter value to target unit"""
    conversions = {
        'M': 1.0,
        'CM': 100.0,
        'MM': 1000.0,
    }
    return value_meters * conversions[target_unit]


def apply_rounding(value, mode, increment):
    """Apply rounding mode with increment"""
    if mode == 'NONE':
        return value

    if increment == 0:
        return value

    if mode == 'ROUND':
        return round(value / increment) * increment
    elif mode == 'FLOOR':
        return math.floor(value / increment) * increment
    elif mode == 'CEIL':
        return math.ceil(value / increment) * increment

    return value


def swizzle_values_by_axis(x, y, z, axis_1, axis_2, axis_3):
    """Reorder XYZ values according to individual axis selections"""
    values = {'X': x, 'Y': y, 'Z': z}
    return [values[axis_1], values[axis_2], values[axis_3]]


def format_number(value, numeric_style, decimal_places, digit_padding, omit_decimal_zero):
    """Format a single dimension value as string"""
    if numeric_style == 'INTEGER':
        formatted = str(int(round(value)))
    else:  # FLOAT
        formatted = f"{value:.{decimal_places}f}"

        # Omit unnecessary .0 from whole numbers
        if omit_decimal_zero:
            # Remove trailing zeros after decimal point
            formatted = formatted.rstrip('0').rstrip('.')

    # Apply digit padding
    if digit_padding > 0 and '.' not in formatted:
        formatted = formatted.zfill(digit_padding)

    return formatted


def strip_blender_numbering(name):
    """Remove Blender's automatic .001, .002, etc. numbering from name

    Blender automatically appends .001, .002, etc. to duplicate objects.
    This function removes that suffix.
    Pattern: dot followed by 3+ digits at end of string
    """
    # Match .001, .002, .999, .1000, .1001, etc. at end of string
    pattern = r'\.\d{3,}$'
    return re.sub(pattern, '', name)


def detect_previous_bounds(name, name_separators=None, dimension_separators=None):
    """Try to detect and extract previous bounds from object name

    Detects both 2D and 3D dimension patterns:
    - 3D: cube_1x2x3, wall_400x200x10cm
    - 2D: floor_500x500, trim_10x100mm

    IMPORTANT: Tries 3D patterns FIRST to avoid matching first 2 numbers of 3D pattern

    Returns:
        tuple: (base_name, bounds_found, bounds_string) or (name, False, None)
    """
    if name_separators is None:
        # Common name separators (between name and bounds)
        name_separators = ['_', '-', ' ', '.']

    if dimension_separators is None:
        # Common dimension separators (between numbers)
        dimension_separators = ['x', 'X', '-', '*', 'by']

    number_pattern = r'\d+(?:\.\d+)?'  # Integer or float
    unit_pattern = r'(?:m|cm|mm)?'      # Optional unit suffix

    # ========================================================================
    # SUFFIX PATTERNS (bounds at end of name)
    # ========================================================================

    # Try 3D suffix pattern FIRST: name_1x2x3
    for name_sep in name_separators:
        for dim_sep in dimension_separators:
            escaped_name_sep = re.escape(name_sep)
            escaped_dim_sep = re.escape(dim_sep)

            pattern = (
                rf'({escaped_name_sep})'   # Name separator
                rf'({number_pattern})'      # First dimension
                rf'{escaped_dim_sep}'       # Dimension separator
                rf'({number_pattern})'      # Second dimension
                rf'{escaped_dim_sep}'       # Dimension separator
                rf'({number_pattern})'      # Third dimension
                rf'{unit_pattern}$'         # Optional unit at end
            )

            match = re.search(pattern, name)
            if match:
                base_name = name[:match.start()]
                bounds_string = name[match.start():]
                return (base_name, True, bounds_string)

    # Try 2D suffix pattern: name_1x2
    for name_sep in name_separators:
        for dim_sep in dimension_separators:
            escaped_name_sep = re.escape(name_sep)
            escaped_dim_sep = re.escape(dim_sep)

            pattern = (
                rf'({escaped_name_sep})'   # Name separator
                rf'({number_pattern})'      # First dimension
                rf'{escaped_dim_sep}'       # Dimension separator
                rf'({number_pattern})'      # Second dimension
                rf'{unit_pattern}$'         # Optional unit at end
            )

            match = re.search(pattern, name)
            if match:
                base_name = name[:match.start()]
                bounds_string = name[match.start():]
                return (base_name, True, bounds_string)

    # ========================================================================
    # PREFIX PATTERNS (bounds at start of name)
    # ========================================================================

    # Try 3D prefix pattern FIRST: 1x2x3_name
    for name_sep in name_separators:
        for dim_sep in dimension_separators:
            escaped_name_sep = re.escape(name_sep)
            escaped_dim_sep = re.escape(dim_sep)

            pattern = (
                rf'^{unit_pattern}'         # Optional unit at start
                rf'({number_pattern})'      # First dimension
                rf'{escaped_dim_sep}'       # Dimension separator
                rf'({number_pattern})'      # Second dimension
                rf'{escaped_dim_sep}'       # Dimension separator
                rf'({number_pattern})'      # Third dimension
                rf'({escaped_name_sep})'    # Name separator
            )

            match = re.search(pattern, name)
            if match:
                bounds_string = name[:match.end()]
                base_name = name[match.end():]
                return (base_name, True, bounds_string)

    # Try 2D prefix pattern: 1x2_name
    for name_sep in name_separators:
        for dim_sep in dimension_separators:
            escaped_name_sep = re.escape(name_sep)
            escaped_dim_sep = re.escape(dim_sep)

            pattern = (
                rf'^{unit_pattern}'         # Optional unit at start
                rf'({number_pattern})'      # First dimension
                rf'{escaped_dim_sep}'       # Dimension separator
                rf'({number_pattern})'      # Second dimension
                rf'({escaped_name_sep})'    # Name separator
            )

            match = re.search(pattern, name)
            if match:
                bounds_string = name[:match.end()]
                base_name = name[match.end():]
                return (base_name, True, bounds_string)

    # No bounds found
    return (name, False, None)


def get_object_bounds(obj, bounds_source):
    """Get object bounding box dimensions"""
    if bounds_source == 'OBJECT':
        # Use object.dimensions (includes modifiers and children)
        return obj.dimensions.x, obj.dimensions.y, obj.dimensions.z
    else:  # MESH
        # Calculate from mesh data only
        if obj.type != 'MESH' or obj.data is None:
            # Fallback to object dimensions for non-mesh objects
            return obj.dimensions.x, obj.dimensions.y, obj.dimensions.z

        # Get local space bounding box from mesh
        mesh = obj.data
        if len(mesh.vertices) == 0:
            return 0.0, 0.0, 0.0

        # Calculate bounds from vertices
        min_x = min((v.co.x for v in mesh.vertices))
        max_x = max((v.co.x for v in mesh.vertices))
        min_y = min((v.co.y for v in mesh.vertices))
        max_y = max((v.co.y for v in mesh.vertices))
        min_z = min((v.co.z for v in mesh.vertices))
        max_z = max((v.co.z for v in mesh.vertices))

        # Apply object scale
        x_dim = (max_x - min_x) * abs(obj.scale.x)
        y_dim = (max_y - min_y) * abs(obj.scale.y)
        z_dim = (max_z - min_z) * abs(obj.scale.z)

        return x_dim, y_dim, z_dim


def build_size_label(props, obj):
    """Build the complete size label for an object"""
    # Get bounds
    x, y, z = get_object_bounds(obj, props.bounds_source)

    # Convert to target units
    x = convert_to_unit(x, props.target_unit)
    y = convert_to_unit(y, props.target_unit)
    z = convert_to_unit(z, props.target_unit)

    # Apply rounding
    x = apply_rounding(x, props.rounding_mode, props.rounding_increment)
    y = apply_rounding(y, props.rounding_mode, props.rounding_increment)
    z = apply_rounding(z, props.rounding_mode, props.rounding_increment)

    # Swizzle using individual axis selections
    values = swizzle_values_by_axis(x, y, z, props.axis_1, props.axis_2, props.axis_3)

    # Format numbers
    formatted_values = [
        format_number(v, props.numeric_style, props.decimal_places, props.digit_padding, props.omit_decimal_zero)
        for v in values
    ]

    # Build size label
    size_label = props.dimension_separator.join(formatted_values)

    # Add unit suffix if enabled
    if props.show_unit_suffix:
        unit_suffix = props.target_unit.lower()
        size_label = f"{size_label}{unit_suffix}"

    return size_label


def build_new_name(original_name, size_label, props):
    """Build the complete new object name

    CRITICAL ORDER OF OPERATIONS:
    1. Strip Blender numbering (.001, .002, etc.) FIRST
    2. Then detect and remove previous bounds
    3. Finally add new bounds

    This order is essential because Blender numbering typically appears AFTER bounds:
    Example: cube_1x1x1.001 (not cube.001_1x1x1)

    If we detect bounds first, the regex won't match because .001 is at the end.
    """
    base_name = original_name

    # STEP 1: Strip Blender numbering if enabled
    # This must happen FIRST because .001 typically comes after bounds: cube_1x1x1.001
    if props.erase_blender_numbering:
        stripped_name = strip_blender_numbering(base_name)
        if props.debug_mode and stripped_name != base_name:
            print(f"[AddBoundsToName] Stripped Blender numbering: '{base_name}' → '{stripped_name}'")
        base_name = stripped_name

    # STEP 2: Try to replace previous bounds if enabled
    # Now that .001 is removed, we can detect bounds patterns like _1x1x1
    if props.replace_previous_bounds:
        if props.auto_detect_separators:
            # Auto-detect with common separators
            cleaned_name, bounds_found, old_bounds = detect_previous_bounds(base_name)
            if bounds_found:
                if props.debug_mode:
                    print(f"[AddBoundsToName] Detected and removed previous bounds: '{old_bounds}'")
                base_name = cleaned_name
        else:
            # Use manual separator specification
            name_seps = [s.strip() for s in props.manual_name_separators.split(',') if s.strip()]
            dim_seps = [s.strip() for s in props.manual_dimension_separators.split(',') if s.strip()]

            if name_seps and dim_seps:
                cleaned_name, bounds_found, old_bounds = detect_previous_bounds(base_name, name_seps, dim_seps)
                if bounds_found:
                    if props.debug_mode:
                        print(f"[AddBoundsToName] Detected and removed previous bounds: '{old_bounds}'")
                    base_name = cleaned_name

    # STEP 3: Build new name with size label
    if props.format_style == 'PREFIX':
        return f"{size_label}{props.name_separator}{base_name}"
    else:  # SUFFIX
        return f"{base_name}{props.name_separator}{size_label}"


def get_preset_directory():
    """Get the directory where presets are stored"""
    import bpy
    preset_dir = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", "add_bounds_to_name")
    os.makedirs(preset_dir, exist_ok=True)
    return preset_dir


def get_preset_list():
    """Get list of available presets"""
    preset_dir = get_preset_directory()
    if not os.path.exists(preset_dir):
        return []

    presets = []
    for filename in os.listdir(preset_dir):
        if filename.endswith('.json'):
            presets.append(filename[:-5])  # Remove .json extension
    return sorted(presets)


# ============================================================================
# PROPERTY GROUP
# ============================================================================

class BOUNDSNAME_PG_Settings(PropertyGroup):
    """Property group for all Add Bounds To Name settings"""

    # Target units
    target_unit: EnumProperty(
        name="Unit",
        description="Output unit for dimensions",
        items=[
            ('M', "Meters", "Output dimensions in meters"),
            ('CM', "Centimeters", "Output dimensions in centimeters"),
            ('MM', "Millimeters", "Output dimensions in millimeters"),
        ],
        default='M'
    )

    # Rounding
    rounding_mode: EnumProperty(
        name="Rounding Mode",
        description="How to round dimension values",
        items=[
            ('NONE', "None", "No rounding, use exact values"),
            ('ROUND', "Round", "Round to nearest increment"),
            ('FLOOR', "Floor", "Always round down"),
            ('CEIL', "Ceil", "Always round up"),
        ],
        default='NONE'
    )

    rounding_increment: FloatProperty(
        name="Rounding Increment",
        description="Value to round to (in target units)",
        default=1.0,
        min=0.0,
        soft_max=100.0
    )

    # Individual axis swizzle (3 separate dropdowns)
    axis_1: EnumProperty(
        name="1st Dimension",
        description="First dimension to output",
        items=[
            ('X', "X", "X axis"),
            ('Y', "Y", "Y axis"),
            ('Z', "Z", "Z axis"),
        ],
        default='X'
    )

    axis_2: EnumProperty(
        name="2nd Dimension",
        description="Second dimension to output",
        items=[
            ('X', "X", "X axis"),
            ('Y', "Y", "Y axis"),
            ('Z', "Z", "Z axis"),
        ],
        default='Y'
    )

    axis_3: EnumProperty(
        name="3rd Dimension",
        description="Third dimension to output",
        items=[
            ('X', "X", "X axis"),
            ('Y', "Y", "Y axis"),
            ('Z', "Z", "Z axis"),
        ],
        default='Z'
    )

    # Formatting
    format_style: EnumProperty(
        name="Format Style",
        description="Where to place size label",
        items=[
            ('PREFIX', "Prefix", "Size before name: 1x1x1_cube"),
            ('SUFFIX', "Suffix", "Size after name: cube_1x1x1"),
        ],
        default='SUFFIX'
    )

    name_separator: StringProperty(
        name="Name Separator",
        description="Character(s) between name and size",
        default="_"
    )

    dimension_separator: StringProperty(
        name="Dimension Separator",
        description="Character(s) between dimension values",
        default="x"
    )

    # Numeric style
    numeric_style: EnumProperty(
        name="Numeric Style",
        description="How to format numbers",
        items=[
            ('INTEGER', "Integer", "Output as whole numbers"),
            ('FLOAT', "Float", "Allow decimal values"),
        ],
        default='INTEGER'
    )

    decimal_places: IntProperty(
        name="Decimal Places",
        description="Number of decimal places (float mode only)",
        default=2,
        min=0,
        max=6
    )

    omit_decimal_zero: BoolProperty(
        name="Omit Decimal Zero",
        description="Remove unnecessary .0 from whole numbers (e.g., 1.0 becomes 1, but 1.5 stays 1.5)",
        default=True
    )

    digit_padding: IntProperty(
        name="Digit Padding",
        description="Minimum number of digits (zero-padded)",
        default=1,
        min=1,
        max=6
    )

    show_unit_suffix: BoolProperty(
        name="Show Unit Suffix",
        description="Append unit abbreviation to size (e.g., '100cm')",
        default=False
    )

    # Bounds source
    bounds_source: EnumProperty(
        name="Bounds Source",
        description="What to measure",
        items=[
            ('OBJECT', "Object Bounds", "Use object.dimensions (includes modifiers and children)"),
            ('MESH', "Mesh Bounds", "Calculate from base mesh data only"),
        ],
        default='OBJECT'
    )

    # Replace previous bounds
    replace_previous_bounds: BoolProperty(
        name="Replace Previous Bounds",
        description="Try to find and replace existing bounds in name instead of appending",
        default=False
    )

    auto_detect_separators: BoolProperty(
        name="Auto-Detect Separators",
        description="Automatically detect common separators (_, -, space for names; x, -, * for dimensions)",
        default=True
    )

    manual_name_separators: StringProperty(
        name="Name Separators",
        description="Comma-separated list of name separators to look for (e.g., '_,-,.')",
        default="_,-,."
    )

    manual_dimension_separators: StringProperty(
        name="Dimension Separators",
        description="Comma-separated list of dimension separators to look for (e.g., 'x,X,-')",
        default="x,X,-"
    )

    # Erase Blender numbering
    erase_blender_numbering: BoolProperty(
        name="Erase Blender Numbering",
        description="Remove Blender's automatic .001, .002, etc. suffixes before adding bounds",
        default=True
    )

    # Debug
    debug_mode: BoolProperty(
        name="Debug Mode",
        description="Print detailed information to console",
        default=False
    )

    # Preset management
    current_preset_name: StringProperty(
        name="Preset Name",
        description="Name for saving/loading presets",
        default=""
    )


# ============================================================================
# OPERATORS - RENAME
# ============================================================================

class BOUNDSNAME_OT_RenameActive(Operator):
    """Rename the active object with its bounding dimensions"""
    bl_idname = "object.boundsname_rename_active"
    bl_label = "Rename Active Object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        props = context.scene.boundsname_settings
        obj = context.active_object

        original_name = obj.name

        try:
            # Build size label
            size_label = build_size_label(props, obj)

            # Build new name
            new_name = build_new_name(original_name, size_label, props)

            # Apply new name
            obj.name = new_name

            if props.debug_mode:
                print(f"[AddBoundsToName] Renamed: '{original_name}' -> '{new_name}'")
                print(f"[AddBoundsToName] Size label: {size_label}")

            self.report({'INFO'}, f"Renamed to: {new_name}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to rename object: {str(e)}")
            if props.debug_mode:
                import traceback
                traceback.print_exc()
            return {'CANCELLED'}


class BOUNDSNAME_OT_RenameBatch(Operator):
    """Rename all selected objects with their bounding dimensions"""
    bl_idname = "object.boundsname_rename_batch"
    bl_label = "Rename Selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        props = context.scene.boundsname_settings
        objects = context.selected_objects

        renamed_count = 0
        failed_count = 0

        for obj in objects:
            original_name = obj.name

            try:
                # Build size label
                size_label = build_size_label(props, obj)

                # Build new name
                new_name = build_new_name(original_name, size_label, props)

                # Apply new name
                obj.name = new_name
                renamed_count += 1

                if props.debug_mode:
                    print(f"[AddBoundsToName] Renamed: '{original_name}' -> '{new_name}'")

            except Exception as e:
                failed_count += 1
                if props.debug_mode:
                    print(f"[AddBoundsToName] Failed to rename '{original_name}': {str(e)}")

        # Report results
        if failed_count == 0:
            self.report({'INFO'}, f"Renamed {renamed_count} object(s)")
        else:
            self.report({'WARNING'}, f"Renamed {renamed_count}, failed {failed_count}")

        return {'FINISHED'}


# ============================================================================
# OPERATORS - PRESETS
# ============================================================================

class BOUNDSNAME_OT_SavePreset(Operator):
    """Save current settings as a preset"""
    bl_idname = "object.boundsname_save_preset"
    bl_label = "Save Preset"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.boundsname_settings

        if not props.current_preset_name:
            self.report({'ERROR'}, "Enter a preset name")
            return {'CANCELLED'}

        # Collect settings to save
        preset_data = {
            'target_unit': props.target_unit,
            'rounding_mode': props.rounding_mode,
            'rounding_increment': props.rounding_increment,
            'axis_1': props.axis_1,
            'axis_2': props.axis_2,
            'axis_3': props.axis_3,
            'format_style': props.format_style,
            'name_separator': props.name_separator,
            'dimension_separator': props.dimension_separator,
            'numeric_style': props.numeric_style,
            'decimal_places': props.decimal_places,
            'omit_decimal_zero': props.omit_decimal_zero,
            'digit_padding': props.digit_padding,
            'show_unit_suffix': props.show_unit_suffix,
            'bounds_source': props.bounds_source,
            'replace_previous_bounds': props.replace_previous_bounds,
            'auto_detect_separators': props.auto_detect_separators,
            'manual_name_separators': props.manual_name_separators,
            'manual_dimension_separators': props.manual_dimension_separators,
            'erase_blender_numbering': props.erase_blender_numbering,
        }

        # Save to file
        preset_dir = get_preset_directory()
        preset_path = os.path.join(preset_dir, f"{props.current_preset_name}.json")

        try:
            with open(preset_path, 'w') as f:
                json.dump(preset_data, f, indent=2)

            self.report({'INFO'}, f"Saved preset: {props.current_preset_name}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to save preset: {str(e)}")
            return {'CANCELLED'}


class BOUNDSNAME_OT_LoadPreset(Operator):
    """Load settings from a preset"""
    bl_idname = "object.boundsname_load_preset"
    bl_label = "Load Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset_name: StringProperty()

    def execute(self, context):
        props = context.scene.boundsname_settings

        if not self.preset_name:
            self.report({'ERROR'}, "No preset specified")
            return {'CANCELLED'}

        preset_dir = get_preset_directory()
        preset_path = os.path.join(preset_dir, f"{self.preset_name}.json")

        if not os.path.exists(preset_path):
            self.report({'ERROR'}, f"Preset not found: {self.preset_name}")
            return {'CANCELLED'}

        try:
            with open(preset_path, 'r') as f:
                preset_data = json.load(f)

            # Apply settings
            for key, value in preset_data.items():
                if hasattr(props, key):
                    setattr(props, key, value)

            props.current_preset_name = self.preset_name
            self.report({'INFO'}, f"Loaded preset: {self.preset_name}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to load preset: {str(e)}")
            return {'CANCELLED'}


class BOUNDSNAME_OT_DeletePreset(Operator):
    """Delete a preset"""
    bl_idname = "object.boundsname_delete_preset"
    bl_label = "Delete Preset"
    bl_options = {'REGISTER'}

    preset_name: StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if not self.preset_name:
            self.report({'ERROR'}, "No preset specified")
            return {'CANCELLED'}

        preset_dir = get_preset_directory()
        preset_path = os.path.join(preset_dir, f"{self.preset_name}.json")

        try:
            if os.path.exists(preset_path):
                os.remove(preset_path)
                self.report({'INFO'}, f"Deleted preset: {self.preset_name}")
            else:
                self.report({'ERROR'}, f"Preset not found: {self.preset_name}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete preset: {str(e)}")
            return {'CANCELLED'}


# ============================================================================
# UI PANEL
# ============================================================================

class VIEW3D_PT_BoundsName(Panel):
    """Add Bounds To Name panel in 3D View sidebar"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bounds Name'
    bl_label = "Add Bounds To Name"

    def draw(self, context):
        layout = self.layout
        props = context.scene.boundsname_settings

        # ============ PRESETS ============
        box = layout.box()
        box.label(text="Presets", icon='PRESET')

        row = box.row(align=True)
        row.prop(props, "current_preset_name", text="")
        row.operator("object.boundsname_save_preset", text="", icon='ADD')

        # List existing presets
        presets = get_preset_list()
        if presets:
            col = box.column(align=True)
            for preset_name in presets:
                row = col.row(align=True)
                op = row.operator("object.boundsname_load_preset", text=preset_name, icon='PRESET')
                op.preset_name = preset_name
                op = row.operator("object.boundsname_delete_preset", text="", icon='X')
                op.preset_name = preset_name

        layout.separator()

        # ============ UNITS & ROUNDING ============
        box = layout.box()
        box.label(text="Units & Rounding", icon='EMPTY_ARROWS')

        box.prop(props, "target_unit")
        box.prop(props, "rounding_mode")
        if props.rounding_mode != 'NONE':
            box.prop(props, "rounding_increment")

        layout.separator()

        # ============ AXIS SWIZZLE ============
        box = layout.box()
        box.label(text="Axis Swizzle", icon='ORIENTATION_VIEW')

        row = box.row(align=True)
        row.prop(props, "axis_1", text="X")
        row.prop(props, "axis_2", text="Y")
        row.prop(props, "axis_3", text="Z")

        layout.separator()

        # ============ FORMATTING ============
        box = layout.box()
        box.label(text="Formatting", icon='SYNTAX_ON')

        box.prop(props, "format_style")
        box.prop(props, "name_separator")
        box.prop(props, "dimension_separator")

        box.separator()

        box.prop(props, "numeric_style")
        if props.numeric_style == 'FLOAT':
            box.prop(props, "decimal_places")
            box.prop(props, "omit_decimal_zero")
        box.prop(props, "digit_padding")
        box.prop(props, "show_unit_suffix")

        layout.separator()

        # ============ REPLACE PREVIOUS BOUNDS ============
        box = layout.box()
        box.label(text="Smart Renaming", icon='FILE_REFRESH')

        box.prop(props, "replace_previous_bounds")

        if props.replace_previous_bounds:
            sub = box.column(align=True)
            sub.prop(props, "auto_detect_separators")

            if not props.auto_detect_separators:
                sub.prop(props, "manual_name_separators")
                sub.prop(props, "manual_dimension_separators")

        box.prop(props, "erase_blender_numbering")

        layout.separator()

        # ============ BOUNDS SOURCE ============
        box = layout.box()
        box.label(text="Measurement", icon='MESH_CUBE')
        box.prop(props, "bounds_source")

        layout.separator()

        # ============ ACTIONS ============
        box = layout.box()
        box.label(text="Rename Operations", icon='SORTALPHA')

        # Active object
        col = box.column(align=True)
        if context.active_object:
            col.operator("object.boundsname_rename_active", icon='OBJECT_DATA')
            col.label(text=f"Active: {context.active_object.name}", icon='DOT')
        else:
            col.label(text="No active object", icon='ERROR')

        box.separator()

        # Selected objects
        col = box.column(align=True)
        if context.selected_objects:
            col.operator("object.boundsname_rename_batch", icon='OUTLINER_OB_GROUP_INSTANCE')
            col.label(text=f"Selected: {len(context.selected_objects)} object(s)", icon='DOT')
        else:
            col.label(text="No selected objects", icon='ERROR')

        layout.separator()

        # ============ DEBUG ============
        layout.prop(props, "debug_mode")


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    BOUNDSNAME_PG_Settings,
    BOUNDSNAME_OT_RenameActive,
    BOUNDSNAME_OT_RenameBatch,
    BOUNDSNAME_OT_SavePreset,
    BOUNDSNAME_OT_LoadPreset,
    BOUNDSNAME_OT_DeletePreset,
    VIEW3D_PT_BoundsName,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.boundsname_settings = PointerProperty(type=BOUNDSNAME_PG_Settings)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.boundsname_settings


if __name__ == "__main__":
    register()
