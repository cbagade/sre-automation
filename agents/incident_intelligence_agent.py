"""Incident Intelligence Agent for analyzing ingested RCA data from vector database.

This agent performs intelligent analysis strictly on data ingested into the vector database.
It does not use external knowledge or assumptions - only the available incident data.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import CHROMA_DB_PATH, RCA_DATA_DISPLAY_PATH

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class IncidentIntelligenceAgent:
    """Agent for analyzing incident patterns and trends from ingested data."""
    
    def __init__(self):
        """Initialize the Incident Intelligence Agent."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Initialize ChromaDB connection
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name="text-embedding-3-small"
        )
        self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        self.collection = self.chroma_client.get_collection(
            name="rca_knowledge_base",
            embedding_function=self.openai_ef  # type: ignore
        )
        
        # Load display data
        self.display_data = self._load_display_data()
    
    def _load_display_data(self) -> Dict[str, Dict[str, Any]]:
        """Load display data from rca_data_display.json."""
        with open(RCA_DATA_DISPLAY_PATH, 'r') as f:
            data = json.load(f)
        return {item['id']: item for item in data}
    
    def get_all_incidents(self, time_period: str = "all", change_related_only: bool = False) -> List[Dict[str, Any]]:
        """Get all incidents from the vector database with optional filtering.
        
        Args:
            time_period: Time period filter (e.g., "last_3_months", "last_12_weeks", "last_2_quarters", "all")
            change_related_only: If True, only return change-related incidents
        
        Returns:
            List of incident dictionaries
        """
        # Get all documents from collection
        all_results = self.collection.get(
            include=["metadatas"]
        )
        
        incidents = []
        
        if all_results['ids'] and all_results['metadatas']:
            for doc_id, metadata in zip(all_results['ids'], all_results['metadatas']):  # type: ignore
                if doc_id in self.display_data:
                    incident = self.display_data[doc_id].copy()
                    incident['components'] = metadata.get('components', '')  # type: ignore
                    
                    # Apply time period filter
                    if time_period != "all":
                        date_str = incident.get('date_occurred', '')
                        if date_str:
                            try:
                                incident_date = datetime.strptime(date_str, '%Y-%m-%d')
                                now = datetime.now()
                                
                                # Parse time period string (e.g., "last_3_months", "last_12_weeks")
                                cutoff = self._calculate_cutoff_date(time_period, now)
                                
                                if incident_date < cutoff:
                                    continue
                            except:
                                pass
                    
                    # Apply change-related filter — only a non-null, non-empty cbc value is change-related
                    if change_related_only and not (incident.get('cbc') or '').strip():
                        continue
                    
                    incidents.append(incident)
        
        return incidents
    
    def _calculate_cutoff_date(self, time_period: str, now: datetime) -> datetime:
        """Calculate cutoff date based on time period string.
        
        Args:
            time_period: Time period string (e.g., "last_3_months", "last_12_weeks")
            now: Current datetime
        
        Returns:
            Cutoff datetime
        """
        # Parse format: "last_N_unit"
        parts = time_period.split('_')
        if len(parts) >= 3 and parts[0] == 'last':
            try:
                value = int(parts[1])
                unit = parts[2]
                
                if unit == 'weeks':
                    return now - timedelta(weeks=value)
                elif unit == 'months':
                    return now - timedelta(days=value * 30)  # Approximate
                elif unit == 'quarters':
                    return now - timedelta(days=value * 90)  # Approximate
                elif unit == 'years':
                    return now - timedelta(days=value * 365)  # Approximate
            except (ValueError, IndexError):
                pass
        
        # Default fallback
        return now - timedelta(days=90)
    
    def analyze_trends(self, time_period: str = "last_3_months", group_by: str = "month", change_related_only: bool = False) -> Dict[str, Any]:
        """Analyze incident trends over time.
        
        Args:
            time_period: Time period to analyze
            group_by: Grouping method ("week", "month", "quarter", "year")
            change_related_only: If True, only include change-related incidents
        
        Returns:
            Analysis results with trends and patterns
        """
        incidents = self.get_all_incidents(time_period=time_period, change_related_only=change_related_only)
        
        if not incidents:
            return {
                "total_incidents": 0,
                "message": "No incidents found in the selected time period"
            }
        
        # Group incidents by time bucket
        time_buckets = defaultdict(list)
        
        for incident in incidents:
            date_str = incident.get('date_occurred', '')
            if date_str:
                try:
                    incident_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if group_by == "week":
                        bucket = incident_date.strftime('%Y-W%U')
                    elif group_by == "month":
                        bucket = incident_date.strftime('%Y-%m')
                    elif group_by == "quarter":
                        quarter = (incident_date.month - 1) // 3 + 1
                        bucket = f"{incident_date.year}-Q{quarter}"
                    elif group_by == "year":
                        bucket = str(incident_date.year)
                    else:
                        bucket = incident_date.strftime('%Y-%m')
                    
                    time_buckets[bucket].append(incident)
                except:
                    pass
        
        # Find peak activity period
        peak_bucket = max(time_buckets.items(), key=lambda x: len(x[1])) if time_buckets else (None, [])
        
        return {
            "total_incidents": len(incidents),
            "time_buckets": {k: len(v) for k, v in sorted(time_buckets.items())},
            "peak_period": peak_bucket[0] if peak_bucket[0] else None,
            "peak_count": len(peak_bucket[1]) if peak_bucket[1] else 0,
            "incidents_over_time": [
                {"period": k, "count": len(v)}
                for k, v in sorted(time_buckets.items())
            ]
        }
    
    def analyze_components(self, time_period: str = "last_3_months", change_related_only: bool = False) -> Dict[str, Any]:
        """Analyze which components are most impacted.
        
        Args:
            time_period: Time period to analyze
            change_related_only: If True, only include change-related incidents
        
        Returns:
            Component analysis with risk levels
        """
        incidents = self.get_all_incidents(time_period=time_period, change_related_only=change_related_only)
        
        if not incidents:
            return {"message": "No incidents found"}
        
        # Count component occurrences
        component_counter = Counter()
        component_incidents = defaultdict(list)
        
        for incident in incidents:
            components_str = incident.get('components', '')
            if components_str:
                components = [c.strip().lower() for c in components_str.split(',')]
                for component in components:
                    if component:
                        component_counter[component] += 1
                        component_incidents[component].append(incident['id'])
        
        # Get top components
        top_components = component_counter.most_common(10)
        
        # Determine risk levels
        component_analysis = []
        max_count = top_components[0][1] if top_components else 0
        
        for component, count in top_components:
            risk_level = "high" if count >= max_count * 0.7 else "medium" if count >= max_count * 0.4 else "low"
            component_analysis.append({
                "component": component,
                "incident_count": count,
                "risk_level": risk_level,
                "incident_ids": component_incidents[component]
            })
        
        return {
            "total_components": len(component_counter),
            "top_components": component_analysis,
            "most_impacted": top_components[0][0] if top_components else None
        }
    
    def analyze_change_correlation(self, time_period: str = "last_3_months") -> Dict[str, Any]:
        """Analyze correlation between incidents and changes.
        
        Args:
            time_period: Time period to analyze
        
        Returns:
            Change correlation analysis
        """
        all_incidents = self.get_all_incidents(time_period=time_period)
        change_related = self.get_all_incidents(time_period=time_period, change_related_only=True)
        
        if not all_incidents:
            return {"message": "No incidents found"}
        
        correlation_percentage = (len(change_related) / len(all_incidents)) * 100 if all_incidents else 0
        
        return {
            "total_incidents": len(all_incidents),
            "change_related_incidents": len(change_related),
            "correlation_percentage": round(correlation_percentage, 1),
            "change_related_ids": [inc['id'] for inc in change_related]
        }
    
    def generate_executive_summary(self, time_period: str = "last_3_months", group_by: str = "month", 
                                   change_related_only: bool = False) -> Dict[str, Any]:
        """Generate an AI-powered executive summary of incident intelligence.
        
        Args:
            time_period: Time period to analyze
            group_by: Grouping method for trends
            change_related_only: Focus on change-related incidents
        
        Returns:
            Executive summary with key insights
        """
        # Gather all analysis data
        incidents = self.get_all_incidents(time_period=time_period, change_related_only=change_related_only)
        trends = self.analyze_trends(time_period=time_period, group_by=group_by)
        components = self.analyze_components(time_period=time_period)
        change_correlation = self.analyze_change_correlation(time_period=time_period)
        
        if not incidents:
            return {
                "what_happened": "No incidents found in the selected time period.",
                "most_impacted": "N/A",
                "change_pattern": "N/A",
                "next_action": "No action required."
            }
        
        # Prepare context for AI analysis
        context = {
            "total_incidents": len(incidents),
            "time_period": time_period,
            "peak_period": trends.get('peak_period'),
            "peak_count": trends.get('peak_count'),
            "top_component": components.get('most_impacted'),
            "change_correlation": change_correlation.get('correlation_percentage', 0),
            "change_related_count": change_correlation.get('change_related_incidents', 0)
        }
        
        # Generate AI summary
        prompt = f"""Based on the following incident data from our RCA knowledge base, provide a concise executive summary:

Total Incidents: {context['total_incidents']}
Time Period: {context['time_period']}
Peak Activity: {context['peak_count']} incidents in {context['peak_period']}
Most Impacted Component: {context['top_component']}
Change Correlation: {context['change_correlation']}% of incidents are change-related

Provide a summary with these sections:
1. WHAT HAPPENED: Brief overview of incident activity (1-2 sentences)
2. MOST IMPACTED: Which component/service had the most issues
3. CHANGE PATTERN: Analysis of change-related incidents
4. NEXT ACTION: Recommended operational focus areas

Keep each section concise and actionable. Base your analysis ONLY on the data provided."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an SRE analyst providing executive summaries based strictly on provided incident data. Be concise and actionable."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            summary_text = response.choices[0].message.content.strip()  # type: ignore
            
            # Parse the summary into sections
            sections = {
                "what_happened": "",
                "most_impacted": "",
                "change_pattern": "",
                "next_action": ""
            }
            
            current_section = None
            for line in summary_text.split('\n'):
                line = line.strip()
                if 'WHAT HAPPENED' in line.upper():
                    current_section = 'what_happened'
                elif 'MOST IMPACTED' in line.upper():
                    current_section = 'most_impacted'
                elif 'CHANGE PATTERN' in line.upper():
                    current_section = 'change_pattern'
                elif 'NEXT ACTION' in line.upper():
                    current_section = 'next_action'
                elif current_section and line and not line.startswith('#'):
                    sections[current_section] += line + " "
            
            # Clean up sections and provide fallbacks
            for key in sections:
                sections[key] = sections[key].strip()
                # If section is empty or contains HTML-like content, use fallback
                if not sections[key] or '<' in sections[key] or '>' in sections[key]:
                    if key == 'what_happened':
                        sections[key] = f"{context['total_incidents']} incidents were observed in the selected window, with the highest activity concentrated around {context['peak_period']}."
                    elif key == 'most_impacted':
                        sections[key] = f"{context['top_component']} is the most impacted component and should receive first-pass triage focus."
                    elif key == 'change_pattern':
                        sections[key] = f"{context['change_related_count']} incidents are change-related ({context['change_correlation']}%), suggesting deployment or configuration correlation."
                    elif key == 'next_action':
                        sections[key] = "Operations should validate recent changes, review recurring component RCA, and create proactive alerts for repeat patterns."
            
            return sections
            
        except Exception as e:
            # Fallback to rule-based summary
            return {
                "what_happened": f"{context['total_incidents']} incidents were observed in the selected window, with the highest activity concentrated around {context['peak_period']}.",
                "most_impacted": f"{context['top_component']} is the most impacted component and should receive first-pass triage focus.",
                "change_pattern": f"{context['change_related_count']} incidents are change-related ({context['change_correlation']}%), suggesting deployment or configuration correlation.",
                "next_action": f"Operations should validate recent changes, review recurring component RCA, and create proactive alerts for repeat patterns."
            }
    
    def get_affected_components_chart_data(self, time_period: str = "last_3_months", change_related_only: bool = False) -> Dict[str, Any]:
        """Get data for affected components visualization.
        
        Returns:
            Chart data with component recurrence and risk levels
        """
        components = self.analyze_components(time_period=time_period, change_related_only=change_related_only)
        
        if not components.get('top_components'):
            return {"labels": [], "data": [], "risk_levels": []}
        
        top_components = components['top_components'][:10]  # Top 10
        
        return {
            "labels": [c['component'] for c in top_components],
            "data": [c['incident_count'] for c in top_components],
            "risk_levels": [c['risk_level'] for c in top_components]
        }
    
    def get_component_mix_over_time(
        self,
        time_period: str = "last_3_months",
        group_by: str = "month",
        top_n: int = 5,
        change_related_only: bool = False,
    ) -> Dict[str, Any]:
        """Get per-period, per-component incident counts for the component mix chart.

        Returns a dict with:
          - periods: sorted list of time-bucket labels
          - components: list of top-N component names
          - series: {component: [count_per_period, ...]}
        """
        incidents = self.get_all_incidents(time_period=time_period, change_related_only=change_related_only)

        if not incidents:
            return {"periods": [], "components": [], "series": {}}

        # --- build per-period per-component matrix ---
        matrix: dict = defaultdict(lambda: defaultdict(int))

        for incident in incidents:
            date_str = incident.get("date_occurred", "")
            components_str = incident.get("components", "")
            if not date_str or not components_str:
                continue
            try:
                incident_date = datetime.strptime(date_str, "%Y-%m-%d")
                if group_by == "week":
                    bucket = incident_date.strftime("%Y-W%U")
                elif group_by == "quarter":
                    q = (incident_date.month - 1) // 3 + 1
                    bucket = f"{incident_date.year}-Q{q}"
                elif group_by == "year":
                    bucket = str(incident_date.year)
                else:
                    bucket = incident_date.strftime("%Y-%m")
            except Exception:
                continue

            for comp in [c.strip().lower() for c in components_str.split(",") if c.strip()]:
                matrix[bucket][comp] += 1

        periods = sorted(matrix.keys())

        # rank components by total across all periods
        component_totals: Counter = Counter()
        for bucket_data in matrix.values():
            component_totals.update(bucket_data)
        top_components = [c for c, _ in component_totals.most_common(top_n)]

        series = {
            comp: [matrix[p].get(comp, 0) for p in periods]
            for comp in top_components
        }

        return {"periods": periods, "components": top_components, "series": series}

    def get_recommended_actions(self, time_period: str = "last_3_months", change_related_only: bool = False) -> List[str]:
        """Get AI-recommended actions based on incident patterns.
        
        Returns:
            List of recommended actions
        """
        incidents = self.get_all_incidents(time_period=time_period, change_related_only=change_related_only)
        components = self.analyze_components(time_period=time_period, change_related_only=change_related_only)
        change_correlation = self.analyze_change_correlation(time_period=time_period)
        
        actions = []
        
        # Action based on top component
        if components.get('most_impacted'):
            top_component = components['most_impacted']
            actions.append(f"Prioritize {top_component} incident review and component-level RCA.")
        
        # Action based on change correlation
        if change_correlation.get('correlation_percentage', 0) >= 50:
            actions.append("Correlate incident spikes with change windows and deployments.")
        
        # Action for recurring issues
        if len(incidents) > 5:
            actions.append("Review recurring incidents for backup or infrastructure dependency issues.")
        
        # Action for proactive monitoring
        if components.get('top_components'):
            high_risk = [c['component'] for c in components['top_components'] if c['risk_level'] == 'high']
            if high_risk:
                actions.append(f"Create proactive alerts for components with repeated monthly recurrence: {', '.join(high_risk[:3])}.")
        
        return actions if actions else ["Continue monitoring incident patterns."]


# Made with Bob