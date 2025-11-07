"""
RAG Client for Brand and Product Documents

Provides access to brand voice guidelines, content pillars, product catalogs,
and design guidelines stored in the RAG system.
"""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RAGClient:
    """
    Client for retrieving brand and product documents from the RAG system.

    The RAG system stores client-specific documents in a structured
    directory hierarchy under shared_modules/rag/
    """

    def __init__(self, rag_base_path: str):
        """
        Initialize RAG client.

        Args:
            rag_base_path: Base path to RAG directory
                          (e.g., "/Users/Damon/klaviyo/klaviyo-audit-automation/shared_modules/rag")
        """
        self.base_path = Path(rag_base_path)

        if not self.base_path.exists():
            logger.warning(f"RAG base path does not exist: {self.base_path}")

    def _get_client_path(self, client_name: str) -> Path:
        """
        Get the RAG directory path for a specific client.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            Path to client's RAG directory
        """
        # Convert client slug to directory name (e.g., "rogue-creamery" -> "rogue_creamery")
        dir_name = client_name.replace("-", "_")
        return self.base_path / dir_name

    def _read_file(self, file_path: Path) -> Optional[str]:
        """
        Read a text file from the RAG system.

        Args:
            file_path: Path to file

        Returns:
            File contents as string, or None if file doesn't exist
        """
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info(f"Read RAG file: {file_path}")
                return content
            else:
                logger.warning(f"RAG file not found: {file_path}")
                return None

        except Exception as e:
            logger.error(f"Error reading RAG file {file_path}: {str(e)}")
            return None

    def _read_json_file(self, file_path: Path) -> Optional[Dict]:
        """
        Read a JSON file from the RAG system.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data, or None if file doesn't exist
        """
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Read RAG JSON file: {file_path}")
                return data
            else:
                logger.warning(f"RAG JSON file not found: {file_path}")
                return None

        except Exception as e:
            logger.error(f"Error reading RAG JSON file {file_path}: {str(e)}")
            return None

    def get_brand_voice(self, client_name: str) -> Optional[str]:
        """
        Get brand voice guidelines for a client.

        Args:
            client_name: Client slug

        Returns:
            Brand voice guidelines text, or None if not found
        """
        client_path = self._get_client_path(client_name)
        brand_voice_path = client_path / "brand_voice.txt"

        return self._read_file(brand_voice_path)

    def get_content_pillars(self, client_name: str) -> Optional[str]:
        """
        Get content pillars for a client.

        Args:
            client_name: Client slug

        Returns:
            Content pillars text, or None if not found
        """
        client_path = self._get_client_path(client_name)
        content_pillars_path = client_path / "content_pillars.txt"

        return self._read_file(content_pillars_path)

    def get_product_catalog(self, client_name: str) -> Optional[Dict]:
        """
        Get product catalog for a client.

        Args:
            client_name: Client slug

        Returns:
            Product catalog data (JSON), or None if not found
        """
        client_path = self._get_client_path(client_name)

        # Try both .json and .txt formats
        json_path = client_path / "products.json"
        txt_path = client_path / "products.txt"

        # Try JSON first
        data = self._read_json_file(json_path)
        if data:
            return data

        # Try text format
        text = self._read_file(txt_path)
        if text:
            return {"products": text}

        return None

    def get_design_guidelines(self, client_name: str) -> Optional[str]:
        """
        Get design guidelines for a client.

        Args:
            client_name: Client slug

        Returns:
            Design guidelines text, or None if not found
        """
        client_path = self._get_client_path(client_name)
        design_path = client_path / "design_guidelines.txt"

        return self._read_file(design_path)

    def get_previous_campaigns(self, client_name: str) -> Optional[str]:
        """
        Get examples of previous successful campaigns.

        Args:
            client_name: Client slug

        Returns:
            Previous campaigns text, or None if not found
        """
        client_path = self._get_client_path(client_name)
        campaigns_path = client_path / "previous_campaigns.txt"

        return self._read_file(campaigns_path)

    def get_target_audience(self, client_name: str) -> Optional[str]:
        """
        Get target audience information.

        Args:
            client_name: Client slug

        Returns:
            Target audience text, or None if not found
        """
        client_path = self._get_client_path(client_name)
        audience_path = client_path / "target_audience.txt"

        return self._read_file(audience_path)

    def get_seasonal_themes(self, client_name: str) -> Optional[str]:
        """
        Get seasonal themes and calendar information.

        Args:
            client_name: Client slug

        Returns:
            Seasonal themes text, or None if not found
        """
        client_path = self._get_client_path(client_name)
        themes_path = client_path / "seasonal_themes.txt"

        return self._read_file(themes_path)

    def list_available_documents(self, client_name: str) -> List[str]:
        """
        List all available RAG documents for a client.

        Args:
            client_name: Client slug

        Returns:
            List of available document names
        """
        client_path = self._get_client_path(client_name)

        if not client_path.exists():
            logger.warning(f"Client RAG directory not found: {client_path}")
            return []

        try:
            files = [f.name for f in client_path.iterdir() if f.is_file()]
            logger.info(f"Found {len(files)} RAG documents for {client_name}")
            return files

        except Exception as e:
            logger.error(f"Error listing RAG documents: {str(e)}")
            return []

    def get_all_data(self, client_name: str) -> Dict[str, Any]:
        """
        Get all available RAG data for a client.

        This is the main method used in Stage 1 (Planning) to fetch
        all brand and product context.

        Args:
            client_name: Client slug

        Returns:
            Dictionary containing all available RAG data:
            {
                "brand_voice": str,
                "content_pillars": str,
                "product_catalog": dict,
                "design_guidelines": str,
                "previous_campaigns": str,
                "target_audience": str,
                "seasonal_themes": str,
                "metadata": {
                    "client_name": str,
                    "available_documents": list
                }
            }
        """
        logger.info(f"Fetching all RAG data for {client_name}")

        result = {
            "brand_voice": self.get_brand_voice(client_name),
            "content_pillars": self.get_content_pillars(client_name),
            "product_catalog": self.get_product_catalog(client_name),
            "design_guidelines": self.get_design_guidelines(client_name),
            "previous_campaigns": self.get_previous_campaigns(client_name),
            "target_audience": self.get_target_audience(client_name),
            "seasonal_themes": self.get_seasonal_themes(client_name),
            "metadata": {
                "client_name": client_name,
                "available_documents": self.list_available_documents(client_name)
            }
        }

        # Count how many documents were found
        found_count = sum(1 for v in result.values() if v is not None and v != result["metadata"])
        logger.info(f"RAG data fetch complete: {found_count} documents found for {client_name}")

        return result

    def format_for_prompt(self, client_name: str) -> str:
        """
        Format all RAG data as a text block for inclusion in AI prompts.

        Args:
            client_name: Client slug

        Returns:
            Formatted text block with all RAG data
        """
        data = self.get_all_data(client_name)

        sections = []

        if data["brand_voice"]:
            sections.append(f"## Brand Voice\n\n{data['brand_voice']}")

        if data["content_pillars"]:
            sections.append(f"## Content Pillars\n\n{data['content_pillars']}")

        if data["product_catalog"]:
            if isinstance(data["product_catalog"], dict):
                products_text = json.dumps(data["product_catalog"], indent=2)
            else:
                products_text = str(data["product_catalog"])
            sections.append(f"## Product Catalog\n\n{products_text}")

        if data["design_guidelines"]:
            sections.append(f"## Design Guidelines\n\n{data['design_guidelines']}")

        if data["target_audience"]:
            sections.append(f"## Target Audience\n\n{data['target_audience']}")

        if data["previous_campaigns"]:
            sections.append(f"## Previous Successful Campaigns\n\n{data['previous_campaigns']}")

        if data["seasonal_themes"]:
            sections.append(f"## Seasonal Themes\n\n{data['seasonal_themes']}")

        if not sections:
            return f"# Brand Intelligence for {client_name}\n\nNo brand documents available."

        formatted = f"# Brand Intelligence for {client_name}\n\n" + "\n\n---\n\n".join(sections)

        logger.info(f"Formatted RAG data for prompt: {len(formatted)} characters")

        return formatted
