"""SRE Analysis Agent for incident search and KB article retrieval.

This agent orchestrates the search for similar incidents and relevant KB articles
based on user queries. It detects user intent and uses appropriate tools.
"""

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from tools.rag_incident_tool import rag_incident_search, RAG_INCIDENT_TOOLS
from tools.broadcom_kb_search_tool import broadcom_kb_search, BROADCOM_KB_TOOLS
from utils.tracing import conditional_observe

load_dotenv()


class SREAnalysisAgent:
    """Agent for analyzing SRE incidents and providing relevant information."""
    
    def __init__(self):
        """Initialize the SRE Analysis Agent."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        
        # Combine tools
        self.tools = RAG_INCIDENT_TOOLS + BROADCOM_KB_TOOLS
        
        # Tool function mapping
        self.tool_functions = {
            "rag_incident_search": rag_incident_search,
            "broadcom_kb_search": broadcom_kb_search,
        }
    
    @conditional_observe(
        name="detect_intent",
        as_type="generation",
        capture_input=True,
        capture_output=True,
    )
    def detect_intent(self, query: str) -> Dict[str, Any]:
        """Detect user intent from the query.
        
        Args:
            query: User's query string
            
        Returns:
            Dictionary with intent classification and reasoning
        """
        print(f"\n[AGENT: SREAnalysisAgent] Detecting intent for query: '{query}'")
        
        intent_prompt = f"""Analyze the following user query and determine the intent.

User Query: "{query}"

Classify the intent as one of:
1. "incident_search" - User is experiencing an issue and wants to find similar past incidents
   Examples: "vcda is down", "nsx edge failing", "replication in red state"
   
2. "information_search" - User wants to learn about a topic, feature, or troubleshooting steps
   Examples: "why does nsx edge go down during maintenance", "how to configure vcda", "what causes certificate errors"

Return a JSON object with:
{{
    "intent": "incident_search" or "information_search",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation of why this intent was chosen",
    "requires_rag": true/false (search past incidents),
    "requires_kb": true/false (search KB articles)
}}

