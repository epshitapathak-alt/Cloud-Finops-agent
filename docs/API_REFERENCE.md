# REST API Reference & Specifications

Base URL: `http://localhost:8000/api`  
Interactive Swagger UI: `http://localhost:8000/docs`

---

## 1. System & Health

### `GET /api/health`
Checks backend and agent status.
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "service": "Autonomous Cloud FinOps Agent",
  "timestamp": "2026-11-13T00:45:00Z"
}
```

### `GET /api/overview`
Retrieves aggregated cloud financial and fleet telemetry.
- **Response `200 OK`**:
```json
{
  "total_cloud_cost": 4435.28,
  "potential_monthly_savings": 1496.42,
  "resources_analyzed": 10,
  "optimization_opportunities": 5,
  "pending_approvals": 4,
  "successful_validations": 5,
  "average_cpu_utilization": 22.8,
  "average_memory_utilization": 31.4
}
```

---

## 2. Resources

### `GET /api/resources`
Lists all managed cloud inventory records (EC2, EBS, RDS, S3).

### `POST /api/resources/seed`
Reloads or resets synthetic cloud telemetry.
- **Query Parameter**: `force_reload=true` (boolean)

---

## 3. Analysis & Multi-Agent Orchestration

### `POST /api/analysis/run`
Triggers the full multi-agent orchestration pipeline across all resources:
1. Analyst Agent (Gemini / Deterministic Fallback)
2. Terraform Generation Agent
3. Validator Agent
4. Self-Correction Bounded Loop (max 3 retries)
5. Safety Critic Agent
6. Audit Ledger Logging

- **Response `200 OK`**:
```json
{
  "run_id": "run-a9c12b7f",
  "status": "COMPLETED",
  "resources_analyzed": 10,
  "proposals_generated": 5,
  "potential_monthly_savings": 1496.42,
  "proposal_ids": ["prop-81ea01-4f12ab", "..."]
}
```

---

## 4. Proposals & Approvals

### `GET /api/optimizations`
Returns all generated optimization proposals.

### `GET /api/optimizations/{id}`
Returns details for a specific proposal.

### `GET /api/optimizations/{id}/terraform`
Returns the generated Terraform HCL code and version history.

### `GET /api/optimizations/{id}/validation`
Returns the validation attempts, exit codes, and self-correction records.

### `GET /api/optimizations/{id}/safety`
Returns the independent Safety Critic evaluation, risk level, and policy reasons.

### `POST /api/optimizations/{id}/approve`
Records human-in-the-loop approval.
- **Request Body**:
```json
{
  "approver": "LeadFinOpsEngineer",
  "reason": "Verified telemetry and downsize impact"
}
```
- **Response `200 OK`**:
```json
{
  "status": "APPROVED",
  "proposal_id": "prop-81ea01-4f12ab",
  "approver": "LeadFinOpsEngineer"
}
```

### `POST /api/optimizations/{id}/reject`
Rejects an optimization proposal.

---

## 5. Simulation & Verification

### `POST /api/optimizations/{id}/simulate`
Executes safe dry-run simulation and post-execution telemetry verification.
- **Enforcement**: If the proposal is not `APPROVED`, returns `HTTP 403 Forbidden`.
- **Response `200 OK`**:
```json
{
  "simulation": {
    "proposal_id": "prop-81ea01-4f12ab",
    "status": "SUCCESS",
    "cost_delta": -372.30,
    "before_state": { "configuration": "c5.4xlarge", "monthly_cost": 496.40 },
    "after_state": { "configuration": "c5.xlarge", "monthly_cost": 124.10 },
    "execution_log": "[DRY-RUN SIMULATION] Started execution..."
  },
  "verification": {
    "status": "VERIFIED",
    "drift_detected": false
  }
}
```

---

## 6. Audit Logs

### `GET /api/audit-logs`
Returns the immutable chronological audit ledger of all agent events, approvals, and simulations.
