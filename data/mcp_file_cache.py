"""
Local file-based cache for MCP data to speed up development iterations.

This cache is intended for development use only and should be disabled in production.
Environment variable USE_MCP_CACHE='true' enables caching.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import hashlib


class MCPFileCache:
    """File-based cache manager for MCP data."""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache files. Defaults to ./data/mcp_cache
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent / "mcp_cache"

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_cache_key(self, client: str, date_range: Tuple[str, str]) -> str:
        """
        Generate unique cache key for client and date range.

        Args:
            client: Client name
            date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format

        Returns:
            Hash string to use as cache filename
        """
        key_string = f"{client}_{date_range[0]}_{date_range[1]}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get full path to cache file."""
        return self.cache_dir / f"{cache_key}.json"

    def _get_metadata_path(self, cache_key: str) -> Path:
        """Get full path to cache metadata file."""
        return self.cache_dir / f"{cache_key}.meta.json"

    def save_cache(
        self,
        client: str,
        date_range: Tuple[str, str],
        data: Dict[str, Any]
    ) -> None:
        """
        Save MCP data to cache file.

        Args:
            client: Client name
            date_range: Tuple of (start_date, end_date)
            data: MCP data dictionary to cache
        """
        cache_key = self._generate_cache_key(client, date_range)
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)

        # Save data
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)

        # Save metadata
        metadata = {
            'client': client,
            'start_date': date_range[0],
            'end_date': date_range[1],
            'cached_at': datetime.now().isoformat(),
            'cache_key': cache_key
        }
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Cached MCP data for {client} ({date_range[0]} to {date_range[1]})")

    def load_cache(
        self,
        client: str,
        date_range: Tuple[str, str],
        max_age_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Load MCP data from cache if exists and not expired.

        Args:
            client: Client name
            date_range: Tuple of (start_date, end_date)
            max_age_days: Maximum age of cache in days before expiration

        Returns:
            Cached data dictionary if valid, None if cache miss or expired
        """
        cache_key = self._generate_cache_key(client, date_range)
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)

        # Check if cache files exist
        if not cache_path.exists() or not meta_path.exists():
            return None

        # Load and check metadata
        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            cached_at = datetime.fromisoformat(metadata['cached_at'])
            age = datetime.now() - cached_at

            # Check if cache is expired
            if age > timedelta(days=max_age_days):
                print(f"Cache expired for {client} (age: {age.days} days)")
                return None

            # Load cached data
            with open(cache_path, 'r') as f:
                data = json.load(f)

            print(f"✓ Loaded cached MCP data for {client} ({date_range[0]} to {date_range[1]}) [age: {age.days}d]")
            return data

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading cache for {client}: {e}")
            return None

    def cleanup_old_cache(self, max_age_days: int = 30) -> int:
        """
        Remove cache files older than specified age.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of cache files removed
        """
        removed_count = 0
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        # Iterate through all .meta.json files
        for meta_path in self.cache_dir.glob("*.meta.json"):
            try:
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)

                cached_at = datetime.fromisoformat(metadata['cached_at'])

                if cached_at < cutoff_date:
                    # Remove both cache and metadata files
                    cache_key = metadata['cache_key']
                    cache_path = self._get_cache_path(cache_key)

                    if cache_path.exists():
                        cache_path.unlink()
                    meta_path.unlink()

                    removed_count += 1
                    print(f"Removed old cache: {metadata['client']} ({metadata['start_date']} to {metadata['end_date']})")

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error processing cache file {meta_path}: {e}")
                continue

        if removed_count > 0:
            print(f"✓ Cleaned up {removed_count} old cache files")

        return removed_count

    def clear_all_cache(self) -> int:
        """
        Remove all cache files.

        Returns:
            Number of cache files removed
        """
        removed_count = 0

        for cache_file in self.cache_dir.glob("*"):
            if cache_file.is_file():
                cache_file.unlink()
                removed_count += 1

        print(f"✓ Cleared all cache ({removed_count} files)")
        return removed_count

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about cached data.

        Returns:
            Dictionary with cache statistics
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        meta_files = list(self.cache_dir.glob("*.meta.json"))

        # Exclude .meta.json from cache file count
        data_files = [f for f in cache_files if not f.name.endswith('.meta.json')]

        total_size = sum(f.stat().st_size for f in data_files)

        cached_clients = []
        for meta_path in meta_files:
            try:
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                cached_clients.append({
                    'client': metadata['client'],
                    'date_range': f"{metadata['start_date']} to {metadata['end_date']}",
                    'cached_at': metadata['cached_at']
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return {
            'cache_dir': str(self.cache_dir),
            'total_cached_datasets': len(data_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cached_clients': cached_clients
        }


# Singleton instance
_cache_instance: Optional[MCPFileCache] = None


def get_cache() -> MCPFileCache:
    """Get or create singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        cache_dir = os.getenv('MCP_CACHE_DIR')
        _cache_instance = MCPFileCache(cache_dir)
    return _cache_instance
