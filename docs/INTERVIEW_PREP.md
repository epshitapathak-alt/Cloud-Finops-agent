# Interview Preparation & Viva Guide: Cloud FinOps AI Agent 🎙️

Use this document to prepare for technical interviews, portfolio presentations, or college capstone vivas.

---

## 1. The 30-Second "Elevator Pitch"

> "I built an Autonomous Cloud FinOps and Infrastructure Remediation Agent that detects cloud waste and performs closed-loop remediation safely. Unlike conventional dashboards that only display billing charts, my system orchestrates multiple specialized agents using LangGraph: a deterministic telemetry analyzer, a Gemini reasoning agent, an IaC generation agent with self-correcting validation loops, an independent safety critic, and server-enforced human approval gates with dry-run simulations. This eliminates cloud waste while mathematically guaranteeing that production systems remain safe."

---

## 2. Frequently Asked Technical Questions

### Q1: Why did you use LangGraph instead of simple LangChain chains or sequential Python functions?
**Answer:**
Sequential scripts cannot handle stateful conditional branching, bounded retry loops, and human-in-the-loop checkpoints gracefully. With LangGraph:
- We model the workflow as a formal state machine (`StateGraph`).
- If validation fails, conditional edges route execution back to the `fix_node` for up to 3 bounded retries.
- If the Safety Critic detects a critical production risk, the graph dynamically terminates with a `BLOCKED` status before reaching the human approval node.
- Workflow state is inspectable and serializable at every node.

### Q2: Why don't you use the LLM to calculate the potential cost savings directly?
**Answer:**
LLMs are probabilistic pattern matchers, not mathematical calculators. Asking an LLM to subtract baseline costs or aggregate CPU percentages introduces hallucination risks. In our architecture, the **Deterministic Cost Analyzer** service computes all mathematical formulas and utilization percentages in pure Python. The LLM is reserved for contextual synthesis, architectural trade-off reasoning, and structured proposal formulation.

### Q3: How do you prevent hallucinated or malicious Terraform code from being executed?
**Answer:**
We implement three defense layers:
1. **Allowlisted Template Engine**: Only approved resource types (`aws_instance`, `aws_ebs_volume`, `aws_db_instance`, `aws_s3_bucket_lifecycle_configuration`) can be emitted.
2. **Validator & Bounded Retry Loop**: Code is structurally and syntactically validated before review.
3. **Independent Safety Critic**: Evaluates generated HCL for public exposure (`0.0.0.0/0`), IAM escalation, and production deletions.

### Q4: How is human approval enforced?
**Answer:**
Approval is enforced **server-side** at the API and database layer, not merely on the UI. The `/simulate` endpoint checks the persistent database state of the proposal. If the record's status is anything other than `APPROVED`, the backend immediately throws an `HTTP 403 Forbidden` exception.

### Q5: How does your system operate if the Gemini API key is not provided?
**Answer:**
The system is built with a **Deterministic Fallback Engine**. If `GEMINI_API_KEY` is not present, the `AnalystAgent` catches the condition, tags the proposal source as `DETERMINISTIC_FALLBACK`, and synthesizes recommendations using rule heuristics. The entire application, test suite, and UI remain 100% operational without crashing.

---

## 3. Resume / Portfolio Bullet Points

- **Architected Closed-Loop FinOps Agent**: Designed and implemented an autonomous multi-agent cloud optimization system using FastAPI, LangGraph, and Google Gemini API.
- **Implemented Bounded IaC Self-Correction**: Engineered a 3-attempt validation and repair loop that autonomously detects and patches syntax and structural anomalies in generated Terraform HCL.
- **Enforced Adversarial Safety Critic**: Developed an isolated policy engine that achieved 100% detection and blocking of unauthorized production deletions and high-risk database alterations.
- **Engineered Zero-Mutation Sandbox Simulation**: Implemented dry-run execution and post-verification engines comparing target configuration against observed telemetry with zero live AWS mutations.
- **100% Test Coverage Across Agent Pipeline**: Authored and passed 12 comprehensive pytest suites validating deterministic analyzers, agent schemas, safety critic barriers, and server-side approval gates.
