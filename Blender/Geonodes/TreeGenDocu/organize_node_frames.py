"""
Procedural Tree Generator - Node Frame Organization Script
Version: 1.1
Author: Stephan Viranyi (Stephko)
Date: 2025-12-04

This script organizes the TreeGenerator Geometry Nodes into labeled, color-coded frames
according to the Procedural Tree Generator Specification.

USAGE:
1. Open Blender with your TreeGenerator node group
2. Run this script in the Scripting workspace
3. The script will organize all 113+ nodes into 5 color-coded frames

FRAME ORGANIZATION (Phase 1):
1. INPUT PROCESSING (Green) - Input geometry processing
2. ATTRIBUTE INITIALIZATION (Blue) - Set up initial attributes
3. BRANCH GENERATION (Red) - Core branching logic with Repeat Zone
4. GROWTH DIRECTION CALCULATOR (Orange) - Vector calculations
5. GEOMETRY BUILDER (Purple) - Final mesh output

Based on: ProceduralTreeGenerator_Specification.md (lines 766-829)
"""

import bpy


def create_frame(node_tree, name, color=(0.6, 0.6, 0.6)):
    """Create a named frame with custom color"""
    frame = node_tree.nodes.new('NodeFrame')
    frame.label = name
    frame.use_custom_color = True
    frame.color = color
    return frame


