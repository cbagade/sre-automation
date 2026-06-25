"""File-based cache manager for operational signals data."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class CacheManager:
    """Manages file-based caching for operational signals data."""
    
    def __init__(self, cache_dir: str = "data/cache/operational_signals"):
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, region: str, date: str) -> str:
        """Generate cache key for region and date.
        
        Args:
            region: Region name (e.g., 'Tokyo', 'Dallas')
            date: Date in format 'YYYY-MM-DD'
            
        Returns:
            str: Cache key
        """
        return f"{region}_{date}"
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get cache file path for a cache key.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Path: Path to cache file
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def get_cached_data(self, region: str, date: str) -> Optional[Dict[str, Any]]:
        """Get cached data for region and date.
        
        Args:
            region: Region name
            date: Date in format 'YYYY-MM-DD'
            
        Returns:
            Optional[Dict]: Cached data if exists, None otherwise
        """
        cache_key = self._get_cache_key(region, date)
        cache_file = self._get_cache_file_path(cache_key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading cache file {cache_file}: {e}")
            return None
    
    def save_cached_data(self, region: str, date: str, timeslot: str, data: Dict[str, Any]) -> bool:
        """Save data to cache.
        
        Args:
            region: Region name
            date: Date in format 'YYYY-MM-DD'
            timeslot: Timeslot (e.g., '00_hr-06_hr')
            data: Data to cache
            
        Returns:
            bool: True if successful, False otherwise
        """
        cache_key = self._get_cache_key(region, date)
        cache_file = self._get_cache_file_path(cache_key)
        
        cache_data = {
            "region": region,
            "date": date,
            "timeslot": timeslot,
            "cached_at": datetime.utcnow().isoformat(),
            "data": data
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error writing cache file {cache_file}: {e}")
            return False
    
    def get_cached_timeslot(self, region: str, date: str) -> Optional[str]:
        """Get the timeslot of cached data.
        
        Args:
            region: Region name
            date: Date in format 'YYYY-MM-DD'
            
        Returns:
            Optional[str]: Timeslot if cache exists, None otherwise
        """
        cached_data = self.get_cached_data(region, date)
        if cached_data:
            return cached_data.get("timeslot")
        return None
    
    def clear_cache(self, region: Optional[str] = None, date: Optional[str] = None) -> int:
        """Clear cache files.
        
        Args:
            region: Optional region to clear (clears all if None)
            date: Optional date to clear (clears all if None)
            
        Returns:
            int: Number of files deleted
        """
        deleted_count = 0
        
        if region and date:
            # Clear specific cache
            cache_key = self._get_cache_key(region, date)
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                cache_file.unlink()
                deleted_count = 1
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                deleted_count += 1
        
        return deleted_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict: Cache statistics
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "total_files": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }

# Made with Bob
