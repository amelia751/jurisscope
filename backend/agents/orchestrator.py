"""
Orchestrator Agent - Coordinates multi-agent workflows.
Routes queries to appropriate agents based on intent.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional

from agents.base_agent import BaseAgent, AgentContext, AgentResponse
from agents.retrieval_agent import RetrievalAgent
from agents.citation_agent import CitationAgent
from agents.compliance_agent import ComplianceAgent
from agents.esql_agent import ESQLAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Master orchestrator that:
    1. Analyzes user intent
    2. Plans multi-step execution
    3. Routes to appropriate sub-agents
    4. Aggregates and synthesizes results
    
    Agent Selection Logic:
    - Legal research queries → Retrieval + Citation
    - Compliance analysis → Compliance + Retrieval
    - Analytics queries → ES|QL + Retrieval
    - Complex queries → Multi-agent pipeline
    """
    
    name = "orchestrator"
    description = "Coordinates multi-agent workflows for complex legal research tasks."
    
    def __init__(self):
        super().__init__()
        # Initialize sub-agents
        self.retrieval_agent = RetrievalAgent()
        self.citation_agent = CitationAgent()
        self.compliance_agent = ComplianceAgent()
        self.esql_agent = ESQLAgent()
        
        # Agent registry
        self.agents = {
            "retrieval": self.retrieval_agent,
            "citation": self.citation_agent,
            "compliance": self.compliance_agent,
            "esql": self.esql_agent
        }
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute multi-agent workflow based on query.
        
        Steps:
        1. Analyze intent
        2. Plan execution steps
        3. Execute agents in sequence
        4. Aggregate results
        5. Generate final response
        """
        self.logger.info(f"Orchestrating query: {context.query}")
        
        try:
            # Step 1: Analyze intent and plan
            intent = self._analyze_intent(context.query)
            execution_plan = self._create_execution_plan(intent)
            
            self.logger.info(f"Intent: {intent}, Plan: {[s['agent'] for s in execution_plan]}")
            
            # Step 2: Execute agents
            results = []
            for step in execution_plan:
                agent_name = step["agent"]
                agent = self.agents.get(agent_name)
                
                if agent:
                    # Update context with step-specific parameters
                    context.metadata.update(step.get("params", {}))
                    
                    # Execute agent
                    result = await agent.execute(context)
                    results.append({
                        "agent": agent_name,
                        "response": result
                    })
                    
                    # Stop if agent failed and it's critical
                    if not result.success and step.get("critical", True):
                        self.logger.warning(f"Critical agent {agent_name} failed, stopping pipeline")
                        break
            
            # Step 3: Aggregate results
            final_result = self._aggregate_results(intent, results, context)
            
            # Add orchestration step to context
            context.add_step(self.name, "orchestrate", {
                "intent": intent,
                "agents_executed": [r["agent"] for r in results]
            })
            
            return AgentResponse(
                success=True,
                agent_name=self.name,
                action_taken="orchestrate",
                result=final_result,
                citations=self._collect_citations(results),
                reasoning=f"Executed {len(results)} agents: {', '.join([r['agent'] for r in results])}"
            )
            
        except Exception as e:
            self.logger.error(f"Orchestration failed: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                agent_name=self.name,
                action_taken="orchestrate",
                result={"error": str(e)},
                reasoning=f"Orchestration failed: {str(e)}"
            )
    
    def _analyze_intent(self, query: str) -> str:
        """
        Analyze query to determine primary intent.
        
        Intent categories:
        - search: Find documents/information
        - compliance: Check regulatory compliance
        - analytics: Statistical/aggregate queries
        - citation: Get precise citations
        - research: Complex multi-step research
        """
        query_lower = query.lower()
        
        # Compliance intent
        if any(term in query_lower for term in [
            "comply", "compliance", "regulation", "gdpr", "ai act",
            "requirement", "violation", "gap"
        ]):
            return "compliance"
        
        # Analytics intent
        if any(term in query_lower for term in [
            "how many", "count", "statistics", "trend", "distribution",
            "aggregate", "breakdown", "summary"
        ]):
            return "analytics"
        
        # Citation intent
        if any(term in query_lower for term in [
            "cite", "citation", "reference", "source", "page number",
            "where does it say", "exact location"
        ]):
            return "citation"
        
        # Default to research (search + citation)
        return "research"
    
    def _create_execution_plan(self, intent: str) -> List[Dict[str, Any]]:
        """
        Create an execution plan based on intent.
        Returns ordered list of agent steps.
        """
        plans = {
            "search": [
                {"agent": "retrieval", "critical": True}
            ],
            "compliance": [
                {"agent": "retrieval", "critical": True, "params": {"k": 20}},
                {"agent": "compliance", "critical": True}
            ],
            "analytics": [
                {"agent": "esql", "critical": True},
                {"agent": "retrieval", "critical": False, "params": {"k": 5}}
            ],
            "citation": [
                {"agent": "retrieval", "critical": True},
                {"agent": "citation", "critical": True}
            ],
            "research": [
                {"agent": "retrieval", "critical": True, "params": {"k": 10}},
                {"agent": "citation", "critical": False}
            ]
        }
        
        return plans.get(intent, plans["research"])
    
    def _aggregate_results(
        self,
        intent: str,
        results: List[Dict[str, Any]],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Aggregate results from multiple agents into final response."""
        
        # Collect successful results
        agent_outputs = {}
        for r in results:
            if r["response"].success:
                agent_outputs[r["agent"]] = r["response"].result
        
        # Build aggregated response based on intent
        if intent == "compliance":
            return self._aggregate_compliance_results(agent_outputs)
        elif intent == "analytics":
            return self._aggregate_analytics_results(agent_outputs)
        elif intent == "citation":
            return self._aggregate_citation_results(agent_outputs)
        else:
            return self._aggregate_research_results(agent_outputs, context.query)
    
    def _aggregate_compliance_results(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate compliance analysis results."""
        compliance = outputs.get("compliance", {})
        retrieval = outputs.get("retrieval", {})
        
        return {
            "type": "compliance_analysis",
            "summary": f"Compliance analysis complete. Score: {compliance.get('compliance_score', 'N/A')}%",
            "compliance": compliance,
            "supporting_documents": retrieval.get("documents", [])[:5]
        }
    
    def _aggregate_analytics_results(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate analytics results."""
        esql = outputs.get("esql", {})
        retrieval = outputs.get("retrieval", {})
        
        return {
            "type": "analytics",
            "analytics": esql.get("results", {}),
            "sample_documents": retrieval.get("documents", [])[:3]
        }
    
    def _aggregate_citation_results(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate citation results."""
        citation = outputs.get("citation", {})
        retrieval = outputs.get("retrieval", {})
        
        return {
            "type": "citations",
            "citations": citation.get("citations", []),
            "search_results": retrieval.get("documents", [])
        }
    
    def _aggregate_research_results(self, outputs: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Aggregate general research results."""
        retrieval = outputs.get("retrieval", {})
        citation = outputs.get("citation", {})
        
        documents = retrieval.get("documents", [])
        
        # Generate a summary answer
        answer = self._generate_answer(query, documents)
        
        return {
            "type": "research",
            "answer": answer,
            "documents": documents,
            "citations": citation.get("citations", []) if citation else documents
        }
    
    def _generate_answer(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Generate an answer from search results.
        In production, this would use an LLM. For hackathon, use template.
        """
        if not documents:
            return "I couldn't find any relevant information to answer your question."
        
        # Build answer from top results
        answer_parts = [f"Based on the search results for '{query}':\n"]
        
        for i, doc in enumerate(documents[:3], 1):
            snippet = doc.get("text", "")[:200]
            title = doc.get("doc_title", "Unknown")
            answer_parts.append(f"\n[{i}] {snippet}...")
        
        return "\n".join(answer_parts)
    
    def _collect_citations(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect all citations from agent results."""
        citations = []
        for r in results:
            if r["response"].citations:
                citations.extend(r["response"].citations)
        return citations
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tools available to the orchestrator."""
        return [
            {
                "name": "plan_workflow",
                "description": "Create an execution plan for a complex query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "User query"},
                        "preferred_agents": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Preferred agents to use"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "execute_agent",
                "description": "Execute a specific agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["retrieval", "citation", "compliance", "esql"],
                            "description": "Agent to execute"
                        },
                        "params": {"type": "object", "description": "Agent parameters"}
                    },
                    "required": ["agent_name"]
                }
            },
            {
                "name": "aggregate_results",
                "description": "Aggregate results from multiple agents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array", "description": "Agent results to aggregate"}
                    },
                    "required": ["results"]
                }
            }
        ]


async def process_query(
    query: str,
    project_id: str,
    k: int = 10
) -> Dict[str, Any]:
    """
    Main entry point for processing queries through the orchestrator.
    
    Args:
        query: User's natural language query
        project_id: Project to search within
        k: Number of results to return
    
    Returns:
        Aggregated response with answer, citations, and metadata
    """
    # Create context
    context = AgentContext(
        query=query,
        project_id=project_id,
        session_id=str(uuid.uuid4()),
        history=[],
        metadata={"k": k}
    )
    
    # Execute orchestrator
    orchestrator = OrchestratorAgent()
    response = await orchestrator.execute(context)
    
    return {
        "query_id": context.session_id,
        "query": query,
        "success": response.success,
        "result": response.result,
        "citations": response.citations or [],
        "reasoning": response.reasoning,
        "agent_path": [step.get("agent") for step in context.history]
    }
