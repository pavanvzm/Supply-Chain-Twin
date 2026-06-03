# 🌐 Real-Time Supply Chain Digital Twin & Disruption Fleet

A multi-agent AI system that ingests real-time global data, simulates supply chain disruptions using a graph-based Digital Twin, and autonomously re-routes logistics to minimize cost, delay, and carbon footprint.

## 🏗️ Architecture Overview

### Agent Workflow

```mermaid
flowchart TD
    Start([Start]) --> Ingestor[Ingestor Agent]
    Ingestor -->|Disruption Event| Simulator[Simulator Agent]
    Simulator -->|Cascade Risk Report| Optimizer[Optimizer Agent]
    Optimizer -->|Route Plan| Negotiator[Negotiator Agent]
    Negotiator -->|Success| End([End: Route Booked])
    Negotiator -->|Failure + Retry < Max| Optimizer
    Optimizer -.->|Relaxed Constraints| Negotiator
