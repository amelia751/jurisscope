"""
LLM Gateway MCP Server
Provides LLM integration tools via Model Context Protocol.
"""
import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for an LLM provider."""
    name: str
    model: str
    api_key: Optional[str]
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7


class LLMGatewayMCP:
    """
    MCP Server for LLM operations.
    
    Tools provided:
    - generate_text: Generate text from a prompt
    - summarize: Summarize text content
    - extract_entities: Extract named entities from text
    - answer_question: Answer a question given context
    - classify_text: Classify text into categories
    
    Supports multiple LLM providers (OpenAI, Anthropic, Elastic inference).
    """
    
    name = "llm_gateway"
    version = "1.0.0"
    description = "LLM integration tools for text generation and analysis"
    
    def __init__(self):
        self.providers = {}
        self._init_providers()
        logger.info("LLM Gateway MCP initialized")
    
    def _init_providers(self):
        """Initialize available LLM providers."""
        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self.providers["openai"] = LLMConfig(
                name="openai",
                model="gpt-4-turbo-preview",
                api_key=openai_key
            )
        
        # Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.providers["anthropic"] = LLMConfig(
                name="anthropic",
                model="claude-3-sonnet-20240229",
                api_key=anthropic_key
            )
        
        # Elastic (placeholder for Elastic inference API)
        self.providers["elastic"] = LLMConfig(
            name="elastic",
            model="elastic-inference",
            api_key=None  # Uses ES credentials
        )
        
        # Mock provider for development
        self.providers["mock"] = LLMConfig(
            name="mock",
            model="mock-model",
            api_key=None
        )
        
        logger.info(f"Initialized LLM providers: {list(self.providers.keys())}")
    
    def get_manifest(self) -> Dict[str, Any]:
        """Return MCP server manifest."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tools": self.get_tools(),
            "resources": [],
            "prompts": self._get_prompt_templates()
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of tools provided by this MCP server."""
        return [
            {
                "name": "generate_text",
                "description": "Generate text from a prompt using an LLM",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt to generate from"
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["openai", "anthropic", "elastic", "mock"],
                            "description": "LLM provider to use",
                            "default": "mock"
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "Maximum tokens to generate",
                            "default": 1024
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Sampling temperature",
                            "default": 0.7
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "summarize",
                "description": "Summarize text content",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to summarize"
                        },
                        "style": {
                            "type": "string",
                            "enum": ["brief", "detailed", "bullet_points"],
                            "description": "Summary style",
                            "default": "brief"
                        },
                        "provider": {
                            "type": "string",
                            "default": "mock"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "extract_entities",
                "description": "Extract named entities (people, organizations, dates, etc.) from text",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to extract entities from"
                        },
                        "entity_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types of entities to extract",
                            "default": ["person", "organization", "date", "location", "regulation"]
                        },
                        "provider": {
                            "type": "string",
                            "default": "mock"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "answer_question",
                "description": "Answer a question given context documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Question to answer"
                        },
                        "context": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Context documents to use"
                        },
                        "provider": {
                            "type": "string",
                            "default": "mock"
                        }
                    },
                    "required": ["question", "context"]
                }
            },
            {
                "name": "classify_text",
                "description": "Classify text into predefined categories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to classify"
                        },
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Categories to classify into"
                        },
                        "provider": {
                            "type": "string",
                            "default": "mock"
                        }
                    },
                    "required": ["text", "categories"]
                }
            }
        ]
    
    def _get_prompt_templates(self) -> List[Dict[str, Any]]:
        """Return prompt templates for common legal tasks."""
        return [
            {
                "name": "legal_summary",
                "description": "Summarize a legal document",
                "template": """Summarize the following legal document, highlighting:
1. Key parties involved
2. Main legal issues or claims
3. Important dates and deadlines
4. Relevant regulations cited
5. Conclusions or decisions

Document:
{text}

Summary:"""
            },
            {
                "name": "compliance_check",
                "description": "Check document for regulatory compliance",
                "template": """Analyze the following document for compliance with {regulation}.

Document:
{text}

For each relevant requirement, indicate:
- Requirement: [description]
- Status: [compliant/non-compliant/unclear]
- Evidence: [relevant text from document]
- Recommendation: [if non-compliant]

Compliance Analysis:"""
            },
            {
                "name": "citation_extraction",
                "description": "Extract legal citations from text",
                "template": """Extract all legal citations from the following text.
For each citation, provide:
- Citation text
- Type (regulation, case law, statute)
- Full reference

Text:
{text}

