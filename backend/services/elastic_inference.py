"""
Elastic Inference Service - Uses Elasticsearch's built-in inference endpoints.
This is the core of the Elasticsearch Agent Builder integration.
"""
import logging
import requests
import json
from typing import Dict, Any, List, Optional, Generator

from config import get_settings

logger = logging.getLogger(__name__)


class ElasticInferenceService:
    """
    Service for interacting with Elasticsearch's inference API.
    
    Available endpoints (serverless):
    - Embeddings: .jina-embeddings-v3, .openai-text-embedding-3-small, etc.
    - Reranking: .jina-reranker-v3, .jina-reranker-v2-base-multilingual
    - Chat: .anthropic-claude-4.5-sonnet, .openai-gpt-5.2, .google-gemini-2.5-pro
    - Sparse: .elser-2-elastic
    """
    
    # Default inference endpoint IDs
    EMBEDDING_ENDPOINT = ".jina-embeddings-v3"
    RERANK_ENDPOINT = ".jina-reranker-v3"
    CHAT_ENDPOINT = ".anthropic-claude-4.5-sonnet-chat_completion"
    SPARSE_ENDPOINT = ".elser-2-elastic"
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.elasticsearch_endpoint
        self.headers = {
            "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"Elastic Inference Service initialized: {self.base_url}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Elastic's inference API."""
        return self.generate_embeddings([text])[0]
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        try:
            response = requests.post(
                f"{self.base_url}/_inference/text_embedding/{self.EMBEDDING_ENDPOINT}",
                headers=self.headers,
                json={"input": texts}
            )
            response.raise_for_status()
            data = response.json()
            
            embeddings = []
            for item in data.get("text_embedding", []):
                embeddings.append(item.get("embedding", []))
            
            logger.debug(f"Generated {len(embeddings)} embeddings (dim: {len(embeddings[0]) if embeddings else 0})")
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using Elastic's inference API.
        
        Returns list of {index, relevance_score} sorted by score.
        """
        try:
            response = requests.post(
                f"{self.base_url}/_inference/rerank/{self.RERANK_ENDPOINT}",
                headers=self.headers,
                json={
                    "query": query,
                    "input": documents[:100]  # Limit to 100 docs
                }
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("rerank", [])
            # Sort by relevance score descending
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            logger.debug(f"Reranked {len(documents)} documents, returning top {top_k}")
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            raise
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Generate chat completion using Elastic's inference API.
        Uses streaming internally but returns complete response.
        """
        endpoint = model or self.CHAT_ENDPOINT
        
        # Build messages with optional system prompt
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        try:
            # Use longer timeout for LLM calls (120 seconds)
            response = requests.post(
                f"{self.base_url}/_inference/chat_completion/{endpoint}/_stream",
                headers=self.headers,
                json={"messages": full_messages},
                stream=True,
                timeout=(30, 120)  # (connect timeout, read timeout)
            )
            response.raise_for_status()
            
            # Collect streamed response
            full_text = ""
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        try:
                            data = json.loads(decoded[6:])
                            if "choices" in data:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                full_text += content
                        except json.JSONDecodeError:
                            pass
            
            logger.debug(f"Chat completion: {len(full_text)} chars")
            return full_text
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Chat completion timed out: {e}")
            raise Exception(f"LLM request timed out. Please try again with a shorter prompt.")
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise
    
    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Generate chat completion with streaming output.
        Yields content chunks as they arrive.
        """
        endpoint = model or self.CHAT_ENDPOINT
        
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        try:
            response = requests.post(
                f"{self.base_url}/_inference/chat_completion/{endpoint}/_stream",
                headers=self.headers,
                json={"messages": full_messages},
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        try:
                            data = json.loads(decoded[6:])
                            if "choices" in data:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            pass
                            
        except Exception as e:
            logger.error(f"Chat stream failed: {e}")
            raise
    
    def generate_sparse_embedding(self, text: str) -> Dict[str, float]:
        """Generate sparse embedding using ELSER."""
        try:
            response = requests.post(
                f"{self.base_url}/_inference/sparse_embedding/{self.SPARSE_ENDPOINT}",
                headers=self.headers,
                json={"input": [text]}
            )
            response.raise_for_status()
            data = response.json()
            
            sparse = data.get("sparse_embedding", [{}])[0]
            return sparse
            
        except Exception as e:
            logger.error(f"Sparse embedding failed: {e}")
            raise
    
    def list_available_endpoints(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all available inference endpoints."""
        try:
            response = requests.get(
                f"{self.base_url}/_inference/_all",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            # Categorize by task type
            endpoints = {
                "text_embedding": [],
                "chat_completion": [],
                "completion": [],
                "rerank": [],
                "sparse_embedding": []
            }
            
            for ep in data.get("endpoints", []):
                task_type = ep.get("task_type")
                if task_type in endpoints:
                    endpoints[task_type].append({
                        "id": ep.get("inference_id"),
                        "service": ep.get("service"),
                        "model": ep.get("service_settings", {}).get("model_id")
                    })
            
            return endpoints
            
        except Exception as e:
            logger.error(f"List endpoints failed: {e}")
            raise


# Global instance
_inference_service = None

def get_inference_service() -> ElasticInferenceService:
    """Get or create the global inference service instance."""
    global _inference_service
    if _inference_service is None:
        _inference_service = ElasticInferenceService()
    return _inference_service
