"""Negotiator Agent - Mocks carrier communications with retry logic."""

import random
from typing import Dict, Any, Optional
from src.models import NegotiationResult, RoutePlan, AgentState


# Negotiation constants
BOOKING_FAILURE_RATE = 0.2  # 20% simulated failure rate
MAX_CARRIER_ATTEMPTS = 3


def mock_carrier_api_call(route_plan: RoutePlan) -> Dict[str, Any]:
    """
    Mock carrier API call for booking.
    
    In production, this would call actual carrier APIs like:
    - Maersk Spot API
    - CMA CGM eBusiness
    - MSC myMSC
    - Freight forwarding platforms
    
    Args:
        route_plan: Route plan to book
        
    Returns:
        Simulated API response
    """
    # Simulate API latency
    # time.sleep(0.2)
    
    # Simulate 20% failure rate
    if random.random() < BOOKING_FAILURE_RATE:
        failure_reasons = [
            "Capacity unavailable on selected dates",
            "Rate exceeded carrier threshold",
            "Equipment shortage at origin port",
            "Schedule conflict with existing bookings",
            "Carrier surcharge not accepted",
        ]
        return {
            "success": False,
            "error_code": "BOOKING_FAILED",
            "message": random.choice(failure_reasons),
            "available_alternatives": random.randint(0, 2),
        }
    
    # Success case
    booking_id = f"BK{random.randint(100000, 999999)}"
    return {
        "success": True,
        "booking_id": booking_id,
        "confirmation_number": f"CNF{random.randint(10000, 99999)}",
        "carrier": random.choice(["MAERSK", "CMA_CGM", "MSC", "COSCO"]),
        "vessel_name": f"MV_{random.choice(['EVERGREEN', 'PACIFIC', 'ATLANTIC', 'GLOBAL'])}_{random.randint(1, 99)}",
        "estimated_departure": "2024-01-20T00:00:00Z",
        "rate_accepted": True,
        "equipment_guaranteed": True,
    }


def should_retry(negotiation_result: NegotiationResult, retry_count: int, max_retries: int) -> bool:
    """
    Determine if negotiation should be retried.
    
    Args:
        negotiation_result: Result from last negotiation attempt
        retry_count: Current retry count
        max_retries: Maximum allowed retries
        
    Returns:
        True if should retry, False otherwise
    """
    if negotiation_result.success:
        return False
    
    if retry_count >= max_retries:
        return False
    
    # Check if carrier has alternatives available
    if negotiation_result.carrier_response:
        available = negotiation_result.carrier_response.get("available_alternatives", 0)
        if available == 0 and retry_count >= 1:
            # No alternatives and already tried once, probably won't succeed
            return False
    
    return True


def negotiate_with_carrier(state: AgentState) -> Dict[str, Any]:
    """
    Negotiate with carriers to book the optimized route.
    
    This agent:
    1. Gets route plan from state
    2. Attempts to book with carrier (mocked API)
    3. Handles success/failure
    4. Implements retry logic with constraint relaxation
    5. Updates state with result
    
    Args:
        state: Current AgentState with route_plan
        
    Returns:
        Updated state dictionary
    """
    print("\n[NEGOTIATOR] Starting carrier negotiation...")
    
    # Get route plan
    route_plan = state.route_plan
    if not route_plan:
        raise ValueError("No route plan found in state")
    
    print(f"[NEGOTIATOR] Attempting to book route: {' -> '.join(route_plan.route_path)}")
    print(f"[NEGOTIATOR] Budget: ${route_plan.total_cost_usd:,.0f} (multiplier: {route_plan.budget_multiplier:.2f}x)")
    print(f"[NEGOTIATOR] Retry attempt: {state.retry_count + 1}")
    
    # Make carrier API call
    carrier_response = mock_carrier_api_call(route_plan)
    
    # Create negotiation result
    if carrier_response["success"]:
        result = NegotiationResult(
            success=True,
            route_plan=route_plan,
            failure_reason=None,
            retry_count=state.retry_count,
            carrier_response=carrier_response,
        )
        
        print(f"\n[NEGOTIATOR] ✓ Booking successful!")
        print(f"[NEGOTIATOR] Booking ID: {carrier_response['booking_id']}")
        print(f"[NEGOTIATOR] Carrier: {carrier_response['carrier']}")
        print(f"[NEGOTIATOR] Vessel: {carrier_response['vessel_name']}")
    else:
        result = NegotiationResult(
            success=False,
            route_plan=route_plan,
            failure_reason=carrier_response.get("message", "Unknown error"),
            retry_count=state.retry_count + 1,
            carrier_response=carrier_response,
        )
        
        print(f"\n[NEGOTIATOR] ✗ Booking failed!")
        print(f"[NEGOTIATOR] Reason: {result.failure_reason}")
        
        # Check if we should retry
        if state.can_retry():
            print(f"[NEGOTIATOR] Will retry with relaxed constraints (+15% budget)")
        else:
            print(f"[NEGOTIATOR] Max retries reached. Cannot retry.")
    
    # Update state
    new_state = state.model_copy()
    new_state.negotiation_result = result
    new_state.add_log(f"Negotiation {'successful' if result.success else 'failed'}: {result.failure_reason or 'OK'}")
    
    if result.success:
        new_state.current_step = "complete"
    elif state.can_retry():
        # Route back to optimizer with relaxed constraints
        new_state.increment_retry()
        new_state.current_step = "optimizer"
        new_state.add_log(f"Retry {new_state.retry_count}: Relaxing budget constraints")
        print(f"\n[NEGOTIATOR] Routing back to OPTIMIZER for re-optimization...")
    else:
        new_state.current_step = "failed"
        new_state.add_log("Workflow failed: Max retries exceeded")
        print(f"\n[NEGOTIATOR] Workflow FAILED: Max retries exceeded")
    
    return new_state.model_dump()
