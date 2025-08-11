"""Simple audio cache for common phrases to reduce TTS API calls"""

import hashlib
from typing import Dict, Optional
from datetime import datetime, timedelta


class SimpleAudioCache:
    """Simple LRU cache for audio responses"""
    
    def __init__(self, ttl_hours: int = 2, max_size: int = 100):
        self._cache: Dict[str, tuple[bytes, datetime]] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._max_size = max_size
        self._hit_count = 0
        self._miss_count = 0
        print(f"✅ SimpleAudioCache initialized (TTL: {ttl_hours}h, Max: {max_size} items)")
    
    def _get_cache_key(self, text: str, voice: str = "alloy") -> str:
        """Generate cache key from text and voice settings"""
        key_string = f"{text}_{voice}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, text: str, voice: str = "alloy") -> Optional[bytes]:
        """Get cached audio if available and not expired"""
        key = self._get_cache_key(text, voice)
        
        if key in self._cache:
            audio_data, cached_time = self._cache[key]
            
            # Check if cache is still valid
            if datetime.now() - cached_time < self._ttl:
                self._hit_count += 1
                print(f"🎯 Audio cache HIT for: {text[:30]}...")
                return audio_data
            else:
                # Remove expired entry
                del self._cache[key]
        
        self._miss_count += 1
        print(f"❌ Audio cache MISS for: {text[:30]}...")
        return None
    
    def set(self, text: str, audio_data: bytes, voice: str = "alloy"):
        """Store audio in cache"""
        key = self._get_cache_key(text, voice)
        
        # Remove oldest item if cache is full (simple LRU)
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            print(f"🗑️ Evicted oldest cache entry")
        
        self._cache[key] = (audio_data, datetime.now())
        print(f"💾 Cached audio for: {text[:30]}...")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        total = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total * 100) if total > 0 else 0
        
        return {
            "hits": self._hit_count,
            "misses": self._miss_count,
            "total": total,
            "hit_rate": round(hit_rate, 2),
            "cache_size": len(self._cache),
            "max_size": self._max_size
        }
    
    def clear(self):
        """Clear all cached items"""
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        print("🗑️ Audio cache cleared")


# Global cache instance
_audio_cache = None

def get_audio_cache() -> SimpleAudioCache:
    """Get global audio cache instance"""
    global _audio_cache
    if _audio_cache is None:
        _audio_cache = SimpleAudioCache()
    return _audio_cache