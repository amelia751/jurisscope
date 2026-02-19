"""
Compliance Agent - Analyzes documents against regulatory requirements.
Specialized for EU AI Act, GDPR, and other legal compliance frameworks.
"""
import logging
from typing import Dict, Any, List
from dataclasses import dataclass, field

from agents.base_agent import BaseAgent, AgentContext, AgentResponse
from services.elasticsearch import ElasticsearchService
from services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class ComplianceRequirement:
    """Represents a regulatory compliance requirement."""
    id: str
    regulation: str
    article: str
    title: str
    description: str
    keywords: List[str] = field(default_factory=list)
    risk_level: str = "high"  # high, medium, low


# Pre-defined compliance requirements for EU AI Act
EU_AI_ACT_REQUIREMENTS = [
    ComplianceRequirement(
        id="ai_act_art6",
        regulation="EU AI Act",
        article="Article 6",
        title="Classification of High-Risk AI Systems",
        description="AI systems that are safety components or fall under Annex III categories",
        keywords=["high-risk", "safety component", "annex III", "classification"],
        risk_level="high"
    ),
    ComplianceRequirement(
        id="ai_act_art9",
        regulation="EU AI Act",
        article="Article 9",
        title="Risk Management System",
        description="Establishment of a risk management system throughout the AI system's lifecycle",
        keywords=["risk management", "lifecycle", "continuous monitoring", "risk assessment"],
        risk_level="high"
    ),
    ComplianceRequirement(
        id="ai_act_art10",
        regulation="EU AI Act",
        article="Article 10",
        title="Data and Data Governance",
        description="Training, validation and testing data sets requirements",
        keywords=["training data", "data governance", "data quality", "bias", "validation"],
        risk_level="high"
    ),
    ComplianceRequirement(
        id="ai_act_art13",
        regulation="EU AI Act",
        article="Article 13",
        title="Transparency and Information",
        description="High-risk AI systems designed to allow users to interpret outputs",
        keywords=["transparency", "interpretability", "user information", "instructions"],
        risk_level="high"
    ),
    ComplianceRequirement(
        id="ai_act_art14",
        regulation="EU AI Act",
        article="Article 14",
        title="Human Oversight",
        description="Effective oversight by natural persons during use",
        keywords=["human oversight", "intervention", "stop", "override", "human-in-the-loop"],
        risk_level="high"
    ),
    ComplianceRequirement(
        id="ai_act_art15",
        regulation="EU AI Act",
        article="Article 15",
        title="Accuracy, Robustness and Cybersecurity",
        description="Appropriate level of accuracy, robustness and cybersecurity",
        keywords=["accuracy", "robustness", "cybersecurity", "resilience", "adversarial"],
        risk_level="high"
    ),
]

GDPR_REQUIREMENTS = [
    ComplianceRequirement(
        id="gdpr_art5",
        regulation="GDPR",
        article="Article 5",
        title="Principles of Processing",
        description="Lawfulness, fairness, transparency, purpose limitation, data minimization",
        keywords=["lawful", "fair", "transparent", "purpose limitation", "data minimization"],
        risk_level="high"
    ),
    ComplianceRequirement(
        id="gdpr_art22",
        regulation="GDPR",
        article="Article 22",
        title="Automated Decision-Making",
        description="Rights related to automated individual decision-making, including profiling",
        keywords=["automated decision", "profiling", "significant effects", "human intervention"],
        risk_level="high"
    ),
    ComplianceRequirement(
        id="gdpr_art35",
        regulation="GDPR",
        article="Article 35",
        title="Data Protection Impact Assessment",
        description="DPIA required for high-risk processing",
        keywords=["DPIA", "impact assessment", "high risk", "evaluation"],
        risk_level="high"
    ),
]