Citations:"""
            }
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given arguments."""
        logger.info(f"LLM MCP tool call: {tool_name}")
        
        try:
            if tool_name == "generate_text":
                return await self._generate_text(arguments)
            elif tool_name == "summarize":
                return await self._summarize(arguments)
            elif tool_name == "extract_entities":
                return await self._extract_entities(arguments)
            elif tool_name == "answer_question":
                return await self._answer_question(arguments)
            elif tool_name == "classify_text":
                return await self._classify_text(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"LLM MCP tool error: {e}")
            return {"error": str(e)}
    
    async def _generate_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate text from a prompt."""
        prompt = args.get("prompt", "")
        provider = args.get("provider", "mock")
        max_tokens = args.get("max_tokens", 1024)
        temperature = args.get("temperature", 0.7)
        
        if not prompt:
            return {"error": "prompt is required"}
        
        # Use the appropriate provider
        if provider == "mock" or provider not in self.providers:
            # Mock response for development
            return {
                "success": True,
                "provider": "mock",
                "generated_text": f"[Mock LLM Response] This is a generated response to: '{prompt[:100]}...' "
                                  f"In a production environment, this would be generated by {provider}.",
                "tokens_used": len(prompt.split()) + 50
            }
        
        # TODO: Implement actual LLM calls for OpenAI, Anthropic, Elastic
        config = self.providers[provider]
        return {
            "success": False,
            "provider": provider,
            "error": f"Provider {provider} not yet implemented. Available: {list(self.providers.keys())}"
        }
    
    async def _summarize(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize text content."""
        text = args.get("text", "")
        style = args.get("style", "brief")
        provider = args.get("provider", "mock")
        
        if not text:
            return {"error": "text is required"}
        
        # Generate summary prompt
        prompt = f"""Summarize the following text in a {style} manner:

{text[:3000]}

Summary:"""
        
        result = await self._generate_text({
            "prompt": prompt,
            "provider": provider,
            "max_tokens": 500
        })
        
        if result.get("success"):
            return {
                "success": True,
                "style": style,
                "summary": result.get("generated_text", ""),
                "original_length": len(text),
                "summary_length": len(result.get("generated_text", ""))
            }
        return result
    
    async def _extract_entities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract named entities from text."""
        text = args.get("text", "")
        entity_types = args.get("entity_types", ["person", "organization", "date", "location"])
        
        if not text:
            return {"error": "text is required"}
        
        # Simple regex-based entity extraction for mock
        import re
        
        entities = []
        
        # Dates
        if "date" in entity_types:
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{2,4}',
                r'\d{1,2}-\d{1,2}-\d{2,4}',
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            ]
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({"type": "date", "text": str(match)})
        
        # Regulations
        if "regulation" in entity_types:
            regulation_patterns = [
                r'(GDPR|AI Act|Regulation \(EU\) \d+/\d+|Directive \d+/\d+)',
                r'Article \d+(?:\(\d+\))?',
            ]
            for pattern in regulation_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({"type": "regulation", "text": str(match)})
        
        # Organizations (simple heuristic)
        if "organization" in entity_types:
            org_patterns = [
                r'(?:TechNova|DataSure|EU Commission|European Commission)',
            ]
            for pattern in org_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({"type": "organization", "text": match})
        
        return {
            "success": True,
            "entity_types": entity_types,
            "entities": entities,
            "count": len(entities)
        }
    
    async def _answer_question(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Answer a question given context."""
        question = args.get("question", "")
        context = args.get("context", [])
        provider = args.get("provider", "mock")
        
        if not question:
            return {"error": "question is required"}
        
        # Build context string
        context_str = "\n\n---\n\n".join(context[:5])  # Limit to 5 contexts
        
        prompt = f"""Based on the following documents, answer the question.

Documents:
{context_str[:4000]}

Question: {question}

Answer:"""
        
        result = await self._generate_text({
            "prompt": prompt,
            "provider": provider,
            "max_tokens": 500
        })
        
        if result.get("success"):
            return {
                "success": True,
                "question": question,
                "answer": result.get("generated_text", ""),
                "context_used": len(context)
            }
        return result
    
    async def _classify_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Classify text into categories."""
        text = args.get("text", "")
        categories = args.get("categories", [])
        
        if not text:
            return {"error": "text is required"}
        if not categories:
            return {"error": "categories is required"}
        
        # Simple keyword-based classification for mock
        text_lower = text.lower()
        scores = {}
        
        for category in categories:
            # Count keyword occurrences
            score = text_lower.count(category.lower())
            scores[category] = score
        
        # Find best match
        if scores:
            best_category = max(scores, key=scores.get)
            confidence = min(scores[best_category] / 5, 1.0)  # Normalize to 0-1
        else:
            best_category = categories[0]
            confidence = 0.0
        
        return {
            "success": True,
            "text_preview": text[:100],
            "categories": categories,
            "predicted_category": best_category,
            "confidence": confidence,
            "all_scores": scores
        }
