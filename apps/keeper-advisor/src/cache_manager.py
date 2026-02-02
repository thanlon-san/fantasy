"""
Global cache manager with TTL support
Provides persistent caching across CLI runs
"""

import json
import shelve
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Persistent cache with time-to-live (TTL) support"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory for cache files (defaults to .cache/)
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / '.cache'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / 'data'
    
    def get(self, key: str, max_age_hours: float = 24) -> Optional[Any]:
        """
        Get cached value if not expired
        
        Args:
            key: Cache key
            max_age_hours: Maximum age in hours (default 24)
            
        Returns:
            Cached value or None if expired/missing
        """
        try:
            with shelve.open(str(self.cache_file)) as db:
                if key not in db:
                    return None
                
                cached_at, value = db[key]
                age_hours = (datetime.now() - cached_at).total_seconds() / 3600
                
                if age_hours < max_age_hours:
                    logger.debug(f"Cache HIT: {key} (age: {age_hours:.1f}h)")
                    return value
                else:
                    logger.debug(f"Cache EXPIRED: {key} (age: {age_hours:.1f}h)")
                    return None
                    
        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Cache a value with timestamp
        
        Args:
            key: Cache key
            value: Value to cache
        """
        try:
            with shelve.open(str(self.cache_file)) as db:
                db[key] = (datetime.now(), value)
            logger.debug(f"Cache SET: {key}")
        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")
    
    def delete(self, key: str) -> None:
        """Delete a cached value"""
        try:
            with shelve.open(str(self.cache_file)) as db:
                if key in db:
                    del db[key]
                    logger.debug(f"Cache DELETE: {key}")
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
    
    def clear(self) -> None:
        """Clear all cached values"""
        try:
            with shelve.open(str(self.cache_file)) as db:
                db.clear()
            logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
    
    def clear_expired(self, max_age_hours: float = 168) -> int:
        """
        Remove expired entries
        
        Args:
            max_age_hours: Maximum age to keep (default 7 days)
            
        Returns:
            Number of entries removed
        """
        removed = 0
        try:
            with shelve.open(str(self.cache_file)) as db:
                keys_to_remove = []
                
                for key in db.keys():
                    try:
                        cached_at, _ = db[key]
                        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
                        
                        if age_hours > max_age_hours:
                            keys_to_remove.append(key)
                    except:
                        keys_to_remove.append(key)  # Remove corrupted entries
                
                for key in keys_to_remove:
                    del db[key]
                    removed += 1
                
            if removed > 0:
                logger.info(f"Removed {removed} expired cache entries")
                
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")
        
        return removed


# Global cache instance
_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
