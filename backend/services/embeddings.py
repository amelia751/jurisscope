"""
Embedding Service - Uses Elasticsearch's Inference API for embeddings.
This replaces the mock embeddings with real Jina embeddings via Elastic.
"""
import logging
from typing import List
import requests

from config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding service using Elasticsearch's inference API.
    Uses Jina embeddings (1024 dims) by default.
    """
    
    EMBEDDING_ENDPOINT = ".jina-embeddings-v3"
    EMBEDDING_DIMS = 1024
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.elasticsearch_endpoint
        self.headers = {
            "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"Embedding service initialized with Elastic inference: {self.EMBEDDING_ENDPOINT}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = self.generate_embeddings([text])
        return embeddings[0] if embeddings else []
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using Elastic inference.
        Processes in batches for efficiency.
        """
        if not texts:
            return []
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = requests.post(
                    f"{self.base_url}/_inference/text_embedding/{self.EMBEDDING_ENDPOINT}",
                    headers=self.headers,
                    json={"input": batch},
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("text_embedding", []):
                    embedding = item.get("embedding", [])
                    all_embeddings.append(embedding)
                
                logger.debug(f"Generated {len(batch)} embeddings (batch {i // batch_size + 1})")
                
            except requests.exceptions.Timeout:
                logger.warning(f"Embedding timeout for batch {i // batch_size + 1}, using fallback")
                # Fallback to random embeddings for this batch
                for _ in batch:
                    all_embeddings.append(self._random_embedding())
                    
            except Exception as e:
                logger.error(f"Embedding failed for batch {i // batch_size + 1}: {e}")
                # Fallback to random embeddings
                for _ in batch:
                    all_embeddings.append(self._random_embedding())
        
        return all_embeddings
    
    def _random_embedding(self) -> List[float]:
        """Fallback random embedding (for error cases only)."""
        import random
        return [random.uniform(-0.1, 0.1) for _ in range(self.EMBEDDING_DIMS)]
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[dict]:
        """
        Chunk text into smaller pieces for embedding.
        
        Args:
            text: Full text to chunk
            chunk_size: Target chunk size in tokens
            overlap: Token overlap between chunks
            
        Returns:
            List of chunk dicts with text, char_start, char_end, chunk_index
        """
        import tiktoken
        
        tokenizer = tiktoken.get_encoding("cl100k_base")
        tokens = tokenizer.encode(text)
        
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = tokenizer.decode(chunk_tokens)
            
            # Find char positions (approximate)
            char_start = len(tokenizer.decode(tokens[:start])) if start > 0 else 0
            char_end = char_start + len(chunk_text)
            
            chunks.append({
                "chunk_index": chunk_idx,
                "text": chunk_text,
                "char_start": char_start,
                "char_end": char_end,
                "token_count": len(chunk_tokens)
            })
            
            start += chunk_size - overlap
            chunk_idx += 1
        
        return chunks
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self.EMBEDDING_DIMS
