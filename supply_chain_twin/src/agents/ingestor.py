"""Ingestor Agent - Mocks API calls and classifies disruption severity."""

import random
from datetime import datetime
from typing import Dict, Any
from src.models import DisruptionEvent, SeverityLevel, AgentState


# Mock event database simulating real-time global supply chain events
MOCK_EVENTS = [
    {
        "event_type": "canal_blockage",
        "description": "Suez Canal Blocked due to grounding incident",
        "affected_nodes": ["suez_canal"],
        "base_severity": SeverityLevel.CRITICAL,
    },
    {
        "event_type": "port_strike",
        "description": "Labor strike at Rotterdam port causing delays",
        "affected_nodes": ["rotterdam"],
        "base_severity": SeverityLevel.HIGH,
    },
    {
        "event_type": "weather_delay",
        "description": "Severe weather in Cape of Good Hope region",
        "affected_nodes": ["cape_of_good_hope"],
        "base_severity": SeverityLevel.MEDIUM,
    },
    {
        "event_type": "canal_congestion",
        "description": "Panama Canal congestion due to drought restrictions",
        "affected_nodes": ["panama_canal"],
        "base_severity": SeverityLevel.HIGH,
    },
    {
        "event_type": "minor_delay",
        "description": "Minor scheduling delay at Shanghai port",
        "affected_nodes": ["shanghai"],
        "base_severity": SeverityLevel.LOW,
    },
]


def classify_severity(event_data: Dict[str, Any]) -> SeverityLevel:
    """
    Classify the severity of a disruption event.
    
    In production, this would use ML models or business rules.
    For this implementation, we use predefined severity levels.
    
    Args:
        event_data: Dictionary containing event information
        
    Returns:
        SeverityLevel: Classified severity
    """
    # Base severity from event type
    base_severity = event_data.get("base_severity", SeverityLevel.MEDIUM)
    
    # Add some randomness for realism (10% chance of escalation)
    if random.random() < 0.1:
        severity_order = [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        current_idx = severity_order.index(base_severity)
        if current_idx < len(severity_order) - 1:
            return severity_order[current_idx + 1]
    
    return base_severity


def mock_fetch_global_events() -> list:
    """
    Mock function to simulate fetching events from external APIs.
    
    In production, this would call actual APIs like:
    - Maritime traffic APIs
    - Weather services
    - Port authority feeds
    - News aggregation services
    
    Returns:
        List of event dictionaries
    """
    # Simulate API latency
    # time.sleep(0.1)
    
    # Return all mock events (in production, would filter by time/location)
    return MOCK_EVENTS.copy()


def ingest_disruption_event(state: AgentState) -> Dict[str, Any]:
    """
    Ingest a disruption event and update the state.
    
    This agent:
    1. Fetches events from mocked external APIs
    2. Selects the most critical event (Suez Canal blockage)
    3. Classifies severity
    4. Creates DisruptionEvent object
    5. Updates state
    
    Args:
        state: Current AgentState
        
    Returns:
        Updated state dictionary
    """
    print("\n[INGESTOR] Starting event ingestion...")
    
    # Fetch events from mocked APIs
    events = mock_fetch_global_events()
    
    # For this demo, select the Suez Canal blockage (most critical)
    selected_event = None
    for event in events:
        if event["event_type"] == "canal_blockage":
            selected_event = event
            break
    
    if not selected_event:
        selected_event = events[0]  # Fallback to first event
    
    # Classify severity
    severity = classify_severity(selected_event)
    
    # Create DisruptionEvent
    disruption = DisruptionEvent(
        event_id=f"evt_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        event_type=selected_event["event_type"],
        severity=severity,
        affected_nodes=selected_event["affected_nodes"],
        description=selected_event["description"],
        timestamp=datetime.now().isoformat() + "Z",
    )
    
    # Log the event
    print(f"[INGESTOR] Received event: {disruption.description}")
    print(f"[INGESTOR] Severity: {severity.value.upper()}")
    print(f"[INGESTOR] Affected nodes: {disruption.affected_nodes}")
    
    # Update state
    new_state = state.model_copy()
    new_state.disruption_event = disruption
    new_state.current_step = "simulator"
    new_state.add_log(f"Ingested event: {disruption.event_id} - {disruption.description}")
    new_state.add_log(f"Severity classified as: {severity.value.upper()}")
    
    return new_state.model_dump()
