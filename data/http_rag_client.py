"""
HTTP RAG Client - Calls orchestrator API for semantic search
Matches production approach used by asana-copy-review
"""

import httpx
import logging
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class HttpRAGClient:
    """
    RAG client that uses the orchestrator's HTTP API for semantic search.
    
    This matches how production services (asana-copy-review) access RAG,
    avoiding the need for LangChain dependencies.
    """
    
    def __init__(
        self,
        rag_api_base_url: Optional[str] = None
    ):
        """
        Initialize HTTP RAG client.
        
        Args:
            rag_api_base_url: Base URL for RAG orchestrator API
                             (defaults to env var or production URL)
        """
        self.rag_api_base_url = (
            rag_api_base_url or
            os.getenv("RAG_API_BASE_URL") or
            "https://emailpilot-orchestrator-935786836546.us-central1.run.app"
        )
        logger.info(f"🌐 HTTP RAG Client initialized with endpoint: {self.rag_api_base_url}")
    
    def _normalize_client_name(self, client_name: str) -> str:
        """Normalize client name for API calls."""
        # API expects dashes (e.g. rogue-creamery), not underscores
        return client_name.lower()
    
    async def get_all_data(self, client_name: str) -> Dict[str, Any]:
        """
        Get all available RAG data for a client using semantic retrieval.
        
        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            
        Returns:
            Dictionary with all RAG data categories
        """
        logger.info(f"Fetching RAG data for {client_name} via HTTP API")
        
        normalized_name = self._normalize_client_name(client_name)
        
        # Define document categories to retrieve
        categories = {
            "brand_voice": "brand voice guidelines and tone of voice",
            "content_pillars": "content pillars and themes",
            "product_catalog": "product catalog and offerings",
            "design_guidelines": "design guidelines and visual standards",
            "previous_campaigns": "previous campaign examples and performance",
            "target_audience": "target audience and customer personas",
            "seasonal_themes": "seasonal themes and calendar events"
        }
        
        result = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for category_key, query in categories.items():
                try:
                    response = await client.post(
                        f"{self.rag_api_base_url}/api/rag/enhanced/retrieve",
                        json={
                            "client_id": normalized_name,
                            "query": query,
                            "top_k": 3,
                            "min_relevance": 0.3
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Error {response.status_code} for {category_key}: {response.text}")
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("success") and data.get("data", {}).get("snippets"):
                        # Transform response to match expected format
                        snippets = data["data"]["snippets"]
                        content = "\n\n".join([s.get("content", "") for s in snippets])
                        result[category_key] = {
                            "content": content,
                            "method": "http_api_vector",
                            "doc_ids": [s.get("doc_id") for s in snippets if s.get("doc_id")]
                        }
                        logger.debug(f"Retrieved {len(snippets)} snippets for {category_key}")
                    else:
                        result[category_key] = None
                        logger.debug(f"No results for {category_key}")
                        
                except httpx.HTTPError as e:
                    logger.warning(f"HTTP error retrieving {category_key}: {e}")
                    result[category_key] = None
                except Exception as e:
                    logger.warning(f"Error retrieving {category_key}: {e}")
                    result[category_key] = None
        
        found_count = len([v for v in result.values() if v])
        logger.info(f"RAG data retrieved for {client_name}: {found_count}/{len(categories)} categories with content")
        return result
    
    async def format_for_prompt(self, client_name: str) -> str:
        """
        Format all RAG data as a text block for AI prompts.
        
        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            
        Returns:
            Formatted text block with all RAG data
        """
        rag_data = await self.get_all_data(client_name)
        
        sections = []
        
        category_labels = {
            "brand_voice": "Brand Voice Guidelines",
            "content_pillars": "Content Pillars",
            "product_catalog": "Product Catalog",
            "design_guidelines": "Design Guidelines",
            "previous_campaigns": "Previous Campaign Examples",
            "target_audience": "Target Audience",
            "seasonal_themes": "Seasonal Themes"
        }
        
        for category_key, label in category_labels.items():
            data = rag_data.get(category_key)
            
            if data and isinstance(data, dict) and data.get("content"):
                sections.append(f"## {label}\n")
                sections.append(data["content"])
                sections.append("\n*Retrieved via semantic search (HTTP API)*\n\n")
        
        if not sections:
            return "No brand intelligence documents available."
        
        return "\n".join(sections)
    
    async def retrieve_semantic(
        self,
        client_name: str,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Perform semantic retrieval with query-based ranking.
        
        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum relevance score
            
        Returns:
            Retrieval results with snippets and metadata
        """
        normalized_name = self._normalize_client_name(client_name)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.rag_api_base_url}/api/rag/enhanced/retrieve",
                    json={
                        "client_id": normalized_name,
                        "query": query,
                        "top_k": top_k,
                        "min_relevance": score_threshold
                    }
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Semantic retrieval failed for {client_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {"snippets": []},
                "method": "error"
            }
