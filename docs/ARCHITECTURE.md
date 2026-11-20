# System Architecture & Technical Specifications

## 1. Architectural Philosophy

Traditional FinOps systems function as passive observers: they ingest CloudWatch / CUR billing records and display charts. When actions are required, humans must manually formulate tickets, write Terraform, and navigate change approvals.

The **Autonomous Cloud FinOps Agent** bridges this gap by implementing **Closed-Loop Infrastructure Remediation** while maintaining strict enterprise safety boundaries:
1. **Never allow LLMs to perform arithmetic**: Telemetry thresholds (e.g. CPU < 15%, unattached EBS, memory buffers) and financial equations are deterministic.
2. **Never trust arbitrary code generation**: Terraform is emitted through allowlisted HCL templates.
3. **Never bypass human approval**: Mutations require an authenticated state change in the audit database.
4. **Independent Safety Review**: The Safety Critic is an adversarial evaluation gate isolated from the proposing agent.

---

## 2. Multi-Agent Communication Model

```mermaid
sequenceDiagram
    autonumber
    actor Operator as FinOps Operator / Web UI
    participant API as FastAPI Backend
    participant DB as SQLite / PostgreSQL Audit DB
    participant LangGraph as LangGraph Orchestrator
    participant Analyst as Analyst Agent (Gemini / Rule Engine)
    participant TF as Terraform Generator Agent
    participant Validator as Validator & Self-Correction Agent
    participant Critic as Independent Safety Critic

    Operator->>API: POST /api/analysis/run
    API->>LangGraph: Initialize Workflow (Run ID)
    LangGraph->>Analyst: Evaluate Telemetry (CPU, Cost, Criticality)
    Analyst-->>LangGraph: Optimization Proposal (Pydantic Schema)
    LangGraph->>TF: Generate Allowlisted HCL Template
    TF-->>LangGraph: Terraform Code (v1)
    
    loop Bounded Self-Correction (Max 3 attempts)
        LangGraph->>Validator: Validate Code (Syntax / Format)
        alt Syntax Error Detected
            Validator->>Validator: Apply Algorithmic Correction
        else Valid
            Validator-->>LangGraph: Validation Status = SUCCESS
        end
    end

    LangGraph->>Critic: Evaluate Safety Risks (Prod deletion, Downtime, CAB)
    Critic-->>LangGraph: Decision (ALLOW / REQUIRE_APPROVAL / BLOCK)
    LangGraph->>DB: Persist Proposal, IaC, Safety Decision & Audit Log
    LangGraph-->>API: Orchestration Complete
    API-->>Operator: Display in Approval Queue

    Operator->>API: POST /api/optimizations/{id}/approve
    API->>DB: Validate Server-Side & Set Status = APPROVED

    Operator->>API: POST /api/optimizations/{id}/simulate
    API->>API: Verify Status == APPROVED
    API->>API: Run Dry-Run Simulation (Zero AWS Mutation)
    API->>API: Run Verification Engine (Telemetry Drift Check)
    API->>DB: Record Simulation & Verification
    API-->>Operator: Return Before/After State Diff & Verification
```

---

## 3. Database Schema Design & Relationships

```mermaid
erDiagram
    RESOURCES ||--o{ OPTIMIZATION_PROPOSALS : "analyzed for"
    OPTIMIZATION_PROPOSALS ||--o{ TERRAFORM_VERSIONS : "generates"
    TERRAFORM_VERSIONS ||--o{ VALIDATION_ATTEMPTS : "records"
    OPTIMIZATION_PROPOSALS ||--o| SAFETY_DECISIONS : "evaluated by"
    OPTIMIZATION_PROPOSALS ||--o| APPROVAL_RECORDS : "reviewed by"
    OPTIMIZATION_PROPOSALS ||--o| EXECUTION_SIMULATIONS : "dry-run tested"
    EXECUTION_SIMULATIONS ||--o| VERIFICATION_RESULTS : "verified by"

    RESOURCES {
        string resource_id PK
        string resource_name
        string resource_type
        string instance_type
        float cpu_utilization
        float memory_utilization
        float monthly_cost
        string environment
        string criticality
        json tags
    }

    OPTIMIZATION_PROPOSALS {
        string proposal_id PK
        string resource_id FK
        string recommended_action
        string recommended_configuration
        float estimated_saving
        string risk
        string status
        string source
    }

    TERRAFORM_VERSIONS {
        int id PK
        string proposal_id FK
        int version
        text code
    }

    SAFETY_DECISIONS {
        int id PK
        string proposal_id FK
        string decision
        string risk_level
        json reasons
        boolean requires_human_approval
    }

    APPROVAL_RECORDS {
        int id PK
        string proposal_id FK
        string status
        string approver
        text reason
    }

    EXECUTION_SIMULATIONS {
        int id PK
        string proposal_id FK
        string status
        json before_state
        json after_state
        float cost_delta
    }

    VERIFICATION_RESULTS {
        int id PK
        int simulation_id FK
        string status
        boolean drift_detected
    }
```
