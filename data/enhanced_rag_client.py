#!/usr/bin/env python3
"""
Enhanced RAG Client with Vector Search Integration

Integrates the production-ready LangChain RAG orchestrator from emailpilot-orchestrator
while maintaining backward compatibility with the existing RAGClient interface.

Features:
- Semantic vector search using FAISS and OpenAI embeddings
- Fallback to keyword search when embeddings unavailable
- Client bleed detection for data isolation
- Automatic migration from file-based to vector stores
- Resilience patterns with automatic fallback
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add orchestrator to path to import LangChain RAG
orchestrator_path = Path(__file__).parent.parent.parent / "emailpilot-orchestrator"
sys.path.insert(0, str(orchestrator_path))

try:
    from services.langchain_rag_orchestrator import get_langchain_rag_orchestrator
    VECTOR_RAG_AVAILABLE = True
except ImportError:
    # LangChain RAG is optional - using HTTP RAG client instead
    VECTOR_RAG_AVAILABLE = False

logger = logging.getLogger(__name__)


class EnhancedRAGClient:
    """
    Enhanced RAG client that integrates vector search while maintaining
    backward compatibility with the original RAGClient interface.

    Provides:
    1. Semantic vector search using FAISS and OpenAI embeddings
    2. Fallback to keyword search when embeddings unavailable
    3. Original get_all_data() and format_for_prompt() interface
    4. Query-based semantic retrieval for advanced use cases
    """

    def __init__(
        self,
        rag_base_path: str,
        use_vector_search: bool = True,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize the enhanced RAG client.

        Args:
            rag_base_path: Base path to RAG corpus (for fallback file-based access)
            use_vector_search: Whether to use vector search (requires OpenAI API key)
            openai_api_key: OpenAI API key for embeddings (or set OPENAI_API_KEY env var)
        """
        self.rag_base_path = Path(rag_base_path)
        self.use_vector_search = use_vector_search and VECTOR_RAG_AVAILABLE

        # Set up OpenAI API key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key

        # Initialize LangChain orchestrator if vector search enabled
        self.orchestrator = None
        if self.use_vector_search:
            try:
                self.orchestrator = get_langchain_rag_orchestrator()
                logger.info("✅ Enhanced RAG initialized with vector search (FAISS + OpenAI)")
            except Exception as e:
                logger.warning(f"Failed to initialize vector RAG, falling back to file-based: {e}")
                self.orchestrator = None
                self.use_vector_search = False

        if not self.use_vector_search:
            logger.info("📁 Using file-based RAG (vector search unavailable)")

    def _normalize_client_name(self, client_name: str) -> str:
        """
        Normalize client name for directory access.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            Normalized name for directory access (e.g., "rogue_creamery")
        """
        return client_name.replace("-", "_")

    async def get_all_data(self, client_name: str) -> Dict[str, Any]:
        """
        Get all available RAG data for a client.

        Maintains backward compatibility with original RAGClient interface.
        Uses semantic retrieval when available, falls back to file-based.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            Dictionary with all RAG data categories
        """
        logger.info(f"Fetching RAG data for {client_name}")

        # Normalize client name for directory access
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

        if self.use_vector_search and self.orchestrator:
            # Use semantic retrieval for each category
            for category_key, query in categories.items():
                try:
                    retrieval_result = await self.orchestrator.retrieve(
                        client_id=normalized_name,
                        query=query,
                        top_k=3,  # Get top 3 most relevant chunks per category
                        score_threshold=0.3  # Lower threshold for broader coverage
                    )

                    if retrieval_result.get("success") and retrieval_result.get("snippets"):
                        result[category_key] = {
                            "content": "\n\n".join(retrieval_result["snippets"]),
                            "method": retrieval_result.get("method", "vector"),
                            "doc_ids": retrieval_result.get("doc_ids", [])
                        }
                    else:
                        result[category_key] = None

                except Exception as e:
                    logger.warning(f"Vector retrieval failed for {category_key}: {e}")
                    result[category_key] = None
        else:
            # Fallback to file-based retrieval
            result = await self._get_all_data_file_based(normalized_name, categories)

        logger.info(f"RAG data retrieved for {client_name}: {len([v for v in result.values() if v])} categories with content")
        return result

    async def _get_all_data_file_based(
        self,
        client_name: str,
        categories: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Fallback file-based retrieval when vector search unavailable.

        Args:
            client_name: Normalized client name
            categories: Dictionary of category keys and queries

        Returns:
            Dictionary with file-based RAG data
        """
        result = {}
        client_dir = self.rag_base_path / client_name

        if not client_dir.exists():
            logger.warning(f"RAG directory not found: {client_dir}")
            return {key: None for key in categories.keys()}

        # Map categories to expected file patterns
        file_patterns = {
            "brand_voice": ["brand_voice.txt", "brand_voice.json"],
            "content_pillars": ["content_pillars.txt", "content_pillars.json"],
            "product_catalog": ["product_catalog.json", "products.json"],
            "design_guidelines": ["design_guidelines.txt", "design.txt"],
            "previous_campaigns": ["campaigns.json", "campaign_history.json"],
            "target_audience": ["audience.txt", "personas.txt"],
            "seasonal_themes": ["seasonal.txt", "calendar.txt"]
        }

        for category_key, patterns in file_patterns.items():
            content = None
            for pattern in patterns:
                file_path = client_dir / pattern
                if file_path.exists():
                    try:
                        if file_path.suffix == ".json":
                            with open(file_path, 'r') as f:
                                content = json.load(f)
                        else:
                            with open(file_path, 'r') as f:
                                content = f.read()
                        break
                    except Exception as e:
                        logger.warning(f"Failed to read {file_path}: {e}")

            result[category_key] = content

        return result

    async def format_for_prompt(self, client_name: str) -> str:
        """
        Format all RAG data as a text block for AI prompts.

        Now async to work properly in async contexts.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            Formatted text block with all RAG data
        """
        # Direct await - works correctly in async context
        rag_data = await self.get_all_data(client_name)

        sections = []

        # Format each category
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

            if data:
                sections.append(f"## {label}\n")

                if isinstance(data, dict):
                    # Vector search result format
                    if "content" in data:
                        sections.append(data["content"])
                        if data.get("method") == "vector":
                            sections.append(f"\n*Retrieved via semantic search*\n")
                    else:
                        # JSON data
                        sections.append(json.dumps(data, indent=2))
                elif isinstance(data, str):
                    sections.append(data)
                else:
                    sections.append(str(data))

                sections.append("\n")

        if not sections:
            return "No brand intelligence documents available."

        return "\n".join(sections)

    async def retrieve_semantic(
        self,
        client_name: str,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
        use_mmr: bool = False
    ) -> Dict[str, Any]:
        """
        Perform semantic retrieval with query-based ranking.

        This is an enhanced method beyond the original RAGClient interface,
        allowing calendar agent to perform query-specific retrieval.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum relevance score
            use_mmr: Use Maximum Marginal Relevance for diverse results

        Returns:
            Retrieval results with snippets and metadata
        """
        if not self.use_vector_search or not self.orchestrator:
            logger.warning("Semantic retrieval requested but vector search unavailable")
            return {
                "success": False,
                "error": "Vector search not available",
                "snippets": [],
                "method": "unavailable"
            }

        normalized_name = self._normalize_client_name(client_name)

        try:
            result = await self.orchestrator.retrieve(
                client_id=normalized_name,
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
                use_mmr=use_mmr
            )
            return result

        except Exception as e:
            logger.error(f"Semantic retrieval failed for {client_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "snippets": [],
                "method": "error"
            }

    async def get_stats(self, client_name: str) -> Dict[str, Any]:
        """
        Get RAG statistics for a client.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            Statistics about RAG system for this client
        """
        normalized_name = self._normalize_client_name(client_name)

        stats = {
            "client_name": client_name,
            "vector_search_enabled": self.use_vector_search,
            "rag_base_path": str(self.rag_base_path)
        }

        if self.use_vector_search and self.orchestrator:
            try:
                vector_stats = await self.orchestrator.get_stats(normalized_name)
                stats.update(vector_stats)
            except Exception as e:
                logger.warning(f"Failed to get vector stats: {e}")
                stats["vector_stats_error"] = str(e)

        # Add file-based stats
        client_dir = self.rag_base_path / normalized_name
        if client_dir.exists():
            stats["corpus_directory_exists"] = True
            stats["corpus_files"] = len(list(client_dir.glob("*")))
        else:
            stats["corpus_directory_exists"] = False
            stats["corpus_files"] = 0

        return stats

    # Backward compatibility methods from original RAGClient

    async def get_brand_voice(self, client_name: str) -> Optional[str]:
        """Get brand voice guidelines (async)"""
        data = await self.get_all_data(client_name)
        brand_voice = data.get("brand_voice")

        if isinstance(brand_voice, dict):
            return brand_voice.get("content")
        return brand_voice

    async def get_content_pillars(self, client_name: str) -> Optional[str]:
        """Get content pillars (async)"""
        data = await self.get_all_data(client_name)
        content_pillars = data.get("content_pillars")

        if isinstance(content_pillars, dict):
            return content_pillars.get("content")
        return content_pillars

    async def get_product_catalog(self, client_name: str) -> Optional[Any]:
        """Get product catalog (async)"""
        data = await self.get_all_data(client_name)
        return data.get("product_catalog")
