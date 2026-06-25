"""Git Issue Parser - Extracts and parses cause/resolution from Git issues using AI."""

import re
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from pathlib import Path
import os
from openai import OpenAI


class GitIssueParser:
    """Parses Git issues to extract cause and resolution information."""
    
    def __init__(self, cache_dir: str = "data/cache/git_issues"):
        """Initialize Git Issue Parser.
        
        Args:
            cache_dir: Directory to cache parsed issue data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Patterns to identify cause and resolution sections
        self.cause_patterns = [
            r"(?:^|\n)#+\s*(?:Root\s*)?Cause[:\s]*\n(.*?)(?=\n#+|\Z)",
            r"(?:^|\n)#+\s*Problem[:\s]*\n(.*?)(?=\n#+|\Z)",
            r"(?:^|\n)#+\s*Issue[:\s]*\n(.*?)(?=\n#+|\Z)",
            r"\*\*(?:Root\s*)?Cause[:\s]*\*\*[:\s]*(.*?)(?=\n\*\*|\Z)",
            r"(?:^|\n)(?:Root\s*)?Cause[:\s]*(.*?)(?=\n(?:Resolution|Solution|Fix)|\Z)",
        ]
        
        self.resolution_patterns = [
            r"(?:^|\n)#+\s*(?:Resolution|Solution|Fix)[:\s]*\n(.*?)(?=\n#+|\Z)",
            r"(?:^|\n)#+\s*How\s*(?:to\s*)?(?:Fix|Resolve)[:\s]*\n(.*?)(?=\n#+|\Z)",
            r"\*\*(?:Resolution|Solution|Fix)[:\s]*\*\*[:\s]*(.*?)(?=\n\*\*|\Z)",
            r"(?:^|\n)(?:Resolution|Solution|Fix)[:\s]*(.*?)(?=\Z)",
        ]
    
    def _extract_github_info(self, url: str) -> Optional[Dict[str, str]]:
        """Extract owner, repo, and issue number from GitHub URL.
        
        Args:
            url: GitHub issue URL
            
        Returns:
            Dict with owner, repo, issue_number or None
        """
        # Pattern for GitHub URLs
        # https://github.com/owner/repo/issues/123
        # https://github.ibm.com/owner/repo/issues/123
        pattern = r"https?://(?:www\.)?github(?:\.ibm)?\.com/([^/]+)/([^/]+)/issues/(\d+)"
        match = re.search(pattern, url)
        
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "issue_number": match.group(3),
                "platform": "github.ibm.com" if "github.ibm.com" in url else "github.com"
            }
        return None
    
    def _fetch_github_issue(self, url: str, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch issue data from GitHub API.
        
        Args:
            url: GitHub issue URL
            token: Optional GitHub token for authentication
            
        Returns:
            Dict with issue data or None
        """
        info = self._extract_github_info(url)
        if not info:
            return None
        
        # Construct API URL
        if info["platform"] == "github.ibm.com":
            api_url = f"https://github.ibm.com/api/v3/repos/{info['owner']}/{info['repo']}/issues/{info['issue_number']}"
        else:
            api_url = f"https://api.github.com/repos/{info['owner']}/{info['repo']}/issues/{info['issue_number']}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpsPilot-AI/1.0"
        }
        
        if token:
            headers["Authorization"] = f"token {token}"
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch issue: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching GitHub issue: {e}")
            return None
    
    def _extract_with_ai(self, issue_body: str, comments: List[str]) -> Dict[str, Optional[str]]:
        """Use AI to extract cause and resolution from issue content.
        
        Args:
            issue_body: Main issue body text
            comments: List of comment texts
            
        Returns:
            Dict with 'cause' and 'resolution' keys
        """
        # Combine body and comments
        all_content = f"Issue Description:\n{issue_body}\n\n"
        if comments:
            all_content += "Discussion/Comments:\n" + "\n\n---Comment---\n".join(comments)
        
        # Truncate if too long (keep within token limits)
        if len(all_content) > 10000:
            all_content = all_content[:10000] + "...[content truncated]"
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""You are analyzing a technical Git issue. Read through the issue description and all comments.

{all_content}

Your task:
Extract ONLY the ROOT CAUSE and RESOLUTION information that is EXPLICITLY STATED in this Git issue.

1. ROOT CAUSE - Extract ONLY if there is an explicit explanation of what caused the problem:
   - Look for sections labeled "Cause", "Root Cause", "Problem", "Reason"
   - Look for explicit statements explaining WHY the issue occurred
   - DO NOT use the issue title or general problem description as the cause
   - DO NOT infer or interpret - only extract what is explicitly stated
   - If no explicit cause is stated, respond with "Not found"

2. RESOLUTION - Extract ONLY if there is an explicit explanation of how it was resolved:
   - Look for sections labeled "Resolution", "Solution", "Fix"
   - Look for explicit statements about actions taken to resolve the issue
   - Look in comments for resolution details, especially closing comments
   - DO NOT infer or interpret - only extract what is explicitly stated
   - If no explicit resolution is stated, respond with "Not found"

STRICT RULES:
- ONLY extract information that is EXPLICITLY STATED in the text
- DO NOT use issue titles or general descriptions as cause/resolution
- DO NOT add your own interpretation or analysis
- DO NOT infer anything - only extract what is clearly written
- Write as clear paragraphs, NOT bullet points
- Be concise but accurate

