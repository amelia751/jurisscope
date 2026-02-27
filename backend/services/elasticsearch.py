"""
Elasticsearch service for JurisScope.
Implements hybrid search (BM25 + vector + RRF) using Elasticsearch Cloud.
Built for Elasticsearch Agent Builder Hackathon.
"""
import logging
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch

from config import get_settings

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Elasticsearch operations for hybrid search."""
    
    # Index mapping with vector fields and proper configuration
    INDEX_MAPPING = {
        "mappings": {
            "properties": {
                "project_id": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "doc_title": {"type": "text"},
                "section_path": {"type": "text"},
                "text": {"type": "text"},
                "char_start": {"type": "integer"},
                "char_end": {"type": "integer"},
                "page": {"type": "integer"},
                "bbox_list": {
                    "type": "nested",
                    "properties": {
                        "x1": {"type": "float"},
                        "y1": {"type": "float"},
                        "x2": {"type": "float"},
                        "y2": {"type": "float"}
                    }
                },
                "vector": {
                    "type": "dense_vector",
                    "dims": 1024,  # Jina embeddings dimension
                    "index": True,
                    "similarity": "cosine"
                },
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
        # Note: Removed settings for serverless Elasticsearch compatibility
    }
    
    def __init__(self):
        """Initialize Elasticsearch client."""
        settings = get_settings()
        
        # Get the Elasticsearch endpoint and API key
        es_endpoint = settings.elasticsearch_endpoint
        api_key = settings.elasticsearch_api_key
        
        logger.info(f"Connecting to Elasticsearch: {es_endpoint}")
        
        self.client = None
        self._connected = False
        
        try:
            # Configure connection for Elastic Cloud
            if api_key:
                self.client = Elasticsearch(
                    hosts=[es_endpoint],
                    api_key=api_key,
                    verify_certs=True,
                    ssl_show_warn=False,
                    request_timeout=10
                )
            else:
                # Fallback for local development without auth
                self.client = Elasticsearch(
                    hosts=[es_endpoint],
                    verify_certs=False,
                    ssl_show_warn=False,
                    request_timeout=10
                )
            
            # Test connection
            self.client.info()
            self._connected = True
            logger.info("✓ Elasticsearch connection successful")
        except Exception as e:
            logger.warning(f"⚠ Elasticsearch connection failed: {e}")
            logger.warning("⚠ Running in offline mode - search features will be limited")
        
        self.index_prefix = settings.elasticsearch_index_prefix
        self.index_name = f"{self.index_prefix}-documents"
        
        logger.info(f"Elasticsearch service initialized, index: {self.index_name}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the Elasticsearch connection."""
        try:
            info = self.client.info()
            return {
                "connected": True,
                "cluster_name": info.get("cluster_name"),
                "version": info.get("version", {}).get("number"),
            }
        except Exception as e:
            logger.error(f"Elasticsearch connection test failed: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def ensure_index(self):
        """Create index with proper mapping if it doesn't exist."""
        try:
            if not self.client.indices.exists(index=self.index_name):
                self.client.indices.create(
                    index=self.index_name,
                    body=self.INDEX_MAPPING
                )
                logger.info(f"Created Elasticsearch index: {self.index_name}")
            else:
                logger.info(f"Elasticsearch index already exists: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to ensure index: {e}")
            raise
    
    def index_document(self, doc_id: str, document: Dict[str, Any]) -> str:
        """Index a single document chunk."""
        response = self.client.index(
            index=self.index_name,
            id=doc_id,
            document=document
        )
        return response["_id"]
    
    def bulk_index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk index multiple document chunks.
        
        Args:
            documents: List of documents with _id and fields
        
        Returns:
            Bulk operation response
        """
        from elasticsearch.helpers import bulk
        
        actions = []
        for doc in documents:
            action = {
                "_index": self.index_name,
                "_id": doc.get("chunk_id"),
                "_source": doc
            }
            actions.append(action)
        
        success, failed = bulk(self.client, actions, raise_on_error=False)
        
        logger.info(f"Bulk indexed {success} documents, {len(failed) if isinstance(failed, list) else failed} failed")
        return {"success": success, "failed": len(failed) if isinstance(failed, list) else failed}
    
    def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        project_id: str,
        k: int = 10,
        num_candidates: int = 100
    ) -> Dict[str, Any]:
        """
        Perform hybrid search using BM25 + kNN + RRF fusion.
        Falls back to simple hybrid if RRF not available (free Elasticsearch).
        
        Args:
            query_text: Text query for BM25
            query_vector: Embedding vector for kNN
            project_id: Project ID filter
            k: Number of results to return
            num_candidates: Number of candidates for kNN
        
        Returns:
            Search results with hits and metadata
        """
        # Try RRF first (paid license)
        search_body = {
            "query": {
                "bool": {
                    "filter": [{"term": {"project_id": project_id}}],
                    "should": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["text^2", "section_path", "doc_title"],
                                "type": "best_fields"
                            }
                        }
                    ]
                }
            },
            "knn": {
                "field": "vector",
                "query_vector": query_vector,
                "k": k,
                "num_candidates": num_candidates,
                "filter": {"term": {"project_id": project_id}}
            },
            "rank": {
                "rrf": {
                    "window_size": 100,
                    "rank_constant": 60
                }
            },
            "_source": [
                "doc_id", "doc_title", "page", "text", "chunk_id",
                "char_start", "char_end", "bbox_list", "section_path"
            ],
            "highlight": {
                "fields": {
                    "text": {
                        "number_of_fragments": 1,
                        "fragment_size": 240
                    }
                }
            },
            "size": k
        }
        
        try:
            response = self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            hits = []
            for hit in response["hits"]["hits"]:
                result = {
                    "chunk_id": hit["_id"],
                    "score": hit["_score"],
                    **hit["_source"]
                }
                
                # Add highlight if available
                if "highlight" in hit:
                    result["highlighted_text"] = hit["highlight"].get("text", [None])[0]
                
                hits.append(result)
            
            return {
                "total": response["hits"]["total"]["value"],
                "hits": hits,
                "max_score": response["hits"]["max_score"]
            }
            
        except Exception as e:
            # If RRF not available (free license or serverless), fall back to weighted hybrid
            error_str = str(e).lower()
            if "rrf" in error_str or "rank" in error_str or "non-compliant" in error_str:
                logger.warning("RRF not available, falling back to weighted hybrid search")
                return self._hybrid_search_fallback(
                    query_text, query_vector, project_id, k, num_candidates
                )
            logger.error(f"Hybrid search failed: {e}")
            raise
    
    def _hybrid_search_fallback(
        self,
        query_text: str,
        query_vector: List[float],
        project_id: str,
        k: int = 10,
        num_candidates: int = 100
    ) -> Dict[str, Any]:
        """
        Fallback hybrid search without RRF (for free Elasticsearch).
        Combines BM25 and kNN results with weighted scoring.
        """
        # Search with BM25 + kNN but without RRF
        search_body = {
            "query": {
                "bool": {
                    "filter": [{"term": {"project_id": project_id}}],
                    "should": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["text^2", "section_path", "doc_title"],
                                "type": "best_fields",
                                "boost": 0.5
                            }
                        }
                    ]
                }
            },
            "knn": {
                "field": "vector",
                "query_vector": query_vector,
                "k": k,
                "num_candidates": num_candidates,
                "filter": {"term": {"project_id": project_id}},
                "boost": 0.5
            },
            "_source": [
                "doc_id", "doc_title", "page", "text", "chunk_id",
                "char_start", "char_end", "bbox_list", "section_path"
            ],
            "highlight": {
                "fields": {
                    "text": {
                        "number_of_fragments": 1,
                        "fragment_size": 240
                    }
                }
            },
            "size": k
        }
        
        response = self.client.search(
            index=self.index_name,
            body=search_body
        )
        
        hits = []
        for hit in response["hits"]["hits"]:
            result = {
                "chunk_id": hit["_id"],
                "score": hit["_score"],
                **hit["_source"]
            }
            
            if "highlight" in hit:
                result["highlighted_text"] = hit["highlight"].get("text", [None])[0]
            
            hits.append(result)
        
        return {
            "total": response["hits"]["total"]["value"],
            "hits": hits,
            "max_score": response["hits"]["max_score"]
        }
    
    def bm25_search(
        self,
        query_text: str,
        project_id: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """Perform BM25-only text search."""
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["text^2", "section_path", "doc_title"]
                            }
                        }
                    ],
                    "filter": [{"term": {"project_id": project_id}}]
                }
            },
            "_source": [
                "doc_id", "doc_title", "page", "text", "chunk_id",
                "char_start", "char_end", "bbox_list"
            ],
            "highlight": {
                "fields": {"text": {}}
            },
            "size": k
        }
        
        response = self.client.search(index=self.index_name, body=search_body)
        
        hits = []
        for hit in response["hits"]["hits"]:
            result = {
                "chunk_id": hit["_id"],
                "score": hit["_score"],
                **hit["_source"]
            }
            if "highlight" in hit:
                result["highlighted_text"] = hit["highlight"].get("text", [None])[0]
            hits.append(result)
        
        return {
            "total": response["hits"]["total"]["value"],
            "hits": hits
        }
    
    def delete_document_chunks(self, doc_id: str):
        """Delete all chunks for a document."""
        self.client.delete_by_query(
            index=self.index_name,
            body={"query": {"term": {"doc_id": doc_id}}}
        )
        logger.info(f"Deleted chunks for document: {doc_id}")
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chunk by ID."""
        try:
            response = self.client.get(index=self.index_name, id=chunk_id)
            return response["_source"]
        except Exception:
            return None
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        try:
            stats = self.client.indices.stats(index=self.index_name)
            return {
                "doc_count": stats["_all"]["primaries"]["docs"]["count"],
                "size_bytes": stats["_all"]["primaries"]["store"]["size_in_bytes"],
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}
    
    def list_documents_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List all unique documents in a project by aggregating from ES index.
        This is used when local storage is ephemeral (Cloud Run).
        """
        try:
            # Use aggregation to get unique documents
            response = self.client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "query": {
                        "term": {"project_id": project_id}
                    },
                    "aggs": {
                        "unique_docs": {
                            "terms": {
                                "field": "doc_id",
                                "size": 1000
                            },
                            "aggs": {
                                "doc_info": {
                                    "top_hits": {
                                        "size": 1,
                                        "_source": ["doc_id", "doc_title", "project_id"]
                                    }
                                },
                                "chunk_count": {
                                    "value_count": {"field": "chunk_id"}
                                },
                                "max_page": {
                                    "max": {"field": "page"}
                                }
                            }
                        }
                    }
                }
            )
            
            documents = []
            buckets = response.get("aggregations", {}).get("unique_docs", {}).get("buckets", [])
            
            for bucket in buckets:
                doc_id = bucket["key"]
                top_hit = bucket["doc_info"]["hits"]["hits"][0]["_source"] if bucket["doc_info"]["hits"]["hits"] else {}
                
                documents.append({
                    "id": doc_id,
                    "project_id": project_id,
                    "title": top_hit.get("doc_title", "Unknown"),
                    "status": "completed",  # If it's in ES, it's processed
                    "num_chunks": bucket["chunk_count"]["value"],
                    "num_pages": int(bucket["max_page"]["value"]) if bucket["max_page"]["value"] else 1
                })
            
            logger.info(f"Found {len(documents)} documents in ES for project {project_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents from ES: {e}")
            return []
