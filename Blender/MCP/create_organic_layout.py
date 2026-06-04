"""
Create organic layout with connection-aware positioning.

Strategy:
1. Detect natural communities/clusters (5-10 nodes each)
2. Use hierarchical layout for Group Input → reroute hubs → consumers
3. Position clusters to minimize crossings while maintaining flow clarity
4. Insert reroute nodes strategically as sub-hubs

Based on user preferences:
- Hybrid: smaller organic sub-frames
- Duplicate Group Input conceptually via reroutes
- Emphasize logical flow clarity
"""

import json
import math
from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass

@dataclass
class NodeCluster:
    """Represents a cluster of tightly connected nodes."""
    id: int
    nodes: Set[str]
    internal_connections: int
    external_connections: int
    center: Tuple[float, float] = None

    @property
    def density(self):
        """Connection density (higher = tighter cluster)."""
        total = self.internal_connections + self.external_connections
        return self.internal_connections / total if total > 0 else 0

def load_data():
    """Load node data and connection analysis."""
    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\tree_generator_nodes_data.json", 'r') as f:
        nodes = json.load(f)

    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\connection_flow_analysis.json", 'r') as f:
        flow_analysis = json.load(f)

    with open(r"D:\Stephko_Tooling\Toolings\Blender\MCP\reorganization_plan.json", 'r') as f:
        original_plan = json.load(f)

    return nodes, flow_analysis, original_plan

def detect_communities_louvain_simple(adjacency: Dict[str, List[str]], max_cluster_size: int = 10) -> List[NodeCluster]:
    """
    Simplified community detection based on Louvain method.
    Creates clusters of max_cluster_size nodes.
    """
    # Start with each node in its own cluster
    node_to_cluster = {node: i for i, node in enumerate(adjacency.keys())}

    # Build edge list
    edges = []
    for node, neighbors in adjacency.items():
        for neighbor in neighbors:
            edges.append((node, neighbor))

    # Iteratively merge clusters that have strong connections
    changed = True
    iteration = 0

    while changed and iteration < 10:
        changed = False
        iteration += 1

        # For each node, check if moving to neighbor's cluster improves modularity
        for node in list(adjacency.keys()):
            current_cluster = node_to_cluster[node]

            # Find which cluster most neighbors belong to
            neighbor_clusters = defaultdict(int)
            for neighbor in adjacency[node]:
                neighbor_clusters[node_to_cluster[neighbor]] += 1

            if not neighbor_clusters:
                continue

            # Best cluster is the one with most connections
            best_cluster = max(neighbor_clusters.items(), key=lambda x: x[1])[0]

            # Check cluster size constraint
            cluster_sizes = defaultdict(int)
            for n, c in node_to_cluster.items():
                cluster_sizes[c] += 1

            if best_cluster != current_cluster and cluster_sizes[best_cluster] < max_cluster_size:
                node_to_cluster[node] = best_cluster
                changed = True

    # Convert to NodeCluster objects
    clusters_dict = defaultdict(set)
    for node, cluster_id in node_to_cluster.items():
        clusters_dict[cluster_id].add(node)

    clusters = []
    for cluster_id, node_set in clusters_dict.items():
        # Count internal vs external connections
        internal = 0
        external = 0

        for node in node_set:
            for neighbor in adjacency.get(node, []):
                if neighbor in node_set:
                    internal += 1
                else:
                    external += 1

        cluster = NodeCluster(
            id=cluster_id,
            nodes=node_set,
            internal_connections=internal // 2,  # Divide by 2 since we count each edge twice
            external_connections=external
        )
        clusters.append(cluster)

    return clusters

def identify_hub_nodes(flow_analysis: Dict) -> List[str]:
    """
    Identify hub nodes (high degree, many outgoing connections).
    These need special handling with reroute sub-hubs.
    """
    adjacency = flow_analysis['clusters']['adjacency']

    hubs = []
    for node, neighbors in adjacency.items():
        degree = len(neighbors)
        if degree > 5:  # Threshold for "hub"
            hubs.append((node, degree))

    hubs.sort(key=lambda x: x[1], reverse=True)
    return [h[0] for h in hubs]