Response format:
ROOT CAUSE: [paragraph if explicitly found, otherwise "Not found"]
RESOLUTION: [paragraph if explicitly found, otherwise "Not found"]"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a technical issue analyzer. Extract ONLY explicitly stated cause and resolution information from Git issues. DO NOT infer, interpret, or use general problem descriptions. Only extract what is clearly and explicitly written in the issue or comments."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            if not content:
                return {"cause": None, "resolution": None}
            
            # Parse the response
            cause = None
            resolution = None
            
            # Extract ROOT CAUSE
            cause_match = re.search(r'ROOT CAUSE:\s*(.+?)(?=RESOLUTION:|$)', content, re.DOTALL | re.IGNORECASE)
            if cause_match:
                cause_text = cause_match.group(1).strip()
                if cause_text and "not found" not in cause_text.lower():
                    cause = cause_text
            
            # Extract RESOLUTION
            resolution_match = re.search(r'RESOLUTION:\s*(.+?)$', content, re.DOTALL | re.IGNORECASE)
            if resolution_match:
                resolution_text = resolution_match.group(1).strip()
                if resolution_text and "not found" not in resolution_text.lower():
                    resolution = resolution_text
            
            return {
                "cause": cause,
                "resolution": resolution
            }
            
        except Exception as e:
            print(f"Error extracting with AI: {e}")
            return {"cause": None, "resolution": None}
    
    def _get_cache_path(self, issue_url: str) -> Path:
        """Get cache file path for an issue.
        
        Args:
            issue_url: Issue URL
            
        Returns:
            Path to cache file
        """
        # Create a safe filename from URL
        safe_name = re.sub(r'[^\w\-]', '_', issue_url)
        return self.cache_dir / f"{safe_name}.json"
    
    def _load_from_cache(self, issue_url: str) -> Optional[Dict[str, Any]]:
        """Load parsed issue from cache.
        
        Args:
            issue_url: Issue URL
            
        Returns:
            Cached data or None
        """
        cache_path = self._get_cache_path(issue_url)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check if cache is recent (within 24 hours)
                    cached_time = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                    if (datetime.utcnow() - cached_time).total_seconds() < 86400:
                        return data
            except Exception as e:
                print(f"Error loading cache: {e}")
        return None
    
    def _save_to_cache(self, issue_url: str, data: Dict[str, Any]) -> bool:
        """Save parsed issue to cache.
        
        Args:
            issue_url: Issue URL
            data: Data to cache
            
        Returns:
            True if successful
        """
        cache_path = self._get_cache_path(issue_url)
        try:
            data["cached_at"] = datetime.utcnow().isoformat()
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving cache: {e}")
            return False
    
    def _fetch_issue_comments(self, issue_url: str, token: Optional[str] = None) -> List[str]:
        """Fetch comments for a GitHub issue.
        
        Args:
            issue_url: GitHub issue URL
            token: Optional GitHub token
            
        Returns:
            List of comment texts
        """
        info = self._extract_github_info(issue_url)
        if not info:
            return []
        
        # Construct API URL for comments
        if info["platform"] == "github.ibm.com":
            api_url = f"https://github.ibm.com/api/v3/repos/{info['owner']}/{info['repo']}/issues/{info['issue_number']}/comments"
        else:
            api_url = f"https://api.github.com/repos/{info['owner']}/{info['repo']}/issues/{info['issue_number']}/comments"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpsPilot-AI/1.0"
        }
        
        if token:
            headers["Authorization"] = f"token {token}"
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                comments_data = response.json()
                return [comment.get("body", "") for comment in comments_data if comment.get("body")]
            return []
        except Exception as e:
            print(f"Error fetching comments: {e}")
            return []
    
    def parse_issue(self, issue_url: str, token: Optional[str] = None,
                   force_refresh: bool = False) -> Dict[str, Any]:
        """Parse a Git issue to extract cause and resolution using AI.
        
        Args:
            issue_url: URL to the Git issue
            token: Optional authentication token
            force_refresh: Force refresh from API (ignore cache)
            
        Returns:
            Dict containing:
                - url: Issue URL
                - title: Issue title
                - state: Issue state (open/closed)
                - cause: Extracted cause text
                - resolution: Extracted resolution text
                - parsed_at: Timestamp
                - error: Error message if parsing failed
        """
        # Check cache first
        if not force_refresh:
            cached = self._load_from_cache(issue_url)
            if cached:
                return cached
        
        result = {
            "url": issue_url,
            "title": None,
            "state": None,
            "cause": None,
            "resolution": None,
            "parsed_at": datetime.utcnow().isoformat(),
            "error": None
        }
        
        # Fetch issue data
        issue_data = self._fetch_github_issue(issue_url, token)
        
        if not issue_data:
            result["error"] = "Failed to fetch issue data"
            return result
        
        # Extract basic info
        result["title"] = issue_data.get("title", "")
        result["state"] = issue_data.get("state", "unknown")
        
        # Get issue body and comments
        body = issue_data.get("body", "") or ""
        comments = self._fetch_issue_comments(issue_url, token)
        
        # Use AI to extract cause and resolution
        extracted = self._extract_with_ai(body, comments)
        result["cause"] = extracted["cause"]
        result["resolution"] = extracted["resolution"]
        
        # Cache the result
        self._save_to_cache(issue_url, result)
        
        return result
    
    def parse_multiple_issues(self, issue_urls: List[str], token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse multiple Git issues.
        
        Args:
            issue_urls: List of issue URLs
            token: Optional authentication token
            
        Returns:
            List of parsed issue data
        """
        results = []
        for url in issue_urls:
            result = self.parse_issue(url, token)
            results.append(result)
        return results


# Singleton instance
_parser_instance = None


def get_git_issue_parser() -> GitIssueParser:
    """Get singleton instance of GitIssueParser.
    
    Returns:
        GitIssueParser: Singleton instance
    """
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = GitIssueParser()
    return _parser_instance


# Made with Bob