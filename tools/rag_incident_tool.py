"""RAG incident search tool for retrieving similar incidents from ChromaDB.

This tool searches the RCA knowledge base using semantic search with OpenAI embeddings
and filters results based on component keyword matching.
"""

import os
import re
import json
from typing import List, Dict, Any, Callable
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import ToolParam

from config import CHROMA_DB_PATH, RCA_DATA_DISPLAY_PATH
from tools.tool_runner import register_tool_category
from utils.tracing import conditional_observe

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_display_data() -> Dict[str, Dict[str, Any]]:
    """Load display data from rca_data_display.json and return as a dictionary keyed by ID."""
    with open(RCA_DATA_DISPLAY_PATH, 'r') as f:
        data = json.load(f)
    return {item['id']: item for item in data}


def normalize_keywords(keywords: List[str]) -> List[str]:
    """Normalize VMware component keywords to standard abbreviations."""
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
        
        if keyword_lower in ['director', 'vcloud', 'cloudirector', 'vcloudirector']:
            normalized.append('vcd')
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
    """Extract VMware component-related keywords from the query using LLM."""
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
        
        # Parse the result
        try:
            keywords = json.loads(result)
            if isinstance(keywords, list):
                raw_keywords = [k.lower() for k in keywords[:max_keywords]]
                return normalize_keywords(raw_keywords)
        except:
            words = re.findall(r'\b[a-z]+\b', result.lower())
            filtered = [w for w in words if w not in ['keywords', 'query', 'the', 'and', 'or']]
            raw_keywords = filtered[:max_keywords]
            return normalize_keywords(raw_keywords)
        
        return []
        
    except Exception as e:
        print(f"Error extracting keywords with LLM: {e}")
        words = re.findall(r'\b[a-z0-9]+\b', query.lower())
        vmware_components = ['vcda', 'vcd', 'nsx', 'veeam', 'edge', 'backup', 'vcenter', 'esxi', 'hpcs', 'vsan', 'replication']
        keywords = [w for w in words if w in vmware_components]
        return keywords[:max_keywords] if keywords else words[:max_keywords]


def get_keyword_variations(keyword: str) -> List[str]:
    """Get both singular and plural forms of a keyword."""
    variations = [keyword]
    
    if keyword.endswith('ions') and len(keyword) > 5:
        variations.append(keyword[:-1])
        variations.append(keyword[:-4])
    elif keyword.endswith('ion') and len(keyword) > 4:
        variations.append(keyword + 's')
    elif keyword.endswith('s') and len(keyword) > 3:
        singular = keyword[:-1]
        variations.append(singular)
        if keyword.endswith('es') and len(keyword) > 4:
            singular_es = keyword[:-2]
            variations.append(singular_es)
    else:
        variations.append(keyword + 's')
        if keyword.endswith(('ch', 'sh', 'x', 'z', 's')) or keyword.endswith('ge'):
            variations.append(keyword + 'es')
    
    # Remove duplicates
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique_variations.append(v)
    
    return unique_variations


def calculate_match_score(keywords: List[str], components: str) -> tuple:
    """Calculate how many keywords match with components."""
    if not keywords:
        return 0, 0.0, []
    
    component_list = [comp.strip().lower() for comp in components.split(',')]
    matched_keywords = []
    
    for keyword in keywords:
        variations = get_keyword_variations(keyword)
        for variation in variations:
            if any(variation in component or component in variation for component in component_list):
                matched_keywords.append(keyword)
                break
    
    matched_count = len(matched_keywords)
    match_percentage = (matched_count / len(keywords)) * 100
    return matched_count, match_percentage, matched_keywords


