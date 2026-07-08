"""PropertyGroups for Compositor Render Sets."""

from datetime import datetime

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from ..core import logbuf


def log_message(context, message):
    """Add a timestamped message to the panel log (capped) and console."""
    props = context.scene.compositor_render_sets
    if props.settings.enable_log:
        entry = logbuf.format_entry(
            message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        props.log_text = logbuf.append_capped(props.log_text, entry)
        print(entry.strip())


class COMPRS_CollectionItem(PropertyGroup):
    """Represents a single collection in a Render Set"""
    collection: PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        description="Collection to include in this render set"
    )

    render_visibility: BoolProperty(
        name="Render Visibility",
        description="Enable render visibility for this collection in this set",
        default=True
    )


class COMPRS_RenderSet(PropertyGroup):
    """Represents a Render Set with name, output path, and collections"""
    name: StringProperty(
        name="Render Set Name",
        description="Name of this render set (used in file naming)",
        default="RenderSet"
    )

    output_path: StringProperty(
        name="Output Path",
        description="Directory path where renders will be saved",
        default="//",
        subtype='DIR_PATH'
    )

    enabled_for_batch_render: BoolProperty(
        name="Enable for Batch Render",
        description="Include this set when batch rendering sets",
        default=True
    )

    collections: CollectionProperty(
        type=COMPRS_CollectionItem,
        name="Render Set Collection"
    )

    active_collection_index: IntProperty(
        name="Active Collection Index",
        description="Index of the active collection in the list",
        default=0
    )

    # Per-set constant collections override
    override_constant_collections: BoolProperty(
        name="Override Constant Render Set Collections",
        description="Override global constant render set collections for this render set",
        default=False
    )

    constant_collections: CollectionProperty(
        type=COMPRS_CollectionItem,
        name="Constant Render Set Collections (Override)"
    )

    active_constant_collection_index: IntProperty(
        name="Active Constant Collection Index",
        description="Index of the active constant collection in the list",
        default=0
    )

    # Internal state for visibility management
    is_visible: BoolProperty(
        name="Is Visible",
        description="Current viewport visibility state of this set",
        default=True
    )

    # Per-set output node settings override
    override_output_settings: BoolProperty(
        name="Override Output Node Settings",
        description="Override global output node settings for this render set",
        default=False
    )

    output_node_name_override: StringProperty(
        name="Output Node Name",
        description="Name of the File Output node for this set",
        default="RenderSetOutput"
    )

    name_prefix_override: StringProperty(
        name="Name Prefix",
        description="Prefix to replace in File Output node input names for this set",
        default="XXX"
    )


