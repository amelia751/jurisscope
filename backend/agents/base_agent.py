"""
Base Agent class for JurisScope AI Agents.
Uses Elasticsearch Agent Builder pattern with tools.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed between agents in multi-step workflows."""
    query: str
    project_id: str
    session_id: str
    history: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    def add_step(self, agent_name: str, action: str, result: Any):
        """Add a step to the execution history."""
        self.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "action": action,
            "result": result
        })


@dataclass
class AgentResponse:
    """Standard response format from agents."""
    success: bool
    agent_name: str
    action_taken: str
    result: Any
    citations: List[Dict[str, Any]] = None
    next_agent: Optional[str] = None
    reasoning: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "agent": self.agent_name,
            "action": self.action_taken,
            "result": self.result,
            "citations": self.citations or [],
            "next_agent": self.next_agent,
            "reasoning": self.reasoning
        }


class BaseAgent(ABC):
    """Base class for all JurisScope agents."""
    
    name: str = "base_agent"
    description: str = "Base agent class"
    
    def __init__(self):
        self.logger = logging.getLogger(f"agent.{self.name}")
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResponse:
        """Execute the agent's primary function."""
        pass
    
    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of tools this agent can use."""
        pass
    
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return f"""You are {self.name}, a specialized legal AI agent.
{self.description}

Always cite your sources with document ID, page number, and relevant text snippets.
Be precise and professional in your responses."""


class Tool:
    """Represents a tool that can be used by agents."""
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: callable
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return await self.handler(**kwargs)
