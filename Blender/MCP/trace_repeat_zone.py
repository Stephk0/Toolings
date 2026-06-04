"""
Trace all nodes inside the Repeat Zone using graph traversal.
This identifies which nodes are encapsulated within the flow control structure.
"""

import json
from collections import deque
from typing import Dict, List, Set

def load_node_data(filepath: str) -> List[Dict]:
    """Load node data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def build_adjacency_lists(nodes: List[Dict]) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Build forward and backward adjacency lists for graph traversal.
    Returns: (forward_graph, backward_graph)
    """
    forward = {node['name']: [] for node in nodes}
    backward = {node['name']: [] for node in nodes}

    for node in nodes:
        # Forward edges (this node outputs to...)
        for output_conn in node['outputs']:
            to_node = output_conn['to_node']
            forward[node['name']].append(to_node)
            backward[to_node].append(node['name'])

    return forward, backward

def trace_repeat_zone_contents(
    nodes: List[Dict],
    repeat_input_name: str,
    repeat_output_name: str
) -> Dict[str, any]:
    """
    Trace all nodes that are inside the repeat zone.

    Strategy:
    1. Forward pass: Find all nodes reachable from Repeat Input outputs
    2. Backward pass: Find all nodes that can reach Repeat Output inputs
    3. Intersection: Nodes in both sets are inside the zone
    4. Include the repeat input/output themselves
    """

    forward_graph, backward_graph = build_adjacency_lists(nodes)

    # Forward BFS from Repeat Input
    forward_reachable = set()
    queue = deque()

    # Start from all immediate outputs of Repeat Input
    for output_conn in next(n for n in nodes if n['name'] == repeat_input_name)['outputs']:
        queue.append(output_conn['to_node'])

    while queue:
        current = queue.popleft()
        if current == repeat_output_name:
            continue  # Stop at repeat output
        if current in forward_reachable:
            continue

        forward_reachable.add(current)

        # Add neighbors
        for neighbor in forward_graph[current]:
            if neighbor not in forward_reachable and neighbor != repeat_output_name:
                queue.append(neighbor)

    # Backward BFS from Repeat Output
    backward_reachable = set()
    queue = deque()

    # Start from all immediate inputs to Repeat Output
    for input_conn in next(n for n in nodes if n['name'] == repeat_output_name)['inputs']:
        queue.append(input_conn['from_node'])

    while queue:
        current = queue.popleft()
        if current == repeat_input_name:
            continue  # Stop at repeat input
        if current in backward_reachable:
            continue

        backward_reachable.add(current)

        # Add neighbors
        for neighbor in backward_graph[current]:
            if neighbor not in backward_reachable and neighbor != repeat_input_name:
                queue.append(neighbor)

    # Nodes inside zone: intersection + the repeat nodes themselves
    inside_zone = forward_reachable & backward_reachable
    inside_zone.add(repeat_input_name)
    inside_zone.add(repeat_output_name)

    # Also include any nodes that only connect within the zone
    # (e.g., helper nodes that don't directly touch repeat input/output)
    # This is a heuristic: if a node only connects to zone nodes, it's probably inside
    extended_zone = inside_zone.copy()
    for node in nodes:
        if node['name'] in extended_zone:
            continue

        # Check if all connections are to zone nodes
        all_outputs_to_zone = all(
            conn['to_node'] in extended_zone
            for conn in node['outputs']
        ) if node['outputs'] else False

        all_inputs_from_zone = all(
            conn['from_node'] in extended_zone
            for conn in node['inputs']
        ) if node['inputs'] else False

        if all_outputs_to_zone and all_inputs_from_zone and (node['outputs'] or node['inputs']):
            extended_zone.add(node['name'])

    return {
        'inside_zone': sorted(list(extended_zone)),
        'outside_zone': sorted([n['name'] for n in nodes if n['name'] not in extended_zone]),
        'forward_reachable': sorted(list(forward_reachable)),
        'backward_reachable': sorted(list(backward_reachable)),
        'zone_input': repeat_input_name,
        'zone_output': repeat_output_name
    }

def categorize_zone_nodes(nodes: List[Dict], zone_nodes: List[str]) -> Dict[str, List[str]]:
    """Categorize nodes inside the zone by their functional role."""
    categories = {
        'iteration_control': [],
        'attribute_setup': [],
        'point_generation': [],
        'random_generation': [],
        'geometry_creation': [],
        'math_operations': [],
        'other': []
    }

    for node in nodes:
        if node['name'] not in zone_nodes:
            continue

        node_type = node['type']
        node_name = node['name']

        if node_type in ['REPEAT_INPUT', 'REPEAT_OUTPUT']:
            categories['iteration_control'].append(node_name)
        elif 'ATTRIBUTE' in node_type:
            categories['attribute_setup'].append(node_name)
        elif 'POINTS' in node_type or 'CURVE_TO_POINTS' in node_type:
            categories['point_generation'].append(node_name)
        elif 'RANDOM' in node_type:
            categories['random_generation'].append(node_name)
        elif 'INSTANCE' in node_type or 'JOIN' in node_type or 'CURVE_TO_MESH' in node_type:
            categories['geometry_creation'].append(node_name)
        elif node_type in ['MATH', 'VECT_MATH', 'BOOLEAN_MATH', 'COMPARE']:
            categories['math_operations'].append(node_name)
        else:
            categories['other'].append(node_name)

    return {k: v for k, v in categories.items() if v}

def main():
    filepath = r"D:\Stephko_Tooling\Toolings\Blender\MCP\tree_generator_nodes_data.json"
    nodes = load_node_data(filepath)

    repeat_input = "Repeat Input.001"
    repeat_output = "Repeat Output.001"

    print("=" * 80)
    print("REPEAT ZONE CONNECTIVITY TRACE")
    print("=" * 80)

    result = trace_repeat_zone_contents(nodes, repeat_input, repeat_output)

    print(f"\nRepeat Zone: {repeat_input} -> {repeat_output}")
    print(f"Nodes inside zone: {len(result['inside_zone'])}")
    print(f"Nodes outside zone: {len(result['outside_zone'])}")

    print(f"\nForward reachable from input: {len(result['forward_reachable'])}")
    print(f"Backward reachable to output: {len(result['backward_reachable'])}")

    print("\n" + "=" * 80)
    print("NODES INSIDE REPEAT ZONE")
    print("=" * 80)

    # Categorize zone nodes
    categories = categorize_zone_nodes(nodes, result['inside_zone'])
    for category, node_names in categories.items():
        print(f"\n{category.upper().replace('_', ' ')} ({len(node_names)} nodes):")
        for name in node_names:
            node_data = next(n for n in nodes if n['name'] == name)
            print(f"  - {name:40s} [{node_data['type']}]")

    print("\n" + "=" * 80)
    print("NODES OUTSIDE REPEAT ZONE")
    print("=" * 80)

    outside_categories = categorize_zone_nodes(nodes, result['outside_zone'])
    for category, node_names in outside_categories.items():
        print(f"\n{category.upper().replace('_', ' ')} ({len(node_names)} nodes):")
        for name in node_names[:10]:  # Limit output
            node_data = next(n for n in nodes if n['name'] == name)
            print(f"  - {name:40s} [{node_data['type']}]")
        if len(node_names) > 10:
            print(f"  ... and {len(node_names) - 10} more")

    # Save result
    output_path = r"D:\Stephko_Tooling\Toolings\Blender\MCP\repeat_zone_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n\nAnalysis saved to: {output_path}")

if __name__ == "__main__":
    main()
