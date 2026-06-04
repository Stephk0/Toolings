"""
Analyze connection flow and visual complexity in the node network.

This script extends the IS state analysis to include:
1. Connection line paths and lengths
2. Line crossing detection
3. Visual noise metrics
4. Natural clustering based on connectivity
5. Reroute node opportunities

The goal is to identify where connection lines create visual noise
and how to reorganize for cleaner flow.
"""

import json
import math
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class Connection:
    """Represents a connection between two nodes."""
    from_node: str
    from_socket: str
    to_node: str
    to_socket: str

    # Calculated properties
    from_pos: Tuple[float, float] = None
    to_pos: Tuple[float, float] = None
    length: float = 0.0
    angle: float = 0.0  # In radians

    def calculate_geometry(self, node_positions: Dict[str, Tuple[float, float]]):
        """Calculate line geometry."""
        self.from_pos = node_positions.get(self.from_node)
        self.to_pos = node_positions.get(self.to_node)

        if self.from_pos and self.to_pos:
            dx = self.to_pos[0] - self.from_pos[0]
            dy = self.to_pos[1] - self.from_pos[1]
            self.length = math.sqrt(dx**2 + dy**2)
            self.angle = math.atan2(dy, dx)

def load_current_state():
    """Load the current reorganized state."""
    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\tree_generator_nodes_data.json", 'r') as f:
        return json.load(f)

def extract_connections(nodes: List[Dict]) -> List[Connection]:
    """Extract all connections from node data."""
    connections = []

    for node in nodes:
        for output_conn in node['outputs']:
            conn = Connection(
                from_node=node['name'],
                from_socket=output_conn['socket_name'],
                to_node=output_conn['to_node'],
                to_socket=output_conn['to_socket']
            )
            connections.append(conn)

    return connections

def get_node_positions(nodes: List[Dict]) -> Dict[str, Tuple[float, float]]:
    """Get current node positions."""
    return {
        node['name']: (node['location'][0], node['location'][1])
        for node in nodes
    }

def detect_line_crossings(connections: List[Connection]) -> List[Tuple[Connection, Connection]]:
    """
    Detect crossing connection lines using line segment intersection.

    Returns list of (connection1, connection2) pairs that cross.
    """
    crossings = []

    for i, c1 in enumerate(connections):
        if not (c1.from_pos and c1.to_pos):
            continue

        for c2 in connections[i+1:]:
            if not (c2.from_pos and c2.to_pos):
                continue

            # Check if line segments intersect
            if segments_intersect(c1.from_pos, c1.to_pos, c2.from_pos, c2.to_pos):
                crossings.append((c1, c2))

    return crossings