class ComplianceAgent(BaseAgent):
    """
    Legal compliance analysis agent.
    
    Capabilities:
    1. Analyze documents against regulatory frameworks (EU AI Act, GDPR)
    2. Identify compliance gaps and risks
    3. Generate compliance checklists
    4. Cross-reference internal docs with regulations
    """
    
    name = "compliance_agent"
    description = "Analyzes documents for regulatory compliance, identifying gaps and requirements."
    
    def __init__(self):
        super().__init__()
        self.es_service = ElasticsearchService()
        self.embeddings_service = EmbeddingService()
        self.requirements = EU_AI_ACT_REQUIREMENTS + GDPR_REQUIREMENTS
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Perform compliance analysis.
        
        Strategy:
        1. Identify which regulations apply based on query/documents
        2. Search for evidence of compliance/non-compliance
        3. Generate compliance assessment with gaps
        """
        self.logger.info(f"Running compliance analysis for: {context.query}")
        
        try:
            # Determine which frameworks to check
            frameworks = self._determine_frameworks(context.query)
            
            # Get requirements for the frameworks
            requirements = [r for r in self.requirements if r.regulation in frameworks]
            
            # Analyze compliance for each requirement
            compliance_results = []
            for req in requirements:
                result = await self._check_requirement(req, context.project_id)
                compliance_results.append(result)
            
            # Calculate overall compliance score
            total = len(compliance_results)
            compliant = sum(1 for r in compliance_results if r["status"] == "compliant")
            partial = sum(1 for r in compliance_results if r["status"] == "partial")
            
            score = (compliant + partial * 0.5) / total * 100 if total > 0 else 0
            
            # Identify gaps
            gaps = [r for r in compliance_results if r["status"] in ["non_compliant", "unknown"]]
            
            # Add to context
            context.add_step(self.name, "compliance_analysis", {
                "frameworks": frameworks,
                "requirements_checked": total,
                "compliance_score": score
            })
            
            return AgentResponse(
                success=True,
                agent_name=self.name,
                action_taken="compliance_analysis",
                result={
                    "frameworks": frameworks,
                    "compliance_score": round(score, 1),
                    "summary": {
                        "total_requirements": total,
                        "compliant": compliant,
                        "partial": partial,
                        "gaps": len(gaps)
                    },
                    "requirements": compliance_results,
                    "critical_gaps": gaps[:5]  # Top 5 gaps
                },
                citations=[r.get("evidence", {}) for r in compliance_results if r.get("evidence")],
                reasoning=f"Analyzed {total} requirements across {len(frameworks)} frameworks. Compliance score: {score:.1f}%"
            )
            
        except Exception as e:
            self.logger.error(f"Compliance analysis failed: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                agent_name=self.name,
                action_taken="compliance_analysis",
                result={"error": str(e)},
                reasoning=f"Compliance analysis failed: {str(e)}"
            )
    
    def _determine_frameworks(self, query: str) -> List[str]:
        """Determine which regulatory frameworks to check based on query."""
        query_lower = query.lower()
        frameworks = []
        
        if any(term in query_lower for term in ["ai act", "eu ai", "high-risk ai", "high risk ai"]):
            frameworks.append("EU AI Act")
        
        if any(term in query_lower for term in ["gdpr", "data protection", "privacy", "personal data"]):
            frameworks.append("GDPR")
        
        # Default to both if query is general
        if not frameworks:
            frameworks = ["EU AI Act", "GDPR"]
        
        return frameworks
    
    async def _check_requirement(
        self,
        requirement: ComplianceRequirement,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Check compliance for a specific requirement.
        Searches for evidence in project documents.
        """
        # Search for relevant documents
        search_query = f"{requirement.title} {' '.join(requirement.keywords)}"
        query_embedding = self.embeddings_service.generate_embedding(search_query)
        
        results = self.es_service.hybrid_search(
            query_text=search_query,
            query_vector=query_embedding,
            project_id=project_id,
            k=3
        )
        
        hits = results.get("hits", [])
        
        if not hits:
            return {
                "requirement_id": requirement.id,
                "regulation": requirement.regulation,
                "article": requirement.article,
                "title": requirement.title,
                "status": "unknown",
                "risk_level": requirement.risk_level,
                "evidence": None,
                "recommendation": f"No documentation found addressing {requirement.title}. Consider documenting compliance measures."
            }
        
        # Analyze the evidence
        top_hit = hits[0]
        score = top_hit.get("score", 0)
        text = top_hit.get("text", "").lower()
        
        # Heuristic compliance check based on keywords
        positive_indicators = ["compliant", "implemented", "established", "documented", "in place"]
        negative_indicators = ["gap", "missing", "not implemented", "lacking", "deficient"]
        
        has_positive = any(indicator in text for indicator in positive_indicators)
        has_negative = any(indicator in text for indicator in negative_indicators)
        
        if has_positive and not has_negative:
            status = "compliant"
            recommendation = "Evidence suggests compliance. Continue monitoring."
        elif has_negative:
            status = "non_compliant"
            recommendation = f"Potential compliance gap identified for {requirement.title}. Review and remediate."
        else:
            status = "partial"
            recommendation = f"Partial evidence found. Recommend detailed review of {requirement.title} compliance."
        
        return {
            "requirement_id": requirement.id,
            "regulation": requirement.regulation,
            "article": requirement.article,
            "title": requirement.title,
            "status": status,
            "risk_level": requirement.risk_level,
            "evidence": {
                "doc_id": top_hit.get("doc_id"),
                "doc_title": top_hit.get("doc_title"),
                "page": top_hit.get("page"),
                "text": top_hit.get("text", "")[:300],
                "score": score
            },
            "recommendation": recommendation
        }
    
    async def generate_checklist(self, frameworks: List[str]) -> List[Dict[str, Any]]:
        """Generate a compliance checklist for specified frameworks."""
        checklist = []
        for req in self.requirements:
            if req.regulation in frameworks:
                checklist.append({
                    "id": req.id,
                    "regulation": req.regulation,
                    "article": req.article,
                    "title": req.title,
                    "description": req.description,
                    "risk_level": req.risk_level,
                    "checked": False
                })
        return checklist
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tools available to this agent."""
        return [
            {
                "name": "analyze_compliance",
                "description": "Analyze documents against regulatory frameworks (EU AI Act, GDPR)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "frameworks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of regulatory frameworks to check"
                        },
                        "focus_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific compliance areas to focus on"
                        }
                    }
                }
            },
            {
                "name": "identify_gaps",
                "description": "Identify compliance gaps and missing documentation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "framework": {"type": "string", "description": "Regulatory framework"},
                        "severity": {
                            "type": "string",
                            "enum": ["all", "high", "critical"],
                            "description": "Gap severity filter"
                        }
                    },
                    "required": ["framework"]
                }
            },
            {
                "name": "generate_checklist",
                "description": "Generate a compliance checklist for specified frameworks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "frameworks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Regulatory frameworks for checklist"
                        }
                    },
                    "required": ["frameworks"]
                }
            },
            {
                "name": "cross_reference",
                "description": "Cross-reference internal documents with regulatory requirements",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string", "description": "Internal document ID"},
                        "regulation": {"type": "string", "description": "Regulation to check against"}
                    },
                    "required": ["doc_id", "regulation"]
                }
            }
        ]
