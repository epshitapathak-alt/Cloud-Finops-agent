import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

class ResourceModel(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String(64), unique=True, index=True, nullable=False)
    resource_name = Column(String(128), nullable=False)
    resource_type = Column(String(32), index=True, nullable=False) # EC2, EBS, RDS, S3
    instance_type = Column(String(64), nullable=True)
    cpu_utilization = Column(Float, default=0.0)
    memory_utilization = Column(Float, default=0.0)
    monthly_cost = Column(Float, nullable=False)
    region = Column(String(32), nullable=False)
    environment = Column(String(32), index=True, nullable=False) # production, staging, dev
    resource_status = Column(String(32), default="running")
    criticality = Column(String(32), default="low") # low, medium, high, critical
    last_activity = Column(String(64), nullable=True)
    tags = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    optimizations = relationship("OptimizationProposalModel", back_populates="resource", cascade="all, delete-orphan")


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    trigger = Column(String(32), default="manual") # manual, scheduled, webhook
    status = Column(String(32), default="RUNNING") # RUNNING, COMPLETED, FAILED, PARTIAL
    total_resources = Column(Integer, default=0)
    total_opportunities = Column(Integer, default=0)
    potential_monthly_savings = Column(Float, default=0.0)
    workflow_state = Column(JSON, default=dict)
    errors = Column(JSON, default=list)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)


class OptimizationProposalModel(Base):
    __tablename__ = "optimization_proposals"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(String(64), unique=True, index=True, nullable=False)
    resource_id = Column(String(64), ForeignKey("resources.resource_id"), nullable=False)
    run_id = Column(String(64), nullable=True)
    
    # Analysis & Proposal Details
    issue = Column(String(255), nullable=False)
    evidence = Column(Text, nullable=False)
    recommended_action = Column(String(64), nullable=False)
    current_configuration = Column(String(128), nullable=False)
    recommended_configuration = Column(String(128), nullable=False)
    current_monthly_cost = Column(Float, nullable=False)
    estimated_saving = Column(Float, nullable=False)
    confidence = Column(Float, default=0.9)
    risk = Column(String(32), default="LOW") # LOW, MEDIUM, HIGH, CRITICAL
    reasoning = Column(Text, nullable=False)
    assumptions = Column(Text, nullable=True)
    source = Column(String(32), default="DETERMINISTIC_FALLBACK") # GEMINI_AGENT, DETERMINISTIC_FALLBACK

    # Lifecycle Status: PENDING, APPROVED, REJECTED, EXECUTED, FAILED, BLOCKED
    status = Column(String(32), default="PENDING", index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    resource = relationship("ResourceModel", back_populates="optimizations")
    terraform_versions = relationship("TerraformVersionModel", back_populates="proposal", cascade="all, delete-orphan")
    safety_decision = relationship("SafetyDecisionModel", back_populates="proposal", uselist=False, cascade="all, delete-orphan")
    approval_record = relationship("ApprovalRecordModel", back_populates="proposal", uselist=False, cascade="all, delete-orphan")
    simulation = relationship("ExecutionSimulationModel", back_populates="proposal", uselist=False, cascade="all, delete-orphan")


class TerraformVersionModel(Base):
    __tablename__ = "terraform_versions"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(String(64), ForeignKey("optimization_proposals.proposal_id"), nullable=False)
    version = Column(Integer, default=1)
    code = Column(Text, nullable=False)
    file_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    proposal = relationship("OptimizationProposalModel", back_populates="terraform_versions")
    validation_attempts = relationship("ValidationAttemptModel", back_populates="terraform_version", cascade="all, delete-orphan")


class ValidationAttemptModel(Base):
    __tablename__ = "validation_attempts"

    id = Column(Integer, primary_key=True, index=True)
    terraform_version_id = Column(Integer, ForeignKey("terraform_versions.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    command = Column(String(64), nullable=False)
    exit_code = Column(Integer, nullable=False)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    status = Column(String(32), nullable=False) # SUCCESS, FAILED, NOT_CONFIGURED
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    terraform_version = relationship("TerraformVersionModel", back_populates="validation_attempts")


class SafetyDecisionModel(Base):
    __tablename__ = "safety_decisions"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(String(64), ForeignKey("optimization_proposals.proposal_id"), unique=True, nullable=False)
    decision = Column(String(32), nullable=False) # ALLOW, BLOCK, REQUIRE_APPROVAL
    risk_level = Column(String(32), nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    reasons = Column(JSON, default=list)
    requires_human_approval = Column(Boolean, default=True)
    evaluated_at = Column(DateTime, default=utcnow)

    # Relationships
    proposal = relationship("OptimizationProposalModel", back_populates="safety_decision")


class ApprovalRecordModel(Base):
    __tablename__ = "approval_records"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(String(64), ForeignKey("optimization_proposals.proposal_id"), unique=True, nullable=False)
    status = Column(String(32), nullable=False) # PENDING, APPROVED, REJECTED
    approver = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utcnow)

    # Relationships
    proposal = relationship("OptimizationProposalModel", back_populates="approval_record")


class ExecutionSimulationModel(Base):
    __tablename__ = "execution_simulations"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(String(64), ForeignKey("optimization_proposals.proposal_id"), unique=True, nullable=False)
    mode = Column(String(32), default="SIMULATION_DRY_RUN") # SIMULATION_DRY_RUN
    status = Column(String(32), default="SUCCESS") # SUCCESS, FAILED, BLOCKED
    before_state = Column(JSON, nullable=False)
    after_state = Column(JSON, nullable=False)
    cost_delta = Column(Float, nullable=False)
    execution_log = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=utcnow)

    # Relationships
    proposal = relationship("OptimizationProposalModel", back_populates="simulation")
    verification = relationship("VerificationResultModel", back_populates="simulation", uselist=False, cascade="all, delete-orphan")


class VerificationResultModel(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("execution_simulations.id"), unique=True, nullable=False)
    status = Column(String(32), default="VERIFIED") # VERIFIED, MISMATCH, FAILED
    expected_state = Column(JSON, nullable=False)
    observed_state = Column(JSON, nullable=False)
    drift_detected = Column(Boolean, default=False)
    verified_at = Column(DateTime, default=utcnow)

    # Relationships
    simulation = relationship("ExecutionSimulationModel", back_populates="verification")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(64), index=True, nullable=False) # PROPOSAL, APPROVAL, SIMULATION, AGENT_RUN
    entity_id = Column(String(64), index=True, nullable=False)
    action = Column(String(64), index=True, nullable=False) # GENERATED, VALIDATED, APPROVED, REJECTED, SIMULATED, VERIFIED
    actor = Column(String(64), default="system")
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=utcnow)