@conditional_observe(
    name="rag_incident_search",
    as_type="tool",
    capture_input=True,
    capture_output=True,
)
def rag_incident_search(query: str, max_results: int = 3) -> str:
    """Search for similar incidents in the RCA knowledge base.
    
    Args:
        query: The search query describing the incident or issue
        max_results: Maximum number of results to return (default: 3)
    
    Returns:
        JSON string containing matching incidents with their details
    """
    print(f"\n[TOOL: rag_incident_search] Searching for incidents matching '{query}'...")
    
    try:
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return json.dumps({"error": "OPENAI_API_KEY not found in environment variables"})
        
        # Create OpenAI embedding function
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name="text-embedding-3-small"
        )
        
        # Connect to ChromaDB
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = chroma_client.get_collection(
            name="rca_knowledge_base",
            embedding_function=openai_ef  # type: ignore
        )
        
        # Extract keywords
        keywords = extract_keywords(query)
        print(f"Extracted keywords: {keywords}")
        
        if not keywords:
            return json.dumps({"message": "No keywords extracted from query", "results": []})
        
        # Semantic search
        semantic_results = collection.query(
            query_texts=[query],
            n_results=20,
            include=["documents", "metadatas", "distances"]
        )
        
        # Filter by keyword matching
        scored_results = []
        threshold = 50.0
        semantic_threshold = 70.0
        
        if semantic_results['ids'] and semantic_results['documents'] and semantic_results['metadatas']:
            ids_list = semantic_results['ids'][0] if semantic_results['ids'] else []  # type: ignore
            metadatas_list = semantic_results['metadatas'][0] if semantic_results['metadatas'] else []  # type: ignore
            distances_list = semantic_results['distances'][0] if semantic_results['distances'] else []  # type: ignore
            
            for doc_id, metadata, distance in zip(ids_list, metadatas_list, distances_list):
                components = str(metadata.get('components', ''))  # type: ignore
                matched_count, match_percentage, matched_kw = calculate_match_score(keywords, components)
                semantic_similarity = 100 * (1 / (1 + distance))
                
                if match_percentage >= threshold and semantic_similarity >= semantic_threshold:
                    scored_results.append({
                        'id': doc_id,
                        'matched_keywords': matched_kw,
                        'semantic_similarity': semantic_similarity
                    })
        
        # Try lower thresholds if no results
        if not scored_results and semantic_threshold > 50.0:
            print("Retrying with 60% semantic threshold...")
            semantic_threshold = 60.0
            
            ids_list = semantic_results['ids'][0] if semantic_results['ids'] else []  # type: ignore
            metadatas_list = semantic_results['metadatas'][0] if semantic_results['metadatas'] else []  # type: ignore
            distances_list = semantic_results['distances'][0] if semantic_results['distances'] else []  # type: ignore
            
            for doc_id, metadata, distance in zip(ids_list, metadatas_list, distances_list):
                components = str(metadata.get('components', ''))  # type: ignore
                matched_count, match_percentage, matched_kw = calculate_match_score(keywords, components)
                semantic_similarity = 100 * (1 / (1 + distance))
                
                if match_percentage >= threshold and semantic_similarity >= semantic_threshold:
                    scored_results.append({
                        'id': doc_id,
                        'matched_keywords': matched_kw,
                        'semantic_similarity': semantic_similarity
                    })
        
        # Sort and get top results
        scored_results.sort(key=lambda x: -x['semantic_similarity'])
        top_results = scored_results[:max_results]
        
        # Load display data and enrich results
        display_data = load_display_data()
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
                    'semantic_similarity': round(result['semantic_similarity'], 1)
                })
        
        return json.dumps({
            "query": query,
            "keywords_extracted": keywords,
            "results_count": len(enriched_results),
            "results": enriched_results
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"RAG search failed: {type(e).__name__}: {str(e)}"})


RAG_INCIDENT_TOOLS: list[ToolParam] = [
    {
        "type": "function",
        "name": "rag_incident_search",
        "description": (
            "Search the RCA knowledge base for similar incidents using semantic search. "
            "Use this when the user is experiencing an issue and wants to find existing "
            "incidents with similar problems, root causes, and resolutions. Returns incident "
            "details including problem description, root cause, resolution steps, and KB links."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query describing the incident or issue. Include technical "
                        "details, component names, and symptoms for better matching."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of incidents to return.",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 3,
                },
            },
            "required": ["query", "max_results"],
            "additionalProperties": False,
        },
    }
]


RAG_INCIDENT_FUNCTIONS: dict[str, Callable[..., str]] = {
    "rag_incident_search": rag_incident_search,
}

register_tool_category(RAG_INCIDENT_FUNCTIONS)

# Made with Bob