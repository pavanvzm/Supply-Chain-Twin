"""Integration tests for the LangGraph workflow."""

import pytest
from unittest.mock import patch, MagicMock
from src.models import AgentState, DisruptionEvent, SeverityLevel, NegotiationResult
from src.workflow import create_workflow, run_workflow, route_after_negotiation


class TestRouteAfterNegotiation:
    """Tests for the routing logic after negotiation."""
    
    def test_route_on_success(self):
        """Test routing ends on successful negotiation."""
        state = AgentState(
            negotiation_result=NegotiationResult(success=True)
        )
        
        result = route_after_negotiation(state)
        assert result in ["END", "__end__"]
    
    def test_route_on_failure_with_retries(self):
        """Test routing goes back to optimizer on failure with retries available."""
        state = AgentState(
            negotiation_result=NegotiationResult(success=False),
            current_step="negotiator",
        )
        
        result = route_after_negotiation(state)
        assert result == "optimizer"
    
    def test_route_on_failure_no_retries(self):
        """Test routing ends on failure with no retries."""
        state = AgentState(
            negotiation_result=NegotiationResult(success=False),
            current_step="failed",
        )
        
        result = route_after_negotiation(state)
        assert result in ["END", "__end__"]
    
    def test_route_no_negotiation_result(self):
        """Test routing when no negotiation result exists."""
        state = AgentState(current_step="optimizer")
        
        result = route_after_negotiation(state)
        assert result == "optimizer"


class TestCreateWorkflow:
    """Tests for workflow creation."""
    
    def test_workflow_creates_successfully(self):
        """Test that workflow is created without errors."""
        app = create_workflow()
        assert app is not None
    
    def test_workflow_has_all_nodes(self):
        """Test that workflow has all required nodes."""
        app = create_workflow()
        
        # Check nodes exist in the graph
        nodes = list(app.nodes.keys())
        assert "ingestor" in nodes
        assert "simulator" in nodes
        assert "optimizer" in nodes
        assert "negotiator" in nodes
    
    def test_workflow_entry_point(self):
        """Test that workflow entry point is set correctly."""
        app = create_workflow()
        
        # Entry point should be ingestor (check via nodes)
        assert "ingestor" in app.nodes