def plan_reroute_hubs(hub_node: str, consumers: List[str], nodes_data: List[Dict]) -> List[Dict]:
    """
    Plan reroute nodes to act as sub-hubs for a fan-out node.

    Strategy: Create 2-4 reroute nodes that group consumers by proximity/type.
    """
    # Get hub position
    hub_data = next(n for n in nodes_data if n['name'] == hub_node)
    hub_x, hub_y = hub_data['location']

    # Group consumers by their functional category or position
    # For simplicity, divide into 2-4 groups
    num_reroutes = min(4, max(2, len(consumers) // 6))  # 2-4 reroutes

    reroute_plans = []
    consumers_per_reroute = len(consumers) // num_reroutes

    for i in range(num_reroutes):
        start_idx = i * consumers_per_reroute
        end_idx = start_idx + consumers_per_reroute if i < num_reroutes - 1 else len(consumers)

        reroute_consumers = consumers[start_idx:end_idx]

        # Position reroute midway between hub and consumers
        if reroute_consumers:
            consumer_positions = [
                next(n for n in nodes_data if n['name'] == c)['location']
                for c in reroute_consumers
            ]

            avg_consumer_x = sum(p[0] for p in consumer_positions) / len(consumer_positions)
            avg_consumer_y = sum(p[1] for p in consumer_positions) / len(consumer_positions)

            reroute_x = (hub_x + avg_consumer_x) / 2
            reroute_y = (hub_y + avg_consumer_y) / 2

            reroute_plans.append({
                'name': f"Reroute_{hub_node}_{i}",
                'position': (reroute_x, reroute_y),
                'source': hub_node,
                'targets': reroute_consumers,
                'group': i
            })

    return reroute_plans

def create_hierarchical_layout(clusters: List[NodeCluster], hubs: List[str],
                                flow_analysis: Dict, nodes_data: List[Dict]) -> Dict:
    """
    Create hierarchical layout with flow emphasis.

    Layout principles:
    1. Left-to-right flow (inputs left, outputs right)
    2. Clusters arranged to minimize external crossings
    3. Hub nodes with reroute sub-hubs
    4. Organic spacing (non-grid)
    """

    print("\\n" + "=" * 80)
    print("CREATING HIERARCHICAL LAYOUT")
    print("=" * 80)

    # Determine flow layers (topological sort-ish)
    adjacency = flow_analysis['clusters']['adjacency']

    # Calculate flow depth for each node (distance from inputs)
    flow_depth = calculate_flow_depth(adjacency, nodes_data)

    # Organize clusters by their average flow depth
    cluster_depths = []
    for cluster in clusters:
        avg_depth = sum(flow_depth.get(n, 0) for n in cluster.nodes) / len(cluster.nodes)
        cluster_depths.append((cluster, avg_depth))

    cluster_depths.sort(key=lambda x: x[1])

    # Create layout layers
    num_layers = 5  # Maintain 5 major layers for flow clarity
    layer_width = 1500  # Horizontal spacing between layers
    cluster_v_spacing = 300  # Vertical spacing between clusters

    layout = {
        'clusters': [],
        'reroute_nodes': [],
        'dimensions': (num_layers * layer_width, 0)
    }

    # Assign clusters to layers
    clusters_per_layer = len(clusters) // num_layers + 1

    current_y = 0
    for layer_idx in range(num_layers):
        layer_x = layer_idx * layer_width
        layer_y_offset = 0

        start_idx = layer_idx * clusters_per_layer
        end_idx = min(start_idx + clusters_per_layer, len(cluster_depths))

        for cluster, depth in cluster_depths[start_idx:end_idx]:
            # Position cluster
            cluster_center = (layer_x, current_y - layer_y_offset)

            layout['clusters'].append({
                'id': cluster.id,
                'nodes': list(cluster.nodes),
                'center': cluster_center,
                'density': cluster.density,
                'layer': layer_idx
            })

            # Estimate cluster height (rough)
            cluster_height = math.ceil(math.sqrt(len(cluster.nodes))) * 200
            layer_y_offset += cluster_height + cluster_v_spacing

        current_y = min(current_y, -layer_y_offset)

    # Plan reroute hubs for identified hub nodes
    for hub in hubs:
        consumers = adjacency.get(hub, [])
        if len(consumers) > 5:  # Worth creating sub-hubs
            reroute_plans = plan_reroute_hubs(hub, consumers, nodes_data)
            layout['reroute_nodes'].extend(reroute_plans)

    layout['dimensions'] = (num_layers * layer_width, abs(current_y))

    print(f"\\nCreated layout with:")
    print(f"  - {len(layout['clusters'])} clusters")
    print(f"  - {len(layout['reroute_nodes'])} reroute hubs")
    print(f"  - {num_layers} flow layers")
    print(f"  - Dimensions: {layout['dimensions'][0]} x {layout['dimensions'][1]}")

    return layout

def calculate_flow_depth(adjacency: Dict[str, List[str]], nodes_data: List[Dict]) -> Dict[str, int]:
    """
    Calculate flow depth (topological distance from input nodes).
    """
    # Find input nodes (GROUP_INPUT type)
    input_nodes = [n['name'] for n in nodes_data if n['type'] == 'GROUP_INPUT']

    # BFS from input nodes
    depth = {}
    queue = deque([(node, 0) for node in input_nodes])

    while queue:
        node, d = queue.popleft()

        if node in depth:
            depth[node] = min(depth[node], d)  # Take minimum depth
        else:
            depth[node] = d

            # Add neighbors
            for neighbor in adjacency.get(node, []):
                if neighbor not in depth:
                    queue.append((neighbor, d + 1))

    return depth

def main():
    print("=" * 80)
    print("ORGANIC LAYOUT PLANNING")
    print("=" * 80)

    # Load data
    nodes, flow_analysis, original_plan = load_data()
    print(f"\\nLoaded {len(nodes)} nodes")

    # Detect communities
    print("\\n" + "=" * 80)
    print("DETECTING NODE COMMUNITIES")
    print("=" * 80)

    adjacency = flow_analysis['clusters']['adjacency']
    clusters = detect_communities_louvain_simple(adjacency, max_cluster_size=10)

    print(f"\\nDetected {len(clusters)} clusters")
    for cluster in sorted(clusters, key=lambda c: len(c.nodes), reverse=True)[:10]:
        print(f"  Cluster {cluster.id}: {len(cluster.nodes)} nodes, "
              f"density={cluster.density:.2f}, "
              f"internal={cluster.internal_connections}, "
              f"external={cluster.external_connections}")

    # Identify hubs
    print("\\n" + "=" * 80)
    print("IDENTIFYING HUB NODES")
    print("=" * 80)

    hubs = identify_hub_nodes(flow_analysis)
    print(f"\\nFound {len(hubs)} hub nodes:")
    for hub in hubs:
        degree = len(adjacency[hub])
        print(f"  - {hub:40s} (degree: {degree})")

    # Create hierarchical layout
    layout = create_hierarchical_layout(clusters, hubs, flow_analysis, nodes)

    # Save layout plan
    output_path = r"D:\Stephko_Tooling\Toolings\Blender\MCP\organic_layout_plan.json"
    with open(output_path, 'w') as f:
        json.dump(layout, f, indent=2)

    print(f"\\n\\nLayout plan saved to: {output_path}")

    print("\\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Strategy: Hybrid organic sub-frames with reroute sub-hubs")
    print(f"  - {len(clusters)} organic clusters (5-10 nodes each)")
    print(f"  - {len(layout['reroute_nodes'])} reroute sub-hubs for fan-out control")
    print(f"  - 5 horizontal flow layers (left-to-right)")
    print(f"  - Estimated dimensions: {layout['dimensions'][0]:.0f} x {layout['dimensions'][1]:.0f}")

if __name__ == "__main__":
    main()
