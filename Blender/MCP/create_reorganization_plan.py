"""
Create a reorganization plan for the TreeGenerator node network.

Based on the specification:
- 5 functional frames: Input Processing, Core Attributes, Branch Generation, Growth Direction, Geometry Builder
- Proper left-to-right flow
- Nodes inside Repeat Zone stay together
- Logical grouping with adequate spacing

Node location coordinates:
- node.location = top-left corner
- Bounding box: (x, y) to (x + width, y - height)
- Y increases upward in Blender
"""

import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class NodeBox:
    """Represents a node's bounding box in abstract space."""
    name: str
    type: str
    x: float  # top-left x
    y: float  # top-left y
    width: float
    height: float
    frame: str = None  # Which frame this belongs to

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y - self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y - self.height / 2

    def __repr__(self):
        return f"NodeBox({self.name}, x={self.x:.0f}, y={self.y:.0f}, {self.width:.0f}x{self.height:.0f})"

def load_data():
    """Load all required data files."""
    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\tree_generator_nodes_data.json", 'r') as f:
        nodes = json.load(f)

    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\repeat_zone_analysis.json", 'r') as f:
        zone_analysis = json.load(f)

    return nodes, zone_analysis

def assign_frames_to_nodes(nodes: List[Dict], zone_analysis: Dict) -> Dict[str, str]:
    """
    Assign each node to a functional frame based on the tree generator spec.

    Frames (in left-to-right order):
    1. Input Processing - Group Input, mesh/curve conversion, resampling
    2. Core Attributes - Attribute initialization and setup
    3. Branch Generation - The Repeat Zone for iterative spawning
    4. Growth Direction - Direction calculation, randomness
    5. Geometry Builder - Final geometry creation, output
    """
    frame_assignments = {}
    inside_zone = set(zone_analysis['inside_zone'])

    for node in nodes:
        name = node['name']
        node_type = node['type']

        # Frame 1: Input Processing
        if node_type == 'GROUP_INPUT':
            frame_assignments[name] = "1_Input_Processing"
        elif name == 'Mesh to Curve':
            frame_assignments[name] = "1_Input_Processing"
        elif node_type in ['RESAMPLE_CURVE', 'CURVE_PRIMITIVE_LINE', 'CURVE_PRIMITIVE_CIRCLE',
                          'CURVE_PRIMITIVE_SPIRAL', 'OBJECT_INFO', 'MESH_PRIMITIVE_ICO_SPHERE']:
            if name not in inside_zone:
                frame_assignments[name] = "1_Input_Processing"

        # Frame 3: Branch Generation (everything inside the repeat zone)
        elif name in inside_zone:
            frame_assignments[name] = "3_Branch_Generation"

        # Frame 5: Geometry Builder (output and final geometry operations)
        elif node_type == 'GROUP_OUTPUT':
            frame_assignments[name] = "5_Geometry_Builder"
        elif node_type in ['CURVE_TO_MESH', 'JOIN_GEOMETRY', 'SET_SHADE_SMOOTH', 'MERGE_BY_DISTANCE']:
            if name not in inside_zone:
                frame_assignments[name] = "5_Geometry_Builder"

        # Frame 4: Growth Direction (random, rotation, vector math outside zone)
        elif node_type in ['RANDOM_VALUE', 'INPUT_ROTATION', 'VECT_MATH', 'TEX_NOISE']:
            if name not in inside_zone:
                frame_assignments[name] = "4_Growth_Direction"
        elif 'Random' in name and name not in inside_zone:
            frame_assignments[name] = "4_Growth_Direction"

        # Frame 2: Core Attributes (attribute operations outside zone and setup)
        elif 'ATTRIBUTE' in node_type and name not in inside_zone:
            frame_assignments[name] = "2_Core_Attributes"
        elif node_type in ['SPLINE_PARAMETER', 'POSITION', 'CURVE_ENDPOINT_SELECTION']:
            frame_assignments[name] = "2_Core_Attributes"

        # Default: try to infer from connections or type
        elif node_type in ['MATH', 'COMPARE', 'BOOLEAN_MATH', 'CLAMP', 'SWITCH']:
            # Math nodes - try to place based on what they connect to
            # For now, default to Core Attributes if outside zone
            if name not in inside_zone:
                frame_assignments[name] = "2_Core_Attributes"

        # Catch-all for unassigned nodes
        if name not in frame_assignments:
            # Use heuristics based on connections
            # For now, place in appropriate frame based on type
            if 'Easing' in name or 'GROUP' in node_type:
                frame_assignments[name] = "2_Core_Attributes"
            elif 'Viewer' in name or node_type == 'VIEWER':
                frame_assignments[name] = "5_Geometry_Builder"
            elif node_type == 'REROUTE':
                frame_assignments[name] = "2_Core_Attributes"  # Will be positioned based on connections
            elif 'SEPXYZ' in node_type or 'SAMPLE' in node_type:
                frame_assignments[name] = "2_Core_Attributes"
            else:
                frame_assignments[name] = "2_Core_Attributes"  # Default

    return frame_assignments

