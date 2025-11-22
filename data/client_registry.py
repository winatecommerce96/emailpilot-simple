import httpx
import logging
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

class ClientRegistry:
    """
    Registry to resolve client identifiers (slugs, IDs) to canonical names
    using the central EmailPilot API.
    """
    def __init__(self, api_url: str = "https://app.emailpilot.ai/api/clients"):
        self.api_url = api_url
        self.clients_by_slug: Dict[str, Dict[str, Any]] = {}
        self.clients_by_id: Dict[str, Dict[str, Any]] = {}
        self.clients_by_name: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    async def initialize(self):
        """Fetch clients from the API and build lookup maps."""
        try:
            logger.info(f"Fetching clients from {self.api_url}...")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.api_url)
                response.raise_for_status()
                clients = response.json()
                
                for client_data in clients:
                    # Index by slug
                    if 'slug' in client_data:
                        self.clients_by_slug[client_data['slug']] = client_data
                    
                    # Index by ID
                    if 'id' in client_data:
                        self.clients_by_id[str(client_data['id'])] = client_data
                        
                    # Index by Name (normalized)
                    if 'name' in client_data:
                        self.clients_by_name[client_data['name'].lower()] = client_data
                        
            self._initialized = True
            logger.info(f"ClientRegistry initialized with {len(clients)} clients")
            
        except Exception as e:
            logger.error(f"Failed to initialize ClientRegistry: {e}")
            # We don't raise here because we want the app to start even if this fails
            # (e.g. offline dev). We'll just fail to resolve names later.

    def resolve_client_name(self, identifier: str) -> str:
        """
        Resolve a client identifier (slug, id, or name) to the canonical client name.
        Returns the original identifier if no match found.
        """
        if not self._initialized:
            logger.warning("ClientRegistry not initialized, returning original identifier")
            return identifier
            
        identifier_lower = identifier.lower()
        
        # 1. Try slug match (exact)
        if identifier in self.clients_by_slug:
            name = self.clients_by_slug[identifier]['name']
            logger.info(f"Resolved client slug '{identifier}' to '{name}'")
            return name
            
        # 2. Try ID match
        if identifier in self.clients_by_id:
            name = self.clients_by_id[identifier]['name']
            logger.info(f"Resolved client ID '{identifier}' to '{name}'")
            return name
            
        # 3. Try name match (case-insensitive)
        if identifier_lower in self.clients_by_name:
            name = self.clients_by_name[identifier_lower]['name']
            logger.info(f"Resolved client name '{identifier}' to '{name}'")
            return name
            
        # 4. Try finding slug in the identifier (e.g. if identifier is a mix)
        # or if the slug is slightly different
        for slug, data in self.clients_by_slug.items():
            if slug == identifier_lower:
                return data['name']
                
        logger.warning(f"Could not resolve client identifier '{identifier}', using as-is")
        return identifier
