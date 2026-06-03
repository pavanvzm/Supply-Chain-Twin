"""Main entry point for the Supply Chain Digital Twin workflow."""

import sys
from src.models import AgentState
from src.workflow import create_workflow


def print_final_summary(final_state: dict) -> None:
    """Print a summary of the workflow results."""
    print("\n" + "=" * 60)
    print("=== SUPPLY CHAIN DIGITAL TWIN - FINAL SUMMARY ===")
    print("=" * 60)
    
    # Check if we have a successful negotiation
    negotiation_result = final_state.get("negotiation_result")
    
    if negotiation_result and negotiation_result.get("success"):
        route_plan = negotiation_result.get("route_plan", {})
        
        print("\n✓ ROUTE SUCCESSFULLY CONFIRMED\n")
        print(f"Route Path: {' -> '.join(route_plan.get('route_path', []))}")
        print(f"\nMetrics:")
        print(f"  • Total Time: {route_plan.get('total_time_days', 0):.1f} days")
        print(f"  • Total Cost: ${route_plan.get('total_cost_usd', 0):,.2f}")
        print(f"  • Carbon Footprint: {route_plan.get('total_carbon_tons', 0):.2f} tons")
        print(f"  • Weighted Score: {route_plan.get('weighted_score', 0):.4f}")
        
        carrier_response = negotiation_result.get("carrier_response", {})
        if carrier_response:
            print(f"\nBooking Details:")
            print(f"  • Booking ID: {carrier_response.get('booking_id', 'N/A')}")
            print(f"  • Carrier: {carrier_response.get('carrier', 'N/A')}")
            print(f"  • Vessel: {carrier_response.get('vessel_name', 'N/A')}")
    else:
        print("\n✗ WORKFLOW FAILED TO CONFIRM ROUTE\n")
        if negotiation_result:
            print(f"Failure Reason: {negotiation_result.get('failure_reason', 'Unknown')}")
        print(f"Retry Count: {final_state.get('retry_count', 0)}")
    
    # Print workflow log
    print(f"\nWorkflow Log ({len(final_state.get('workflow_log', []))} entries):")
    for i, log_entry in enumerate(final_state.get("workflow_log", [])[-10:], 1):
        print(f"  {i}. {log_entry}")
    
    print("\n" + "=" * 60)


def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 60)
    print("=== SUPPLY CHAIN DIGITAL TWIN & DISRUPTION FLEET ===")
    print("=" * 60)
    print("\nInitializing multi-agent workflow...")
    print("Agents: Ingestor → Simulator → Optimizer → Negotiator")
    
    try:
        # Create and run workflow
        app = create_workflow()
        initial_state = AgentState().model_dump()
        
        print("\nStarting workflow execution...\n")
        print("-" * 60)
        
        final_state = app.invoke(initial_state)
        
        print("-" * 60)
        
        # Print summary
        print_final_summary(final_state)
        
        # Return appropriate exit code
        negotiation_result = final_state.get("negotiation_result")
        if negotiation_result and negotiation_result.get("success"):
            print("\n✓ Workflow completed successfully!")
            return 0
        else:
            print("\n✗ Workflow completed with failures.")
            return 1
            
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
