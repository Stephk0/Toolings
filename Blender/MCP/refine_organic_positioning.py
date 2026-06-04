"""
Refine organic positioning using force-directed principles.

This creates truly organic layouts with:
1. Natural spacing (non-grid)
2. Connection-aware positioning (connected nodes closer)
3. Cluster compactness
4. Flow-layer constraints (maintain left-to-right progression)
"""

import json
import math
import random
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class Force:
    """Represents a 2D force vector."""
    x: float
    y: float

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self) -> 'Force':
        mag = self.magnitude()
        if mag > 0:
            return Force(self.x / mag, self.y / mag)
        return Force(0, 0)

    def __add__(self, other):
        return Force(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        return Force(self.x * scalar, self.y * scalar)

def load_layout_plan():
    """Load the organic layout plan."""
    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\organic_layout_plan.json", 'r') as f:
        return json.load(f)

def load_node_data():
    """Load node data."""
    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\tree_generator_nodes_data.json", 'r') as f:
        return json.load(f)

def load_flow_analysis():
    """Load connection flow analysis."""
    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\connection_flow_analysis.json", 'r') as f:
        return json.load(f)

def initialize_cluster_positions(layout_plan: Dict, nodes_data: List[Dict]) -> Dict[str, Tuple[float, float]]:
    """
    Initialize node positions within clusters using organic placement.
    """
    positions = {}

    for cluster_info in layout_plan['clusters']:
        cluster_nodes = cluster_info['nodes']
        cluster_center = tuple(cluster_info['center'])
        cluster_id = cluster_info['id']

        # Use spiral placement for organic feel
        positions.update(
            spiral_placement(cluster_nodes, cluster_center, base_radius=80, spacing=150)
        )

    return positions

def spiral_placement(nodes: List[str], center: Tuple[float, float],
                     base_radius: float = 80, spacing: float = 150) -> Dict[str, Tuple[float, float]]:
    """
    Place nodes in an organic spiral pattern around center.
    Creates natural, non-grid appearance.
    """
    positions = {}
    angle_step = math.pi * (3 - math.sqrt(5))  # Golden angle for natural distribution

    for i, node in enumerate(nodes):
        # Fibonacci spiral
        angle = i * angle_step
        radius = base_radius + i * spacing / len(nodes)

        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)

        # Add small random jitter for organic feel
        x += random.uniform(-20, 20)
        y += random.uniform(-20, 20)

        positions[node] = (x, y)

    return positions

