"""Tests for the Simulator agent and Monte Carlo simulations."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.models import AgentState, DisruptionEvent, SeverityLevel, CascadeRiskReport
from src.agents.simulator import (
    add_random_variance,
    run_single_simulation,
    analyze_cascade_risks,
    generate_recommendation,
    run_monte_carlo_simulation,
    DEFAULT_SIMULATION_COUNT,
)
from src.digital_twin import create_supply_chain_graph


class TestAddRandomVariance:
    """Tests for the add_random_variance function."""
    
    def test_variance_adds_noise(self):
        """Test that variance adds noise to values."""
        base_value = 100.0
        results = [add_random_variance(base_value) for _ in range(100)]
        
        # Results should vary around the base value
        assert min(results) < base_value < max(results)
        
        # Mean should be close to base value
        mean_result = np.mean(results)
        assert abs(mean_result - base_value) < base_value * 0.1  # Within 10%
    
    def test_variance_minimum_zero(self):
        """Test that variance never produces negative values."""
        base_value = 10.0
        results = [add_random_variance(base_value) for _ in range(1000)]
        
        # All results should be >= 0
        assert all(r >= 0 for r in results)
    
    def test_variance_proportional(self):
        """Test that variance is proportional to base value."""
        small_base = 10.0
        large_base = 1000.0
        
        small_results = [add_random_variance(small_base) for _ in range(100)]
        large_results = [add_random_variance(large_base) for _ in range(100)]
        
        # Standard deviation should be larger for larger base
        small_std = np.std(small_results)
        large_std = np.std(large_results)
        
        assert large_std > small_std


class TestRunSingleSimulation:
    """Tests for run_single_simulation function."""
    
    def test_simulation_returns_valid_structure(self):
        """Test that simulation returns expected structure."""
        graph = create_supply_chain_graph()
        
        result = run_single_simulation(
            graph=graph,
            source="shanghai",
            target="chicago",
            excluded_nodes=[]
        )
        
        assert "success" in result
        assert "route" in result
        assert "time_days" in result
        assert "cost_usd" in result
        assert "carbon_tons" in result
        assert "delay_days" in result
    
    def test_simulation_with_excluded_node(self):
        """Test simulation excludes blocked nodes."""
        graph = create_supply_chain_graph()
        
        # Exclude suez_canal
        result = run_single_simulation(
            graph=graph,
            source="shanghai",
            target="chicago",
            excluded_nodes=["suez_canal"]
        )
        
        # Should still find a route
        assert result["success"] is True
        
        # Route should not include excluded node
        if result["route"]:
            assert "suez_canal" not in result["route"]
    
    def test_simulation_metrics_are_positive(self):
        """Test that simulation metrics are positive."""
        graph = create_supply_chain_graph()
        
        result = run_single_simulation(
            graph=graph,
            source="shanghai",
            target="chicago",
            excluded_nodes=[]
        )
        
        if result["success"]:
            assert result["time_days"] >= 0
            assert result["cost_usd"] >= 0
            assert result["carbon_tons"] >= 0
            assert result["delay_days"] >= 0


class TestAnalyzeCascadeRisks:
    """Tests for analyze_cascade_risks function."""
    
    def test_risk_analysis_returns_expected_structure(self):
        """Test that risk analysis returns expected keys."""
        simulation_results = [
            {"success": True, "delay_days": 2.5, "time_days": 28},
            {"success": True, "delay_days": 0, "time_days": 25},
            {"success": True, "delay_days": 5.0, "time_days": 30},
        ]
        
        analysis = analyze_cascade_risks(simulation_results, ["suez_canal"])
        
        assert "risk_level" in analysis
        assert "avg_delay" in analysis
        assert "max_delay" in analysis
        assert "delay_probability" in analysis
    
    def test_risk_level_determination(self):
        """Test risk level is determined correctly based on delays."""
        # High delay scenario
        high_delay_results = [
            {"success": True, "delay_days": 10.0, "time_days": 40}
            for _ in range(100)
        ]
        
        analysis = analyze_cascade_risks(high_delay_results, ["suez_canal"])
        assert analysis["risk_level"] in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        
        # Low delay scenario
        low_delay_results = [
            {"success": True, "delay_days": 0, "time_days": 25}
            for _ in range(100)
        ]
        
        analysis = analyze_cascade_risks(low_delay_results, ["suez_canal"])
        assert analysis["risk_level"] == SeverityLevel.LOW
    
    def test_no_successful_simulations(self):
        """Test handling of no successful simulations."""
        simulation_results = [
            {"success": False, "delay_days": 0, "time_days": float('inf')}
            for _ in range(10)
        ]
        
        analysis = analyze_cascade_risks(simulation_results, ["suez_canal"])
        
        assert analysis["risk_level"] == SeverityLevel.CRITICAL


class TestGenerateRecommendation:
    """Tests for generate_recommendation function."""
    
    def test_cape_route_recommendation(self):
        """Test recommendation for Cape of Good Hope route."""
        alternative_paths = [
            ["shanghai", "cape_of_good_hope", "rotterdam", "chicago"]
        ]
        
        recommendation = generate_recommendation({}, alternative_paths)
        
        assert "Cape of Good Hope" in recommendation
    
    def test_panama_route_recommendation(self):
        """Test recommendation for Panama Canal route."""
        alternative_paths = [
            ["shanghai", "panama_canal", "chicago"]
        ]
        
        recommendation = generate_recommendation({}, alternative_paths)
        
        assert "Panama Canal" in recommendation
    
    def test_no_alternatives_recommendation(self):
        """Test recommendation when no alternatives exist."""
        recommendation = generate_recommendation({}, [])
        
        assert "delay" in recommendation.lower() or "No viable" in recommendation


class TestRunMonteCarloSimulation:
    """Tests for the main Monte Carlo simulation function."""
    
    def test_simulation_creates_cascade_report(self):
        """Test that simulation creates valid CascadeRiskReport."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        state = AgentState(disruption_event=disruption)
        
        # Run with fewer simulations for testing
        with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 100):
            result_state = run_monte_carlo_simulation(state)
        
        assert "cascade_report" in result_state
        assert result_state["cascade_report"] is not None
        
        # Verify report structure
        report_data = result_state["cascade_report"]
        assert report_data["simulation_count"] > 0
        assert "risk_level" in report_data
        assert "recommended_action" in report_data
    
    def test_simulation_updates_current_step(self):
        """Test that simulation updates current step to optimizer."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        state = AgentState(disruption_event=disruption)
        
        with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 10):
            result_state = run_monte_carlo_simulation(state)
        
        assert result_state["current_step"] == "optimizer"
    
    def test_simulation_adds_workflow_logs(self):
        """Test that simulation adds logs to workflow."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        state = AgentState(disruption_event=disruption)
        
        with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 10):
            result_state = run_monte_carlo_simulation(state)
        
        assert len(result_state["workflow_log"]) > 0
        assert any("simulation" in log.lower() for log in result_state["workflow_log"])
    
    def test_simulation_without_disruption_raises_error(self):
        """Test that simulation raises error without disruption event."""
        state = AgentState()
        
        with pytest.raises(ValueError, match="No disruption event"):
            run_monte_carlo_simulation(state)
    
    def test_simulation_confidence_score_bounds(self):
        """Test that confidence score is within valid bounds."""
        disruption = DisruptionEvent(
            event_id="evt_001",
            event_type="canal_blockage",
            severity=SeverityLevel.CRITICAL,
            affected_nodes=["suez_canal"],
            description="Suez Canal Blocked",
            timestamp="2024-01-15T08:30:00Z",
        )
        
        state = AgentState(disruption_event=disruption)
        
        with patch('src.agents.simulator.DEFAULT_SIMULATION_COUNT', 100):
            result_state = run_monte_carlo_simulation(state)
        
        confidence = result_state["cascade_report"]["confidence_score"]
        assert 0 <= confidence <= 1
