import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from backend.app.database.session import get_db
from backend.app.database.models import (
    ResourceModel, AgentRunModel, OptimizationProposalModel,
    TerraformVersionModel, ValidationAttemptModel, SafetyDecisionModel,
    ApprovalRecordModel, ExecutionSimulationModel, VerificationResultModel,
    AuditLogModel
)
from backend.app.schemas.resource import ResourceResponse
from backend.app.schemas.optimization import (
    OptimizationProposalResponse, ApprovalActionRequest
)
from backend.app.schemas.terraform import TerraformVersionResponse
from backend.app.schemas.safety import SafetyDecisionResponse, SimulationResponse
from backend.app.schemas.audit import AuditLogResponse, OverviewMetricsResponse
from backend.app.services.cost_analyzer import CostAnalyzerService
from backend.app.services.dataset_loader import load_synthetic_dataset
from backend.app.services.simulation_engine import SimulationEngine
from backend.app.services.verification_engine import VerificationEngine
from backend.app.agents.analyst_agent import AnalystAgent
from backend.app.agents.terraform_agent import TerraformAgent
from backend.app.agents.validator_agent import ValidatorAgent
from backend.app.agents.correction_agent import CorrectionAgent
from backend.app.agents.safety_critic_agent import SafetyCriticAgent
from backend.app.workflows.finops_workflow import create_finops_workflow

router = APIRouter()

analyst_agent = AnalystAgent()
terraform_agent = TerraformAgent()
validator_agent = ValidatorAgent()
correction_agent = CorrectionAgent()
safety_critic_agent = SafetyCriticAgent()
compiled_workflow = create_finops_workflow()

def log_audit(db: Session, entity_type: str, entity_id: str, action: str, actor: str = "system", details: dict = None):
    audit = AuditLogModel(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        details=details or {}
    )
    db.add(audit)
    db.commit()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Autonomous Cloud FinOps Agent",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@router.post("/resources/seed")
def seed_resources(force_reload: bool = False, db: Session = Depends(get_db)):
    count = load_synthetic_dataset(db, force_reload=force_reload)
    log_audit(db, "DATASET", "synthetic_cloud_data", "SEEDED", "system", {"count": count})
    return {"message": "Dataset loaded successfully", "total_resources": count}

@router.get("/resources", response_model=List[ResourceResponse])
def get_resources(db: Session = Depends(get_db)):
    # Auto-seed if empty
    if db.query(ResourceModel).count() == 0:
        load_synthetic_dataset(db)
    return db.query(ResourceModel).all()

@router.get("/overview", response_model=OverviewMetricsResponse)
def get_overview_metrics(db: Session = Depends(get_db)):
    resources = db.query(ResourceModel).all()
    metrics = CostAnalyzerService.calculate_overview_metrics(resources)
    pending_approvals = db.query(OptimizationProposalModel).filter_by(status="PENDING").count()
    successful_validations = db.query(ValidationAttemptModel).filter_by(status="SUCCESS").count()
    
    return OverviewMetricsResponse(
        total_cloud_cost=metrics["total_cloud_cost"],
        potential_monthly_savings=metrics["potential_monthly_savings"],
        resources_analyzed=metrics["resources_analyzed"],
        optimization_opportunities=metrics["optimization_opportunities"],
        pending_approvals=pending_approvals,
        successful_validations=successful_validations,
        average_cpu_utilization=metrics["average_cpu_utilization"],
        average_memory_utilization=metrics["average_memory_utilization"]
    )

