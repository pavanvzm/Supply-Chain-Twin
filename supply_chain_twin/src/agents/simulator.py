"""Simulator Agent - Runs Monte Carlo simulations on the Digital Twin graph."""

import random
import numpy as np
from typing import Dict, Any, List
from src.models import (
    CascadeRiskReport, 
    SeverityLevel, 
    AgentState, 
    DisruptionEvent
)
from src.digital_twin import (
    create_supply_chain_graph,
    remove_node_safely,
    get_alternative_routes,
    calculate_path_metrics,
    serialize_graph,
)


# Simulation constants
DEFAULT_SIMULATION_COUNT = 1000
EDGE_VARIANCE_FACTOR = 0.25  # 25% variance in edge weights
DELAY_PROBABILITY = 0.3  # 30% chance of additional delay per simulation


def add_random_variance(
    base_value: float, 
    variance_factor: float = EDGE_VARIANCE_FACTOR
) -> float:
    """
    Add random variance to a value using normal distribution.
    
    Args:
        base_value: Original value
        variance_factor: Standard deviation as fraction of base value
        
    Returns:
        Value with added variance (minimum 0)
    """
    std_dev = base_value * variance_factor
    variance = np.random.normal(0, std_dev)
    return max(0, base_value + variance)


def run_single_simulation(
    graph: Any,
    source: str,
    target: str,
    excluded_nodes: List[str]
) -> Dict[str, Any]:
    """
    Run a single Monte Carlo simulation iteration.
    
    Adds random variance to edge weights and calculates route metrics.
    
    Args:
        graph: Supply chain graph
        source: Starting node
        target: Destination node
        excluded_nodes: Nodes to exclude (blocked)
        
    Returns:
        Dictionary with simulation results
    """
    # Get alternative routes
    routes = get_alternative_routes(graph, source, target, excluded_nodes)
    
    if not routes:
        return {
            "success": False,
            "route": None,
            "time_days": float('inf'),
            "cost_usd": float('inf'),
            "carbon_tons": float('inf'),
            "delay_days": 0,
        }
    
    # Select best route (first is fastest)
    best_route, base_metrics = routes[0]
    
    # Add variance to metrics
    simulated_time = add_random_variance(base_metrics["total_time_days"])
    simulated_cost = add_random_variance(base_metrics["total_cost_usd"])
    simulated_carbon = add_random_variance(base_metrics["total_carbon_tons"])
    
    # Add potential cascade delays
    delay_days = 0
    if random.random() < DELAY_PROBABILITY:
        # Random delay between 1-7 days
        delay_days = random.uniform(1, 7)
        simulated_time += delay_days
    
    return {
        "success": True,
        "route": best_route,
        "time_days": simulated_time,
        "cost_usd": simulated_cost,
        "carbon_tons": simulated_carbon,
        "delay_days": delay_days,
    }


def analyze_cascade_risks(
    simulation_results: List[Dict[str, Any]],
    affected_nodes: List[str]
) -> Dict[str, Any]:
    """
    Analyze simulation results for cascade risks.
    
    Args:
        simulation_results: List of simulation result dictionaries
        affected_nodes: Originally affected nodes
        
    Returns:
        Risk analysis dictionary
    """
    successful_sims = [r for r in simulation_results if r["success"]]
    
    if not successful_sims:
        return {
            "risk_level": SeverityLevel.CRITICAL,
            "avg_delay": float('inf'),
            "max_delay": float('inf'),
            "delay_probability": 1.0,
        }
    
    # Calculate statistics
    delays = [r["delay_days"] for r in successful_sims]
    times = [r["time_days"] for r in successful_sims]
    
    avg_delay = np.mean(delays) if delays else 0
    max_delay = np.max(delays) if delays else 0
    delay_count = sum(1 for d in delays if d > 0)
    delay_probability = delay_count / len(successful_sims) if successful_sims else 0
    
    # Determine risk level based on delay probability and magnitude
    if delay_probability > 0.5 or avg_delay > 5:
        risk_level = SeverityLevel.CRITICAL
    elif delay_probability > 0.3 or avg_delay > 3:
        risk_level = SeverityLevel.HIGH
    elif delay_probability > 0.1 or avg_delay > 1:
        risk_level = SeverityLevel.MEDIUM
    else:
        risk_level = SeverityLevel.LOW
    
    return {
        "risk_level": risk_level,
        "avg_delay": avg_delay,
        "max_delay": max_delay,
        "delay_probability": delay_probability,
        "avg_time": np.mean(times),
        "std_time": np.std(times),
    }


