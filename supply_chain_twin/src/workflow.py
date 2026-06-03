"""LangGraph workflow definition for the Supply Chain Digital Twin."""

from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from src.models import AgentState
from src.agents.ingestor import ingest_disruption_event
from src.agents.simulator import run_monte_carlo_simulation
from src.agents.optimizer import optimize_route
from src.agents.negotiator import negotiate_with_carrier


def route_after_negotiation(state: AgentState) -> str:
    """
    Determine next step after negotiation.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name or END
    """
    negotiation_result = state.negotiation_result
    
    if not negotiation_result:
        return "optimizer"
    
    if negotiation_result.success:
        return END
    
    current_step = state.current_step
    if current_step == "failed":
        return END
    
    # Route back to optimizer for retry
    return "optimizer"


def create_workflow() -> StateGraph:
    """
    Create the LangGraph StateGraph for the supply chain workflow.
    
    Workflow:
    1. Ingestor: Fetch and classify disruption events
    2. Simulator: Run Monte Carlo simulations
    3. Optimizer: Find optimal alternative route
    4. Negotiator: Book with carrier (with retry loop)
    
    Returns:
        Compiled StateGraph
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("ingestor", ingest_disruption_event)
    workflow.add_node("simulator", run_monte_carlo_simulation)
    workflow.add_node("optimizer", optimize_route)
    workflow.add_node("negotiator", negotiate_with_carrier)
    
    # Set entry point
    workflow.set_entry_point("ingestor")
    
    # Add edges
    workflow.add_edge("ingestor", "simulator")
    workflow.add_edge("simulator", "optimizer")
    workflow.add_edge("optimizer", "negotiator")
    
    # Add conditional edge from negotiator (retry loop)
    workflow.add_conditional_edges(
        "negotiator",
        route_after_negotiation,
        {
            "optimizer": "optimizer",
            END: END,
        }
    )
    
    # Compile the graph
    app = workflow.compile()
    
    return app


def run_workflow(initial_state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run the complete workflow from start to finish.
    
    Args:
        initial_state: Optional initial state dictionary
        
    Returns:
        Final state dictionary
    """
    # Create workflow
    app = create_workflow()
    
    # Initialize state if not provided
    if initial_state is None:
        initial_state = AgentState().model_dump()
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    return final_state
