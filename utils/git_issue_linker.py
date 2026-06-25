"""Git Issue Linker - Manages mappings between Operational Signals and Git Issues."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class GitIssueLinker:
    """Manages file-based storage for linking Git issues to Operational Signals."""
    
    def __init__(self, storage_file: str = "data/cache/git_issue_links.json"):
        """Initialize Git Issue Linker.
        
        Args:
            storage_file: Path to the JSON file storing the mappings
        """
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage file if it doesn't exist
        if not self.storage_file.exists():
            self._save_data({})
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from storage file.
        
        Returns:
            Dict: Stored data
        """
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading git issue links: {e}")
            return {}
    
    def _save_data(self, data: Dict[str, Any]) -> bool:
        """Save data to storage file.
        
        Args:
            data: Data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving git issue links: {e}")
            return False
    
    def _generate_signal_key(self, signal_info: Dict[str, str]) -> str:
        """Generate a unique key for an operational signal.
        
        Args:
            signal_info: Dictionary containing signal identification info
                - component: Component name (e.g., 'Hierarchical', 'Clusters')
                - category: Category name (optional, for hierarchical)
                - alert_name: Alert/issue name
                
        Returns:
            str: Unique key for the signal
        """
        component = signal_info.get('component', '')
        category = signal_info.get('category', '')
        alert_name = signal_info.get('alert_name', '')
        
        # Create a normalized key
        if category:
            key = f"{component}::{category}::{alert_name}"
        else:
            key = f"{component}::{alert_name}"
        
        return key.lower().replace(" ", "_").replace("/", "_")
    
    def link_issue(self, signal_info: Dict[str, str], git_issue_url: str) -> bool:
        """Link a Git issue to an operational signal.
        
        Args:
            signal_info: Dictionary containing signal identification info
            git_issue_url: Git issue URL or ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        signal_key = self._generate_signal_key(signal_info)
        data = self._load_data()
        
        # Initialize signal entry if it doesn't exist
        if signal_key not in data:
            data[signal_key] = {
                "signal_info": signal_info,
                "linked_issues": [],
                "created_at": datetime.utcnow().isoformat()
            }
        
        # Add the issue if it's not already linked
        linked_issues = data[signal_key]["linked_issues"]
        
        # Check if issue already exists
        issue_exists = any(
            issue["url"] == git_issue_url 
            for issue in linked_issues
        )
        
        if not issue_exists:
            linked_issues.append({
                "url": git_issue_url,
                "linked_at": datetime.utcnow().isoformat()
            })
            data[signal_key]["updated_at"] = datetime.utcnow().isoformat()
            return self._save_data(data)
        
        return True  # Already exists, consider it successful
    
    def get_linked_issues(self, signal_info: Dict[str, str]) -> List[Dict[str, str]]:
        """Get all Git issues linked to an operational signal.
        
        Args:
            signal_info: Dictionary containing signal identification info
            
        Returns:
            List[Dict]: List of linked issues with their metadata
        """
        signal_key = self._generate_signal_key(signal_info)
        data = self._load_data()
        
        if signal_key in data:
            return data[signal_key].get("linked_issues", [])
        
        return []
    
    def unlink_issue(self, signal_info: Dict[str, str], git_issue_url: str) -> bool:
        """Unlink a Git issue from an operational signal.
        
        Args:
            signal_info: Dictionary containing signal identification info
            git_issue_url: Git issue URL to unlink
            
        Returns:
            bool: True if successful, False otherwise
        """
        signal_key = self._generate_signal_key(signal_info)
        data = self._load_data()
        
        if signal_key in data:
            linked_issues = data[signal_key]["linked_issues"]
            data[signal_key]["linked_issues"] = [
                issue for issue in linked_issues 
                if issue["url"] != git_issue_url
            ]
            data[signal_key]["updated_at"] = datetime.utcnow().isoformat()
            return self._save_data(data)
        
        return False
    
    def get_all_mappings(self) -> Dict[str, Any]:
        """Get all signal-to-issue mappings.
        
        Returns:
            Dict: All mappings
        """
        return self._load_data()
    
    def clear_all_links(self) -> bool:
        """Clear all Git issue links.
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self._save_data({})
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about linked issues.
        
        Returns:
            Dict: Statistics
        """
        data = self._load_data()
        
        total_signals = len(data)
        total_issues = sum(
            len(signal_data.get("linked_issues", [])) 
            for signal_data in data.values()
        )
        
        return {
            "total_signals_with_links": total_signals,
            "total_linked_issues": total_issues,
            "storage_file": str(self.storage_file)
        }


# Singleton instance
_linker_instance = None


def get_git_issue_linker() -> GitIssueLinker:
    """Get singleton instance of GitIssueLinker.
    
    Returns:
        GitIssueLinker: Singleton instance
    """
    global _linker_instance
    if _linker_instance is None:
        _linker_instance = GitIssueLinker()
    return _linker_instance

# Made with Bob
