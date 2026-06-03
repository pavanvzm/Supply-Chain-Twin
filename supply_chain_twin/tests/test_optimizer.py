"""Tests for the Optimizer agent and OR-Tools optimization."""

import pytest
from unittest.mock import patch, MagicMock
from src.models import (
    AgentState, 
    DisruptionEvent, 
    SeverityLevel, 
    CascadeRiskReport,
    RoutePlan,
)
from src.agents.optimizer import (
    normalize_value,
    calculate_weighted_score,
    solve_with_ortools,
    select_best_route_simple,
    build_route_edges,
    optimize_route,
    TIME_WEIGHT,
    COST_WEIGHT,
    CARBON_WEIGHT,
    BASE_BUDGET_MULTIPLIER,
    RETRY_BUDGET_INCREASE,
)
from src.digital_twin import create_supply_chain_graph


class TestNormalizeValue:
    """Tests for normalize_value function."""
    
    def test_normalize_within_range(self):
        """Test normalization produces values between 0 and 1."""
        result = normalize_value(50, 0, 100)
        assert 0 <= result <= 1
    
    def test_normalize_min_value(self):
        """Test normalization of minimum value."""
        result = normalize_value(0, 0, 100)
        assert result == 0
    
    def test_normalize_max_value(self):
        """Test normalization of maximum value."""
        result = normalize_value(100, 0, 100)
        assert result == 1
    
    def test_normalize_midpoint(self):
        """Test normalization of midpoint."""
        result = normalize_value(50, 0, 100)
        assert result == 0.5
    
    def test_normalize_equal_min_max(self):
        """Test normalization when min equals max."""
        result = normalize_value(50, 50, 50)
        assert result == 0.5


class TestCalculateWeightedScore:
    """Tests for calculate_weighted_score function."""
    
    def test_weighted_score_calculation(self):
        """Test weighted score is calculated correctly."""
        all_routes = [
            (["path1"], {"total_time_days": 20, "total_cost_usd": 30000, "total_carbon_tons": 500}),
            (["path2"], {"total_time_days": 30, "total_cost_usd": 40000, "total_carbon_tons": 600}),
        ]
        
        score = calculate_weighted_score(20, 30000, 500, all_routes)
        
        # Score should be between 0 and 1
        assert 0 <= score <= 1
        
        # Best route should have lower score
        score2 = calculate_weighted_score(30, 40000, 600, all_routes)
        assert score < score2
    
    def test_weighted_score_empty_routes(self):
        """Test weighted score with empty routes list."""
        score = calculate_weighted_score(20, 30000, 500, [])
        assert score == float('inf')
    
    def test_weights_sum_to_one(self):
        """Test that optimization weights sum to 1."""
        total_weight = TIME_WEIGHT + COST_WEIGHT + CARBON_WEIGHT
        assert abs(total_weight - 1.0) < 0.001


class TestSolveWithOrtools:
    """Tests for solve_with_ortools function."""
    
    def test_solve_with_multiple_routes(self):
        """Test solving with multiple route options."""
        routes = [
            (["shanghai", "suez", "rotterdam"], {
                "total_time_days": 25,
                "total_cost_usd": 40000,
                "total_carbon_tons": 700
            }),
            (["shanghai", "cape", "rotterdam"], {
                "total_time_days": 35,
                "total_cost_usd": 50000,
                "total_carbon_tons": 850
            }),
        ]
        
        result = solve_with_ortools(routes, BASE_BUDGET_MULTIPLIER)
        
        assert result is not None
        path, metrics, score = result
        assert len(path) > 1
        assert "total_time_days" in metrics
        assert 0 <= score <= 1
    
    def test_solve_with_empty_routes(self):
        """Test solving with no routes."""
        result = solve_with_ortools([], BASE_BUDGET_MULTIPLIER)
        assert result is None
    
    def test_solve_respects_budget_constraint(self):
        """Test that solver respects budget constraints."""
        routes = [
            (["cheap_route"], {
                "total_time_days": 40,
                "total_cost_usd": 20000,
                "total_carbon_tons": 900
            }),
            (["expensive_route"], {
                "total_time_days": 20,
                "total_cost_usd": 100000,
                "total_carbon_tons": 400
            }),
        ]
        
        # With tight budget, should prefer cheaper route
        result = solve_with_ortools(routes, budget_multiplier=0.5)
        
        assert result is not None
        path, metrics, score = result


class TestSelectBestRouteSimple:
    """Tests for select_best_route_simple function."""
    
    def test_select_best_from_routes(self):
        """Test selecting best route from list."""
        routes = [
            (["path1"], {"total_time_days": 30, "total_cost_usd": 40000, "total_carbon_tons": 600}),
            (["path2"], {"total_time_days": 25, "total_cost_usd": 35000, "total_carbon_tons": 550}),
        ]
        
        result = select_best_route_simple(routes, BASE_BUDGET_MULTIPLIER)
        
        assert result is not None
        path, metrics, score = result
    
    def test_select_best_empty_routes(self):
        """Test selecting from empty routes."""
        result = select_best_route_simple([], BASE_BUDGET_MULTIPLIER)
        assert result is None


