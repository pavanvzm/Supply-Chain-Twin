"""Digital Twin graph representation using NetworkX."""

import networkx as nx
from typing import Dict, List, Tuple, Any, Optional
from src.models import RouteEdge


def create_supply_chain_graph() -> nx.DiGraph:
    """
    Create a supply chain graph representing global shipping routes.
    
    Primary route: Shanghai -> Suez Canal -> Rotterdam -> Chicago
    Alternative routes via Cape of Good Hope and Panama Canal
    
    Returns:
        nx.DiGraph: Directed graph with weighted edges (time, cost, carbon)
    """
    graph = nx.DiGraph()
    
    # Add nodes (ports and key waypoints)
    nodes = [
        "shanghai",
        "suez_canal",
        "rotterdam",
        "chicago",
        "cape_of_good_hope",
        "panama_canal",
        "los_angeles",
        "singapore",
        "dubai"
    ]
    graph.add_nodes_from(nodes)
    
    # Add edges with attributes: time_days, cost_usd, carbon_tons
    # Primary route through Suez Canal
    edges = [
        # Shanghai to Suez Canal route
        ("shanghai", "singapore", {"time_days": 3.5, "cost_usd": 8000, "carbon_tons": 120}),
        ("singapore", "suez_canal", {"time_days": 9.0, "cost_usd": 18000, "carbon_tons": 340}),
        
        # Suez Canal to Rotterdam
        ("suez_canal", "dubai", {"time_days": 2.0, "cost_usd": 5000, "carbon_tons": 85}),
        ("dubai", "rotterdam", {"time_days": 8.5, "cost_usd": 16000, "carbon_tons": 290}),
        ("suez_canal", "rotterdam", {"time_days": 6.0, "cost_usd": 12000, "carbon_tons": 220}),
        
        # Rotterdam to Chicago (transatlantic + land)
        ("rotterdam", "chicago", {"time_days": 7.0, "cost_usd": 14000, "carbon_tons": 260}),
        
        # Alternative route via Cape of Good Hope
        ("shanghai", "cape_of_good_hope", {"time_days": 18.0, "cost_usd": 32000, "carbon_tons": 580}),
        ("cape_of_good_hope", "rotterdam", {"time_days": 10.0, "cost_usd": 18000, "carbon_tons": 310}),
        
        # Alternative route via Panama Canal
        ("shanghai", "los_angeles", {"time_days": 12.0, "cost_usd": 22000, "carbon_tons": 400}),
        ("los_angeles", "chicago", {"time_days": 3.0, "cost_usd": 6000, "carbon_tons": 95}),
        ("shanghai", "panama_canal", {"time_days": 16.0, "cost_usd": 28000, "carbon_tons": 510}),
        ("panama_canal", "chicago", {"time_days": 5.0, "cost_usd": 10000, "carbon_tons": 170}),
        
        # Additional connectivity for flexibility
        ("singapore", "cape_of_good_hope", {"time_days": 14.0, "cost_usd": 24000, "carbon_tons": 450}),
        ("dubai", "cape_of_good_hope", {"time_days": 8.0, "cost_usd": 14000, "carbon_tons": 260}),
    ]
    
    graph.add_edges_from(edges)
    
    return graph


def get_edge_attributes(graph: nx.DiGraph, source: str, target: str) -> Optional[Dict[str, float]]:
    """Get edge attributes between two nodes."""
    if graph.has_edge(source, target):
        return graph.edges[source, target]
    return None


def remove_node_safely(graph: nx.DiGraph, node: str) -> nx.DiGraph:
    """
    Remove a node from the graph safely, returning a copy.
    
    Args:
        graph: The original graph
        node: Node to remove
        
    Returns:
        nx.DiGraph: New graph with node removed
    """
    graph_copy = graph.copy()
    if node in graph_copy.nodes:
        graph_copy.remove_node(node)
    return graph_copy


def find_all_paths(
    graph: nx.DiGraph, 
    source: str, 
    target: str, 
    cutoff: Optional[int] = None
) -> List[List[str]]:
    """
    Find all simple paths between source and target.
    
    Args:
        graph: The supply chain graph
        source: Starting node
        target: Destination node
        cutoff: Maximum path length
        
    Returns:
        List of paths (each path is a list of nodes)
    """
    try:
        paths = list(nx.all_simple_paths(graph, source=source, target=target, cutoff=cutoff))
        return paths
    except nx.NetworkXNoPath:
        return []


def calculate_path_metrics(
    graph: nx.DiGraph, 
    path: List[str]
) -> Dict[str, float]:
    """
    Calculate total metrics for a given path.
    
    Args:
        graph: The supply chain graph
        path: List of nodes representing the path
        
    Returns:
        Dictionary with total_time_days, total_cost_usd, total_carbon_tons
    """
    total_time = 0.0
    total_cost = 0.0
    total_carbon = 0.0
    
    for i in range(len(path) - 1):
        edge_data = get_edge_attributes(graph, path[i], path[i + 1])
        if edge_data:
            total_time += edge_data.get("time_days", 0)
            total_cost += edge_data.get("cost_usd", 0)
            total_carbon += edge_data.get("carbon_tons", 0)
        else:
            # Edge doesn't exist, return None metrics
            return {
                "total_time_days": float('inf'),
                "total_cost_usd": float('inf'),
                "total_carbon_tons": float('inf')
            }
    
    return {
        "total_time_days": total_time,
        "total_cost_usd": total_cost,
        "total_carbon_tons": total_carbon
    }


def serialize_graph(graph: nx.DiGraph) -> Dict[str, Any]:
    """
    Serialize graph to dictionary format for state storage.
    
    Args:
        graph: NetworkX graph to serialize
        
    Returns:
        Dictionary representation of the graph
    """
    nodes = list(graph.nodes())
    edges = []
    for source, target, data in graph.edges(data=True):
        edges.append({
            "source": source,
            "target": target,
            **data
        })
    
    return {
        "nodes": nodes,
        "edges": edges
    }


def deserialize_graph(data: Dict[str, Any]) -> nx.DiGraph:
    """
    Deserialize graph from dictionary format.
    
    Args:
        data: Dictionary representation of the graph
        
    Returns:
        NetworkX graph
    """
    graph = nx.DiGraph()
    graph.add_nodes_from(data["nodes"])
    for edge in data["edges"]:
        source = edge.pop("source")
        target = edge.pop("target")
        graph.add_edge(source, target, **edge)
    
    return graph


def get_alternative_routes(
    graph: nx.DiGraph,
    source: str,
    target: str,
    excluded_nodes: List[str]
) -> List[Tuple[List[str], Dict[str, float]]]:
    """
    Find alternative routes excluding certain nodes.
    
    Args:
        graph: The supply chain graph
        source: Starting node
        target: Destination node
        excluded_nodes: Nodes to avoid (e.g., blocked ports)
        
    Returns:
        List of tuples (path, metrics) sorted by total time
    """
    # Create graph without excluded nodes
    temp_graph = graph.copy()
    for node in excluded_nodes:
        if node in temp_graph.nodes:
            temp_graph.remove_node(node)
    
    # Find all paths
    paths = find_all_paths(temp_graph, source, target, cutoff=6)
    
    # Calculate metrics for each path
    routes_with_metrics = []
    for path in paths:
        metrics = calculate_path_metrics(temp_graph, path)
        if metrics["total_time_days"] != float('inf'):
            routes_with_metrics.append((path, metrics))
    
    # Sort by total time
    routes_with_metrics.sort(key=lambda x: x[1]["total_time_days"])
    
    return routes_with_metrics
