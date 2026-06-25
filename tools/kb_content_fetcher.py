"""KB Content Fetcher - Extracts Cause and Resolution from Broadcom KB articles."""

import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional


def fetch_kb_article_content(url: str) -> Dict[str, Optional[str]]:
    """Fetch and parse a Broadcom KB article to extract Cause and Resolution.
    
    Args:
        url: The Broadcom KB article URL
        
    Returns:
        Dictionary with 'cause' and 'resolution' keys
    """
    try:
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        result = {
            'cause': None,
            'resolution': None,
            'workaround': None
        }
        
        # Try to find sections by common headings
        # Look for h2, h3, or strong tags with these keywords
        text_content = soup.get_text()
        
        # Extract Cause section
        cause_patterns = [
            r'(?:Cause|CAUSE|Root Cause|ROOT CAUSE)[:\s]+(.*?)(?=(?:Resolution|Workaround|Solution|RESOLUTION|WORKAROUND|SOLUTION|\n\n\n))',
            r'(?:Cause|CAUSE)[:\s]+(.*?)(?=\n\n)',
        ]
        
        for pattern in cause_patterns:
            match = re.search(pattern, text_content, re.DOTALL | re.IGNORECASE)
            if match:
                result['cause'] = match.group(1).strip()[:500]  # Limit to 500 chars
                break
        
        # Extract Resolution/Workaround section
        resolution_patterns = [
            r'(?:Resolution|RESOLUTION|Solution|SOLUTION)[:\s]+(.*?)(?=(?:\n\n\n|$))',
            r'(?:Workaround|WORKAROUND)[:\s]+(.*?)(?=(?:\n\n\n|$))',
        ]
        
        for pattern in resolution_patterns:
            match = re.search(pattern, text_content, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()[:500]  # Limit to 500 chars
                if 'Resolution' in pattern or 'RESOLUTION' in pattern or 'Solution' in pattern:
                    result['resolution'] = content
                else:
                    result['workaround'] = content
                break
        
        # If no specific sections found, try to extract from article body
        if not result['cause'] and not result['resolution']:
            # Look for article body or main content
            article_body = soup.find('div', class_=re.compile(r'article|content|body', re.I))
            if article_body:
                paragraphs = article_body.find_all('p')
                if len(paragraphs) >= 2:
                    result['cause'] = paragraphs[0].get_text().strip()[:300]
                    result['resolution'] = paragraphs[1].get_text().strip()[:300]
        
        return result
        
    except requests.RequestException as e:
        print(f"Error fetching KB article {url}: {e}")
        return {'cause': None, 'resolution': None, 'workaround': None}
    except Exception as e:
        print(f"Error parsing KB article {url}: {e}")
        return {'cause': None, 'resolution': None, 'workaround': None}


def format_kb_content(kb_data: Dict[str, Optional[str]]) -> str:
    """Format KB article content for display.
    
    Args:
        kb_data: Dictionary with cause and resolution
        
    Returns:
        Formatted string for display
    """
    parts = []
    
    if kb_data.get('cause'):
        parts.append(f"**Cause:**\n{kb_data['cause']}")
    
    if kb_data.get('resolution'):
        parts.append(f"**Resolution:**\n{kb_data['resolution']}")
    elif kb_data.get('workaround'):
        parts.append(f"**Workaround:**\n{kb_data['workaround']}")
    
    if not parts:
        return "*Content extraction in progress...*"
    
    return "\n\n".join(parts)

# Made with Bob
