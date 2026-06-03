# Real-Time Supply Chain Digital Twin & Disruption Fleet

A multi-agent system that ingests real-time global data, simulates supply chain disruptions using a graph-based Digital Twin, and autonomously re-routes logistics to minimize cost, delay, and carbon footprint.

## Architecture Overview

```mermaid
graph TD
    A[Ingestor Agent] -->|DisruptionEvent| B[Simulator Agent]
    B -->|CascadeRiskReport| C[Optimizer Agent]
    C -->|RoutePlan| D[Negotiator Agent]
    D -->|Success| E[Final Route Confirmed]
    D -->|Failure + Retry| C
    C -->|Relaxed Constraints| D
    
    subgraph "Digital Twin Graph"
        G1[Shanghai]
        G2[Suez Canal]
        G3[Rotterdam]
        G4[Chicago]
        G5[Los Angeles]
        G6[Panama Canal]
        G1 --> G2
        G2 --> G3
        G3 --> G4
        G1 --> G5
        G5 --> G4
        G1 --> G6
        G6 --> G4
    end
    
    B -.->|Graph Modification| Digital Twin Graph
    C -.->|Path Optimization| Digital Twin Graph
```

## Features

- **Real-time Data Ingestion**: Mocks global supply chain events with severity classification
- **Graph-based Digital Twin**: NetworkX representation of supply chain routes (Shanghai → Suez → Rotterdam → Chicago, with alternatives via Los Angeles and Panama Canal)
- **Monte Carlo Simulation**: 1000+ simulations to predict cascade delays and risks
- **Multi-Objective Optimization**: Google OR-Tools solver balancing time (40%), cost (35%), and carbon footprint (25%)
- **Autonomous Negotiation**: Carrier booking with retry logic and constraint relaxation (+15% budget per retry)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the complete workflow:

```bash
python main.py
```

Run tests:

```bash
pytest tests/ -v
```

## Project Structure

```
supply_chain_twin/
├── README.md
├── requirements.txt
├── main.py
├── src/
│   ├── __init__.py
│   ├── models.py          # Pydantic models for State, DisruptionEvent, RoutePlan
│   ├── digital_twin.py    # NetworkX graph setup
│   ├── workflow.py        # LangGraph StateGraph definition
│   └── agents/
│       ├── __init__.py
│       ├── ingestor.py    # Mocks API calls, classifies severity
│       ├── simulator.py   # Monte Carlo simulations
│       ├── optimizer.py   # OR-Tools multi-objective solver
│       └── negotiator.py  # Mocks carrier communications
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_simulator.py
    ├── test_optimizer.py
    └── test_workflow.py
```

## Agent Descriptions

### Ingestor Agent
- Mocks external API calls for supply chain events
- Classifies disruption severity (Low/Medium/High/Critical)
- Outputs `DisruptionEvent` with affected nodes

### Simulator Agent
- Removes blocked nodes from the Digital Twin graph
- Runs 1000+ Monte Carlo simulations with random edge weight variance
- Generates `CascadeRiskReport` with predicted delays

### Optimizer Agent
- Uses Google OR-Tools for multi-objective linear programming
- Minimizes weighted score of: time, cost, carbon footprint
- Handles constraint relaxation on retry

### Negotiator Agent
- Attempts to book routes with carriers (mocked)
- Simulates 20% failure rate
- Implements retry logic with relaxed constraints (+15% budget)

## Example Output

```
============================================================
=== SUPPLY CHAIN DIGITAL TWIN & DISRUPTION FLEET ===
============================================================

Initializing multi-agent workflow...
Agents: Ingestor → Simulator → Optimizer → Negotiator

Starting workflow execution...

------------------------------------------------------------

[INGESTOR] Starting event ingestion...
[INGESTOR] Received event: Suez Canal Blocked due to grounding incident
[INGESTOR] Severity: CRITICAL
[INGESTOR] Affected nodes: ['suez_canal']

[SIMULATOR] Starting Monte Carlo simulation...
[SIMULATOR] Simulating impact of: Suez Canal Blocked due to grounding incident
[SIMULATOR] Running 1000 simulations...
[SIMULATOR] Completed 1000/1000 simulations...

[SIMULATOR] Simulation complete!
[SIMULATOR] Risk level: MEDIUM
[SIMULATOR] Average delay: 1.19 days
[SIMULATOR] Recommended action: Re-route via Los Angeles - transpacific alternative
[SIMULATOR] Found 4 alternative routes
[SIMULATOR] Best alternative: shanghai -> los_angeles -> chicago

[OPTIMIZER] Starting route optimization...
[OPTIMIZER] Optimizing based on 1000 simulations
[OPTIMIZER] Risk level: MEDIUM
[OPTIMIZER] Budget multiplier: 1.00x (retry 0)
[OPTIMIZER] Found 4 alternative routes

[OPTIMIZER] Optimization complete!
[OPTIMIZER] Optimal route: shanghai -> los_angeles -> chicago
[OPTIMIZER] Estimated time: 15.0 days
[OPTIMIZER] Estimated cost: $28,000
[OPTIMIZER] Carbon footprint: 495 tons
[OPTIMIZER] Weighted score: 0.0000 (lower is better)

[NEGOTIATOR] Starting carrier negotiation...
[NEGOTIATOR] Attempting to book route: shanghai -> los_angeles -> chicago
[NEGOTIATOR] Budget: $28,000 (multiplier: 1.00x)
[NEGOTIATOR] Retry attempt: 1

[NEGOTIATOR] ✓ Booking successful!
[NEGOTIATOR] Booking ID: BK733510
[NEGOTIATOR] Carrier: MSC
[NEGOTIATOR] Vessel: MV_GLOBAL_75
------------------------------------------------------------

============================================================
=== SUPPLY CHAIN DIGITAL TWIN - FINAL SUMMARY ===
============================================================

✓ ROUTE SUCCESSFULLY CONFIRMED

Route Path: shanghai -> los_angeles -> chicago

Metrics:
  • Total Time: 15.0 days
  • Total Cost: $28,000.00
  • Carbon Footprint: 495.00 tons
  • Weighted Score: 0.0000

Booking Details:
  • Booking ID: BK733510
  • Carrier: MSC
  • Vessel: MV_GLOBAL_75

Workflow Log (8 entries):
  1. Ingested event: evt_20260603135532 - Suez Canal Blocked due to grounding incident
  2. Severity classified as: CRITICAL
  3. Completed 1000 Monte Carlo simulations
  4. Cascade risk level: MEDIUM
  5. Recommended: Re-route via Los Angeles - transpacific alternative
  6. Optimized route: shanghai -> los_angeles -> chicago
  7. Time: 15.0d, Cost: $28,000, Carbon: 495t
  8. Negotiation successful: OK

============================================================

✓ Workflow completed successfully!
```

## License

MIT License
