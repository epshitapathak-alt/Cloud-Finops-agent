import os
import json
import logging
from typing import Dict, Any, List
from backend.app.core.config import settings
from backend.app.schemas.optimization import OptimizationProposalBase
from backend.app.services.cost_analyzer import CostAnalyzerService
from backend.app.database.models import ResourceModel

logger = logging.getLogger("AnalystAgent")

class AnalystAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("AnalystAgent initialized with Google Gemini API client.")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}. Defaulting to deterministic fallback.")

    def analyze_resource(self, resource: ResourceModel) -> OptimizationProposalBase:
        """Analyze a single resource using Gemini LLM if available, or deterministic rules."""
        # Check deterministic opportunities first for ground truth
        opportunities = CostAnalyzerService.identify_optimization_opportunities([resource])
        if not opportunities:
            return OptimizationProposalBase(
                resource_id=resource.resource_id,
                issue="Resource is optimally configured or marked critical",
                evidence=f"CPU utilization ({resource.cpu_utilization}%) and status ({resource.resource_status}) within healthy parameters.",
                recommended_action="NO_ACTION",
                current_configuration=resource.instance_type or "N/A",
                recommended_configuration=resource.instance_type or "N/A",
                current_monthly_cost=resource.monthly_cost,
                estimated_saving=0.0,
                confidence=1.0,
                risk="LOW",
                reasoning="Resource utilization meets efficiency baselines.",
                assumptions="No remediation necessary.",
                source="DETERMINISTIC_RULES"
            )

        base_opp = opportunities[0]

        # If Gemini API is configured, invoke LLM to generate rich reasoning
        if self.client:
            try:
                prompt = f"""
                You are a Senior Cloud FinOps Principal Engineer.
                Analyze the following cloud resource and verify the optimization opportunity:
                
                Resource ID: {resource.resource_id}
                Name: {resource.resource_name}
                Type: {resource.resource_type}
                Instance: {resource.instance_type}
                Monthly Cost: ${resource.monthly_cost}
                CPU: {resource.cpu_utilization}%
                Memory: {resource.memory_utilization}%
                Environment: {resource.environment}
                Criticality: {resource.criticality}
                Tags: {resource.tags}
                
                Deterministic Recommendation:
                Action: {base_opp['recommended_action']}
                Recommended Config: {base_opp['recommended_configuration']}
                Estimated Saving: ${base_opp['estimated_saving']}
                
                Respond ONLY with a valid JSON object matching this schema:
                {{
                    "resource_id": "{resource.resource_id}",
                    "issue": "brief description of the issue",
                    "evidence": "metrics evidence",
                    "recommended_action": "{base_opp['recommended_action']}",
                    "current_configuration": "{base_opp['current_configuration']}",
                    "recommended_configuration": "{base_opp['recommended_configuration']}",
                    "current_monthly_cost": {resource.monthly_cost},
                    "estimated_saving": {base_opp['estimated_saving']},
                    "confidence": 0.95,
                    "risk": "{base_opp['risk']}",
                    "reasoning": "detailed architectural reasoning",
                    "assumptions": "underlying assumptions"
                }}
                """
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                data = json.loads(text)
                data["source"] = "GEMINI_AGENT"
                return OptimizationProposalBase(**data)
            except Exception as e:
                logger.warning(f"Gemini API call failed ({e}); falling back gracefully to deterministic rule engine.")

        # Deterministic fallback mode
        return OptimizationProposalBase(
            resource_id=base_opp["resource_id"],
            issue=base_opp["issue"],
            evidence=base_opp["evidence"],
            recommended_action=base_opp["recommended_action"],
            current_configuration=base_opp["current_configuration"],
            recommended_configuration=base_opp["recommended_configuration"],
            current_monthly_cost=base_opp["current_monthly_cost"],
            estimated_saving=base_opp["estimated_saving"],
            confidence=base_opp["confidence"],
            risk=base_opp["risk"],
            reasoning=base_opp["reasoning"],
            assumptions=base_opp.get("assumptions"),
            source="DETERMINISTIC_FALLBACK"
        )
