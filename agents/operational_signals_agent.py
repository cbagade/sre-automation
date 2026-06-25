"""Operational Signals Agent for fetching and managing daily issues from git repository."""

from typing import Dict, Any, Optional
from datetime import datetime

from tools.git_data_fetcher import GitDataFetcher
from utils.cache_manager import CacheManager
from utils.date_utils import get_current_timeslot, is_later_timeslot, format_date_for_git
from utils.json_parsers import parser_registry


class OperationalSignalsAgent:
    """Agent to fetch and manage operational signals data."""
    
    def __init__(self, git_url: Optional[str] = None, branch: Optional[str] = None,
                 token: Optional[str] = None):
        """Initialize operational signals agent.
        
        Args:
            git_url: Optional base git URL
            branch: Optional branch name
            token: Optional authentication token
        """
        self.git_fetcher = GitDataFetcher(git_url=git_url, branch=branch, token=token)
        self.cache_manager = CacheManager()
    
    def get_operational_signals(self, region: str, date: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get operational signals for a specific region and date.
        
        This method implements intelligent caching:
        1. Check if cached data exists for the region and date
        2. If cached data exists, check if a newer timeslot is available on git
        3. If newer data is available, fetch and update cache
        4. Otherwise, return cached data
        
        Args:
            region: Region name (e.g., 'Tokyo', 'Dallas')
            date: Date in format 'YYYY-MM-DD'
            force_refresh: Force refresh from git, ignoring cache
            
        Returns:
            Dict: Operational signals data with metadata
        """
        current_timeslot = get_current_timeslot()
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.cache_manager.get_cached_data(region, date)
            
            if cached_data:
                cached_timeslot = cached_data.get("timeslot")
                
                # Check if we need to fetch newer data
                if cached_timeslot:
                    # If cached timeslot is the current or later, use cache
                    if not is_later_timeslot(current_timeslot, cached_timeslot):
                        return {
                            "status": "success",
                            "source": "cache",
                            "region": region,
                            "date": date,
                            "timeslot": cached_timeslot,
                            "data": cached_data.get("data", {}),
                            "cached_at": cached_data.get("cached_at")
                        }
                    
                    # Check if newer timeslot data is available on git
                    latest_timeslot = self.git_fetcher.get_latest_available_timeslot(
                        region, date, current_timeslot
                    )
                    
                    if latest_timeslot and is_later_timeslot(latest_timeslot, cached_timeslot):
                        # Fetch newer data
                        return self._fetch_and_cache(region, date, latest_timeslot)
                    else:
                        # No newer data available, use cache
                        return {
                            "status": "success",
                            "source": "cache",
                            "region": region,
                            "date": date,
                            "timeslot": cached_timeslot,
                            "data": cached_data.get("data", {}),
                            "cached_at": cached_data.get("cached_at")
                        }
        
        # No cache or force refresh - fetch from git
        latest_timeslot = self.git_fetcher.get_latest_available_timeslot(
            region, date, current_timeslot
        )
        
        if latest_timeslot:
            return self._fetch_and_cache(region, date, latest_timeslot)
        else:
            return {
                "status": "error",
                "source": "git",
                "region": region,
                "date": date,
                "message": f"No data available for {region} on {date}",
                "data": {}
            }
    
    def _fetch_and_cache(self, region: str, date: str, timeslot: str) -> Dict[str, Any]:
        """Fetch data from git and cache it.
        
        Args:
            region: Region name
            date: Date in format 'YYYY-MM-DD'
            timeslot: Timeslot to fetch
            
        Returns:
            Dict: Fetched data with metadata
        """
        # Fetch from git
        git_data = self.git_fetcher.fetch_timeslot_data(region, date, timeslot)
        
        if git_data.get("files"):
            # Cache the data
            self.cache_manager.save_cached_data(region, date, timeslot, git_data)
            
            return {
                "status": "success",
                "source": "git",
                "region": region,
                "date": date,
                "timeslot": timeslot,
                "data": git_data,
                "fetch_errors": git_data.get("fetch_errors", [])
            }
        else:
            return {
                "status": "error",
                "source": "git",
                "region": region,
                "date": date,
                "timeslot": timeslot,
                "message": "No data files found",
                "data": {},
                "fetch_errors": git_data.get("fetch_errors", [])
            }
    
    def get_available_regions(self) -> list:
        """Get list of available regions.
        
        Returns:
            list: List of region names
        """
        return self.git_fetcher.get_available_regions()
    
    def parse_issues_by_category(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and organize issues by category from fetched data.
        
        Uses file-specific parsers from the parser registry.
        
        Args:
            data: Raw data from git
            
        Returns:
            Dict: Organized issues by category with appropriate structure
        """
        files = data.get("files", {})
        
        parsed_issues = {}
        
        for filename, file_data in files.items():
            # Remove .json extension for category name
            category = filename.replace(".json", "").replace("_", " ").title()
            
            # Use parser registry to parse file-specific structure
            parsed_data = parser_registry.parse(filename, file_data)
            
            if parsed_data:
                parsed_issues[category] = parsed_data
        
        return parsed_issues
    
    def get_summary_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary statistics from operational signals data.
        
        Args:
            data: Operational signals data
            
        Returns:
            Dict: Summary statistics
        """
        parsed_issues = self.parse_issues_by_category(data)
        
        total_issues = sum(category["count"] for category in parsed_issues.values())
        total_categories = len(parsed_issues)
        
        return {
            "total_issues": total_issues,
            "total_categories": total_categories,
            "categories": list(parsed_issues.keys()),
            "breakdown": {
                category: info["count"] 
                for category, info in parsed_issues.items()
            }
        }
    
    def clear_cache(self, region: Optional[str] = None, date: Optional[str] = None) -> int:
        """Clear cache for specific region/date or all cache.
        
        Args:
            region: Optional region to clear
            date: Optional date to clear
            
        Returns:
            int: Number of cache files deleted
        """
        return self.cache_manager.clear_cache(region, date)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict: Cache statistics
        """
        return self.cache_manager.get_cache_stats()

# Made with Bob
