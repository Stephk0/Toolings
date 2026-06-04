"""
Procedural Tree Generator - GeoNodes Setup Script
Version: 1.0 - Phase 1 MVP
Author: Stephan Viranyi (Stephko)
Date: 2025-12-03

This script creates a Geometry Nodes setup for procedural tree generation.
Run this script in Blender's Text Editor or via command line.

Requirements:
- Blender 4.0+ (for Repeat Zones)
- Recommended: Blender 4.5+

Usage:
1. Open Blender
2. Create a curve object (this will be your trunk)
3. Select the curve object
4. Run this script in the Scripting workspace
"""

import bpy
import mathutils

def clear_node_tree(node_tree):
    """Clear all nodes from a node tree"""
    node_tree.nodes.clear()

def create_frame(node_tree, name, color=(0.6, 0.6, 0.6)):
    """Create a named frame for organizing nodes"""
    frame = node_tree.nodes.new('NodeFrame')
    frame.label = name
    frame.use_custom_color = True
    frame.color = color
    return frame

def setup_tree_generator():
    """Main function to set up the procedural tree generator"""

    # Get active object
    obj = bpy.context.active_object

    if not obj:
        print("ERROR: No active object. Please select a curve object.")
        return None

    # Add Geometry Nodes modifier
    modifier = obj.modifiers.new(name="ProceduralTreeGenerator", type='NODES')

    # Create or get node group
    if modifier.node_group is None:
        node_group = bpy.data.node_groups.new('TreeGenerator_Main', 'GeometryNodeTree')
        modifier.node_group = node_group
    else:
        node_group = modifier.node_group

    # Clear existing nodes
    clear_node_tree(node_group)

    nodes = node_group.nodes
    links = node_group.links

    # Create frames for organization
    frame_input = create_frame(node_group, "INPUT PROCESSING", (0.3, 0.5, 0.3))
    frame_branch_gen = create_frame(node_group, "BRANCH GENERATION", (0.5, 0.3, 0.3))
    frame_attributes = create_frame(node_group, "ATTRIBUTE INITIALIZATION", (0.3, 0.3, 0.5))
    frame_growth = create_frame(node_group, "GROWTH DIRECTION", (0.5, 0.4, 0.2))
    frame_geometry = create_frame(node_group, "GEOMETRY BUILDER", (0.2, 0.4, 0.5))

    # ===== INPUT/OUTPUT NODES =====
    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-1200, 0)

    group_output = nodes.new('NodeGroupOutput')
    group_output.location = (1200, 0)

    # ===== INPUT PROCESSING FRAME =====
    # Mesh to Curve conversion
    mesh_to_curve = nodes.new('GeometryNodeMeshToCurve')
    mesh_to_curve.parent = frame_input
    mesh_to_curve.location = (-900, 100)
    mesh_to_curve.label = "Convert Input"

    # Resample curve for even distribution
    resample_curve = nodes.new('GeometryNodeResampleCurve')
    resample_curve.parent = frame_input
    resample_curve.location = (-900, -50)
    resample_curve.mode = 'COUNT'
    resample_curve.inputs['Count'].default_value = 20

    # Set Curve Normal (for consistent direction)
    set_curve_normal = nodes.new('GeometryNodeSetCurveNormal')
    set_curve_normal.parent = frame_input
    set_curve_normal.location = (-900, -200)
    set_curve_normal.mode = 'FREE'

    # ===== ATTRIBUTE INITIALIZATION FRAME =====
    # Store iteration_level (starts at 0 for trunk)
    store_iteration = nodes.new('GeometryNodeStoreNamedAttribute')
    store_iteration.parent = frame_attributes
    store_iteration.location = (-600, 200)
    store_iteration.data_type = 'INT'
    store_iteration.domain = 'POINT'
    store_iteration.inputs['Name'].default_value = 'iteration_level'
    store_iteration.inputs['Value'].default_value = 0

    # Store branch_id (unique identifier)
    store_branch_id = nodes.new('GeometryNodeStoreNamedAttribute')
    store_branch_id.parent = frame_attributes
    store_branch_id.location = (-600, 50)
    store_branch_id.data_type = 'INT'
    store_branch_id.domain = 'POINT'
    store_branch_id.inputs['Name'].default_value = 'branch_id'

    # Index node for branch_id
    index_node = nodes.new('GeometryNodeInputIndex')
    index_node.parent = frame_attributes
    index_node.location = (-800, 0)

    # Store branch_thickness
    store_thickness = nodes.new('GeometryNodeStoreNamedAttribute')
    store_thickness.parent = frame_attributes
    store_thickness.location = (-600, -100)
    store_thickness.data_type = 'FLOAT'
    store_thickness.domain = 'POINT'
    store_thickness.inputs['Name'].default_value = 'branch_thickness'

    # Store curve_parameter (0-1 along curve)
    store_curve_param = nodes.new('GeometryNodeStoreNamedAttribute')
    store_curve_param.parent = frame_attributes
    store_curve_param.location = (-600, -250)
    store_curve_param.data_type = 'FLOAT'
    store_curve_param.domain = 'POINT'
    store_curve_param.inputs['Name'].default_value = 'curve_parameter'

    # Spline Parameter node
    spline_param = nodes.new('GeometryNodeSplineParameter')
    spline_param.parent = frame_attributes
    spline_param.location = (-800, -250)

    # ===== REPEAT ZONE FOR BRANCH GENERATION =====
    # Create repeat zone
    repeat_input = nodes.new('GeometryNodeRepeatInput')
    repeat_input.parent = frame_branch_gen
    repeat_input.location = (-300, 0)

    repeat_output = nodes.new('GeometryNodeRepeatOutput')
    repeat_output.parent = frame_branch_gen
    repeat_output.location = (300, 0)

    # Link repeat zone
    repeat_output.pair_with_output(repeat_input)

    # Sample curve for spawn points (inside repeat zone)
    sample_curve = nodes.new('GeometryNodeSampleCurve')
    sample_curve.parent = frame_branch_gen
    sample_curve.location = (-100, 200)
    sample_curve.mode = 'FACTOR'

    # Random value for spawn positions
    random_value = nodes.new('FunctionNodeRandomValue')
    random_value.parent = frame_branch_gen
    random_value.location = (-300, 200)
    random_value.data_type = 'FLOAT'
    random_value.inputs['Min'].default_value = 0.2  # Avoid root
    random_value.inputs['Max'].default_value = 0.8  # Avoid tip

    # ===== GROWTH DIRECTION CALCULATION =====
    # Normal node (parent curve direction)
    normal_node = nodes.new('GeometryNodeInputNormal')
    normal_node.parent = frame_growth
    normal_node.location = (-100, -100)

    # Random Vector for variation
    random_vector = nodes.new('FunctionNodeRandomValue')
    random_vector.parent = frame_growth
    random_vector.location = (-100, -250)
    random_vector.data_type = 'FLOAT_VECTOR'
    random_vector.inputs['Min'].default_value = (-1, -1, -1)
    random_vector.inputs['Max'].default_value = (1, 1, 1)

    # Mix vectors (blend normal + random)
    mix_vector = nodes.new('ShaderNodeMix')
    mix_vector.parent = frame_growth
    mix_vector.location = (100, -150)
    mix_vector.data_type = 'VECTOR'
    mix_vector.inputs['Factor'].default_value = 0.3  # 30% random

    # Normalize final direction
    normalize_vector = nodes.new('ShaderNodeVectorMath')
    normalize_vector.parent = frame_growth
    normalize_vector.location = (250, -150)
    normalize_vector.operation = 'NORMALIZE'

    # ===== CURVE CREATION =====
    # Curve Line (creates new branch segment)
    curve_line = nodes.new('GeometryNodeCurveLine')
    curve_line.parent = frame_branch_gen
    curve_line.location = (0, 0)
    curve_line.mode = 'DIRECTION'

    # Vector Math for branch length
    scale_direction = nodes.new('ShaderNodeVectorMath')
    scale_direction.parent = frame_branch_gen
    scale_direction.location = (0, -200)
    scale_direction.operation = 'SCALE'

    # Join geometry (add new branches to existing)
    join_geometry = nodes.new('GeometryNodeJoinGeometry')
    join_geometry.parent = frame_branch_gen
    join_geometry.location = (150, 50)

    # ===== GEOMETRY BUILDER FRAME =====
    # Set Curve Radius (for thickness)
    set_radius = nodes.new('GeometryNodeSetCurveRadius')
    set_radius.parent = frame_geometry
    set_radius.location = (500, 200)

    # Named Attribute for thickness
    named_attr_thickness = nodes.new('GeometryNodeInputNamedAttribute')
    named_attr_thickness.parent = frame_geometry
    named_attr_thickness.location = (300, 150)
    named_attr_thickness.data_type = 'FLOAT'
    named_attr_thickness.inputs['Name'].default_value = 'branch_thickness'

    # Curve Circle (profile for mesh)
    curve_circle = nodes.new('GeometryNodeCurvePrimitiveCircle')
    curve_circle.parent = frame_geometry
    curve_circle.location = (500, 50)
    curve_circle.mode = 'RADIUS'
    curve_circle.inputs['Resolution'].default_value = 8
    curve_circle.inputs['Radius'].default_value = 1.0

    # Curve to Mesh
    curve_to_mesh = nodes.new('GeometryNodeCurveToMesh')
    curve_to_mesh.parent = frame_geometry
    curve_to_mesh.location = (700, 150)
    curve_to_mesh.inputs['Fill Caps'].default_value = True

    # Set Shade Smooth
    set_shade_smooth = nodes.new('GeometryNodeSetShadeSmooth')
    set_shade_smooth.parent = frame_geometry
    set_shade_smooth.location = (900, 150)
    set_shade_smooth.inputs['Shade Smooth'].default_value = True

    # ===== CREATE LINKS =====

    # Input processing chain
    links.new(group_input.outputs['Geometry'], mesh_to_curve.inputs['Mesh'])
    links.new(mesh_to_curve.outputs['Curve'], resample_curve.inputs['Curve'])
    links.new(resample_curve.outputs['Curve'], set_curve_normal.inputs['Curve'])

    # Attribute initialization
    links.new(set_curve_normal.outputs['Curve'], store_iteration.inputs['Geometry'])
    links.new(store_iteration.outputs['Geometry'], store_branch_id.inputs['Geometry'])
    links.new(index_node.outputs['Index'], store_branch_id.inputs['Value'])
    links.new(store_branch_id.outputs['Geometry'], store_thickness.inputs['Geometry'])
    links.new(store_thickness.outputs['Geometry'], store_curve_param.inputs['Geometry'])
    links.new(spline_param.outputs['Factor'], store_curve_param.inputs['Value'])

    # Into repeat zone
    links.new(store_curve_param.outputs['Geometry'], repeat_input.inputs['Geometry'])

    # Branch generation (simplified for Phase 1)
    links.new(repeat_input.outputs['Geometry'], sample_curve.inputs['Curve'])
    links.new(random_value.outputs['Value'], sample_curve.inputs['Factor'])

    # Growth direction
    links.new(normal_node.outputs['Normal'], mix_vector.inputs['A'])
    links.new(random_vector.outputs['Value'], mix_vector.inputs['B'])
    links.new(mix_vector.outputs['Result'], normalize_vector.inputs['Vector'])

    # Create branch curve
    links.new(sample_curve.outputs['Position'], curve_line.inputs['Start'])
    links.new(normalize_vector.outputs['Vector'], scale_direction.inputs['Vector'])
    links.new(scale_direction.outputs['Vector'], curve_line.inputs['Direction'])

    # Join with existing geometry
    links.new(repeat_input.outputs['Geometry'], join_geometry.inputs['Geometry'])
    links.new(curve_line.outputs['Curve'], join_geometry.inputs['Geometry'])

    # Out of repeat zone
    links.new(join_geometry.outputs['Geometry'], repeat_output.inputs['Geometry'])

    # Geometry building
    links.new(repeat_output.outputs['Geometry'], set_radius.inputs['Curve'])
    links.new(named_attr_thickness.outputs['Attribute'], set_radius.inputs['Radius'])
    links.new(set_radius.outputs['Curve'], curve_to_mesh.inputs['Curve'])
    links.new(curve_circle.outputs['Curve'], curve_to_mesh.inputs['Profile Curve'])
    links.new(curve_to_mesh.outputs['Mesh'], set_shade_smooth.inputs['Geometry'])

    # Final output
    links.new(set_shade_smooth.outputs['Geometry'], group_output.inputs['Geometry'])

    # ===== ADD INPUT SOCKETS TO GROUP =====
    inputs = node_group.interface.items_tree

    # Clear existing inputs/outputs
    for item in list(inputs):
        node_group.interface.remove(item)

    # Add geometry input
    geo_in = node_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')

    # Main Branch Settings
    node_group.interface.new_socket(name='Base Thickness', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Base Thickness'].default_value = 0.1
    node_group.inputs['Base Thickness'].min_value = 0.01
    node_group.inputs['Base Thickness'].max_value = 2.0

    node_group.interface.new_socket(name='Branch Length', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Branch Length'].default_value = 1.0
    node_group.inputs['Branch Length'].min_value = 0.1
    node_group.inputs['Branch Length'].max_value = 10.0

    node_group.interface.new_socket(name='Iterations', in_out='INPUT', socket_type='NodeSocketInt')
    node_group.inputs['Iterations'].default_value = 2
    node_group.inputs['Iterations'].min_value = 0
    node_group.inputs['Iterations'].max_value = 10

    node_group.interface.new_socket(name='Random Seed', in_out='INPUT', socket_type='NodeSocketInt')
    node_group.inputs['Random Seed'].default_value = 0
    node_group.inputs['Random Seed'].min_value = 0
    node_group.inputs['Random Seed'].max_value = 999999

    node_group.interface.new_socket(name='Angular Spread', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Angular Spread'].default_value = 0.3
    node_group.inputs['Angular Spread'].min_value = 0.0
    node_group.inputs['Angular Spread'].max_value = 1.0

    # Add geometry output
    node_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # ===== CONNECT INPUT PARAMETERS =====
    links.new(group_input.outputs['Base Thickness'], store_thickness.inputs['Value'])
    links.new(group_input.outputs['Branch Length'], scale_direction.inputs['Scale'])
    links.new(group_input.outputs['Iterations'], repeat_input.inputs['Iterations'])
    links.new(group_input.outputs['Random Seed'], random_value.inputs['Seed'])
    links.new(group_input.outputs['Random Seed'], random_vector.inputs['Seed'])
    links.new(group_input.outputs['Angular Spread'], mix_vector.inputs['Factor'])

    # Position frames nicely
    frame_input.location = (-1000, 0)
    frame_attributes.location = (-600, 0)
    frame_branch_gen.location = (0, 0)
    frame_growth.location = (0, -300)
    frame_geometry.location = (600, 0)

    print("✓ Procedural Tree Generator setup complete!")
    print(f"✓ Modifier created: {modifier.name}")
    print(f"✓ Node group: {node_group.name}")
    print("\nUSAGE:")
    print("1. Adjust parameters in the modifier panel")
    print("2. 'Base Thickness' controls trunk radius")
    print("3. 'Branch Length' controls how long branches grow")
    print("4. 'Iterations' controls recursion depth (0-10)")
    print("5. 'Random Seed' for variation")
    print("6. 'Angular Spread' for randomness (0=straight, 1=chaotic)")

    return modifier

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    print("\n" + "="*60)
    print("PROCEDURAL TREE GENERATOR - SETUP SCRIPT")
    print("Phase 1: Core Branch Generation (MVP)")
    print("="*60 + "\n")

    modifier = setup_tree_generator()

    if modifier:
        print("\n" + "="*60)
        print("SUCCESS! Tree generator is ready.")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("FAILED! Check error messages above.")
        print("="*60 + "\n")
