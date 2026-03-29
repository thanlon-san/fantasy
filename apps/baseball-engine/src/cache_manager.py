"""
Global cache manager with TTL support.

Backed by the SQLite database layer (database.py) for persistent,
concurrent-safe caching with proper TTL and eviction.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """Persistent cache with time-to-live (TTL) support, backed by SQLite."""

    def get(self, key: str, max_age_hours: float = 24) -> Optional[Any]:
        try:
            from src.database import cache_get
            value = cache_get(key, max_age_hours=max_age_hours)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
            return value
        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_hours: Optional[float] = None) -> None:
        try:
            from src.database import cache_set
            cache_set(key, value, ttl_hours=ttl_hours)
            logger.debug(f"Cache SET: {key}")
        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")

    def delete(self, key: str) -> None:
        try:
            from src.database import cache_delete
            cache_delete(key)
            logger.debug(f"Cache DELETE: {key}")
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")

    def clear(self) -> None:
        try:
            from src.database import get_connection
            with get_connection() as conn:
                conn.execute("DELETE FROM cache")
            logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")

    def clear_expired(self, max_age_hours: float = 168) -> int:
        try:
            from src.database import cache_clear_expired
            removed = cache_clear_expired()
            if removed > 0:
                logger.info(f"Removed {removed} expired cache entries")
            return removed
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")
            return 0


_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