def generate_recommendation(
    risk_analysis: Dict[str, Any],
    alternative_paths: List[List[str]]
) -> str:
    """
    Generate recommended action based on risk analysis.
    
    Args:
        risk_analysis: Risk analysis results
        alternative_paths: Available alternative paths
        
    Returns:
        Recommendation string
    """
    if not alternative_paths:
        return "No viable alternative routes. Consider delaying shipment."
    
    best_path = alternative_paths[0]
    
    if "cape_of_good_hope" in best_path:
        return "Re-route via Cape of Good Hope - longer but avoids blockage"
    elif "panama_canal" in best_path:
        return "Re-route via Panama Canal - moderate time increase"
    elif "los_angeles" in best_path:
        return "Re-route via Los Angeles - transpacific alternative"
    else:
        return f"Use alternative route: {' -> '.join(best_path)}"


def run_monte_carlo_simulation(state: AgentState) -> Dict[str, Any]:
    """
    Run Monte Carlo simulations to predict cascade effects.
    
    This agent:
    1. Gets the disruption event from state
    2. Removes blocked nodes from the graph
    3. Runs 1000+ simulations with random edge variance
    4. Analyzes cascade risks
    5. Generates CascadeRiskReport
    6. Updates state
    
    Args:
        state: Current AgentState with disruption_event
        
    Returns:
        Updated state dictionary
    """
    print("\n[SIMULATOR] Starting Monte Carlo simulation...")
    
    # Get disruption event
    disruption = state.disruption_event
    if not disruption:
        raise ValueError("No disruption event found in state")
    
    print(f"[SIMULATOR] Simulating impact of: {disruption.description}")
    print(f"[SIMULATOR] Running {DEFAULT_SIMULATION_COUNT} simulations...")
    
    # Create graph and remove blocked nodes
    graph = create_supply_chain_graph()
    modified_graph = remove_node_safely(graph, disruption.affected_nodes[0])
    
    # Define source and target for this demo
    source = "shanghai"
    target = "chicago"
    
    # Run simulations
    simulation_results = []
    for i in range(DEFAULT_SIMULATION_COUNT):
        result = run_single_simulation(
            modified_graph,
            source,
            target,
            disruption.affected_nodes
        )
        simulation_results.append(result)
        
        # Progress indicator every 250 simulations
        if (i + 1) % 250 == 0:
            print(f"[SIMULATOR] Completed {i + 1}/{DEFAULT_SIMULATION_COUNT} simulations...")
    
    # Analyze results
    risk_analysis = analyze_cascade_risks(simulation_results, disruption.affected_nodes)
    
    # Get alternative paths
    alternative_routes = get_alternative_routes(
        modified_graph, source, target, disruption.affected_nodes
    )
    alternative_paths = [route[0] for route in alternative_routes[:5]]  # Top 5 alternatives
    
    # Generate recommendation
    recommendation = generate_recommendation(risk_analysis, alternative_paths)
    
    # Calculate confidence score based on simulation consistency
    time_std = risk_analysis.get("std_time", 0)
    time_mean = risk_analysis.get("avg_time", 1)
    cv = time_std / time_mean if time_mean > 0 else 1  # Coefficient of variation
    confidence_score = max(0.5, min(0.99, 1 - cv))  # Higher CV = lower confidence
    
    # Create CascadeRiskReport
    cascade_report = CascadeRiskReport(
        simulation_count=DEFAULT_SIMULATION_COUNT,
        affected_routes=[
            {
                "path": ["shanghai", "suez_canal", "rotterdam", "chicago"],
                "delay_days": risk_analysis["avg_delay"],
                "status": "blocked"
            }
        ],
        cascade_delays={
            "shanghai_chicago_direct": risk_analysis["avg_delay"],
            "alternative_route_delay": risk_analysis["avg_delay"] * 0.3,
        },
        risk_level=risk_analysis["risk_level"],
        recommended_action=recommendation,
        alternative_paths=alternative_paths,
        confidence_score=round(confidence_score, 2),
    )
    
    # Log results
    print(f"\n[SIMULATOR] Simulation complete!")
    print(f"[SIMULATOR] Risk level: {risk_analysis['risk_level'].value.upper()}")
    print(f"[SIMULATOR] Average delay: {risk_analysis['avg_delay']:.2f} days")
    print(f"[SIMULATOR] Recommended action: {recommendation}")
    
    if alternative_paths:
        print(f"[SIMULATOR] Found {len(alternative_paths)} alternative routes")
        print(f"[SIMULATOR] Best alternative: {' -> '.join(alternative_paths[0])}")
    
    # Update state
    new_state = state.model_copy()
    new_state.cascade_report = cascade_report
    new_state.current_step = "optimizer"
    new_state.graph_data = serialize_graph(modified_graph)
    new_state.add_log(f"Completed {DEFAULT_SIMULATION_COUNT} Monte Carlo simulations")
    new_state.add_log(f"Cascade risk level: {risk_analysis['risk_level'].value.upper()}")
    new_state.add_log(f"Recommended: {recommendation}")
    
    return new_state.model_dump()