class TestBuildRouteEdges:
    """Tests for build_route_edges function."""
    
    def test_build_edges_from_path(self):
        """Test building edges from a path."""
        graph = create_supply_chain_graph()
        path = ["shanghai", "singapore", "suez_canal"]
        
        edges = build_route_edges(graph, path)
        
        assert len(edges) == 2
        assert edges[0].source == "shanghai"
        assert edges[0].target == "singapore"
        assert edges[1].source == "singapore"
        assert edges[1].target == "suez_canal"
    
    def test_build_edges_metrics_positive(self):
        """Test that built edges have positive metrics."""
        graph = create_supply_chain_graph()
        path = ["shanghai", "singapore"]
        
        edges = build_route_edges(graph, path)
        
        for edge in edges:
            assert edge.time_days > 0
            assert edge.cost_usd > 0
            assert edge.carbon_tons > 0


class TestOptimizeRoute:
    """Tests for the main optimize_route function."""
    
    def test_optimization_creates_route_plan(self):
        """Test that optimization creates valid RoutePlan."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        cascade_report = CascadeRiskReport(
            simulation_count=100,
            affected_routes=[],
            cascade_delays={},
            risk_level=SeverityLevel.HIGH,
            recommended_action="Re-route",
            alternative_paths=[],
            confidence_score=0.85,
        )
        
        state = AgentState(
            disruption_event=disruption,
            cascade_report=cascade_report,
        )
        
        result_state = optimize_route(state)
        
        assert "route_plan" in result_state
        assert result_state["route_plan"] is not None
        
        # Verify plan structure
        plan_data = result_state["route_plan"]
        assert len(plan_data["route_path"]) > 1
        assert plan_data["total_time_days"] > 0
        assert plan_data["total_cost_usd"] > 0
        assert plan_data["total_carbon_tons"] > 0
    
    def test_optimization_updates_current_step(self):
        """Test that optimization updates current step to negotiator."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        cascade_report = CascadeRiskReport(
            simulation_count=100,
            affected_routes=[],
            cascade_delays={},
            risk_level=SeverityLevel.HIGH,
            recommended_action="Re-route",
            alternative_paths=[],
            confidence_score=0.85,
        )
        
        state = AgentState(
            disruption_event=disruption,
            cascade_report=cascade_report,
        )
        
        result_state = optimize_route(state)
        
        assert result_state["current_step"] == "negotiator"
    
    def test_optimization_adds_workflow_logs(self):
        """Test that optimization adds logs to workflow."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        cascade_report = CascadeRiskReport(
            simulation_count=100,
            affected_routes=[],
            cascade_delays={},
            risk_level=SeverityLevel.HIGH,
            recommended_action="Re-route",
            alternative_paths=[],
            confidence_score=0.85,
        )
        
        state = AgentState(
            disruption_event=disruption,
            cascade_report=cascade_report,
        )
        
        result_state = optimize_route(state)
        
        assert len(result_state["workflow_log"]) > 0
        assert any("route" in log.lower() for log in result_state["workflow_log"])
    
    def test_optimization_without_cascade_report_raises_error(self):
        """Test that optimization raises error without cascade report."""
        state = AgentState()
        
        with pytest.raises(ValueError, match="No cascade report"):
            optimize_route(state)
    
    def test_optimization_retry_budget_increase(self):
        """Test that budget multiplier increases on retry."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        cascade_report = CascadeRiskReport(
            simulation_count=100,
            affected_routes=[],
            cascade_delays={},
            risk_level=SeverityLevel.HIGH,
            recommended_action="Re-route",
            alternative_paths=[],
            confidence_score=0.85,
        )
        
        # First attempt
        state = AgentState(
            disruption_event=disruption,
            cascade_report=cascade_report,
            retry_count=0,
        )
        
        result_state = optimize_route(state)
        plan_data = result_state["route_plan"]
        base_multiplier = plan_data["budget_multiplier"]
        
        # Retry attempt
        state_retry = AgentState(
            disruption_event=disruption,
            cascade_report=cascade_report,
            retry_count=1,
        )
        
        result_state_retry = optimize_route(state_retry)
        plan_data_retry = result_state_retry["route_plan"]
        retry_multiplier = plan_data_retry["budget_multiplier"]
        
        # Retry should have higher budget
        assert retry_multiplier > base_multiplier
        assert abs(retry_multiplier - base_multiplier - RETRY_BUDGET_INCREASE) < 0.01