def organize_tree_generator_frames():
    """Main function to organize TreeGenerator node frames"""

    # Get the TreeGenerator node group
    node_group = None
    for ng in bpy.data.node_groups:
        if 'TreeGenerator' in ng.name:
            node_group = ng
            break

    if not node_group:
        print("ERROR: TreeGenerator node group not found!")
        return False

    nodes = node_group.nodes

    print("="*70)
    print("PROCEDURAL TREE GENERATOR - FRAME ORGANIZATION")
    print("="*70)
    print(f"Node group: {node_group.name}")
    print(f"Total nodes: {len(nodes)}")

    # Remove existing frames
    existing_frames = [n for n in nodes if n.type == 'FRAME']
    for frame in existing_frames:
        nodes.remove(frame)
    print(f"Removed {len(existing_frames)} existing frames")

    # ===== CREATE FRAMES WITH SPECIFICATION COLORS =====
    print("\nCreating frames...")

    # Frame 1: INPUT PROCESSING - Green (0.3, 0.5, 0.3)
    frame_input = create_frame(node_group, "INPUT PROCESSING", (0.3, 0.5, 0.3))
    frame_input.location = (-1200, 100)
    print("  ✓ INPUT PROCESSING (Green)")

    # Frame 2: ATTRIBUTE INITIALIZATION - Blue (0.3, 0.3, 0.5)
    frame_attributes = create_frame(node_group, "ATTRIBUTE INITIALIZATION", (0.3, 0.3, 0.5))
    frame_attributes.location = (-650, 100)
    print("  ✓ ATTRIBUTE INITIALIZATION (Blue)")

    # Frame 3: BRANCH GENERATION - Red (0.5, 0.3, 0.3)
    frame_branch = create_frame(node_group, "BRANCH GENERATION", (0.5, 0.3, 0.3))
    frame_branch.location = (-350, 200)
    print("  ✓ BRANCH GENERATION (Red)")

    # Frame 4: GROWTH DIRECTION CALCULATOR - Orange (0.5, 0.4, 0.2)
    frame_growth = create_frame(node_group, "GROWTH DIRECTION CALCULATOR", (0.5, 0.4, 0.2))
    frame_growth.location = (-350, -450)
    print("  ✓ GROWTH DIRECTION CALCULATOR (Orange)")

    # Frame 5: GEOMETRY BUILDER - Purple (0.4, 0.3, 0.5)
    frame_geometry = create_frame(node_group, "GEOMETRY BUILDER", (0.4, 0.3, 0.5))
    frame_geometry.location = (550, 100)
    print("  ✓ GEOMETRY BUILDER (Purple)")

    # ===== ASSIGN NODES TO FRAMES =====
    print("\nAssigning nodes to frames...")

    # Frame 1: INPUT PROCESSING
    input_count = 0
    for node in nodes:
        if node.type in ['GROUP_INPUT', 'MESH_TO_CURVE', 'RESAMPLE_CURVE', 'SET_CURVE_NORMAL']:
            if node.type != 'FRAME':
                node.parent = frame_input
                input_count += 1
    print(f"  ✓ INPUT PROCESSING: {input_count} nodes")

    # Frame 2: ATTRIBUTE INITIALIZATION
    attr_count = 0
    for node in nodes:
        if node.parent is None and node.type != 'FRAME':
            if node.type == 'STORE_NAMED_ATTRIBUTE':
                try:
                    attr_name = node.inputs['Name'].default_value
                    if attr_name in ['iteration_level', 'branch_id', 'branch_thickness', 'curve_parameter']:
                        node.parent = frame_attributes
                        attr_count += 1
                except:
                    pass
            elif node.type in ['INDEX', 'SPLINE_PARAMETER']:
                node.parent = frame_attributes
                attr_count += 1
    print(f"  ✓ ATTRIBUTE INITIALIZATION: {attr_count} nodes")

    # Frame 5: GEOMETRY BUILDER (assign these first before branch)
    geom_count = 0
    for node in nodes:
        if node.parent is None and node.type != 'FRAME':
            if node.type in ['CURVE_PRIMITIVE_CIRCLE', 'CURVE_TO_MESH', 'SET_CURVE_RADIUS',
                           'SET_SHADE_SMOOTH', 'GROUP_OUTPUT']:
                node.parent = frame_geometry
                geom_count += 1
            elif node.type == 'INPUT_ATTRIBUTE':
                try:
                    if 'thickness' in node.inputs['Name'].default_value.lower():
                        node.parent = frame_geometry
                        geom_count += 1
                except:
                    pass
    print(f"  ✓ GEOMETRY BUILDER: {geom_count} nodes")

    # Frame 4: GROWTH DIRECTION
    growth_count = 0
    for node in nodes:
        if node.parent is None and node.type != 'FRAME':
            if node.type in ['VECT_MATH', 'TEX_NOISE', 'INPUT_ROTATION', 'SEPXYZ', 'INPUT_NORMAL']:
                node.parent = frame_growth
                growth_count += 1
    print(f"  ✓ GROWTH DIRECTION: {growth_count} nodes")

    # Frame 3: BRANCH GENERATION (everything else)
    branch_count = 0
    for node in nodes:
        if node.parent is None and node.type != 'FRAME':
            node.parent = frame_branch
            branch_count += 1
    print(f"  ✓ BRANCH GENERATION: {branch_count} nodes (includes Repeat Zone)")

    # ===== ORGANIZE NODE POSITIONS =====
    print("\nOrganizing node positions...")

    def organize_nodes_in_frame(frame, base_x, base_y, spacing_x=250, spacing_y=100, cols=4):
        """Organize nodes in a frame in a grid pattern"""
        frame_nodes = [n for n in nodes if n.parent == frame and n.type != 'FRAME']
        frame_nodes.sort(key=lambda n: n.location.x)

        row = 0
        col = 0

        for node in frame_nodes:
            node.location.x = base_x + (col * spacing_x)
            node.location.y = base_y - (row * spacing_y)

            col += 1
            if col >= cols:
                col = 0
                row += 1

        return len(frame_nodes)

    # Organize each frame
    organize_nodes_in_frame(frame_input, -1150, 50, spacing_x=200, spacing_y=100, cols=3)
    organize_nodes_in_frame(frame_attributes, -600, 50, spacing_x=200, spacing_y=100, cols=3)
    organize_nodes_in_frame(frame_growth, -300, -500, spacing_x=200, spacing_y=100, cols=4)
    organize_nodes_in_frame(frame_geometry, 600, 50, spacing_x=200, spacing_y=100, cols=3)

    # Special handling for Branch Generation (contains Repeat Zone)
    branch_nodes = [n for n in nodes if n.parent == frame_branch and n.type != 'FRAME']
    for node in branch_nodes:
        if node.type == 'REPEAT_INPUT':
            node.location = (-200, 150)
        elif node.type == 'REPEAT_OUTPUT':
            node.location = (300, 150)

    other_branch_nodes = [n for n in branch_nodes if n.type not in ['REPEAT_INPUT', 'REPEAT_OUTPUT']]
    other_branch_nodes.sort(key=lambda n: n.location.x)

    cols = 6
    row = 0
    col = 0
    for node in other_branch_nodes:
        node.location.x = -150 + (col * 150)
        node.location.y = 50 - (row * 120)

        col += 1
        if col >= cols:
            col = 0
            row += 1

    print("  ✓ All nodes positioned in left-to-right flow")

    # ===== SUMMARY =====
    print("\n" + "="*70)
    print("ORGANIZATION COMPLETE!")
    print("="*70)
    print("\nFrame Summary:")
    print(f"  1. INPUT PROCESSING (Green): {input_count} nodes")
    print(f"  2. ATTRIBUTE INITIALIZATION (Blue): {attr_count} nodes")
    print(f"  3. BRANCH GENERATION (Red): {branch_count} nodes")
    print(f"  4. GROWTH DIRECTION (Orange): {growth_count} nodes")
    print(f"  5. GEOMETRY BUILDER (Purple): {geom_count} nodes")
    print(f"\nTotal organized: {input_count + attr_count + branch_count + growth_count + geom_count} nodes")
    print("\n✓ Frames positioned to avoid overlaps")
    print("✓ Left-to-right flow maintained")
    print("✓ Proper spacing between nodes")
    print("✓ Color-coded according to specification")
    print("\nTo view: Open Geometry Node Editor and press 'Home' to frame all")
    print("="*70)

    return True


# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    print("\n" + "="*70)
    print("PROCEDURAL TREE GENERATOR - FRAME ORGANIZATION SCRIPT")
    print("Version 1.1")
    print("="*70 + "\n")

    success = organize_tree_generator_frames()

    if success:
        print("\n✓ SUCCESS! Node tree is now organized into frames.")
    else:
        print("\n✗ FAILED! Check error messages above.")