@router.post("/analysis/run")
def run_autonomous_analysis(db: Session = Depends(get_db)):
    """
    Run the end-to-end multi-agent orchestration analysis across all cloud resources.
    Executes Analyst -> Terraform -> Validation -> Self-Correction -> Safety Critic.
    """
    resources = db.query(ResourceModel).all()
    if not resources:
        load_synthetic_dataset(db)
        resources = db.query(ResourceModel).all()

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    agent_run = AgentRunModel(
        run_id=run_id,
        trigger="manual",
        status="RUNNING",
        total_resources=len(resources)
    )
    db.add(agent_run)
    db.commit()

    generated_proposals = []
    total_savings = 0.0

    for res in resources:
        # Step 1: Analyst Agent Evaluation
        proposal_base = analyst_agent.analyze_resource(res)
        if proposal_base.recommended_action == "NO_ACTION":
            continue

        proposal_id = f"prop-{res.resource_id[-8:]}-{uuid.uuid4().hex[:6]}"
        proposal = OptimizationProposalModel(
            proposal_id=proposal_id,
            resource_id=res.resource_id,
            run_id=run_id,
            issue=proposal_base.issue,
            evidence=proposal_base.evidence,
            recommended_action=proposal_base.recommended_action,
            current_configuration=proposal_base.current_configuration,
            recommended_configuration=proposal_base.recommended_configuration,
            current_monthly_cost=proposal_base.current_monthly_cost,
            estimated_saving=proposal_base.estimated_saving,
            confidence=proposal_base.confidence,
            risk=proposal_base.risk,
            reasoning=proposal_base.reasoning,
            assumptions=proposal_base.assumptions,
            source=proposal_base.source,
            status="PENDING"
        )
        db.add(proposal)
        db.commit()

        total_savings += proposal.estimated_saving

        # Step 2: Terraform Generation Agent
        initial_tf_code = terraform_agent.generate_terraform(res, proposal)
        
        # Step 3 & 4: Validation and Self-Correction Loop
        correction_result = correction_agent.run_correction_loop(initial_tf_code)
        
        tf_version = TerraformVersionModel(
            proposal_id=proposal_id,
            version=1,
            code=correction_result["code"],
            file_path=f"terraform/generated/{proposal_id}.tf"
        )
        db.add(tf_version)
        db.commit()

        for att in correction_result["attempts"]:
            val_record = ValidationAttemptModel(
                terraform_version_id=tf_version.id,
                attempt_number=att["attempt_number"],
                command=att["command"],
                exit_code=att["exit_code"],
                stdout=att["stdout"],
                stderr=att["stderr"],
                status=att["status"]
            )
            db.add(val_record)
        db.commit()

        # Step 5: Independent Safety Critic Agent
        safety_eval = safety_critic_agent.evaluate_proposal(res, proposal, correction_result["code"])
        safety_record = SafetyDecisionModel(
            proposal_id=proposal_id,
            decision=safety_eval["decision"],
            risk_level=safety_eval["risk_level"],
            reasons=safety_eval["reasons"],
            requires_human_approval=safety_eval["requires_human_approval"]
        )
        db.add(safety_record)

        if safety_eval["decision"] == "BLOCK":
            proposal.status = "BLOCKED"
        db.commit()

        # Audit event
        log_audit(
            db,
            "PROPOSAL",
            proposal_id,
            "GENERATED",
            "orchestration_agent",
            {
                "resource_id": res.resource_id,
                "action": proposal.recommended_action,
                "savings": proposal.estimated_saving,
                "validation_status": correction_result["status"],
                "safety_decision": safety_eval["decision"]
            }
        )
        generated_proposals.append(proposal_id)

    agent_run.status = "COMPLETED"
    agent_run.total_opportunities = len(generated_proposals)
    agent_run.potential_monthly_savings = round(total_savings, 2)
    agent_run.completed_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    return {
        "run_id": run_id,
        "status": "COMPLETED",
        "resources_analyzed": len(resources),
        "proposals_generated": len(generated_proposals),
        "potential_monthly_savings": round(total_savings, 2),
        "proposal_ids": generated_proposals
    }

@router.get("/optimizations", response_model=List[OptimizationProposalResponse])
def get_optimizations(db: Session = Depends(get_db)):
    return db.query(OptimizationProposalModel).order_by(OptimizationProposalModel.created_at.desc()).all()

