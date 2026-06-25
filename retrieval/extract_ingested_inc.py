import os
import re
import json
import sys
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from typing import List, Dict, Any
from openai import OpenAI
from pathlib import Path

# Add project root to path to import config
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import CHROMA_DB_PATH, RCA_DATA_DISPLAY_PATH

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_display_data() -> Dict[str, Dict[str, Any]]:
    """
    Load display data from rca_data_display.json and return as a dictionary keyed by ID.
    Uses path from config.
    """
    with open(RCA_DATA_DISPLAY_PATH, 'r') as f:
        data = json.load(f)
    return {item['id']: item for item in data}


def normalize_keywords(keywords: List[str]) -> List[str]:
    """
    Normalize VMware component keywords to standard abbreviations.
    Handles both single keywords and combinations.
    """
    # First, check if we have a combination that should be normalized
    keywords_str = ' '.join(keywords).lower()
    
    # Check for vCloud Director Availability (vcda)
    if any(phrase in keywords_str for phrase in ['vcloud director availability', 'cloud director availability', 'director availability']):
        return ['vcda']
    
    # Check for vCloud Director (vcd)
    if any(phrase in keywords_str for phrase in ['vcloud director', 'cloud director']):
        return ['vcd']
    
    # Otherwise normalize individual keywords
    normalized = []
    for keyword in keywords:
        keyword_lower = keyword.lower()
        
        # Normalize vCloud Director variations to 'vcd'
        if keyword_lower in ['director', 'vcloud', 'cloudirector', 'vcloudirector']:
            normalized.append('vcd')
        # Normalize vCloud Director Availability to 'vcda'
        elif keyword_lower in ['availability', 'vcloudavailability', 'directoravailability']:
            normalized.append('vcda')
        else:
            normalized.append(keyword_lower)
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for k in normalized:
        if k not in seen:
            seen.add(k)
            result.append(k)
    
    return result