def segments_intersect(p1: Tuple[float, float], p2: Tuple[float, float],
                       p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
    """
    Check if line segment p1-p2 intersects with p3-p4.
    Uses cross product method.
    """
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    # Lines are the same if they share endpoints - not a crossing
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False

    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

def calculate_visual_noise_metrics(connections: List[Connection], crossings: List) -> Dict:
    """Calculate metrics for visual complexity."""

    # Length statistics
    lengths = [c.length for c in connections if c.length > 0]
    avg_length = sum(lengths) / len(lengths) if lengths else 0
    max_length = max(lengths) if lengths else 0

    # Long connections (> 2x average) create visual noise
    long_connections = [c for c in connections if c.length > avg_length * 2]

    # Backwards connections (negative angle, going right-to-left)
    backwards = [c for c in connections if c.angle and abs(c.angle) > math.pi/2]

    # Sharp angle changes (connections with very different angles)
    angle_variance = calculate_angle_variance(connections)

    return {
        'total_connections': len(connections),
        'total_crossings': len(crossings),
        'average_length': avg_length,
        'max_length': max_length,
        'long_connections': len(long_connections),
        'backwards_connections': len(backwards),
        'angle_variance': angle_variance,
        'visual_noise_score': len(crossings) + len(long_connections) * 2 + len(backwards) * 3
    }

def calculate_angle_variance(connections: List[Connection]) -> float:
    """Calculate variance in connection angles."""
    angles = [c.angle for c in connections if c.angle is not None]
    if len(angles) < 2:
        return 0.0

    avg_angle = sum(angles) / len(angles)
    variance = sum((a - avg_angle)**2 for a in angles) / len(angles)
    return variance

def identify_connectivity_clusters(nodes: List[Dict], connections: List[Connection]) -> Dict[str, Set[str]]:
    """
    Identify natural clusters based on strong connectivity.

    Uses a simple heuristic: nodes that share many connections
    should be clustered together.
    """
    # Build adjacency list
    adjacency = defaultdict(set)
    for conn in connections:
        adjacency[conn.from_node].add(conn.to_node)
        adjacency[conn.to_node].add(conn.from_node)

    # Calculate connectivity strength between all pairs
    connectivity_strength = defaultdict(int)
    for node1, neighbors in adjacency.items():
        for node2 in neighbors:
            key = tuple(sorted([node1, node2]))
            connectivity_strength[key] += 1

    # Strong connections (multiple links between same nodes)
    strong_pairs = {k: v for k, v in connectivity_strength.items() if v > 1}

    return {
        'adjacency': {k: list(v) for k, v in adjacency.items()},
        'strong_pairs': strong_pairs,
        'avg_degree': sum(len(v) for v in adjacency.values()) / len(adjacency) if adjacency else 0
    }

def find_reroute_opportunities(connections: List[Connection], crossings: List) -> List[Dict]:
    """
    Identify where reroute nodes would help reduce visual noise.

    Criteria:
    1. Long connections that cross many others
    2. Bundles of parallel connections
    3. Connections that go backwards (right-to-left)
    """
    opportunities = []

    # Find connections involved in many crossings
    crossing_count = defaultdict(int)
    for c1, c2 in crossings:
        crossing_count[id(c1)] += 1
        crossing_count[id(c2)] += 1

    for conn in connections:
        crosses = crossing_count.get(id(conn), 0)

        # High-crossing connections need reroutes
        if crosses > 3:
            opportunities.append({
                'connection': f"{conn.from_node} -> {conn.to_node}",
                'reason': f"Crosses {crosses} other lines",
                'priority': 'high',
                'suggested_reroute_pos': calculate_midpoint(conn.from_pos, conn.to_pos)
            })

        # Very long connections need reroutes
        elif conn.length > 1500:
            opportunities.append({
                'connection': f"{conn.from_node} -> {conn.to_node}",
                'reason': f"Very long ({conn.length:.0f} units)",
                'priority': 'medium',
                'suggested_reroute_pos': calculate_midpoint(conn.from_pos, conn.to_pos)
            })

        # Backwards connections need reroutes
        elif conn.angle and abs(conn.angle) > 2.5:  # ~143 degrees
            opportunities.append({
                'connection': f"{conn.from_node} -> {conn.to_node}",
                'reason': "Backwards flow (right-to-left)",
                'priority': 'high',
                'suggested_reroute_pos': calculate_midpoint(conn.from_pos, conn.to_pos)
            })

    return opportunities

def calculate_midpoint(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float]:
    """Calculate midpoint between two points."""
    if p1 and p2:
        return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    return None

def main():
    print("=" * 80)
    print("CONNECTION FLOW ANALYSIS")
    print("=" * 80)

    # Load current state
    nodes = load_current_state()
    print(f"\nLoaded {len(nodes)} nodes")

    # Extract connections
    connections = extract_connections(nodes)
    print(f"Found {len(connections)} connections")

    # Get node positions and calculate connection geometry
    node_positions = get_node_positions(nodes)
    for conn in connections:
        conn.calculate_geometry(node_positions)

    # Detect line crossings
    print("\nDetecting line crossings...")
    crossings = detect_line_crossings(connections)
    print(f"Found {len(crossings)} line crossings")

    # Calculate visual noise metrics
    print("\n" + "=" * 80)
    print("VISUAL NOISE METRICS")
    print("=" * 80)
    metrics = calculate_visual_noise_metrics(connections, crossings)
    for key, value in metrics.items():
        print(f"{key:30s}: {value}")

    # Identify connectivity clusters
    print("\n" + "=" * 80)
    print("CONNECTIVITY CLUSTERS")
    print("=" * 80)
    clusters = identify_connectivity_clusters(nodes, connections)
    print(f"Average node degree: {clusters['avg_degree']:.2f}")
    print(f"Strong node pairs (>1 connection): {len(clusters['strong_pairs'])}")

    # Find reroute opportunities
    print("\n" + "=" * 80)
    print("REROUTE NODE OPPORTUNITIES")
    print("=" * 80)
    opportunities = find_reroute_opportunities(connections, crossings)

    high_priority = [o for o in opportunities if o['priority'] == 'high']
    medium_priority = [o for o in opportunities if o['priority'] == 'medium']

    print(f"\nHigh priority: {len(high_priority)}")
    for opp in high_priority[:10]:  # Show first 10
        print(f"  - {opp['connection']:50s} | {opp['reason']}")

    print(f"\nMedium priority: {len(medium_priority)}")
    for opp in medium_priority[:10]:  # Show first 10
        print(f"  - {opp['connection']:50s} | {opp['reason']}")

    # Save analysis
    analysis = {
        'metrics': metrics,
        'crossings_sample': [
            {
                'from': f"{c1.from_node} -> {c1.to_node}",
                'crosses': f"{c2.from_node} -> {c2.to_node}"
            }
            for c1, c2 in crossings[:50]  # Sample
        ],
        'clusters': {
            'adjacency': clusters['adjacency'],
            'strong_pairs': [{'nodes': list(k), 'count': v} for k, v in clusters['strong_pairs'].items()],
            'avg_degree': clusters['avg_degree']
        },
        'reroute_opportunities': opportunities
    }

    output_path = r"D:\Stephko_Tooling\Toolings\Blender\MCP\connection_flow_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2)

    print(f"\n\nAnalysis saved to: {output_path}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Visual noise score: {metrics['visual_noise_score']}")
    print(f"  - {metrics['total_crossings']} line crossings")
    print(f"  - {metrics['long_connections']} overly long connections")
    print(f"  - {metrics['backwards_connections']} backwards connections")
    print(f"\nRecommended reroute nodes: {len(opportunities)}")
    print(f"  - {len(high_priority)} high priority")
    print(f"  - {len(medium_priority)} medium priority")

if __name__ == "__main__":
    main()