class COMPRS_Settings(PropertyGroup):
    """Settings for the addon"""
    # Output Node Settings (Global)
    output_node_name: StringProperty(
        name="Output Node Name",
        description="Name of the File Output node in compositor to manipulate",
        default="RenderSetOutput"
    )

    name_prefix: StringProperty(
        name="Name Prefix",
        description="Prefix to replace in File Output node input names (e.g., 'XXX' in 'XXX_Beauty')",
        default="XXX"
    )

    mute_unused_output_nodes: BoolProperty(
        name="Mute Unused File Output Nodes",
        description="Automatically mute all File Output nodes except the one used for render sets to prevent unwanted file outputs",
        default=True
    )

    # Render Settings
    sync_visibility: BoolProperty(
        name="Sync Collection Viewport Visibility to Render",
        description="Sync collection render visibility to match viewport visibility (eye icon) for each render",
        default=True
    )

    sync_modifiers: BoolProperty(
        name="Sync Modifier Viewport Visibility to Render",
        description="Sync modifier render settings to match viewport display (what you see is what you get)",
        default=True
    )

    only_sync_modifiers_in_renderset: BoolProperty(
        name="Only Sync Modifiers in Render Set",
        description="Only sync modifiers on objects in the render set collections (faster, less debug output)",
        default=True
    )

    sync_objects: BoolProperty(
        name="Sync Objects in Collection Viewport Visibility to Render",
        description="Sync object render visibility to match viewport visibility for objects in render set collections only",
        default=False
    )

    hide_undefined_collections: BoolProperty(
        name="Only Hide Defined Collections for Render",
        description="Only hide/show collections defined in render sets during render, leaving other collections untouched",
        default=False
    )

    render_constant_collections: BoolProperty(
        name="Render Constant Render Set Collections",
        description="Always render constant render set collections with each render set",
        default=True
    )

    # UI Settings
    only_show_renderable: BoolProperty(
        name="Hide/Show Set Only Renderable",
        description="Limit hide/show set visibility toggle to only affect collections enabled for render (camera icon on)",
        default=False
    )

    max_tabs_per_row: IntProperty(
        name="Max Tabs Per Row",
        description="Maximum number of render set tabs to display per row before wrapping to a new row",
        default=8,
        min=1,
        max=20
    )

    enable_log: BoolProperty(
        name="Enable Log",
        description="Log render operations to the log panel",
        default=True
    )

    enable_debug: BoolProperty(
        name="Debug Console Output",
        description="Print verbose diagnostic output to the system console",
        default=False
    )

    # UI Collapse/Expand States
    expand_render_set_setup: BoolProperty(
        name="Expand Render Set Setup",
        description="Show/hide the Render Set Setup section",
        default=True
    )

    expand_constant_collections: BoolProperty(
        name="Expand Constant Collections",
        description="Show/hide the Global Constant Render Set Collections section",
        default=True
    )

    expand_render: BoolProperty(
        name="Expand Render",
        description="Show/hide the Render section",
        default=True
    )

    expand_settings: BoolProperty(
        name="Expand Settings",
        description="Show/hide the Settings section",
        default=False
    )

    expand_log: BoolProperty(
        name="Expand Log",
        description="Show/hide the Log section",
        default=False
    )


class COMPRS_Properties(PropertyGroup):
    """Main property group storing all addon data"""
    render_sets: CollectionProperty(
        type=COMPRS_RenderSet,
        name="Render Sets"
    )

    active_set_index: IntProperty(
        name="Active Set",
        description="Currently active render set",
        default=0
    )

    settings: PointerProperty(
        type=COMPRS_Settings
    )

    # Global constant render set collections
    constant_collections: CollectionProperty(
        type=COMPRS_CollectionItem,
        name="Constant Render Set Collections (Global)"
    )

    active_constant_collection_index: IntProperty(
        name="Active Constant Collection Index",
        description="Index of the active constant collection in the global list",
        default=0
    )

    log_text: StringProperty(
        name="Log",
        description="Render log messages",
        default=""
    )

    # Cache for solo mode
    solo_active: BoolProperty(
        name="Solo Active",
        description="Whether solo mode is currently active",
        default=False
    )

    # Cache for original visibility states (for solo undo)
    cached_visibility: StringProperty(
        name="Cached Visibility",
        description="JSON string of cached collection visibility states",
        default=""
    )

    # Cache for hide other sets toggle
    other_sets_hidden: BoolProperty(
        name="Other Sets Hidden",
        description="Whether other render sets are currently hidden",
        default=False
    )

    cached_other_sets_visibility: StringProperty(
        name="Cached Other Sets Visibility",
        description="JSON string of cached visibility states for hide other sets feature",
        default=""
    )

    # Cache for render operations (for abort/recovery functionality)
    is_rendering: BoolProperty(
        name="Is Rendering",
        description="Whether a render set operation is currently in progress",
        default=False
    )

    cached_node_state: StringProperty(
        name="Cached Node State",
        description="JSON string of cached File Output node state for abort functionality",
        default=""
    )

    # Cache for constant render set collections visibility
    constant_collections_visible: BoolProperty(
        name="Constant Render Set Collections Visible",
        description="Whether constant render set collections are currently visible in viewport",
        default=True
    )

    cached_constant_collections_visibility: StringProperty(
        name="Cached Constant Render Set Collections Visibility",
        description="JSON string of cached visibility states for constant render set collections",
        default=""
    )


classes = (
    COMPRS_CollectionItem,
    COMPRS_RenderSet,
    COMPRS_Settings,
    COMPRS_Properties,
)