def extract_keywords(query: str, max_keywords: int = 2) -> List[str]:
    """
    Extract VMware component-related keywords from the query using LLM.
    Uses OpenAI to intelligently identify component names.
    Returns 1-2 keywords with preference to VMware components.
    Normalizes variations (director -> vcd, availability -> vcda).
    """
    try:
        prompt = f"""Extract VMware component keywords from the following query.
Focus ONLY on technical component names. VMware components include:
- Infrastructure: vcda, nsx, vcd, vcenter, esxi, vsan, hpcs
- Services: veeam, backup, replication, edge, manager
- Resources: vm (virtual machine), vms, host, datastore, network
- Other: certificate, ssl, authentication, ldap, etc.

Ignore status words (failing, down, issue, error, unavailable, etc.) and action words (provisioning, deployment, edit, option, manage, etc.).

Return 1-2 component keywords maximum. Prefer specific VMware/infrastructure component names.

Examples:
Query: "vcda is experiencing outage as replication vms are in red state"
Keywords: ["vcda", "replication"]

Query: "edit options not available on vcd"
Keywords: ["vcd"]

Query: "workload provisioning is affected as nsx manager is not available"
Keywords: ["nsx", "manager"]

Query: "vm provisioning failing due to hpcs issue"
Keywords: ["hpcs", "vm"]

Query: "veeam backup jobs are failing"
Keywords: ["veeam", "backup"]

Query: "customer unable to manage vm"
Keywords: ["vm"]

Now extract keywords from this query:
Query: "{query}"
Keywords:"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a VMware infrastructure expert. Extract only technical component names from queries. Return a JSON array of 1-2 keywords."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=50
        )
        
        result = response.choices[0].message.content.strip()  # type: ignore
        
        # Parse the result - handle both JSON array and plain text
        try:
            # Try to parse as JSON
            keywords = json.loads(result)
            if isinstance(keywords, list):
                raw_keywords = [k.lower() for k in keywords[:max_keywords]]
                # Normalize keywords
                return normalize_keywords(raw_keywords)
        except:
            # Fallback: extract words from the response
            words = re.findall(r'\b[a-z]+\b', result.lower())
            # Filter out common words
            filtered = [w for w in words if w not in ['keywords', 'query', 'the', 'and', 'or']]
            raw_keywords = filtered[:max_keywords]
            # Normalize keywords
            return normalize_keywords(raw_keywords)
        
        return []
        
    except Exception as e:
        print(f"Error extracting keywords with LLM: {e}")
        # Fallback to simple extraction
        words = re.findall(r'\b[a-z0-9]+\b', query.lower())
        # Simple filter for common VMware components
        vmware_components = ['vcda', 'vcd', 'nsx', 'veeam', 'edge', 'backup', 'vcenter', 'esxi', 'hpcs', 'vsan', 'replication']
        keywords = [w for w in words if w in vmware_components]
        return keywords[:max_keywords] if keywords else words[:max_keywords]


def get_keyword_variations(keyword: str) -> List[str]:
    """
    Get both singular and plural forms of a keyword.
    Simple rule-based approach for common patterns.
    """
    variations = [keyword]
    
    # Handle words ending with 'ions' (e.g., replications -> replication)
    if keyword.endswith('ions') and len(keyword) > 5:
        variations.append(keyword[:-1])  # Remove 's'
        variations.append(keyword[:-4])  # Remove 'ions'
    
    # Handle words ending with 'ion' (e.g., replication -> replications)
    elif keyword.endswith('ion') and len(keyword) > 4:
        variations.append(keyword + 's')
    
    # If keyword ends with 's', try removing it (plural to singular)
    elif keyword.endswith('s') and len(keyword) > 3:
        singular = keyword[:-1]
        variations.append(singular)
        
        # Handle words ending in 'es' (e.g., edges -> edge)
        if keyword.endswith('es') and len(keyword) > 4:
            singular_es = keyword[:-2]
            variations.append(singular_es)
    else:
        # Try adding 's' for plural
        variations.append(keyword + 's')
        
        # Try adding 'es' for plural (e.g., edge -> edges)
        if keyword.endswith(('ch', 'sh', 'x', 'z', 's')) or keyword.endswith('ge'):
            variations.append(keyword + 'es')
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique_variations.append(v)
    
    return unique_variations


def calculate_match_score(keywords: List[str], components: str) -> tuple:
    """
    Calculate how many keywords match with components.
    Returns (matched_count, match_percentage, matched_keywords_list).
    """
    if not keywords:
        return 0, 0.0, []
    
    # Split components into individual items
    component_list = [comp.strip().lower() for comp in components.split(',')]
    
    matched_keywords = []
    
    for keyword in keywords:
        # Get all variations (singular/plural)
        variations = get_keyword_variations(keyword)
        
        # Check if any variation matches any component
        for variation in variations:
            if any(variation in component or component in variation for component in component_list):
                matched_keywords.append(keyword)
                break  # Count this keyword only once
    
    matched_count = len(matched_keywords)
    match_percentage = (matched_count / len(keywords)) * 100
    return matched_count, match_percentage, matched_keywords


def search_incidents(query: str, threshold: float = 50.0, top_k: int = 10, semantic_top_k: int = 20, semantic_threshold: float = 70.0, auto_adjust_threshold: bool = True) -> List[Dict[str, Any]]:
    """
    Search for incidents using two-stage approach:
    1. Semantic search using OpenAI embeddings to find similar documents
    2. Filter by keyword matching with metadata components
    
    Args:
        query: The search query string
        threshold: Minimum percentage of keywords that must match (default: 50%)
        top_k: Maximum number of results to return
        semantic_top_k: Number of semantically similar documents to retrieve first
        semantic_threshold: Minimum semantic similarity percentage (default: 70%)
        auto_adjust_threshold: Automatically reduce threshold if no results found (default: True)
    
    Returns:
        List of matching incidents with their metadata and match scores
    """
    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    # Create OpenAI embedding function (using OpenAI SDK)
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name="text-embedding-3-small"
    )
    
    # Connect to ChromaDB using config path
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    
    # Get collection with OpenAI embeddings
    collection = client.get_collection(
        name="rca_knowledge_base",
        embedding_function=openai_ef  # type: ignore
    )
    
    # Extract keywords from query
    keywords = extract_keywords(query)
    print(f"\nExtracted keywords: {keywords}")
    
    if not keywords:
        print("No keywords extracted from query")
        return []
    
    # STAGE 1: Semantic search using OpenAI embeddings
    # Query the collection to find semantically similar documents
    semantic_results = collection.query(
        query_texts=[query],
        n_results=semantic_top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    # STAGE 2: Filter by keyword matching in components
    scored_results = []
    
    if semantic_results['ids'] and semantic_results['documents'] and semantic_results['metadatas']:
        for doc_id, document, metadata, distance in zip(  # type: ignore
            semantic_results['ids'][0],
            semantic_results['documents'][0],
            semantic_results['metadatas'][0],
            semantic_results['distances'][0]  # type: ignore
        ):
            components = str(metadata.get('components', ''))  # type: ignore
            matched_count, match_percentage, matched_kw = calculate_match_score(keywords, components)
            
            # Calculate semantic similarity percentage
            semantic_similarity = 100 * (1 / (1 + distance))
            
            # Filter by both component match threshold AND semantic similarity threshold
            if match_percentage >= threshold and semantic_similarity >= semantic_threshold:
                scored_results.append({
                    'id': doc_id,
                    'matched_keywords': matched_kw,
                    'matched_count': matched_count,
                    'total_keywords': len(keywords),
                    'match_percentage': match_percentage,
                    'semantic_distance': distance,  # Lower is better
                    'semantic_similarity': semantic_similarity
                })
    
    # Sort by match percentage first, then by semantic distance
    scored_results.sort(key=lambda x: (-x['match_percentage'], x['semantic_distance']))
    
    # Get top_k results
    top_results = scored_results[:top_k]
    
    # Load display data
    display_data = load_display_data()
    
    # Enrich results with display data
    enriched_results = []
    for result in top_results:
        doc_id = result['id']
        if doc_id in display_data:
            display_info = display_data[doc_id]
            enriched_results.append({
                'id': doc_id,
                'title': display_info.get('title', ''),
                'problem': display_info.get('problem', ''),
                'root_cause': display_info.get('root_cause', ''),
                'resolution': display_info.get('resolution', ''),
                'impact': display_info.get('impact', ''),
                'incident_number': display_info.get('incident_number', ''),
                'incident_link': display_info.get('incident_link', ''),
                'date_occurred': display_info.get('date_occurred', ''),
                'broadcom_kb': display_info.get('broadcom_kb', ''),
                'cbc': display_info.get('cbc', ''),
                'cbc_link': display_info.get('cbc_link', ''),
                'matched_keywords': result['matched_keywords'],
                'matched_count': result['matched_count'],
                'total_keywords': result['total_keywords'],
                'match_percentage': result['match_percentage'],
                'semantic_similarity': result['semantic_similarity']
            })
    
    # If no results and auto_adjust_threshold is enabled, try with lower thresholds
    if not enriched_results and auto_adjust_threshold and semantic_threshold > 50.0:
        print(f"No results found with {semantic_threshold}% threshold. Trying with lower thresholds...")
        
        # Try 60% threshold
        if semantic_threshold > 60.0:
            print(f"Retrying with 60% semantic threshold...")
            return search_incidents(query, threshold, top_k, semantic_top_k, 60.0, False)
        
        # Try 50% threshold
        elif semantic_threshold > 50.0:
            print(f"Retrying with 50% semantic threshold...")
            return search_incidents(query, threshold, top_k, semantic_top_k, 50.0, False)
    
    return enriched_results


def main():
    """
    Example usage of the search function.
    """
    # Example queries to test
    test_queries = [
        "vcda is down as replications are in red state",
        "nsx edge deployment failing",
        "veeam backup jobs are failing"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("=" * 80)
        
        # Search for matching incidents (50% threshold)
        results = search_incidents(query, threshold=50.0)
        
        if not results:
            print(f"No matching incidents found with 50% threshold.")
        else:
            print(f"Found {len(results)} matching incident(s):\n")
            
            for i, result in enumerate(results, 1):
                print(f"{i}. ID: {result['id']}")
                print(f"   Match: {result['matched_count']}/{result['total_keywords']} keywords ({result['match_percentage']:.1f}%)")
                print(f"   Matched Keywords: {', '.join(result['matched_keywords'])}")
                print(f"   Components: {result['metadata']['components']}")
                print(f"   Date: {result['metadata']['date_occurred']}")
                if result['metadata']['cbc']:
                    print(f"   CBC: {result['metadata']['cbc']}")
                print(f"   Document Preview: {result['document'][:150]}...")
                print()
        
        print()


if __name__ == "__main__":
    main()

# Made with Bob
