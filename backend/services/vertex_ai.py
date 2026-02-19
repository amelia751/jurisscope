"""
Vertex AI service for embeddings and LLM (Gemini).
Used for generating text embeddings and powering the Orchestrator agent.
"""
import logging
import os
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from google.auth import default
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from vertexai.generative_models import GenerativeModel, GenerationConfig

from config import get_settings

logger = logging.getLogger(__name__)


class VertexAIService:
    """Vertex AI operations for embeddings and LLM."""
    
    def __init__(self):
        """Initialize Vertex AI client with service account credentials or ADC."""
        settings = get_settings()
        
        # Check if credentials file exists (local dev) or use ADC (Cloud Run)
        credentials_path = str(settings.gcp_credentials_path)
        if os.path.exists(credentials_path):
            logger.info(f"Using service account credentials from: {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            vertexai.init(
                project=settings.gcp_project_id,
                location=settings.vertex_ai_location,
                credentials=credentials
            )
        else:
            logger.info("Credentials file not found, using Application Default Credentials (ADC)")
            # Use ADC - Cloud Run provides credentials automatically
            vertexai.init(
                project=settings.gcp_project_id,
                location=settings.vertex_ai_location
            )
        
        self.embedding_model_name = settings.vertex_ai_embedding_model
        self.llm_model_name = settings.vertex_ai_llm_model
        
        # Set API key if available (for direct Gemini API access)
        if hasattr(settings, 'google_api_key') and settings.google_api_key:
            os.environ['GOOGLE_API_KEY'] = settings.google_api_key
            logger.info("Using direct Gemini API key")
        
        # Load embedding model
        self.embedding_model = TextEmbeddingModel.from_pretrained(self.embedding_model_name)
        
        logger.info(f"Vertex AI initialized with embedding model: {self.embedding_model_name}")
    
    def generate_embeddings(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            task_type: Task type for embeddings (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)
        
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not texts:
            return []
        
        try:
            # Create TextEmbeddingInput objects
            inputs = [TextEmbeddingInput(text=text, task_type=task_type) for text in texts]
            
            # Generate embeddings
            embeddings = self.embedding_model.get_embeddings(inputs)
            
            # Extract vectors
            vectors = [embedding.values for embedding in embeddings]
            
            logger.info(f"Generated {len(vectors)} embeddings (dim: {len(vectors[0]) if vectors else 0})")
            return vectors
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Query text
        
        Returns:
            Embedding vector
        """
        vectors = self.generate_embeddings([query], task_type="RETRIEVAL_QUERY")
        return vectors[0] if vectors else []
    
    def generate_document_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 250
    ) -> List[List[float]]:
        """
        Generate embeddings for documents in batches.
        Vertex AI has limits on batch size.
        
        Args:
            texts: List of text strings
            batch_size: Maximum batch size (250 for text-embedding-004)
        
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.generate_embeddings(batch, task_type="RETRIEVAL_DOCUMENT")
            all_embeddings.extend(batch_embeddings)
            
            logger.info(f"Processed batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")
        
        return all_embeddings
    
    def get_llm(self, system_instruction: Optional[str] = None) -> GenerativeModel:
        """
        Get a Gemini LLM instance for agent use.
        
        Args:
            system_instruction: Optional system instruction for the model
        
        Returns:
            GenerativeModel instance
        """
        settings = get_settings()
        
        # Try direct API first if key is available
        if hasattr(settings, 'google_api_key') and settings.google_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.google_api_key)
                
                # Return a wrapper that mimics GenerativeModel
                class DirectGeminiModel:
                    def __init__(self, model_name):
                        self.model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    def generate_content(self, prompt, **kwargs):
                        response = self.model.generate_content(prompt)
                        # Mimic Vertex AI response structure
                        class Response:
                            def __init__(self, text):
                                self.text = text
                        return Response(response.text)
                
                logger.info("Using direct Gemini API with API key")
                return DirectGeminiModel(self.llm_model_name)
            except Exception as e:
                logger.warning(f"Failed to use direct Gemini API: {e}, falling back to Vertex AI")
        
        # Fall back to Vertex AI
        model = GenerativeModel(self.llm_model_name)
        return model
    
    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: int = 2048
    ) -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: User prompt
            system_instruction: Optional system instruction (prepended to prompt)
            temperature: Sampling temperature (0.0-1.0)
            max_output_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        model = self.get_llm()
        
        # Prepend system instruction to prompt if provided
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"
        
        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
        
        try:
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise
    
    def generate_text_with_context(
        self,
        query: str,
        context_passages: List[Dict[str, Any]],
        system_instruction: str,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Generate answer with citations using retrieved context.
        
        Args:
            query: User query
            context_passages: Retrieved passages from Elasticsearch
            system_instruction: System instruction for the model
            temperature: Sampling temperature
        
        Returns:
            Dictionary with answer and citation markers
        """
        # Build prompt with context
        context_text = ""
        for i, passage in enumerate(context_passages, 1):
            context_text += f"\n[{i}] (from {passage.get('doc_title', 'Unknown')}, page {passage.get('page', '?')})\n"
            context_text += passage.get('text', '') + "\n"
        
        prompt = f"""Based on the following context, answer the question. Always cite your sources using [n] markers.

Context:
{context_text}

Question: {query}

Answer with citations:"""
        
        answer = self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature
        )
        
        return {
            "answer": answer,
            "num_citations": len(context_passages)
        }

