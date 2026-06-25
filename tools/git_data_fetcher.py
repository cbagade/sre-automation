"""Tool to fetch operational signals data from git repository."""

import json
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.operational_signals_config import GIT_CONFIG, JSON_FILES, AVAILABLE_REGIONS
except ImportError:
    # Fallback to defaults if config not found
    GIT_CONFIG = {
        "git_url": "https://raw.githubusercontent.com/your-org/operational-signals",
        "branch": "main",
        "token": None,
    }
    JSON_FILES = [
        "active_critical_immediate_alerts.json",
        "clusters_needing_attention.json",
    ]
    AVAILABLE_REGIONS = ["Tokyo", "Dallas", "Paris"]


class GitDataFetcher:
    """Fetches operational signals data from git repository."""
    
    def __init__(self, git_url: Optional[str] = None, branch: Optional[str] = None, token: Optional[str] = None):
        """Initialize git data fetcher.
        
        Args:
            git_url: Base git URL (e.g., 'https://raw.githubusercontent.com/org/repo')
            branch: Branch name (default: 'main')
            token: Authentication token (optional)
        """
        self.git_url = git_url or GIT_CONFIG.get("git_url", "https://raw.githubusercontent.com/your-org/operational-signals")
        self.branch = branch or GIT_CONFIG.get("branch", "main")
        self.token = token or GIT_CONFIG.get("token")
        
        # List of JSON files to fetch
        self.json_files = JSON_FILES
    
    def _construct_url(self, region: str, date: str, timeslot: str, filename: str) -> str:
        """Construct URL for fetching data from git.
        
        Args:
            region: Region name (e.g., 'Tokyo', 'Dallas')
            date: Date in format 'YYYY-MM-DD'
            timeslot: Timeslot (e.g., '00_hr-06_hr')
            filename: JSON filename
            
        Returns:
            str: Full URL to fetch data
        """
        # For GitHub Enterprise, convert tree URL to raw URL
        # Example: https://github.ibm.com/VMWSolutions/sre-report/tree/master/TOKST/...
        # Becomes: https://raw.github.ibm.com/VMWSolutions/sre-report/master/TOKST/...
        
        git_url = self.git_url
        
        # Convert github.ibm.com to raw.github.ibm.com if needed
        if "github.ibm.com" in git_url and not git_url.startswith("https://raw."):
            git_url = git_url.replace("https://github.ibm.com", "https://raw.github.ibm.com")
        
        # Construct URL without 'data/' folder since regions are at root level
        return f"{git_url}/{self.branch}/{region}/{date}/{timeslot}/{filename}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for git requests, including authentication if configured.
        
        Returns:
            Dict: HTTP headers
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "OpsPilot-AI/1.0"
        }
        
        # Add authentication if token is provided
        if self.token:
            # GitHub/GitLab use Bearer token
            headers["Authorization"] = f"token {self.token}"
        
        return headers
    
    def fetch_file(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch a single JSON file from git.
        
        Args:
            url: URL to fetch
            
        Returns:
            Optional[Dict]: Parsed JSON data if successful, None otherwise
        """
        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # File doesn't exist yet
                return None
            elif response.status_code == 401:
                print(f"Authentication failed for {url}. Check your git token.")
                return None
            elif response.status_code == 403:
                print(f"Access forbidden for {url}. Check your git token permissions.")
                return None
            else:
                print(f"Error fetching {url}: Status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request error fetching {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {url}: {e}")
            return None
    
    def fetch_timeslot_data(self, region: str, date: str, timeslot: str) -> Dict[str, Any]:
        """Fetch all data for a specific region, date, and timeslot.
        
        Args:
            region: Region name
            date: Date in format 'YYYY-MM-DD'
            timeslot: Timeslot
            
        Returns:
            Dict: Dictionary with all fetched data
        """
        result = {
            "region": region,
            "date": date,
            "timeslot": timeslot,
            "files": {},
            "fetch_errors": []
        }
        
        for filename in self.json_files:
            url = self._construct_url(region, date, timeslot, filename)
            data = self.fetch_file(url)
            
            if data is not None:
                result["files"][filename] = data
            else:
                result["fetch_errors"].append(filename)
        
        return result
    
    def check_timeslot_exists(self, region: str, date: str, timeslot: str) -> bool:
        """Check if data exists for a specific timeslot.
        
        Args:
            region: Region name
            date: Date in format 'YYYY-MM-DD'
            timeslot: Timeslot
            
        Returns:
            bool: True if at least one file exists, False otherwise
        """
        # Check if at least one file exists for this timeslot
        # Check multiple files since not all files may exist for every timeslot
        headers = self._get_headers()
        for filename in self.json_files:  # Check all files to ensure we find available data
            url = self._construct_url(region, date, timeslot, filename)
            try:
                response = requests.head(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                continue
        
        return False
    
    def get_latest_available_timeslot(self, region: str, date: str, current_timeslot: str) -> Optional[str]:
        """Get the latest available timeslot for a date.
        
        Args:
            region: Region name
            date: Date in format 'YYYY-MM-DD'
            current_timeslot: Current timeslot to check from
            
        Returns:
            Optional[str]: Latest available timeslot or None
        """
        from utils.date_utils import get_timeslot_order
        
        timeslots = get_timeslot_order()
        current_idx = timeslots.index(current_timeslot)
        
        # Check from current timeslot backwards to find the latest available
        for i in range(current_idx, -1, -1):
            if self.check_timeslot_exists(region, date, timeslots[i]):
                return timeslots[i]
        
        return None
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions.
        
        Returns:
            List[str]: List of region names
        """
        return AVAILABLE_REGIONS


def fetch_operational_signals(region: str, date: str, timeslot: str,
                              git_url: Optional[str] = None, branch: Optional[str] = None,
                              token: Optional[str] = None) -> Dict[str, Any]:
    """Fetch operational signals data from git repository.
    
    Args:
        region: Region name
        date: Date in format 'YYYY-MM-DD'
        timeslot: Timeslot
        git_url: Optional base git URL
        branch: Optional branch name
        token: Optional authentication token
        
    Returns:
        Dict: Fetched data
    """
    fetcher = GitDataFetcher(git_url=git_url, branch=branch, token=token)
    return fetcher.fetch_timeslot_data(region, date, timeslot)

# Made with Bob
