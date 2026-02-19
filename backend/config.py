"""
Configuration management for JurisScope backend.
Rebuilt for Elasticsearch Agent Builder Hackathon.
Loads environment variables from .env.local
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Elasticsearch Configuration (Primary - for Agent Builder)
    elasticsearch_endpoint: str = "https://localhost:9200"
    elasticsearch_api_key: Optional[str] = None
    elasticsearch_index_prefix: str = "jurisscope"
    
    # Legacy Elasticsearch URL (kept for compatibility)
    elasticsearch_url: Optional[str] = None
    
    # LLM Configuration (for agents)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Local Storage Configuration (replaces GCS for hackathon)
    upload_dir: str = "./uploads"
    processed_dir: str = "./processed"
    
    # API Configuration
    api_port: int = 8005
    api_host: str = "0.0.0.0"
    api_cors_origins: str = "http://localhost:3005,http://localhost:8005"
    
    # Embedding Configuration
    embedding_model: str = "jina-embeddings-v3"  # Use Elastic's Jina embeddings
    embedding_dims: int = 1024  # Jina embeddings dimension
    
    # Chunking Configuration
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Hardcoded User (for hackathon - no auth)
    default_user_id: str = "hackathon-user-001"
    default_user_name: str = "JurisScope User"
    default_user_email: str = "user@jurisscope.dev"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = str(Path(__file__).parent.parent / ".env.local")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"
        
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.api_cors_origins.split(",")]
    
    @property
    def es_url(self) -> str:
        """Get the Elasticsearch URL (prefer endpoint over legacy url)."""
        return self.elasticsearch_endpoint or self.elasticsearch_url or "https://localhost:9200"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection for settings."""
    return settings
