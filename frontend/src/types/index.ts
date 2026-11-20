export interface CloudResource {
  id: number;
  resource_id: string;
  resource_name: string;
  resource_type: string;
  instance_type?: string;
  cpu_utilization: number;
  memory_utilization: number;
  monthly_cost: number;
  region: string;
  environment: string;
  resource_status: string;
  criticality: string;
  last_activity?: string;
  tags: Record<string, any>;
}

export interface OptimizationProposal {
  id: number;
  proposal_id: string;
  resource_id: string;
  run_id?: string;
  issue: string;
  evidence: string;
  recommended_action: string;
  current_configuration: string;
  recommended_configuration: string;
  current_monthly_cost: number;
  estimated_saving: number;
  confidence: number;
  risk: string;
  reasoning: string;
  assumptions?: string;
  source: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface OverviewMetrics {
  total_cloud_cost: number;
  potential_monthly_savings: number;
  resources_analyzed: number;
  optimization_opportunities: number;
  pending_approvals: number;
  successful_validations: number;
  average_cpu_utilization: number;
  average_memory_utilization: number;
}

export interface AuditLog {
  id: number;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  details: Record<string, any>;
  timestamp: string;
}
