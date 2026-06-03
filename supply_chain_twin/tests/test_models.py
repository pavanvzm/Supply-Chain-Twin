"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from src.models import (
    SeverityLevel,
    RouteEdge,
    DisruptionEvent,
    CascadeRiskReport,
    RoutePlan,
    NegotiationResult,
    AgentState,
)


class TestSeverityLevel:
    """Tests for SeverityLevel enum."""
    
    def test_severity_levels_exist(self):
        """Test that all severity levels are defined."""
        assert SeverityLevel.LOW == "low"
        assert SeverityLevel.MEDIUM == "medium"
        assert SeverityLevel.HIGH == "high"
        assert SeverityLevel.CRITICAL == "critical"
    
    def test_severity_level_values(self):
        """Test severity level values."""
        levels = [level.value for level in SeverityLevel]
        assert "low" in levels
        assert "medium" in levels
        assert "high" in levels
        assert "critical" in levels


class TestRouteEdge:
    """Tests for RouteEdge model."""
    
    def test_valid_route_edge(self):
        """Test creating a valid RouteEdge."""
        edge = RouteEdge(
            source="shanghai",
            target="suez_canal",
            time_days=7.5,
            cost_usd=15000,
            carbon_tons=280,
        )
        assert edge.source == "shanghai"
        assert edge.target == "suez_canal"
        assert edge.time_days == 7.5
        assert edge.cost_usd == 15000
        assert edge.carbon_tons == 280
    
    def test_route_edge_validation_negative_time(self):
        """Test that negative time raises validation error."""
        with pytest.raises(Exception):
            RouteEdge(
                source="shanghai",
                target="suez_canal",
                time_days=-1,
                cost_usd=15000,
                carbon_tons=280,
            )
    
    def test_route_edge_validation_negative_cost(self):
        """Test that negative cost raises validation error."""
        with pytest.raises(Exception):
            RouteEdge(
                source="shanghai",
                target="suez_canal",
                time_days=7.5,
                cost_usd=-100,
                carbon_tons=280,
            )
    
    def test_route_edge_validation_negative_carbon(self):
        """Test that negative carbon raises validation error."""
        with pytest.raises(Exception):
            RouteEdge(
                source="shanghai",
                target="suez_canal",
                time_days=7.5,
                cost_usd=15000,
                carbon_tons=-50,
            )


class TestDisruptionEvent:
    """Tests for DisruptionEvent model."""
    
    def test_valid_disruption_event(self):
        """Test creating a valid DisruptionEvent."""
        event = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        assert event.event_id == "evt_001"
        assert event.severity == SeverityLevel.CRITICAL
        assert len(event.affected_nodes) == 1
        assert "suez_canal" in event.affected_nodes
    
    def test_disruption_event_multiple_nodes(self):
        """Test disruption affecting multiple nodes."""
        event = DisruptionEvent(
            event_id="evt_002",
            event_type="weather_system",
            severity=SeverityLevel.HIGH,
            affected_nodes=["rotterdam", "hamburg", "antwerp"],
            description="Storm affecting North Sea ports",
            timestamp="2024-01-15T10:00:00Z",
        )
        assert len(event.affected_nodes) == 3
    
    def test_disruption_event_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(Exception):
            DisruptionEvent(
                event_type="canal_blockage",
                # Missing required fields
            )


class TestCascadeRiskReport:
    """Tests for CascadeRiskReport model."""
    
    def test_valid_cascade_report(self):
        """Test creating a valid CascadeRiskReport."""
        report = CascadeRiskReport(
            simulation_count=1000,
            affected_routes=[{"path": ["shanghai", "rotterdam"], "delay_days": 5}],
            cascade_delays={"shanghai_rotterdam": 5.5},
            risk_level=SeverityLevel.HIGH,
            recommended_action="Re-route via Cape of Good Hope",
            alternative_paths=[["shanghai", "cape_of_good_hope", "rotterdam"]],
            confidence_score=0.87,
        )
        assert report.simulation_count == 1000
        assert report.risk_level == SeverityLevel.HIGH
        assert report.confidence_score == 0.87
    
    def test_cascade_report_confidence_bounds(self):
        """Test confidence score bounds validation."""
        # Valid confidence
        report = CascadeRiskReport(
            simulation_count=100,
            affected_routes=[],
            cascade_delays={},
            risk_level=SeverityLevel.LOW,
            recommended_action="Continue as normal",
            alternative_paths=[],
            confidence_score=0.99,
        )
        assert report.confidence_score == 0.99
        
        # Invalid confidence (> 1)
        with pytest.raises(Exception):
            CascadeRiskReport(
                simulation_count=100,
                affected_routes=[],
                cascade_delays={},
                risk_level=SeverityLevel.LOW,
                recommended_action="Continue",
                alternative_paths=[],
                confidence_score=1.5,
            )
        
        # Invalid confidence (< 0)
        with pytest.raises(Exception):
            CascadeRiskReport(
                simulation_count=100,
                affected_routes=[],
                cascade_delays={},
                risk_level=SeverityLevel.LOW,
                recommended_action="Continue",
                alternative_paths=[],
                confidence_score=-0.1,
            )