Consider:
- Incident search: User describes a problem, error, or outage they're experiencing
- Information search: User asks "why", "how", "what", or seeks general knowledge
- Both may be needed if the query has elements of both"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an intent classification expert for SRE queries. Return only valid JSON."},
                    {"role": "user", "content": intent_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            intent_data = json.loads(response.choices[0].message.content or "{}")  # type: ignore
            print(f"Intent detected: {intent_data.get('intent')} (confidence: {intent_data.get('confidence')})")
            print(f"Reasoning: {intent_data.get('reasoning')}")
            
            return intent_data
            
        except Exception as e:
            print(f"Error detecting intent: {e}")
            # Default to both searches
            return {
                "intent": "incident_search",
                "confidence": 0.5,
                "reasoning": "Error in intent detection, defaulting to incident search",
                "requires_rag": True,
                "requires_kb": False
            }
    
    @conditional_observe(
        name="execute_tools",
        as_type="generation",
        capture_input=True,
        capture_output=True,
    )
    def execute_tools(self, query: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute appropriate tools based on detected intent.
        
        Args:
            query: User's query string
            intent_data: Intent classification data
            
        Returns:
            Dictionary with results from executed tools
        """
        results = {
            "query": query,
            "intent": intent_data.get("intent"),
            "rag_results": None,
            "kb_results": None,
            "broadcom_kb_from_rag": []
        }
        
        # Execute RAG search if needed
        if intent_data.get("requires_rag", True):
            print("\n[AGENT: SREAnalysisAgent] Executing RAG incident search...")
            try:
                rag_response = rag_incident_search(query, max_results=3)
                rag_data = json.loads(rag_response)
                results["rag_results"] = rag_data
                
                # Extract Broadcom KB links from RAG results
                if rag_data.get("results"):
                    for incident in rag_data["results"]:
                        kb_link = incident.get("broadcom_kb", "")
                        if kb_link and kb_link.strip():
                            results["broadcom_kb_from_rag"].append({
                                "incident_id": incident.get("id"),
                                "incident_title": incident.get("title"),
                                "kb_link": kb_link
                            })
            except Exception as e:
                print(f"Error in RAG search: {e}")
                results["rag_results"] = {"error": str(e)}
        
        # Execute KB search if needed
        if intent_data.get("requires_kb", False):
            print("\n[AGENT: SREAnalysisAgent] Executing Broadcom KB search...")
            try:
                kb_response = broadcom_kb_search(query, max_results=2)
                results["kb_results"] = kb_response
            except Exception as e:
                print(f"Error in KB search: {e}")
                results["kb_results"] = f"Error: {str(e)}"
        
        # If no KB links from RAG, do KB search (for both incident and information search)
        if not results["broadcom_kb_from_rag"] and not results["kb_results"]:
            print("\n[AGENT: SREAnalysisAgent] No KB links in RAG results, executing KB search...")
            try:
                kb_response = broadcom_kb_search(query, max_results=2)
                results["kb_results"] = kb_response
            except Exception as e:
                print(f"Error in KB search: {e}")
                results["kb_results"] = f"Error: {str(e)}"
        
        return results
    
    @conditional_observe(
        name="synthesize_response",
        as_type="generation",
        capture_input=True,
        capture_output=True,
    )
    def synthesize_response(self, query: str, results: Dict[str, Any]) -> str:
        """Synthesize a natural language response from the tool results.
        
        Args:
            query: User's original query
            results: Results from tool execution
            
        Returns:
            Natural language response
        """
        print("\n[AGENT: SREAnalysisAgent] Synthesizing response...")
        
        synthesis_prompt = f"""You are an SRE expert assistant. Based on the search results, provide a helpful response to the user's query.

User Query: "{query}"

Search Results:
{json.dumps(results, indent=2)}

Provide a clear, concise response that:
1. Acknowledges what the user is looking for
2. Summarizes the most relevant findings
3. Highlights key information (incident IDs, KB article links, root causes, resolutions)
4. Uses a professional but friendly tone

If there are similar incidents, mention the most relevant ones with their IDs and brief descriptions.
If there are KB articles, mention them with their links.
If no results were found, suggest alternative search terms or approaches."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful SRE assistant providing incident analysis and guidance."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content or "Unable to generate response."  # type: ignore
            
        except Exception as e:
            print(f"Error synthesizing response: {e}")
            return f"I found some results but encountered an error generating the response: {str(e)}"
    
    @conditional_observe(
        name="analyze_query",
        as_type="generation",
        capture_input=True,
        capture_output=True,
    )
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Main entry point: analyze a user query and return comprehensive results.
        
        Args:
            query: User's query string
            
        Returns:
            Dictionary containing intent, tool results, and synthesized response
        """
        print(f"\n{'='*80}")
        print(f"[AGENT: SREAnalysisAgent] Starting analysis for query: '{query}'")
        print(f"{'='*80}")
        
        # Step 1: Detect intent
        intent_data = self.detect_intent(query)
        
        # Step 2: Execute appropriate tools
        tool_results = self.execute_tools(query, intent_data)
        
        # Step 3: Synthesize response
        synthesized_response = self.synthesize_response(query, tool_results)
        
        # Combine everything
        final_result = {
            "query": query,
            "intent": intent_data,
            "tool_results": tool_results,
            "response": synthesized_response
        }
        
        print(f"\n{'='*80}")
        print(f"[AGENT: SREAnalysisAgent] Analysis complete")
        print(f"{'='*80}\n")
        
        return final_result


# Convenience function for direct usage
def analyze_incident_query(query: str) -> Dict[str, Any]:
    """Analyze an incident query using the SRE Analysis Agent.
    
    Args:
        query: User's query string
        
    Returns:
        Analysis results including intent, tool results, and response
    """
    agent = SREAnalysisAgent()
    return agent.analyze_query(query)


# Made with Bob