def calculate_frame_layout(
    nodes: List[Dict],
    frame_assignments: Dict[str, str],
    zone_analysis: Dict
) -> Dict[str, Dict]:
    """
    Calculate the ideal layout for each frame using column-based packing.

    Returns a dict with frame names as keys and layout info as values.
    """

    # Group nodes by frame
    nodes_by_frame = defaultdict(list)
    for node in nodes:
        frame = frame_assignments.get(node['name'], "2_Core_Attributes")
        nodes_by_frame[frame].append(node)

    # Layout parameters
    FRAME_PADDING = 100  # Padding inside frame
    FRAME_GAP = 400  # Gap between frames
    NODE_HORIZONTAL_SPACING = 200  # Space between nodes horizontally
    NODE_VERTICAL_SPACING = 150  # Space between nodes vertically
    COLUMN_MAX_HEIGHT = 2000  # Max height of a column before starting new one

    frame_layouts = {}
    current_frame_x = 0

    # Process frames in order
    for frame_name in sorted(nodes_by_frame.keys()):
        frame_nodes = nodes_by_frame[frame_name]

        print(f"\n{frame_name}: {len(frame_nodes)} nodes")

        # Pack nodes into columns
        columns = []
        current_column = []
        current_column_height = 0
        current_column_max_width = 0

        # Sort nodes by type for better grouping
        sorted_nodes = sorted(frame_nodes, key=lambda n: (n['type'], n['name']))

        for node in sorted_nodes:
            node_height = node['height']
            node_width = node['width']

            # Check if we need a new column
            if current_column_height + node_height + NODE_VERTICAL_SPACING > COLUMN_MAX_HEIGHT and current_column:
                # Save current column
                columns.append({
                    'nodes': current_column,
                    'height': current_column_height,
                    'width': current_column_max_width
                })
                # Start new column
                current_column = []
                current_column_height = 0
                current_column_max_width = 0

            # Add node to current column
            current_column.append(node)
            current_column_height += node_height + NODE_VERTICAL_SPACING
            current_column_max_width = max(current_column_max_width, node_width)

        # Don't forget the last column
        if current_column:
            columns.append({
                'nodes': current_column,
                'height': current_column_height,
                'width': current_column_max_width
            })

        # Calculate frame dimensions
        frame_width = sum(col['width'] + NODE_HORIZONTAL_SPACING for col in columns)
        frame_width -= NODE_HORIZONTAL_SPACING  # Remove last spacing
        frame_width += 2 * FRAME_PADDING

        frame_height = max((col['height'] for col in columns), default=500) + 2 * FRAME_PADDING

        frame_layouts[frame_name] = {
            'nodes': [n['name'] for n in frame_nodes],
            'columns': columns,
            'frame_size': (frame_width, frame_height),
            'target_x': current_frame_x,
            'target_y_center': 0,  # Will center frames vertically
            'num_columns': len(columns)
        }

        print(f"  Packed into {len(columns)} columns")
        print(f"  Frame size: {frame_width:.0f} x {frame_height:.0f}")

        # Update x for next frame
        current_frame_x += frame_width + FRAME_GAP

    return frame_layouts

def create_reorganization_plan(
    nodes: List[Dict],
    zone_analysis: Dict
) -> Dict:
    """Create a complete reorganization plan."""

    print("=" * 80)
    print("CREATING REORGANIZATION PLAN")
    print("=" * 80)

    # Step 1: Assign frames
    frame_assignments = assign_frames_to_nodes(nodes, zone_analysis)

    # Count nodes per frame
    frame_counts = defaultdict(int)
    for frame in frame_assignments.values():
        frame_counts[frame] += 1

    print("\nFrame assignments:")
    for frame_name in sorted(frame_counts.keys()):
        print(f"  {frame_name}: {frame_counts[frame_name]} nodes")

    # Step 2: Calculate frame layouts
    frame_layouts = calculate_frame_layout(nodes, frame_assignments, zone_analysis)

    # Step 3: Create detailed positioning plan
    positioning_plan = {
        'frame_assignments': frame_assignments,
        'frame_layouts': frame_layouts,
        'layout_parameters': {
            'frame_padding': 100,
            'frame_gap': 400,
            'node_h_spacing': 200,
            'node_v_spacing': 150,
            'column_max_width': 1500
        }
    }

    return positioning_plan

def main():
    nodes, zone_analysis = load_data()

    plan = create_reorganization_plan(nodes, zone_analysis)

    # Save plan
    output_path = r"D:\Stephko_Tooling\Toolings\Blender\MCP\reorganization_plan.json"
    with open(output_path, 'w') as f:
        json.dump(plan, f, indent=2)

    print(f"\n\nReorganization plan saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("REORGANIZATION SUMMARY")
    print("=" * 80)

    total_width = 0
    for frame_name, layout in sorted(plan['frame_layouts'].items()):
        width = layout['frame_size'][0]
        total_width += width + plan['layout_parameters']['frame_gap']
        print(f"\n{frame_name}:")
        print(f"  Nodes: {len(layout['nodes'])}")
        print(f"  Frame size: {layout['frame_size'][0]:.0f} x {layout['frame_size'][1]:.0f}")
        print(f"  Columns: {layout['num_columns']}")
        print(f"  Target X: {layout['target_x']:.0f}")

    print(f"\n\nCurrent total width: 8760 units")
    print(f"Estimated new total width: {total_width:.0f} units")
    print(f"Reduction: {((8760 - total_width) / 8760 * 100):.1f}%")

if __name__ == "__main__":
    main()
