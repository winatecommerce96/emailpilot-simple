"""
MCP Data Cache

Provides temporary in-memory caching for MCP data to avoid redundant API calls
across workflow stages.
"""

import time
from typing import Any, Dict, Optional
import json


class MCPCache:
    """
    In-memory cache for MCP data with TTL (Time To Live) support.

    The cache stores MCP data fetched in Stage 1 (Planning) and reuses it
    in Stage 2 (Structuring) and Stage 3 (Brief Generation) to avoid
    making redundant API calls.
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize the MCP cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 1 hour)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Store data in the cache with TTL.

        Args:
            key: Cache key (e.g., "mcp_data:rogue-creamery:2025-12-01_2025-12-31")
            data: Data to cache (will be JSON-serializable)
            ttl: Time-to-live in seconds (uses default if None)
        """
        expires_at = time.time() + (ttl or self._default_ttl)

        self._cache[key] = {
            "data": data,
            "expires_at": expires_at,
            "created_at": time.time()
        }

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve data from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached data if exists and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]

        # Check if expired
        if time.time() > entry["expires_at"]:
            del self._cache[key]
            return None

        return entry["data"]

    def has(self, key: str) -> bool:
        """
        Check if key exists in cache and is not expired.

        Args:
            key: Cache key

        Returns:
            True if key exists and not expired, False otherwise
        """
        return self.get(key) is not None

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, keys, etc.)
        """
        current_time = time.time()
        expired_keys = []
        active_keys = []

        for key, entry in self._cache.items():
            if current_time > entry["expires_at"]:
                expired_keys.append(key)
            else:
                active_keys.append(key)

        return {
            "total_keys": len(self._cache),
            "active_keys": len(active_keys),
            "expired_keys": len(expired_keys),
            "keys": active_keys
        }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time > entry["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


# Global cache instance (singleton pattern)
_global_cache: Optional[MCPCache] = None


def get_cache(ttl: int = 3600) -> MCPCache:
    """
    Get the global MCP cache instance (singleton).

    Args:
        ttl: Default TTL for cache entries

    Returns:
        Global MCPCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = MCPCache(default_ttl=ttl)
    return _global_cache