def apply_force_directed_refinement(
    positions: Dict[str, Tuple[float, float]],
    connections: List[Dict],
    layout_plan: Dict,
    iterations: int = 50
) -> Dict[str, Tuple[float, float]]:
    """
    Refine positions using force-directed algorithm with layer constraints.

    Forces:
    1. Attraction: connected nodes pull together
    2. Repulsion: all nodes push apart (prevent overlap)
    3. Layer constraint: nodes stay within their flow layer
    4. Cluster cohesion: nodes within clusters stay close
    """

    print(f"\\nApplying force-directed refinement ({iterations} iterations)...")

    # Build node-to-cluster mapping
    node_to_cluster = {}
    node_to_layer = {}
    for cluster_info in layout_plan['clusters']:
        for node in cluster_info['nodes']:
            node_to_cluster[node] = cluster_info['id']
            node_to_layer[node] = cluster_info['layer']

    # Build connection list
    edges = []
    for conn in connections:
        from_node = conn.get('from_node')
        to_node = conn.get('to_node')
        if from_node and to_node:
            edges.append((from_node, to_node))

    # Simulation parameters
    ATTRACTION_STRENGTH = 0.05
    REPULSION_STRENGTH = 50000
    LAYER_CONSTRAINT_STRENGTH = 0.3
    CLUSTER_COHESION_STRENGTH = 0.02
    DAMPING = 0.8

    velocities = {node: Force(0, 0) for node in positions}

    for iteration in range(iterations):
        forces = {node: Force(0, 0) for node in positions}

        # 1. Attraction force (connected nodes)
        for from_node, to_node in edges:
            if from_node not in positions or to_node not in positions:
                continue

            pos1 = positions[from_node]
            pos2 = positions[to_node]

            dx = pos2[0] - pos1[0]
            dy = pos2[1] - pos1[1]
            distance = math.sqrt(dx**2 + dy**2)

            if distance > 0:
                # Spring force proportional to distance
                force_magnitude = distance * ATTRACTION_STRENGTH
                force_x = (dx / distance) * force_magnitude
                force_y = (dy / distance) * force_magnitude

                forces[from_node] = forces[from_node] + Force(force_x, force_y)
                forces[to_node] = forces[to_node] + Force(-force_x, -force_y)

        # 2. Repulsion force (all pairs - prevent overlap)
        nodes_list = list(positions.keys())
        for i, node1 in enumerate(nodes_list):
            for node2 in nodes_list[i+1:]:
                pos1 = positions[node1]
                pos2 = positions[node2]

                dx = pos2[0] - pos1[0]
                dy = pos2[1] - pos1[1]
                distance = math.sqrt(dx**2 + dy**2)

                if distance > 0 and distance < 500:  # Only repel if close
                    # Inverse square repulsion
                    force_magnitude = REPULSION_STRENGTH / (distance ** 2)
                    force_x = (dx / distance) * force_magnitude
                    force_y = (dy / distance) * force_magnitude

                    forces[node1] = forces[node1] + Force(-force_x, -force_y)
                    forces[node2] = forces[node2] + Force(force_x, force_y)

        # 3. Layer constraint (keep nodes in their flow layer X range)
        layer_width = 1500
        for node, layer in node_to_layer.items():
            if node not in positions:
                continue

            pos = positions[node]
            target_x = layer * layer_width + layer_width / 2

            dx = target_x - pos[0]
            force_x = dx * LAYER_CONSTRAINT_STRENGTH

            forces[node] = forces[node] + Force(force_x, 0)

        # 4. Cluster cohesion (nodes in same cluster attract)
        cluster_positions = {}
        cluster_counts = {}

        for node, cluster_id in node_to_cluster.items():
            if node in positions:
                if cluster_id not in cluster_positions:
                    cluster_positions[cluster_id] = [0, 0]
                    cluster_counts[cluster_id] = 0

                pos = positions[node]
                cluster_positions[cluster_id][0] += pos[0]
                cluster_positions[cluster_id][1] += pos[1]
                cluster_counts[cluster_id] += 1

        # Calculate cluster centers
        cluster_centers = {}
        for cluster_id, pos_sum in cluster_positions.items():
            count = cluster_counts[cluster_id]
            cluster_centers[cluster_id] = (pos_sum[0] / count, pos_sum[1] / count)

        # Apply cohesion force
        for node, cluster_id in node_to_cluster.items():
            if node not in positions or cluster_id not in cluster_centers:
                continue

            pos = positions[node]
            center = cluster_centers[cluster_id]

            dx = center[0] - pos[0]
            dy = center[1] - pos[1]

            force_x = dx * CLUSTER_COHESION_STRENGTH
            force_y = dy * CLUSTER_COHESION_STRENGTH

            forces[node] = forces[node] + Force(force_x, force_y)

        # Update positions with damping
        for node in positions:
            # Update velocity
            velocities[node] = (velocities[node] + forces[node]) * DAMPING

            # Update position
            pos = positions[node]
            new_x = pos[0] + velocities[node].x
            new_y = pos[1] + velocities[node].y

            positions[node] = (new_x, new_y)

        # Print progress every 10 iterations
        if (iteration + 1) % 10 == 0:
            total_force = sum(f.magnitude() for f in forces.values())
            print(f"  Iteration {iteration + 1}/{iterations}: total force = {total_force:.2f}")

    return positions

def main():
    print("=" * 80)
    print("REFINING ORGANIC POSITIONING")
    print("=" * 80)

    # Load data
    layout_plan = load_layout_plan()
    nodes_data = load_node_data()
    flow_analysis = load_flow_analysis()

    print(f"\\nLoaded layout with {len(layout_plan['clusters'])} clusters")

    # Initialize positions with spiral placement
    print("\\nInitializing organic positions...")
    positions = initialize_cluster_positions(layout_plan, nodes_data)
    print(f"Initialized {len(positions)} node positions")

    # Build connection list from node data
    connections = []
    for node in nodes_data:
        for output in node['outputs']:
            connections.append({
                'from_node': node['name'],
                'to_node': output['to_node']
            })

    # Apply force-directed refinement
    refined_positions = apply_force_directed_refinement(
        positions,
        connections,
        layout_plan,
        iterations=50
    )

    # Add reroute nodes to positions
    for reroute_info in layout_plan['reroute_nodes']:
        reroute_name = reroute_info['name']
        reroute_pos = tuple(reroute_info['position'])
        refined_positions[reroute_name] = reroute_pos

    # Calculate final dimensions
    x_coords = [p[0] for p in refined_positions.values()]
    y_coords = [p[1] for p in refined_positions.values()]

    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)

    # Create final layout
    final_layout = {
        'positions': {node: list(pos) for node, pos in refined_positions.items()},
        'clusters': layout_plan['clusters'],
        'reroute_nodes': layout_plan['reroute_nodes'],
        'dimensions': {
            'width': max_x - min_x,
            'height': max_y - min_y,
            'bounds': {
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y
            }
        }
    }

    # Save refined layout
    output_path = r"D:\Stephko_Tooling\Toolings\Blender\MCP\refined_organic_layout.json"
    with open(output_path, 'w') as f:
        json.dump(final_layout, f, indent=2)

    print(f"\\n\\nRefined layout saved to: {output_path}")

    print("\\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Organic positioning complete:")
    print(f"  - {len(refined_positions)} nodes positioned")
    print(f"  - {len(layout_plan['clusters'])} organic clusters")
    print(f"  - {len(layout_plan['reroute_nodes'])} reroute sub-hubs")
    print(f"  - Dimensions: {final_layout['dimensions']['width']:.0f} x {final_layout['dimensions']['height']:.0f}")

if __name__ == "__main__":
    main()
