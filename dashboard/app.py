"""OpsPilot AI Dashboard - Main Streamlit Application.

A premium dark-themed dashboard for RCA assistance and KB article search.
"""

import html
import json
import sys
from pathlib import Path
import streamlit as st
from typing import Any, Dict, List

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.sre_analysis_agent import SREAnalysisAgent
from dashboard.components.operational_signals_page import render_operational_signals_page
from dashboard.components.incident_intelligence_page import render_incident_intelligence_page


def apply_theme() -> None:
    """Apply dashboard-specific styling with OpsPilot AI look and feel."""
    st.markdown(
        """
        <style>
        :root {
            --panel: rgba(255, 255, 255, 0.86);
            --line: rgba(20, 33, 61, 0.12);
            --ink: #14213d;
            --muted: #607086;
            --green: #1b998b;
            --amber: #f4a261;
            --red: #d1495b;
            --blue: #2f80ed;
        }
        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(47, 128, 237, 0.18), transparent 28%),
                radial-gradient(circle at 88% 16%, rgba(27, 153, 139, 0.14), transparent 30%),
                linear-gradient(135deg, #060b16 0%, #0b1220 48%, #111827 100%);
            color: #e8eef8;
            font-family: Inter, "IBM Plex Sans", Poppins, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        header[data-testid="stHeader"],
        div[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        #MainMenu,
        footer {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
        }
        section.main > div {
            padding-top: 0 !important;
        }
        .command-bar {
            position: sticky;
            top: 0;
            z-index: 999;
            min-height: 70px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            padding: 10px 16px;
            margin: 0 0 0 0;
            border: 1px solid rgba(125, 211, 252, 0.26);
            border-radius: 0 0 18px 18px;
            background:
                linear-gradient(135deg, rgba(6, 11, 22, 0.94), rgba(15, 23, 42, 0.82)),
                rgba(15, 23, 42, 0.70);
            box-shadow: 0 14px 38px rgba(0, 0, 0, 0.32), 0 0 30px rgba(56, 189, 248, 0.10);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
        }
        .command-bar::after {
            content: "";
            position: absolute;
            left: 18px;
            right: 18px;
            bottom: -1px;
            height: 2px;
            border-radius: 999px;
            background: linear-gradient(90deg, transparent, #38bdf8, #2563eb, #14b8a6, transparent);
            background-size: 220% 100%;
            animation: commandLineFlow 4.5s ease-in-out infinite;
            opacity: 0.82;
        }
        .command-title {
            color: #f8fafc;
            font-size: clamp(1.50rem, 1.50vw, 1.85rem);
            font-weight: 850;
            line-height: 1.1;
            letter-spacing: 0;
        }
        .command-subtitle {
            color: #94a3b8;
            font-size: clamp(0.88rem, 0.84vw, 1.00rem);
            margin-top: 3px;
        }
        .command-powered {
            white-space: nowrap;
            border: 1px solid rgba(45, 212, 191, 0.34);
            color: #bff7ef;
            background: linear-gradient(135deg, rgba(20, 184, 166, 0.14), rgba(37, 99, 235, 0.10));
            box-shadow: 0 0 24px rgba(20, 184, 166, 0.14);
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 0.90rem;
            font-weight: 760;
        }
        @keyframes commandLineFlow {
            0% { background-position: 0% 50%; opacity: 0.45; }
            50% { background-position: 100% 50%; opacity: 0.95; }
            100% { background-position: 0% 50%; opacity: 0.45; }
        }
        .glass-card {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 18px;
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.78), rgba(30, 41, 59, 0.46));
            box-shadow: 0 14px 38px rgba(0, 0, 0, 0.20);
            padding: 15px 17px;
            margin: 12px 0;
            color: #dbe7f7;
        }
        .glass-card-title {
            color: #f8fafc;
            font-size: 1.15rem;
            font-weight: 820;
            margin-bottom: 5px;
        }
        .glass-card-body {
            color: #94a3b8;
            font-size: 1.00rem;
            line-height: 1.45;
        }
        .incident-card {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 16px;
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.86), rgba(30, 41, 59, 0.58));
            padding: 15px 16px;
            box-shadow: 0 14px 38px rgba(0, 0, 0, 0.22);
            margin-bottom: 12px;
            color: #dbe7f7;
        }
        .incident-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .incident-title {
            color: #f8fafc;
            font-size: 1.22rem;
            font-weight: 820;
            margin-bottom: 4px;
        }
        .incident-id {
            color: #7dd3fc;
            font-size: 0.92rem;
            font-weight: 700;
            background: rgba(56, 189, 248, 0.12);
            padding: 4px 10px;
            border-radius: 999px;
            border: 1px solid rgba(125, 211, 252, 0.24);
        }
        .incident-section {
            margin: 10px 0;
        }
        .incident-label {
            color: #94a3b8;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 800;
            margin-bottom: 4px;
        }
        .incident-text {
            color: #dbe7f7;
            font-size: 1.02rem;
            line-height: 1.45;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 5px 10px;
            border: 1px solid rgba(96, 165, 250, 0.28);
            background: rgba(37, 99, 235, 0.16);
            color: #bfdbfe;
            font-size: 0.88rem;
            font-weight: 800;
            margin: 3px 6px 3px 0;
        }
        .status-badge.good {
            border-color: rgba(45, 212, 191, 0.30);
            background: rgba(20, 184, 166, 0.14);
            color: #99f6e4;
        }
        .status-badge.warn {
            border-color: rgba(245, 158, 11, 0.30);
            background: rgba(245, 158, 11, 0.14);
            color: #fde68a;
        }
        .ai-insight {
            border-radius: 18px;
            border: 1px solid rgba(125, 211, 252, 0.25);
            background:
                linear-gradient(135deg, rgba(37, 99, 235, 0.36), rgba(20, 184, 166, 0.20)),
                rgba(15, 23, 42, 0.78);
            box-shadow: 0 18px 58px rgba(8, 47, 73, 0.30);
            padding: 18px 20px;
            margin: 16px 0;
        }
        .ai-insight-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 8px;
        }
        .ai-icon {
            width: 38px;
            height: 38px;
            border-radius: 14px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #e0f2fe;
            background: linear-gradient(135deg, #2563eb, #14b8a6);
            font-weight: 850;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.28);
        }
        .ai-pill {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            border: 1px solid rgba(226, 232, 240, 0.20);
            color: #dbeafe;
            background: rgba(15, 23, 42, 0.50);
            font-size: 0.85rem;
            font-weight: 700;
            margin-left: 6px;
        }
        .ai-insight p {
            color: #e5eefb;
            margin: 0;
            line-height: 1.55;
            font-size: 1.00rem;
        }
        .stButton > button {
            border-radius: 999px !important;
            border: 1px solid rgba(125, 211, 252, 0.32) !important;
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.88), rgba(20, 184, 166, 0.62)) !important;
            color: #f8fafc !important;
            font-weight: 820 !important;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.18) !important;
            transition: transform 160ms ease, filter 160ms ease, box-shadow 160ms ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            filter: brightness(1.12);
            box-shadow: 0 16px 34px rgba(56, 189, 248, 0.22) !important;
        }
        .stTextArea textarea {
            min-height: 120px !important;
            border-radius: 16px !important;
            background: rgba(15, 23, 42, 0.88) !important;
            color: #f8fafc !important;
            caret-color: #38bdf8 !important;
            cursor: text !important;
            border: 1px solid rgba(96, 165, 250, 0.24) !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
        }
        .stTextArea textarea:focus {
            caret-color: #67e8f9 !important;
            border-color: rgba(56, 189, 248, 0.58) !important;
            box-shadow:
                0 0 0 1px rgba(56, 189, 248, 0.30),
                0 0 22px rgba(56, 189, 248, 0.14),
                inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
            outline: none !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
            border-radius: 16px !important;
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.72), rgba(30, 41, 59, 0.42)) !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.16);
            overflow: hidden;
        }
        div[data-testid="stExpander"] details summary {
            background:
                linear-gradient(145deg, rgba(15, 23, 42, 0.84), rgba(30, 41, 59, 0.56)) !important;
            color: #e5eefb !important;
            font-weight: 760 !important;
        }
        div[data-testid="stExpander"] details[open] summary {
            background:
                linear-gradient(135deg, rgba(37, 99, 235, 0.32), rgba(20, 184, 166, 0.18)),
                rgba(15, 23, 42, 0.92) !important;
            color: #f8fafc !important;
        }
        .block-container {
            max-width: 1680px;
            padding-top: 0 !important;
            padding-bottom: 2rem;
        }
        .stApp {
            background-size: 160% 160%;
            animation: dashboardGradient 22s ease-in-out infinite;
        }
        @keyframes dashboardGradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        label, .stMarkdown, .stCaption {
            color: #dbe7f7;
            font-size: 1.00rem;
        }
        div[data-testid="stTextInput"] label,
        div[data-testid="stTextArea"] label {
            color: #f8fafc !important;
            font-weight: 850 !important;
            opacity: 1 !important;
            font-size: 1.05rem !important;
        }
        .stTextArea textarea {
            font-size: 1.00rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_command_bar() -> str:
    """Render the compact top command bar with navigation menu and return selected page."""
    # Custom CSS for navigation buttons
    st.markdown(
        """
        <style>
        .command-bar-container {
            display: flex;
            align-items: center;
            gap: 24px;
        }
        .nav-menu {
            display: flex;
            gap: 12px;
            align-items: center;
            flex: 1;
            justify-content: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Create columns for layout: branding | navigation | spacer
    col1, col2, col3 = st.columns([1.5, 3, 1])
    
    with col1:
        st.markdown(
            """
            <div>
                <div class="command-title">OpsPilot AI</div>
                <div class="command-subtitle">AI-powered operational intelligence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        # Navigation buttons in the center
        nav_col1, nav_col2, nav_col3 = st.columns(3)
        
        with nav_col1:
            if st.button("📊 Operational Signals", key="nav_signals", use_container_width=True):
                st.session_state.current_page = "signals"
        
        with nav_col2:
            if st.button("🤖 RCA Assistant", key="nav_rca", use_container_width=True, type="primary"):
                st.session_state.current_page = "rca"
        
        with nav_col3:
            if st.button("📈 Incident Intelligence", key="nav_intelligence", use_container_width=True):
                st.session_state.current_page = "intelligence"
    
    # Initialize session state for current page
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "rca"
    
    return st.session_state.current_page


def render_incident_card(incident: Dict[str, Any]) -> None:
    """Render an incident card with all details (excluding Impact)."""
    incident_id = incident.get('id', 'N/A')
    title = incident.get('title', 'No title')
    problem = incident.get('problem', '')
    root_cause = incident.get('root_cause', '')
    resolution = incident.get('resolution', '')
    incident_number = incident.get('incident_number', '')
    incident_link = incident.get('incident_link', '')
    date_occurred = incident.get('date_occurred', '')
    broadcom_kb = incident.get('broadcom_kb', '')
    cbc = incident.get('cbc', '')
    cbc_link = incident.get('cbc_link', '')
    similarity = incident.get('semantic_similarity', 0)
    
    # Build HTML sections (removed impact_html)
    problem_html = f'<div class="incident-section"><div class="incident-label">Problem</div><div class="incident-text">{html.escape(problem)}</div></div>' if problem else ''
    root_cause_html = f'<div class="incident-section"><div class="incident-label">Root Cause</div><div class="incident-text">{html.escape(root_cause)}</div></div>' if root_cause else ''
    resolution_html = f'<div class="incident-section"><div class="incident-label">Resolution</div><div class="incident-text">{html.escape(resolution)}</div></div>' if resolution else ''
    
    date_badge = f'<span class="status-badge">{html.escape(date_occurred)}</span>' if date_occurred else ''
    incident_badge = f'<a href="{html.escape(incident_link)}" target="_blank" class="status-badge">Incident: {html.escape(incident_number)}</a>' if incident_link else ''
    kb_badge = f'<a href="{html.escape(broadcom_kb)}" target="_blank" class="status-badge good">Broadcom KB</a>' if broadcom_kb else ''
    cbc_badge = f'<a href="{html.escape(cbc_link)}" target="_blank" class="status-badge warn">CBC: {html.escape(cbc)}</a>' if cbc_link else ''
    
    card_html = f"""<div class="incident-card">
<div class="incident-card-header">
<div>
<div class="incident-title">{html.escape(title)}</div>
<span class="status-badge good">Match: {similarity}%</span>
{date_badge}
</div>
<div class="incident-id">{html.escape(incident_id)}</div>
</div>
{problem_html}
{root_cause_html}
{resolution_html}
<div class="incident-section">
{incident_badge}
{kb_badge}
{cbc_badge}
</div>
</div>"""
    
    st.markdown(card_html, unsafe_allow_html=True)


def render_ai_insight(intent_data: Dict[str, Any]) -> None:
    """Render AI insight banner."""
    intent = intent_data.get('intent', 'unknown')
    confidence = int(intent_data.get('confidence', 0) * 100)
    reasoning = intent_data.get('reasoning', '')
    
    intent_label = "Incident Search" if intent == "incident_search" else "Information Search"
    
    st.markdown(
        f"""
        <div class="ai-insight">
            <div class="ai-insight-top">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div class="ai-icon">AI</div>
                    <div>
                        <span class="ai-pill">Intent: {html.escape(intent_label)}</span>
                        <span class="ai-pill">Confidence: {confidence}%</span>
                    </div>
                </div>
            </div>
            <p>{html.escape(reasoning)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="OpsPilot AI",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Apply theme
    apply_theme()
    
    # Render command bar and get current page
    current_page = render_command_bar()
    
    # Add spacing
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Route to different pages based on selection
    if current_page == "signals":
        render_operational_signals_page()
        return
    
    elif current_page == "intelligence":
        render_incident_intelligence_page()
        return
    
    # RCA Assistant page (default)
    st.markdown(
        """
        <div class="glass-card">
            <div class="glass-card-title">🔍 RCA Assistant</div>
            <div class="glass-card-body">
                Describe your incident or ask a question. Our AI will search for similar past incidents
                and relevant knowledge base articles to help you resolve issues faster.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Query input
    query = st.text_area(
        "Enter your query",
        placeholder="Example: vcda experienced outage as replication vms are in red state",
        height=100,
        help="Describe the incident you're experiencing or ask a question about VMware/Broadcom products"
    )
    
    # Search button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_button = st.button("🔎 Analyze", use_container_width=True)
    
    # Process query
    if search_button and query:
        with st.spinner("🤖 Analyzing your query..."):
            # Initialize agent
            agent = SREAnalysisAgent()
            
            # Analyze query
            result = agent.analyze_query(query)
            
            # Store results in session state
            st.session_state.analysis_result = result
            st.session_state.current_query = query
            st.session_state.web_search_results = None
    
    # Display results if available in session state
    if 'analysis_result' in st.session_state and st.session_state.analysis_result:
        result = st.session_state.analysis_result
        
        # Create two-column layout for results
        col_left, col_right = st.columns(2)
        
        # Get tool results
        tool_results = result.get('tool_results', {})
        rag_results = tool_results.get('rag_results')
        kb_results = tool_results.get('kb_results')
        kb_from_rag = tool_results.get('broadcom_kb_from_rag', [])
        
        # Check if we have historical RCA results and collect KB URLs
        has_historical_results = False
        historical_kb_urls = set()
        if rag_results and isinstance(rag_results, dict):
            incidents = rag_results.get('results', [])
            has_historical_results = len(incidents) > 0
            
            # Collect all KB URLs from historical incidents
            for incident in incidents:
                kb_url = incident.get('broadcom_kb', '').strip()
                if kb_url:
                    historical_kb_urls.add(kb_url)
            
            # LEFT COLUMN: Historical RCA Solutions
            with col_left:
                st.markdown(
                    """
                    <div class="glass-card">
                        <div class="glass-card-title">📋 Historical RCA Solutions</div>
                        <div class="glass-card-body">
                            Collapsed evidence from vector DB retrieval.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                if rag_results and isinstance(rag_results, dict):
                    incidents = rag_results.get('results', [])
                    if incidents:
                        for idx, incident in enumerate(incidents, 1):
                            incident_title = incident.get('title', 'No title')
                            incident_id = incident.get('id', 'N/A')
                            similarity = incident.get('semantic_similarity', 0)
                            with st.expander(f"▸ {incident_title}", expanded=False):
                                render_incident_card(incident)
                    else:
                        st.markdown(
                            """
                            <div style="text-align: center; padding: 40px 20px; border: 2px dashed rgba(148, 163, 184, 0.3); border-radius: 12px; margin: 20px 0;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: #94a3b8; margin-bottom: 8px;">No RCA matches</div>
                                <div style="color: #64748b; font-size: 0.95rem;">No historical RCA evidence was returned for this prompt.</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        """
                        <div style="text-align: center; padding: 40px 20px; border: 2px dashed rgba(148, 163, 184, 0.3); border-radius: 12px; margin: 20px 0;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: #94a3b8; margin-bottom: 8px;">No RCA matches</div>
                            <div style="color: #64748b; font-size: 0.95rem;">No historical RCA evidence was returned for this prompt.</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            
        # RIGHT COLUMN: Web Solutions
        with col_right:
            st.markdown(
                """
                <div class="glass-card">
                    <div class="glass-card-title">🌐 Web Solutions</div>
                    <div class="glass-card-body">
                        Collapsed external KB evidence and optional web expansion.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            # Behavior based on whether we have historical results
            if has_historical_results:
                # Has historical results: Show button, only search on click
                st.info("The primary answer came from historical RCAs. You can broaden evidence with KB search if needed.")
                
                # Search Web button
                if st.button("🔍 Search Web", use_container_width=True, key="search_web_btn"):
                    # Perform KB search and store in session state
                    with st.spinner("🔍 Searching web for additional solutions..."):
                        from tools.broadcom_kb_search_tool import broadcom_kb_search
                        try:
                            web_kb_results = broadcom_kb_search(st.session_state.current_query, max_results=3)
                            st.session_state.web_search_results = web_kb_results
                        except Exception as e:
                            st.error(f"Error searching web: {str(e)}")
                            st.session_state.web_search_results = None
                
                # Check if we have web search results to display
                if st.session_state.get('web_search_results'):
                    display_kb_results = True
                    kb_results = st.session_state.web_search_results
                else:
                    display_kb_results = False
            else:
                # No historical results: Automatically show KB results
                st.info("No historical RCA matches found. Showing web-based solutions.")
                display_kb_results = True
            
            # Display KB Articles if we should show them
            if display_kb_results and ((kb_results and isinstance(kb_results, str) and kb_results.strip()) or kb_from_rag):
                    import re
                    
                    # Parse and display KB search results
                    if kb_results and isinstance(kb_results, str) and kb_results.strip():
                        # Try to parse markdown links with relevance: • [Title](URL) [Relevance: XX%]
                        kb_pattern_with_relevance = r'•\s*\[([^\]]+)\]\(([^\)]+)\)\s*\[Relevance:\s*(\d+)%\]'
                        kb_matches_with_relevance = re.findall(kb_pattern_with_relevance, kb_results)
                        
                        if kb_matches_with_relevance:
                            # Filter out KB articles already shown in historical results
                            filtered_matches = [(title, url, relevance) for title, url, relevance in kb_matches_with_relevance if url not in historical_kb_urls]
                            
                            if filtered_matches:
                                from tools.kb_content_fetcher import fetch_kb_article_content, format_kb_content
                                
                                for idx, (title, url, relevance) in enumerate(filtered_matches, 1):
                                    with st.expander(f"▸ {title} (Relevance: {relevance}%)", expanded=False):
                                        st.markdown(f"**Title:** {title}")
                                        st.markdown(f"**URL:** [{url}]({url})")
                                        st.markdown(f"**Relevance:** {relevance}%")
                                        
                                        # Fetch and display KB article content
                                        with st.spinner("Fetching article content..."):
                                            kb_content = fetch_kb_article_content(url)
                                            formatted_content = format_kb_content(kb_content)
                                            st.markdown(formatted_content)
                            else:
                                st.info("All web search results are already included in Historical RCA Solutions.")
                        else:
                            # Fallback: Try to parse markdown links without relevance: • [Title](URL)
                            kb_pattern = r'•\s*\[([^\]]+)\]\(([^\)]+)\)'
                            kb_matches = re.findall(kb_pattern, kb_results)
                            
                            if kb_matches:
                                # Filter out KB articles already shown in historical results
                                filtered_matches = [(title, url) for title, url in kb_matches if url not in historical_kb_urls]
                                
                                if filtered_matches:
                                    from tools.kb_content_fetcher import fetch_kb_article_content, format_kb_content
                                    
                                    for idx, (title, url) in enumerate(filtered_matches, 1):
                                        with st.expander(f"▸ {title}", expanded=False):
                                            st.markdown(f"**Title:** {title}")
                                            st.markdown(f"**URL:** [{url}]({url})")
                                            
                                            # Fetch and display KB article content
                                            with st.spinner("Fetching article content..."):
                                                kb_content = fetch_kb_article_content(url)
                                                formatted_content = format_kb_content(kb_content)
                                                st.markdown(formatted_content)
                                else:
                                    st.info("All web search results are already included in Historical RCA Solutions.")
                            else:
                                # Try to parse plain URLs with bullet points
                                url_pattern = r'•\s*(https://knowledge\.broadcom\.com/[^\s\n]+)'
                                url_matches = re.findall(url_pattern, kb_results)
                            
                                if url_matches:
                                    # Filter out KB articles already shown in historical results
                                    filtered_urls = [url for url in url_matches if url not in historical_kb_urls]
                                    
                                    if filtered_urls:
                                        from tools.kb_content_fetcher import fetch_kb_article_content, format_kb_content
                                        
                                        for idx, url in enumerate(filtered_urls, 1):
                                            # Extract article ID from URL for title
                                            article_id_match = re.search(r'/article/(\d+)/', url)
                                            article_id = article_id_match.group(1) if article_id_match else f"Article {idx}"
                                            
                                            with st.expander(f"▸ KB Article {article_id}", expanded=False):
                                                st.markdown(f"**URL:** [{url}]({url})")
                                                
                                                # Fetch and display KB article content
                                                with st.spinner("Fetching article content..."):
                                                    kb_content = fetch_kb_article_content(url)
                                                    formatted_content = format_kb_content(kb_content)
                                                    st.markdown(formatted_content)
                                    else:
                                        st.info("All web search results are already included in Historical RCA Solutions.")
                                else:
                                    # Fallback: show all content in one expander
                                    with st.expander("▸ KB Search Results", expanded=False):
                                        st.markdown(kb_results)
                    
                    # Display KB links from RAG incidents (filter out duplicates)
                    if kb_from_rag:
                        filtered_kb_from_rag = [
                            kb_item for kb_item in kb_from_rag
                            if kb_item.get('kb_link', '').strip() not in historical_kb_urls
                        ]
                        
                        if filtered_kb_from_rag:
                            from tools.kb_content_fetcher import fetch_kb_article_content, format_kb_content
                            
                            for idx, kb_item in enumerate(filtered_kb_from_rag, 1):
                                incident_title = kb_item.get('incident_title', 'N/A')
                                incident_id = kb_item.get('incident_id', 'N/A')
                                kb_link = kb_item.get('kb_link', '')
                                
                                with st.expander(f"▸ {incident_title}", expanded=False):
                                    st.markdown(f"**Source Incident:** {incident_title} ({incident_id})")
                                    st.markdown(f"**KB Article:** [{kb_link}]({kb_link})")
                                    
                                    # Fetch and display KB article content
                                    if kb_link:
                                        with st.spinner("Fetching article content..."):
                                            kb_content = fetch_kb_article_content(kb_link)
                                            formatted_content = format_kb_content(kb_content)
                                            st.markdown(formatted_content)


if __name__ == "__main__":
    main()

# Made with Bob