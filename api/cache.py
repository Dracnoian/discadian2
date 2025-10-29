"""API response caching."""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger('EMCBot.API.Cache')


class APICache:
    """In-memory cache for API responses."""
    
    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache.
        
        Args:
            ttl_seconds: Time to live for cache entries in seconds (default 5 minutes)
        """
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    def _make_key(self, endpoint: str, identifier: str) -> str:
        """Generate cache key."""
        return f"{endpoint}:{identifier}"
    
    async def get(self, endpoint: str, identifier: str) -> Optional[Dict]:
        """Get cached response.
        
        Args:
            endpoint: API endpoint (e.g., 'players', 'towns')
            identifier: Resource identifier (UUID, name, etc.)
            
        Returns:
            Cached data or None if not found/expired
        """
        async with self._lock:
            key = self._make_key(endpoint, identifier)
            
            if key in self.cache:
                entry = self.cache[key]
                
                # Check if expired
                if datetime.now() - entry['timestamp'] < self.ttl:
                    logger.debug(f"Cache hit: {key}")
                    return entry['data']
                else:
                    # Remove expired entry
                    del self.cache[key]
                    logger.debug(f"Cache expired: {key}")
            
            logger.debug(f"Cache miss: {key}")
            return None
    
    async def set(self, endpoint: str, identifier: str, data: Dict) -> None:
        """Store response in cache.
        
        Args:
            endpoint: API endpoint
            identifier: Resource identifier
            data: Data to cache
        """
        async with self._lock:
            key = self._make_key(endpoint, identifier)
            self.cache[key] = {
                'data': data,
                'timestamp': datetime.now()
            }
            logger.debug(f"Cached: {key}")
    
    async def invalidate(self, endpoint: str, identifier: str) -> None:
        """Invalidate a cache entry.
        
        Args:
            endpoint: API endpoint
            identifier: Resource identifier
        """
        async with self._lock:
            key = self._make_key(endpoint, identifier)
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Invalidated: {key}")
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared {count} cache entries")
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self.cache.items()
                if now - entry['timestamp'] >= self.ttl
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            'entries': len(self.cache),
            'ttl_seconds': self.ttl.total_seconds()
        }