class TestRoutePlan:
    """Tests for RoutePlan model."""
    
    def test_valid_route_plan(self):
        """Test creating a valid RoutePlan."""
        plan = RoutePlan(
            route_path=["shanghai", "cape_of_good_hope", "rotterdam", "chicago"],
            total_time_days=28.0,
            total_cost_usd=45000,
            total_carbon_tons=890,
            weighted_score=0.72,
            is_alternative=True,
        )
        assert len(plan.route_path) == 4
        assert plan.total_time_days == 28.0
        assert plan.is_alternative is True
    
    def test_route_plan_budget_multiplier(self):
        """Test budget multiplier validation."""
        # Valid multiplier
        plan = RoutePlan(
            route_path=["shanghai", "rotterdam"],
            total_time_days=25,
            total_cost_usd=40000,
            total_carbon_tons=800,
            weighted_score=0.65,
            budget_multiplier=1.15,
        )
        assert plan.budget_multiplier == 1.15
        
        # Invalid multiplier (< 1)
        with pytest.raises(Exception):
            RoutePlan(
                route_path=["shanghai", "rotterdam"],
                total_time_days=25,
                total_cost_usd=40000,
                total_carbon_tons=800,
                weighted_score=0.65,
                budget_multiplier=0.9,
            )


class TestNegotiationResult:
    """Tests for NegotiationResult model."""
    
    def test_successful_negotiation(self):
        """Test successful negotiation result."""
        result = NegotiationResult(
            success=True,
            route_plan=None,
            failure_reason=None,
            retry_count=0,
            carrier_response={"booking_id": "BK123456"},
        )
        assert result.success is True
        assert result.failure_reason is None
        assert result.retry_count == 0
    
    def test_failed_negotiation(self):
        """Test failed negotiation result."""
        result = NegotiationResult(
            success=False,
            route_plan=None,
            failure_reason="Capacity unavailable",
            retry_count=1,
            carrier_response={"error_code": "BOOKING_FAILED"},
        )
        assert result.success is False
        assert result.failure_reason == "Capacity unavailable"
        assert result.retry_count == 1


class TestAgentState:
    """Tests for AgentState model."""
    
    def test_default_agent_state(self):
        """Test default AgentState values."""
        state = AgentState()
        assert state.disruption_event is None
        assert state.cascade_report is None
        assert state.route_plan is None
        assert state.retry_count == 0
        assert state.max_retries == 3
        assert state.current_step == "ingestor"
        assert len(state.workflow_log) == 0
    
    def test_agent_state_add_log(self):
        """Test adding logs to AgentState."""
        state = AgentState()
        state.add_log("Test log entry 1")
        state.add_log("Test log entry 2")
        
        assert len(state.workflow_log) == 2
        assert state.workflow_log[0] == "Test log entry 1"
        assert state.workflow_log[1] == "Test log entry 2"
    
    def test_agent_state_increment_retry(self):
        """Test incrementing retry count."""
        state = AgentState()
        assert state.retry_count == 0
        
        state.increment_retry()
        assert state.retry_count == 1
        
        state.increment_retry()
        assert state.retry_count == 2
    
    def test_agent_state_can_retry(self):
        """Test can_retry method."""
        state = AgentState()
        state.max_retries = 3
        
        assert state.can_retry() is True
        
        state.retry_count = 2
        assert state.can_retry() is True
        
        state.retry_count = 3
        assert state.can_retry() is False
    
    def test_agent_state_with_disruption(self):
        """Test AgentState with disruption event."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        state = AgentState(disruption_event=disruption)
        assert state.disruption_event is not None
        assert state.disruption_event.severity == SeverityLevel.CRITICAL
