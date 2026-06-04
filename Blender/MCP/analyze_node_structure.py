"""
Analyze TreeGenerator node network structure for reorganization.
This script parses the node data and identifies:
- Flow control structures (Repeat Zones)
- Node groupings by type
- Spatial distribution
- Connection patterns
"""

import json
from collections import defaultdict
from typing import Dict, List, Tuple

def load_node_data(filepath: str) -> List[Dict]:
    """Load node data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_node_types(nodes: List[Dict]) -> Dict[str, List[str]]:
    """Group nodes by their type."""
    by_type = defaultdict(list)
    for node in nodes:
        by_type[node['type']].append(node['name'])
    return dict(by_type)

def find_repeat_zones(nodes: List[Dict]) -> Dict[str, Dict]:
    """Identify Repeat Zone structures (input/output pairs)."""
    repeat_zones = {}

    # Find all REPEAT_INPUT nodes
    for node in nodes:
        if node['type'] == 'REPEAT_INPUT':
            zone_id = node['name']
            repeat_zones[zone_id] = {
                'input_node': node['name'],
                'input_location': node['location'],
                'output_node': None,
                'output_location': None,
                'encapsulated_nodes': []
            }

    # Find corresponding REPEAT_OUTPUT nodes
    for node in nodes:
        if node['type'] == 'REPEAT_OUTPUT':
            # Try to match with input based on connections
            for input_conn in node['inputs']:
                from_node_name = input_conn.get('from_node')
                # Check if this connects to a repeat input's outputs
                from_node = next((n for n in nodes if n['name'] == from_node_name), None)
                if from_node and from_node['type'] == 'REPEAT_INPUT':
                    zone_id = from_node['name']
                    if zone_id in repeat_zones:
                        repeat_zones[zone_id]['output_node'] = node['name']
                        repeat_zones[zone_id]['output_location'] = node['location']
                        break

    return repeat_zones

def get_spatial_bounds(nodes: List[Dict]) -> Tuple[float, float, float, float]:
    """Get min/max X and Y coordinates of all nodes."""
    x_coords = [n['location'][0] for n in nodes]
    y_coords = [n['location'][1] for n in nodes]
    return (min(x_coords), max(x_coords), min(y_coords), max(y_coords))

def analyze_connectivity(nodes: List[Dict]) -> Dict[str, Dict]:
    """Analyze node connectivity patterns."""
    connectivity = {}
    for node in nodes:
        connectivity[node['name']] = {
            'inputs_from': [conn['from_node'] for conn in node['inputs']],
            'outputs_to': [conn['to_node'] for conn in node['outputs']],
            'degree_in': len(node['inputs']),
            'degree_out': len(node['outputs'])
        }
    return connectivity

def identify_logical_groups(nodes: List[Dict]) -> Dict[str, List[str]]:
    """
    Identify logical groupings based on:
    - Connection patterns
    - Node types
    - Functional roles
    """
    groups = {
        'inputs': [],
        'outputs': [],
        'attribute_operations': [],
        'math_operations': [],
        'geometry_operations': [],
        'random_generators': [],
        'repeat_zones': [],
        'other': []
    }

    for node in nodes:
        node_type = node['type']

        if node_type == 'GROUP_INPUT':
            groups['inputs'].append(node['name'])
        elif node_type == 'GROUP_OUTPUT':
            groups['outputs'].append(node['name'])
        elif 'ATTRIBUTE' in node_type or 'STORE_NAMED_ATTRIBUTE' in node_type or 'CAPTURE_ATTRIBUTE' in node_type:
            groups['attribute_operations'].append(node['name'])
        elif node_type.startswith('MATH') or 'COMPARE' in node_type or 'BOOLEAN_MATH' in node_type:
            groups['math_operations'].append(node['name'])
        elif 'CURVE' in node_type or 'MESH' in node_type or 'POINTS' in node_type or 'INSTANCE' in node_type:
            groups['geometry_operations'].append(node['name'])
        elif 'RANDOM' in node_type:
            groups['random_generators'].append(node['name'])
        elif node_type in ['REPEAT_INPUT', 'REPEAT_OUTPUT']:
            groups['repeat_zones'].append(node['name'])
        else:
            groups['other'].append(node['name'])

    return {k: v for k, v in groups.items() if v}  # Remove empty groups

def main():
    filepath = r"D:\Stephko_Tooling\Toolings\Blender\MCP\tree_generator_nodes_data.json"
    nodes = load_node_data(filepath)

    print("=" * 80)
    print("TREE GENERATOR NODE NETWORK ANALYSIS")
    print("=" * 80)
    print(f"\nTotal nodes: {len(nodes)}")

    # Node type analysis
    print("\n" + "=" * 80)
    print("NODE TYPES DISTRIBUTION")
    print("=" * 80)
    by_type = analyze_node_types(nodes)
    for node_type, node_names in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{node_type:30s}: {len(node_names):3d} nodes")

    # Repeat zones
    print("\n" + "=" * 80)
    print("REPEAT ZONE STRUCTURES")
    print("=" * 80)
    repeat_zones = find_repeat_zones(nodes)
    for zone_id, zone_data in repeat_zones.items():
        print(f"\nZone: {zone_id}")
        print(f"  Input:  {zone_data['input_node']} at {zone_data['input_location']}")
        print(f"  Output: {zone_data['output_node']} at {zone_data['output_location']}")

    # Spatial bounds
    print("\n" + "=" * 80)
    print("SPATIAL DISTRIBUTION")
    print("=" * 80)
    min_x, max_x, min_y, max_y = get_spatial_bounds(nodes)
    print(f"X range: {min_x:.1f} to {max_x:.1f} (width: {max_x - min_x:.1f})")
    print(f"Y range: {min_y:.1f} to {max_y:.1f} (height: {max_y - min_y:.1f})")

    # Logical groups
    print("\n" + "=" * 80)
    print("LOGICAL GROUPINGS")
    print("=" * 80)
    logical_groups = identify_logical_groups(nodes)
    for group_name, node_names in logical_groups.items():
        print(f"{group_name:25s}: {len(node_names):3d} nodes")

    # Connectivity analysis
    print("\n" + "=" * 80)
    print("CONNECTIVITY PATTERNS")
    print("=" * 80)
    connectivity = analyze_connectivity(nodes)

    # Find highly connected nodes (hubs)
    hubs = [(name, data['degree_in'] + data['degree_out'])
            for name, data in connectivity.items()]
    hubs.sort(key=lambda x: x[1], reverse=True)

    print("\nMost connected nodes (potential organization anchors):")
    for name, degree in hubs[:10]:
        node = next(n for n in nodes if n['name'] == name)
        print(f"  {name:30s} (type: {node['type']:20s}) - degree: {degree}")

if __name__ == "__main__":
    main()