class TestRunWorkflow:
    """Integration tests for running the complete workflow."""
    
    @pytest.mark.integration
    def test_workflow_completes_successfully(self):
        """Test that workflow completes from start to finish."""
        # Mock the negotiator to always succeed on first try
        with patch('src.agents.negotiator.mock_carrier_api_call') as mock_booking:
            mock_booking.return_value = {
                "success": True,
                "booking_id": "BK123456",
                "carrier": "MAERSK",
                "vessel_name": "MV_TEST_01",
                "estimated_departure": "2024-01-20T00:00:00Z",
                "rate_accepted": True,
                "equipment_guaranteed": True,
            }
            
            # Run with reduced simulations for speed
            with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 50):
                final_state = run_workflow()
            
            # Verify workflow completed
            assert final_state["current_step"] == "complete"
            assert final_state["negotiation_result"] is not None
            assert final_state["negotiation_result"]["success"] is True
    
    @pytest.mark.integration
    def test_workflow_handles_negotiation_failure_and_retry(self):
        """Test that workflow handles negotiation failure and retries."""
        call_count = [0]
        
        def mock_booking_side_effect(*args):
            call_count[0] += 1
            # Fail first attempt, succeed on second
            if call_count[0] < 2:
                return {
                    "success": False,
                    "error_code": "BOOKING_FAILED",
                    "message": "Capacity unavailable",
                    "available_alternatives": 1,
                }
            return {
                "success": True,
                "booking_id": f"BK{call_count[0] * 100000}",
                "carrier": "MSC",
                "vessel_name": "MV_RETRY_TEST",
                "estimated_departure": "2024-01-20T00:00:00Z",
                "rate_accepted": True,
                "equipment_guaranteed": True,
            }
        
        with patch('src.agents.negotiator.mock_carrier_api_call') as mock_booking:
            mock_booking.side_effect = mock_booking_side_effect
            
            with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 50):
                final_state = run_workflow()
            
            # Should have retried at least once
            assert call_count[0] >= 2
            assert final_state["retry_count"] >= 1
            assert final_state["negotiation_result"]["success"] is True
    
    @pytest.mark.integration
    def test_workflow_max_retries_exceeded(self):
        """Test that workflow stops after max retries."""
        def mock_always_fail(*args):
            return {
                "success": False,
                "error_code": "BOOKING_FAILED",
                "message": "Always failing",
                "available_alternatives": 0,
            }
        
        with patch('src.agents.negotiator.mock_carrier_api_call') as mock_booking:
            mock_booking.side_effect = mock_always_fail
            
            with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 50):
                final_state = run_workflow()
            
            # Should have stopped after max retries
            assert final_state["retry_count"] >= 3
            assert final_state["current_step"] == "failed"
    
    @pytest.mark.integration
    def test_workflow_state_transitions(self):
        """Test that workflow transitions through all states correctly."""
        with patch('src.agents.negotiator.mock_carrier_api_call') as mock_booking:
            mock_booking.return_value = {
                "success": True,
                "booking_id": "BK999999",
                "carrier": "COSCO",
                "vessel_name": "MV_STATE_TEST",
                "estimated_departure": "2024-01-20T00:00:00Z",
                "rate_accepted": True,
                "equipment_guaranteed": True,
            }
            
            with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 50):
                final_state = run_workflow()
            
            # Check workflow log contains expected transitions
            logs = final_state["workflow_log"]
            
            # Should have ingested event
            assert any("Ingested event" in log for log in logs)
            
            # Should have run simulations
            assert any("simulation" in log.lower() for log in logs)
            
            # Should have optimized route
            assert any("Optimized route" in log or "route" in log.lower() for log in logs)
            
            # Should have negotiation result
            assert any("Negotiation" in log for log in logs)
    
    @pytest.mark.integration
    def test_workflow_creates_valid_route_plan(self):
        """Test that workflow creates a valid route plan."""
        with patch('src.agents.negotiator.mock_carrier_api_call') as mock_booking:
            mock_booking.return_value = {
                "success": True,
                "booking_id": "BK777777",
                "carrier": "CMA_CGM",
                "vessel_name": "MV_ROUTE_TEST",
                "estimated_departure": "2024-01-20T00:00:00Z",
                "rate_accepted": True,
                "equipment_guaranteed": True,
            }
            
            with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 50):
                final_state = run_workflow()
            
            # Get route plan from negotiation result
            route_plan = final_state["negotiation_result"]["route_plan"]
            
            # Verify route plan structure
            assert route_plan is not None
            assert len(route_plan["route_path"]) >= 2
            assert route_plan["total_time_days"] > 0
            assert route_plan["total_cost_usd"] > 0
            assert route_plan["total_carbon_tons"] > 0
            assert route_plan["weighted_score"] >= 0  # Can be 0 if it's the best route
            
            # Route should avoid suez_canal (blocked)
            assert "suez_canal" not in route_plan["route_path"]
    
    @pytest.mark.integration
    def test_workflow_disruption_event_captured(self):
        """Test that disruption event is captured in state."""
        with patch('src.agents.negotiator.mock_carrier_api_call') as mock_booking:
            mock_booking.return_value = {
                "success": True,
                "booking_id": "BK555555",
                "carrier": "MAERSK",
                "vessel_name": "MV_DISRUPTION_TEST",
                "estimated_departure": "2024-01-20T00:00:00Z",
                "rate_accepted": True,
                "equipment_guaranteed": True,
            }
            
            with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 50):
                final_state = run_workflow()
            
            # Verify disruption event was captured
            disruption = final_state["disruption_event"]
            assert disruption is not None
            assert disruption["event_type"] == "canal_blockage"
            assert disruption["severity"] == "critical"
            assert "suez_canal" in disruption["affected_nodes"]
    
    @pytest.mark.integration
    def test_workflow_cascade_report_generated(self):
        """Test that cascade risk report is generated."""
        with patch('src.agents.negotiator.mock_carrier_api_call') as mock_booking:
            mock_booking.return_value = {
                "success": True,
                "booking_id": "BK333333",
                "carrier": "MSC",
                "vessel_name": "MV_CASCADE_TEST",
                "estimated_departure": "2024-01-20T00:00:00Z",
                "rate_accepted": True,
                "equipment_guaranteed": True,
            }
            
            with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 50):
                final_state = run_workflow()
            
            # Verify cascade report was generated
            cascade_report = final_state["cascade_report"]
            assert cascade_report is not None
            assert cascade_report["simulation_count"] > 0
            assert cascade_report["risk_level"] in ["low", "medium", "high", "critical"]
            assert cascade_report["confidence_score"] >= 0
            assert cascade_report["confidence_score"] <= 1


class TestWorkflowWithCustomInitialState:
    """Tests for workflow with custom initial state."""
    
    def test_workflow_with_custom_max_retries(self):
        """Test workflow respects custom max_retries setting."""
        initial_state = AgentState(max_retries=5).model_dump()
        
        call_count = [0]
        
        def mock_always_fail(*args):
            call_count[0] += 1
            return {
                "success": False,
                "error_code": "BOOKING_FAILED",
                "message": "Always failing",
                "available_alternatives": 0,
            }
        
        with patch('src.agents.negotiator.mock_carrier_api_call') as mock_booking:
            mock_booking.side_effect = mock_always_fail
            
            with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 50):
                final_state = run_workflow(initial_state)
            
            # Should retry up to 5 times
            assert final_state["retry_count"] == 5
            assert final_state["current_step"] == "failed"