@router.get("/optimizations/{proposal_id}", response_model=OptimizationProposalResponse)
def get_optimization(proposal_id: str, db: Session = Depends(get_db)):
    prop = db.query(OptimizationProposalModel).filter_by(proposal_id=proposal_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Optimization proposal not found.")
    return prop

@router.get("/optimizations/{proposal_id}/terraform")
def get_optimization_terraform(proposal_id: str, db: Session = Depends(get_db)):
    versions = db.query(TerraformVersionModel).filter_by(proposal_id=proposal_id).all()
    if not versions:
        raise HTTPException(status_code=404, detail="No Terraform code generated for this proposal.")
    return versions

@router.get("/optimizations/{proposal_id}/validation")
def get_optimization_validation(proposal_id: str, db: Session = Depends(get_db)):
    tf_version = db.query(TerraformVersionModel).filter_by(proposal_id=proposal_id).first()
    if not tf_version:
        raise HTTPException(status_code=404, detail="No Terraform record found.")
    attempts = db.query(ValidationAttemptModel).filter_by(terraform_version_id=tf_version.id).all()
    return attempts

@router.get("/optimizations/{proposal_id}/safety", response_model=SafetyDecisionResponse)
def get_optimization_safety(proposal_id: str, db: Session = Depends(get_db)):
    decision = db.query(SafetyDecisionModel).filter_by(proposal_id=proposal_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="No safety evaluation found.")
    return decision

@router.post("/optimizations/{proposal_id}/approve")
def approve_proposal(proposal_id: str, req: ApprovalActionRequest, db: Session = Depends(get_db)):
    proposal = db.query(OptimizationProposalModel).filter_by(proposal_id=proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    
    # Check safety decision
    safety = db.query(SafetyDecisionModel).filter_by(proposal_id=proposal_id).first()
    if safety and safety.decision == "BLOCK":
        raise HTTPException(
            status_code=400,
            detail=f"Approval Blocked: Safety Critic policy forbids execution. Reasons: {safety.reasons}"
        )

    proposal.status = "APPROVED"
    approval = db.query(ApprovalRecordModel).filter_by(proposal_id=proposal_id).first()
    if not approval:
        approval = ApprovalRecordModel(
            proposal_id=proposal_id,
            status="APPROVED",
            approver=req.approver,
            reason=req.reason or "Approved by operator"
        )
        db.add(approval)
    else:
        approval.status = "APPROVED"
        approval.approver = req.approver
        approval.reason = req.reason or "Approved by operator"
    
    db.commit()
    log_audit(db, "PROPOSAL", proposal_id, "APPROVED", req.approver, {"reason": req.reason})
    return {"status": "APPROVED", "proposal_id": proposal_id, "approver": req.approver}

@router.post("/optimizations/{proposal_id}/reject")
def reject_proposal(proposal_id: str, req: ApprovalActionRequest, db: Session = Depends(get_db)):
    proposal = db.query(OptimizationProposalModel).filter_by(proposal_id=proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")

    proposal.status = "REJECTED"
    approval = db.query(ApprovalRecordModel).filter_by(proposal_id=proposal_id).first()
    if not approval:
        approval = ApprovalRecordModel(
            proposal_id=proposal_id,
            status="REJECTED",
            approver=req.approver,
            reason=req.reason or "Rejected by operator"
        )
        db.add(approval)
    else:
        approval.status = "REJECTED"
        approval.approver = req.approver
        approval.reason = req.reason or "Rejected by operator"

    db.commit()
    log_audit(db, "PROPOSAL", proposal_id, "REJECTED", req.approver, {"reason": req.reason})
    return {"status": "REJECTED", "proposal_id": proposal_id, "approver": req.approver}

@router.post("/optimizations/{proposal_id}/simulate")
def simulate_execution(proposal_id: str, db: Session = Depends(get_db)):
    proposal = db.query(OptimizationProposalModel).filter_by(proposal_id=proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    
    resource = db.query(ResourceModel).filter_by(resource_id=proposal.resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Underlying resource not found.")

    # Server-side Human Approval Enforcement Check
    if proposal.status != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail=f"Execution Forbidden: Proposal '{proposal_id}' status is '{proposal.status}'. Infrastructure mutations mandate server-validated human approval."
        )

    sim_result = SimulationEngine.simulate_execution(resource, proposal)
    
    sim_record = db.query(ExecutionSimulationModel).filter_by(proposal_id=proposal_id).first()
    if not sim_record:
        sim_record = ExecutionSimulationModel(
            proposal_id=proposal_id,
            mode="SIMULATION_DRY_RUN",
            status=sim_result["status"],
            before_state=sim_result["before_state"],
            after_state=sim_result["after_state"],
            cost_delta=sim_result["cost_delta"],
            execution_log=sim_result["execution_log"]
        )
        db.add(sim_record)
        db.commit()
    else:
        sim_record.status = sim_result["status"]
        sim_record.before_state = sim_result["before_state"]
        sim_record.after_state = sim_result["after_state"]
        sim_record.cost_delta = sim_result["cost_delta"]
        sim_record.execution_log = sim_result["execution_log"]
        db.commit()

    # Step 6: Post-Execution Verification
    ver_result = VerificationEngine.verify_remediation(
        sim_result["before_state"],
        sim_result["after_state"],
        sim_result["cost_delta"]
    )
    
    ver_record = db.query(VerificationResultModel).filter_by(simulation_id=sim_record.id).first()
    if not ver_record:
        ver_record = VerificationResultModel(
            simulation_id=sim_record.id,
            status=ver_result["status"],
            expected_state=ver_result["expected_state"],
            observed_state=ver_result["observed_state"],
            drift_detected=ver_result["drift_detected"]
        )
        db.add(ver_record)
    else:
        ver_record.status = ver_result["status"]
        ver_record.expected_state = ver_result["expected_state"]
        ver_record.observed_state = ver_result["observed_state"]
        ver_record.drift_detected = ver_result["drift_detected"]

    proposal.status = "EXECUTED"
    db.commit()

    log_audit(
        db,
        "EXECUTION",
        proposal_id,
        "SIMULATED_AND_VERIFIED",
        "simulation_engine",
        {"status": sim_result["status"], "verification": ver_result["status"]}
    )

    return {
        "simulation": {
            "proposal_id": proposal_id,
            "status": sim_result["status"],
            "cost_delta": sim_result["cost_delta"],
            "before_state": sim_result["before_state"],
            "after_state": sim_result["after_state"],
            "execution_log": sim_result["execution_log"]
        },
        "verification": ver_result
    }

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db)):
    return db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(100).all()
