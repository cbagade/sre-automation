"""Operational Signals Page Component."""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import html
import urllib.parse

from agents.operational_signals_agent import OperationalSignalsAgent
from utils.git_issue_linker import get_git_issue_linker
from utils.git_issue_parser import get_git_issue_parser
from utils.ai_text_enhancer import get_ai_text_enhancer


def render_operational_signals_page():
    """Render the Operational Signals page."""
    
    # Add custom CSS to make buttons same height and highlight selected ones
    st.markdown("""
        <style>
        /* Make all buttons same height */
        div[data-testid="column"] button {
            height: 2.5rem !important;
            min-height: 2.5rem !important;
            padding: 0.25rem 0.75rem !important;
            font-size: 0.875rem !important;
        }
        
        /* Secondary buttons (unselected) - default styling */
        div[data-testid="column"] button[kind="secondary"] {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            color: #e2e8f0 !important;
        }
        
        div[data-testid="column"] button[kind="secondary"]:hover {
            background-color: rgba(255, 255, 255, 0.15) !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
        }
        
        /* Primary buttons (selected) - highlighted with amber/orange gradient */
        div[data-testid="column"] button[kind="primary"] {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
            border: 2px solid #fbbf24 !important;
            box-shadow: 0 0 15px rgba(245, 158, 11, 0.5) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
        }
        
        div[data-testid="column"] button[kind="primary"]:hover {
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%) !important;
            box-shadow: 0 0 20px rgba(245, 158, 11, 0.7) !important;
            transform: translateY(-1px) !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Page header
    st.markdown(
        """
        <div class="glass-card">
            <div class="glass-card-title">Signal Intelligence Controls</div>
            <div class="glass-card-body">
                View component-level operational insights, incident patterns, and infrastructure health signals.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Initialize agent
    if 'ops_agent' not in st.session_state:
        st.session_state.ops_agent = OperationalSignalsAgent()
    
    agent = st.session_state.ops_agent
    
    # Top controls section
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown('<div style="color: #f8fafc; font-weight: 700; margin-bottom: 8px;">Snapshot date</div>', unsafe_allow_html=True)
        # Date picker
        selected_date = st.date_input(
            "Select date",
            value=datetime.now().date(),
            max_value=datetime.now().date(),
            label_visibility="collapsed"
        )
        date_str = selected_date.strftime("%Y-%m-%d")
    
    with col2:
        st.markdown('<div style="color: #f8fafc; font-weight: 700; margin-bottom: 8px;">Refresh from git</div>', unsafe_allow_html=True)
        refresh_button = st.checkbox("Refresh from git", value=False, key="refresh_from_git", label_visibility="collapsed")
    
    with col3:
        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)
        load_button = st.button("🔄 Load Operational Signals", use_container_width=True, type="primary")
    
    # Display snapshot date
    st.markdown(
        f"""
        <div style="margin: 20px 0;">
            <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 4px;">Snapshot date</div>
            <div style="color: #f8fafc; font-size: 2rem; font-weight: 800;">{date_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Region selection
    st.markdown('<div style="color: #f8fafc; font-weight: 700; margin: 20px 0 10px 0; font-size: 1.1rem;">Region</div>', unsafe_allow_html=True)
    
    regions = agent.get_available_regions()
    
    # Initialize selected region
    if 'selected_region' not in st.session_state:
        st.session_state.selected_region = regions[0]
    
    # Create region buttons with highlighting for selected region
    region_cols = st.columns(len(regions))
    
    for idx, region in enumerate(regions):
        with region_cols[idx]:
            is_selected = (st.session_state.selected_region == region)
            button_label = f"{'✓ ' if is_selected else ''}{region}"
            button_type = "primary" if is_selected else "secondary"
            
            if st.button(button_label, key=f"region_{region}", use_container_width=True, type=button_type):
                st.session_state.selected_region = region
                st.rerun()
    
    selected_region = st.session_state.selected_region
    
    # Load data when button is clicked
    if load_button:
        with st.spinner(f"🔍 Loading operational signals for {selected_region} on {date_str}..."):
            result = agent.get_operational_signals(
                region=selected_region,
                date=date_str,
                force_refresh=refresh_button
            )
            st.session_state.ops_signals_result = result
            st.session_state.ops_signals_date = date_str
            st.session_state.ops_signals_region = selected_region
    
    # Display results if available
    if 'ops_signals_result' in st.session_state and st.session_state.ops_signals_result:
        result = st.session_state.ops_signals_result
        
        # Check if we're displaying the current selection
        if (st.session_state.get('ops_signals_date') == date_str and 
            st.session_state.get('ops_signals_region') == selected_region):
            
            status = result.get("status")
            
            if status == "success":
                # Get data
                data = result.get("data", {})
                source = result.get("source", "unknown")
                timeslot = result.get("timeslot", "N/A")
                
                # Display metadata including region
                region_display = st.session_state.get('ops_signals_region', selected_region)
                st.markdown(
                    f"""
                    <div style="margin: 20px 0; padding: 12px; border-radius: 12px;
                         background: rgba(37, 99, 235, 0.1); border: 1px solid rgba(96, 165, 250, 0.2);">
                        <span style="color: #94a3b8;">Source:</span> <span style="color: #bfdbfe; font-weight: 700;">{source.upper()}</span>
                        <span style="margin: 0 12px;">|</span>
                        <span style="color: #94a3b8;">Timeslot:</span> <span style="color: #bfdbfe; font-weight: 700;">{timeslot}</span>
                        <span style="margin: 0 12px;">|</span>
                        <span style="color: #94a3b8;">Region:</span> <span style="color: #bfdbfe; font-weight: 700;">{region_display}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                # Parse and display issues by category
                parsed_issues = agent.parse_issues_by_category(data)
                
                if parsed_issues:
                    # Component filter section
                    st.markdown('<div style="color: #f8fafc; font-weight: 700; margin: 30px 0 10px 0; font-size: 1.1rem;">Component</div>', unsafe_allow_html=True)
                    
                    # Create component buttons - show all components
                    component_names = sorted(list(parsed_issues.keys()))
                    
                    # Calculate number of rows needed (4 buttons per row)
                    num_components = len(component_names)
                    num_rows = (num_components + 3) // 4
                    
                    # Initialize selected component if not set
                    if 'selected_component' not in st.session_state:
                        st.session_state.selected_component = component_names[0]
                    
                    # Display component buttons in rows of 4
                    for row in range(num_rows):
                        start_idx = row * 4
                        end_idx = min(start_idx + 4, num_components)
                        row_components = component_names[start_idx:end_idx]
                        
                        cols = st.columns(len(row_components))
                        for idx, component in enumerate(row_components):
                            with cols[idx]:
                                count = parsed_issues[component]["count"]
                                is_selected = (st.session_state.selected_component == component)
                                
                                # Add visual indicator for selected component
                                button_label = f"{'✓ ' if is_selected else ''}{component} ({count})"
                                button_type = "primary" if is_selected else "secondary"
                                
                                if st.button(button_label, key=f"comp_{component}", use_container_width=True, type=button_type):
                                    st.session_state.selected_component = component
                                    st.rerun()
                    
                    # Display only the selected component's data
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    selected_component = st.session_state.selected_component
                    if selected_component in parsed_issues:
                        component_data = parsed_issues[selected_component]
                        
                        # Check structure type
                        structure = component_data.get("structure", "flat")
                        
                        if structure == "hierarchical":
                            # Display hierarchical structure
                            _render_hierarchical_data(component_data)
                        elif structure == "clusters":
                            # Display clusters structure
                            _render_clusters_data(component_data)
                        elif structure == "vms":
                            # Display VMs structure
                            _render_vms_data(component_data)
                        elif structure == "datastores":
                            # Display datastores structure
                            _render_datastores_data(component_data)
                        elif structure == "alarms":
                            # Display alarms structure
                            _render_alarms_data(component_data)
                        elif structure == "provider_vdcs":
                            # Display provider VDCs structure
                            _render_provider_vdcs_data(component_data)
                        elif structure == "vcenter_alarms":
                            # Display vCenter alarms structure
                            _render_vcenter_alarms_data(component_data)
                        elif structure == "director_cells":
                            # Display director cells structure
                            _render_director_cells_data(component_data)
                        elif structure == "vsan_clusters":
                            # Display vSAN clusters structure
                            _render_vsan_clusters_data(component_data)
                        else:
                            # Display flat structure
                            _render_flat_data(selected_component, component_data)
                else:
                    st.info("No issues found in the data.")
            
            else:
                # Error status
                message = result.get("message", "Unknown error")
                st.error(f"❌ {message}")
        else:
            st.info("👆 Select a region and click 'Load Operational Signals' to view data.")
    else:
        st.info("👆 Select a date and region, then click 'Load Operational Signals' to view data.")


def _render_git_issue_button(git_issue_url: str, unique_key: str = "", signal_info: Optional[Dict[str, str]] = None):
    """Render a styled Git Issue button with linking functionality and display linked issues.
    
    Args:
        git_issue_url: The GitHub issue URL to open for creating new issue
        unique_key: Unique key for the text input to avoid conflicts
        signal_info: Dictionary containing signal identification info for linking
    """
    linker = get_git_issue_linker()
    
    # Create three columns: Create button, Text input, Link button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown(f'''
            <a href="{git_issue_url}" target="_blank" style="
                display: inline-block;
                padding: 0.5rem 1rem;
                background: linear-gradient(135deg, rgba(30, 58, 138, 0.6), rgba(30, 64, 175, 0.4));
                color: #e0e7ff;
                text-decoration: none;
                border-radius: 0.5rem;
                border: 1px solid rgba(96, 165, 250, 0.3);
                font-size: 0.875rem;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                margin-bottom: 0.5rem;
                width: 100%;
                text-align: center;
            " onmouseover="this.style.background='linear-gradient(135deg, rgba(37, 99, 235, 0.7), rgba(59, 130, 246, 0.5))'; this.style.borderColor='rgba(96, 165, 250, 0.5)'; this.style.boxShadow='0 4px 8px rgba(59, 130, 246, 0.3)';"
               onmouseout="this.style.background='linear-gradient(135deg, rgba(30, 58, 138, 0.6), rgba(30, 64, 175, 0.4))'; this.style.borderColor='rgba(96, 165, 250, 0.3)'; this.style.boxShadow='0 2px 4px rgba(0, 0, 0, 0.2)';">
                🔗 Create Issue
            </a>
        ''', unsafe_allow_html=True)
    
    # Handle linking before rendering widgets to avoid session state modification error
    link_button_key = f"link_btn_{unique_key}"
    text_input_key = f"git_issue_link_{unique_key}"
    
    # Check if link button was clicked in previous run
    if link_button_key in st.session_state and st.session_state.get(link_button_key):
        git_issue_value = st.session_state.get(text_input_key, "")
        if git_issue_value and signal_info:
            success = linker.link_issue(signal_info, git_issue_value)
            if success:
                # Clear the text input value for next render
                st.session_state[text_input_key] = ""
                st.success("✅ Issue linked!", icon="✅")
            else:
                st.error("❌ Failed to link issue")
    
    with col2:
        # Text input for linking existing git issue
        git_issue_link = st.text_input(
            "Link existing Git Issue",
            placeholder="Enter Git Issue URL or ID (e.g., #123)",
            key=text_input_key,
            label_visibility="collapsed"
        )
    
    with col3:
        # Link button
        link_button = st.button("🔗 Link Issue", key=link_button_key, use_container_width=True)
    
    # Display linked issues if signal_info is provided
    if signal_info:
        linked_issues = linker.get_linked_issues(signal_info)
        if linked_issues:
            st.markdown("**Issue References:**")
            for issue in linked_issues:
                issue_url = issue["url"]
                linked_at = issue.get("linked_at", "")
                
                # Create a row for each linked issue with unlink button
                issue_col1, issue_col2 = st.columns([4, 1])
                
                with issue_col1:
                    # Display as clickable link
                    st.markdown(f'''
                        <a href="{issue_url}" target="_blank" style="
                            color: #60a5fa;
                            text-decoration: none;
                            font-size: 0.875rem;
                        " onmouseover="this.style.textDecoration='underline';"
                           onmouseout="this.style.textDecoration='none';">
                            🔗 {issue_url}
                        </a>
                    ''', unsafe_allow_html=True)
                
                with issue_col2:
                    # Unlink button
                    if st.button("🗑️", key=f"unlink_{unique_key}_{issue_url}", help="Unlink this issue"):
                        linker.unlink_issue(signal_info, issue_url)
                        st.rerun()


def _create_github_issue_url(title: str, description: str) -> str:
    """Create GitHub issue URL with title and description.
    
    Args:
        title: Issue title
        description: Issue description to populate in WORK ITEM DESCRIPTION section
        
    Returns:
        str: Formatted GitHub issue URL
    """
    base_url = "https://github.ibm.com/VMWSolutions/tracker/issues/new"
    
    # Create body that preserves template structure but fills in the description
    body = f"""# WORK ITEM DESCRIPTION OR ISSUE

{description}

---

# PRIORITY
<!-- Select one: P0 (Critical), P1 (High), P2 (Medium), P3 (Low) -->


# ENVIRONMENT
<!-- e.g., Production, Staging, Development -->


# STEPS TO REPRODUCE (if applicable)


# EXPECTED BEHAVIOR


# ACTUAL BEHAVIOR


# ADDITIONAL CONTEXT


# ATTACHMENTS
<!-- Add any relevant screenshots, logs, or files -->
"""
    
    params = {
        "template": "IaaS-Ops-Request.md",
        "title": title,
        "body": body
    }
    query_string = urllib.parse.urlencode(params)
    return f"{base_url}?{query_string}"


def _render_git_section(git_issue_url: str, unique_key: str, signal_info: Dict[str, str],
                        show_enhanced: bool = True):
    """Render Git section with issue linking and cause/resolution display.
    
    Args:
        git_issue_url: GitHub issue URL for creating new issue
        unique_key: Unique key for widgets
        signal_info: Signal identification info
        show_enhanced: Whether to show AI-enhanced text
    """
    st.markdown('<div style="margin-top: 0.5rem;"></div>', unsafe_allow_html=True)
    st.markdown("**🔗 Git Issue Management:**")
    
    linker = get_git_issue_linker()
    parser = get_git_issue_parser()
    
    # Create three columns: Create button, Text input, Link button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown(f'''
            <a href="{git_issue_url}" target="_blank" style="
                display: inline-block;
                padding: 0.5rem 1rem;
                background: linear-gradient(135deg, rgba(30, 58, 138, 0.6), rgba(30, 64, 175, 0.4));
                color: #e0e7ff;
                text-decoration: none;
                border-radius: 0.5rem;
                border: 1px solid rgba(96, 165, 250, 0.3);
                font-size: 0.875rem;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                margin-bottom: 0.5rem;
                width: 100%;
                text-align: center;
            " onmouseover="this.style.background='linear-gradient(135deg, rgba(37, 99, 235, 0.7), rgba(59, 130, 246, 0.5))'; this.style.borderColor='rgba(96, 165, 250, 0.5)'; this.style.boxShadow='0 4px 8px rgba(59, 130, 246, 0.3)';"
               onmouseout="this.style.background='linear-gradient(135deg, rgba(30, 58, 138, 0.6), rgba(30, 64, 175, 0.4))'; this.style.borderColor='rgba(96, 165, 250, 0.3)'; this.style.boxShadow='0 2px 4px rgba(0, 0, 0, 0.2)';">
                🔗 Create Issue
            </a>
        ''', unsafe_allow_html=True)
    
    # Handle linking
    link_button_key = f"link_btn_{unique_key}"
    text_input_key = f"git_issue_link_{unique_key}"
    
    if link_button_key in st.session_state and st.session_state.get(link_button_key):
        git_issue_value = st.session_state.get(text_input_key, "")
        if git_issue_value and signal_info:
            success = linker.link_issue(signal_info, git_issue_value)
            if success:
                st.session_state[text_input_key] = ""
                st.success("✅ Issue linked!", icon="✅")
            else:
                st.error("❌ Failed to link issue")
    
    with col2:
        git_issue_link = st.text_input(
            "Link existing Git Issue",
            placeholder="Enter Git Issue URL (e.g., https://github.com/org/repo/issues/123)",
            key=text_input_key,
            label_visibility="collapsed"
        )
    
    with col3:
        link_button = st.button("🔗 Link Issue", key=link_button_key, use_container_width=True)
    
    # Display linked issues with cause/resolution
    linked_issues = linker.get_linked_issues(signal_info)
    if linked_issues:
        st.markdown("**Issue References:**")
        
        for idx, issue in enumerate(linked_issues):
            issue_url = issue["url"]
            linked_at = issue.get("linked_at", "")
            
            # Create expandable section for each issue
            with st.expander(f"📋 Issue: {issue_url}", expanded=True):
                # Display issue link and unlink button
                issue_col1, issue_col2 = st.columns([4, 1])
                
                with issue_col1:
                    st.markdown(f'''
                        <a href="{issue_url}" target="_blank" style="
                            color: #60a5fa;
                            text-decoration: none;
                            font-weight: 500;
                        ">
                            🔗 {issue_url}
                        </a>
                    ''', unsafe_allow_html=True)
                
                with issue_col2:
                    unlink_key = f"unlink_{unique_key}_{idx}"
                    if st.button("🗑️ Unlink", key=unlink_key, use_container_width=True):
                        linker.unlink_issue(signal_info, issue_url)
                        st.rerun()
                
                # Parse and display cause/resolution
                with st.spinner("Parsing issue..."):
                    import os
                    token = os.getenv("OPS_SIGNALS_GIT_TOKEN")
                    parsed_data = parser.parse_issue(issue_url, token=token)
                
                if parsed_data.get("error"):
                    st.warning(f"⚠️ {parsed_data['error']}")
                else:
                    # Check if we found cause or resolution
                    has_cause = parsed_data.get("cause") is not None
                    has_resolution = parsed_data.get("resolution") is not None
                    
                    if not has_cause and not has_resolution:
                        st.warning("⚠️ No cause or resolution information found in this Git issue.")
                    else:
                        # Display cause with AI enhancement (to format as paragraph)
                        if has_cause:
                            st.markdown("**🔍 Cause:**")
                            with st.spinner("Formatting cause..."):
                                enhancer = get_ai_text_enhancer()
                                enhanced_cause = enhancer.enhance_cause(parsed_data["cause"])
                            st.markdown(f'<div style="background: rgba(59, 130, 246, 0.1); padding: 1rem; border-radius: 0.5rem; border-left: 3px solid #3b82f6; color: #dbe7f7; line-height: 1.6;">{enhanced_cause}</div>', unsafe_allow_html=True)
                        
                        if has_cause and has_resolution:
                            st.markdown("<br>", unsafe_allow_html=True)
                        
                        # Display resolution with AI enhancement (to format as paragraph)
                        if has_resolution:
                            st.markdown("**✅ Resolution:**")
                            with st.spinner("Formatting resolution..."):
                                enhancer = get_ai_text_enhancer()
                                enhanced_resolution = enhancer.enhance_resolution(parsed_data["resolution"])
                            st.markdown(f'<div style="background: rgba(34, 197, 94, 0.1); padding: 1rem; border-radius: 0.5rem; border-left: 3px solid #22c55e; color: #dbe7f7; line-height: 1.6;">{enhanced_resolution}</div>', unsafe_allow_html=True)


def _render_hierarchical_data(component_data: Dict[str, Any]):
    """Render hierarchical data structure (Category -> Alert -> Resources)."""
    categories = component_data.get("categories", {})
    
    for category_name, category_info in categories.items():
        # Category as collapsible expander
        category_count = category_info["count"]
        
        with st.expander(f"▸ {category_name} ({category_count} resources)", expanded=False):
            # Display alerts under this category
            alerts = category_info.get("alerts", {})
            for alert_name, alert_info in alerts.items():
                resources = alert_info.get("resources", [])
                resource_count = alert_info.get("count", 0)
                
                with st.expander(f"▸ {alert_name} ({resource_count})", expanded=False):
                    # Get region and date from session state
                    region = st.session_state.get('ops_signals_region', 'Unknown')
                    date = st.session_state.get('ops_signals_date', 'Unknown')
                    
                    # Create title and description
                    title = f"Active Critical Alert: {alert_name} - {category_name}"
                    description = f"""## Alert Details
**Region:** {region}
**Date:** {date}
**Category:** {category_name}
**Alert:** {alert_name}
**Affected Resources:** {resource_count}

### Resources
{', '.join([r.get('resourceName', r.get('name', str(r))) if isinstance(r, dict) else str(r) for r in resources[:10]])}
{'...' if len(resources) > 10 else ''}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
                    
                    # Display resources first (moved up)
                    resource_displays = []
                    for resource in resources:
                        if isinstance(resource, dict):
                            # Try different name fields
                            resource_name = (
                                resource.get("resourceName") or
                                resource.get("clusterName") or
                                resource.get("hostName") or
                                resource.get("vmName") or
                                resource.get("name") or
                                "Unknown"
                            )
                            
                            # Add additional info if available
                            additional_info = []
                            if "clusterComputeUsagePercent" in resource:
                                additional_info.append(f"CPU: {resource['clusterComputeUsagePercent']:.1f}%")
                            if "haCpuFailoverPercent" in resource:
                                additional_info.append(f"HA CPU: {resource['haCpuFailoverPercent']}%")
                            if "haMemoryFailoverPercent" in resource:
                                additional_info.append(f"HA Memory: {resource['haMemoryFailoverPercent']}%")
                            
                            if additional_info:
                                resource_displays.append(f"{resource_name} ({', '.join(additional_info)})")
                            else:
                                resource_displays.append(resource_name)
                        else:
                            resource_displays.append(str(resource))
                    
                    # Display resources with count in the label
                    resources_text = ", ".join(resource_displays)
                    st.markdown(f"**📊 Affected Resources ({resource_count}):**")
                    st.markdown(f'<div style="background: rgba(59, 130, 246, 0.05); padding: 0.75rem; border-radius: 0.5rem; color: #dbe7f7; line-height: 1.6; margin-bottom: 1rem;">{resources_text}</div>', unsafe_allow_html=True)
                    
                    # Create GitHub issue URL with query parameters
                    git_issue_url = _create_github_issue_url(title, description)
                    
                    # Add Git section with unique key and signal info
                    unique_key = f"hierarchical_{category_name}_{alert_name}".replace(" ", "_").replace("/", "_")
                    signal_info = {
                        "component": "Hierarchical",
                        "category": category_name,
                        "alert_name": alert_name
                    }
                    _render_git_section(git_issue_url, unique_key, signal_info)


def _render_clusters_data(component_data: Dict[str, Any]):
    """Render clusters data structure (Issue Type -> Clusters)."""
    issues = component_data.get("issues", [])
    
    for issue_data in issues:
        issue_type = issue_data.get("issue_type", "Unknown Issue")
        clusters = issue_data.get("clusters", [])
        cluster_count = issue_data.get("count", len(clusters))
        
        # Display issue type as collapsible expander
        with st.expander(f"▸ {issue_type} ({cluster_count})", expanded=False):
            region = st.session_state.get('ops_signals_region', 'Unknown')
            date = st.session_state.get('ops_signals_date', 'Unknown')
            
            title = f"Clusters Needing Attention: {issue_type}"
            description = f"""## Issue Details
**Region:** {region}
**Date:** {date}
**Component:** Clusters Needing Attention
**Issue Type:** {issue_type}
**Affected Clusters:** {cluster_count}

### Clusters
{', '.join([c.get('clusterName', c.get('name', str(c))) if isinstance(c, dict) else str(c) for c in clusters[:10]])}
{'...' if len(clusters) > 10 else ''}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
            
            # Display clusters first (moved up)
            cluster_displays = []
            for cluster in clusters:
                if isinstance(cluster, dict):
                    # Try different name fields
                    cluster_name = (
                        cluster.get("clusterName") or
                        cluster.get("name") or
                        "Unknown"
                    )
                    
                    # Add additional info if available
                    additional_info = []
                    if "clusterComputeUsagePercent" in cluster:
                        additional_info.append(f"CPU: {cluster['clusterComputeUsagePercent']:.1f}%")
                    if "haCpuFailoverPercent" in cluster:
                        additional_info.append(f"HA CPU: {cluster['haCpuFailoverPercent']}%")
                    if "haMemoryFailoverPercent" in cluster:
                        additional_info.append(f"HA Memory: {cluster['haMemoryFailoverPercent']}%")
                    
                    if additional_info:
                        cluster_displays.append(f"{cluster_name} ({', '.join(additional_info)})")
                    else:
                        cluster_displays.append(cluster_name)
                else:
                    cluster_displays.append(str(cluster))
            
            # Display clusters with enhanced styling
            clusters_text = ", ".join(cluster_displays)
            st.markdown(f"**📊 Affected Clusters ({cluster_count}):**")
            st.markdown(f'<div style="background: rgba(59, 130, 246, 0.05); padding: 0.75rem; border-radius: 0.5rem; color: #dbe7f7; line-height: 1.6; margin-bottom: 1rem;">{clusters_text}</div>', unsafe_allow_html=True)
            
            # Git section below resources
            git_issue_url = _create_github_issue_url(title, description)
            unique_key = f"clusters_{issue_type}".replace(" ", "_").replace("/", "_")
            signal_info = {
                "component": "Clusters",
                "alert_name": issue_type
            }
            _render_git_section(git_issue_url, unique_key, signal_info)


def _render_vms_data(component_data: Dict[str, Any]):
    """Render VMs data structure (Issue Type -> VMs)."""
    issues = component_data.get("issues", [])
    
    for issue_data in issues:
        issue_type = issue_data.get("issue_type", "Unknown Issue")
        vms = issue_data.get("vms", [])
        vm_count = issue_data.get("count", len(vms))
        
        # Display issue type as collapsible expander
        with st.expander(f"▸ {issue_type} ({vm_count})", expanded=False):
            region = st.session_state.get('ops_signals_region', 'Unknown')
            date = st.session_state.get('ops_signals_date', 'Unknown')
            
            title = f"Management VMs Needing Attention: {issue_type}"
            description = f"""## Issue Details
**Region:** {region}
**Date:** {date}
**Component:** Management VMs Needing Attention
**Issue Type:** {issue_type}
**Affected VMs:** {vm_count}

### VMs
{', '.join([vm.get('name', str(vm)) if isinstance(vm, dict) else str(vm) for vm in vms[:10]])}
{'...' if len(vms) > 10 else ''}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
            
            git_issue_url = _create_github_issue_url(title, description)
            unique_key = f"vms_{issue_type}".replace(" ", "_").replace("/", "_")
            signal_info = {
                "component": "VMs",
                "alert_name": issue_type
            }
            _render_git_issue_button(git_issue_url, unique_key, signal_info)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display VMs intelligently based on their structure
            vm_displays = []
            for vm in vms:
                if isinstance(vm, dict):
                    # Get VM name
                    vm_name = vm.get("name", "Unknown")
                    
                    # Add additional info based on issue type
                    additional_info = []
                    
                    # OS uptime
                    if "osUptimeDays" in vm and vm["osUptimeDays"] is not None:
                        additional_info.append(f"Uptime: {vm['osUptimeDays']:.2f} days")
                    
                    # Packet drops
                    if "packetDropsPercent" in vm and vm["packetDropsPercent"] is not None:
                        additional_info.append(f"Packet Drops: {vm['packetDropsPercent']:.1f}%")
                    
                    # Power state
                    if "powerState" in vm and vm["powerState"]:
                        additional_info.append(f"State: {vm['powerState']}")
                    
                    # Availability
                    if "availabilityPercent" in vm and vm["availabilityPercent"] is not None:
                        additional_info.append(f"Availability: {vm['availabilityPercent']:.1f}%")
                    
                    # CPU usage
                    if "cpuUsagePercent" in vm and vm["cpuUsagePercent"] is not None:
                        additional_info.append(f"CPU: {vm['cpuUsagePercent']:.1f}%")
                    
                    # Memory usage
                    if "memoryUsagePercent" in vm and vm["memoryUsagePercent"] is not None:
                        additional_info.append(f"Memory: {vm['memoryUsagePercent']:.1f}%")
                    
                    # Guest filesystem
                    if "guestFilesystem" in vm and vm["guestFilesystem"]:
                        fs = vm["guestFilesystem"]
                        if "guestFileUtilizationPercent" in vm and vm["guestFileUtilizationPercent"] is not None:
                            additional_info.append(f"{fs}: {vm['guestFileUtilizationPercent']:.1f}%")
                    
                    if additional_info:
                        vm_displays.append(f"{vm_name} ({', '.join(additional_info)})")
                    else:
                        vm_displays.append(vm_name)
                else:
                    vm_displays.append(str(vm))
            
            # Display VMs
            vms_text = ", ".join(vm_displays)
            st.markdown(f'<div style="color: #dbe7f7; line-height: 1.6;">{vms_text}</div>', unsafe_allow_html=True)


def _render_datastores_data(component_data: Dict[str, Any]):
    """Render datastores data structure (Issue Type -> Datastores)."""
    issues = component_data.get("issues", [])
    
    for issue_data in issues:
        issue_type = issue_data.get("issue_type", "Unknown Issue")
        datastores = issue_data.get("datastores", [])
        datastore_count = issue_data.get("count", len(datastores))
        
        # Display issue type as collapsible expander
        with st.expander(f"▸ {issue_type} ({datastore_count})", expanded=False):
            region = st.session_state.get('ops_signals_region', 'Unknown')
            date = st.session_state.get('ops_signals_date', 'Unknown')
            
            title = f"NFS Datastores Needing Attention: {issue_type}"
            description = f"""## Issue Details
**Region:** {region}
**Date:** {date}
**Component:** NFS Datastores Needing Attention
**Issue Type:** {issue_type}
**Affected Datastores:** {datastore_count}

### Datastores
{', '.join([ds.get('name', str(ds)) if isinstance(ds, dict) else str(ds) for ds in datastores[:10]])}
{'...' if len(datastores) > 10 else ''}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
            
            git_issue_url = _create_github_issue_url(title, description)
            unique_key = f"datastores_{issue_type}".replace(" ", "_").replace("/", "_")
            signal_info = {
                "component": "Datastores",
                "alert_name": issue_type
            }
            _render_git_issue_button(git_issue_url, unique_key, signal_info)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display datastores intelligently based on their structure
            datastore_displays = []
            for datastore in datastores:
                if isinstance(datastore, dict):
                    # Get datastore name
                    datastore_name = datastore.get("name", "Unknown")
                    
                    # Add additional info based on available fields
                    additional_info = []
                    
                    # Usage percent
                    if "usagePercent" in datastore and datastore["usagePercent"] is not None:
                        additional_info.append(f"Usage: {datastore['usagePercent']:.1f}%")
                    
                    # Disk space remaining
                    if "diskSpaceRemainingTB" in datastore and datastore["diskSpaceRemainingTB"] is not None:
                        additional_info.append(f"Remaining: {datastore['diskSpaceRemainingTB']:.2f} TB")
                    
                    if "diskSpaceRemainingPercent" in datastore and datastore["diskSpaceRemainingPercent"] is not None:
                        additional_info.append(f"{datastore['diskSpaceRemainingPercent']:.1f}%")
                    
                    if additional_info:
                        datastore_displays.append(f"{datastore_name} ({', '.join(additional_info)})")
                    else:
                        datastore_displays.append(datastore_name)
                else:
                    datastore_displays.append(str(datastore))
            
            # Display datastores
            datastores_text = ", ".join(datastore_displays)
            st.markdown(f'<div style="color: #dbe7f7; line-height: 1.6;">{datastores_text}</div>', unsafe_allow_html=True)


def _render_alarms_data(component_data: Dict[str, Any]):
    """Render alarms data structure (Alarm Type -> Alarms)."""
    import json
    
    issues = component_data.get("issues", [])
    
    for issue_data in issues:
        issue_type = issue_data.get("issue_type", "Unknown Issue")
        alarms = issue_data.get("alarms", [])
        alarm_count = issue_data.get("count", len(alarms))
        
        # Format alarm type for display
        formatted_alarm_type = issue_type.replace("_", " ").title()
        
        # Display alarm type as collapsible expander
        with st.expander(f"▸ {formatted_alarm_type} ({alarm_count})", expanded=False):
            region = st.session_state.get('ops_signals_region', 'Unknown')
            date = st.session_state.get('ops_signals_date', 'Unknown')
            
            title = f"NSX Alarms: {formatted_alarm_type}"
            description = f"""## Issue Details
**Region:** {region}
**Date:** {date}
**Component:** NSX Alarms
**Alarm Type:** {formatted_alarm_type}
**Affected Alarms:** {alarm_count}

### Alarm Summary
Total alarms of this type: {alarm_count}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
            
            git_issue_url = _create_github_issue_url(title, description)
            unique_key = f"alarms_{issue_type}".replace(" ", "_").replace("/", "_")
            signal_info = {
                "component": "Alarms",
                "alert_name": issue_type
            }
            _render_git_issue_button(git_issue_url, unique_key, signal_info)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display each alarm as a nested collapsible
            for idx, alarm in enumerate(alarms, 1):
                if isinstance(alarm, dict):
                    # Create header: node_id (node_resource_type)
                    node_id = alarm.get("node_id", "Unknown")
                    node_resource_type = alarm.get("node_resource_type", "Unknown")
                    alarm_header = f"{node_id} ({node_resource_type})"
                    
                    # Nested expander for each alarm
                    with st.expander(f"▸ {alarm_header}", expanded=False):
                        # Display full JSON content line by line
                        for key, value in alarm.items():
                            # Format the value for display
                            if isinstance(value, str):
                                # For long strings, display with proper wrapping
                                display_value = value
                            else:
                                display_value = json.dumps(value, indent=2)
                            
                            # Display key-value pair
                            st.markdown(f"**{key}:**")
                            st.markdown(f'<div style="color: #dbe7f7; line-height: 1.6; margin-bottom: 12px; white-space: pre-wrap; word-wrap: break-word;">{display_value}</div>', unsafe_allow_html=True)
                else:
                    st.text(str(alarm))


def _render_provider_vdcs_data(component_data: Dict[str, Any]):
    """Render provider VDCs data structure (Issue Type -> Provider VDCs)."""
    issues = component_data.get("issues", [])
    
    for issue_data in issues:
        issue_type = issue_data.get("issue_type", "Unknown Issue")
        provider_vdcs = issue_data.get("provider_vdcs", [])
        vdc_count = issue_data.get("count", len(provider_vdcs))
        
        # Display issue type as collapsible expander
        with st.expander(f"▸ {issue_type} ({vdc_count})", expanded=False):
            region = st.session_state.get('ops_signals_region', 'Unknown')
            date = st.session_state.get('ops_signals_date', 'Unknown')
            
            title = f"Provider VDCs Needing Attention: {issue_type}"
            description = f"""## Issue Details
**Region:** {region}
**Date:** {date}
**Component:** Provider VDCs Needing Attention
**Issue Type:** {issue_type}
**Affected Provider VDCs:** {vdc_count}

### Provider VDCs
{', '.join([vdc.get('name', str(vdc)) if isinstance(vdc, dict) else str(vdc) for vdc in provider_vdcs[:10]])}
{'...' if len(provider_vdcs) > 10 else ''}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
            
            git_issue_url = _create_github_issue_url(title, description)
            unique_key = f"provider_vdcs_{issue_type}".replace(" ", "_").replace("/", "_")
            signal_info = {
                "component": "Provider VDCs",
                "alert_name": issue_type
            }
            _render_git_issue_button(git_issue_url, unique_key, signal_info)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display provider VDCs intelligently based on their structure
            vdc_displays = []
            for vdc in provider_vdcs:
                if isinstance(vdc, dict):
                    # Get VDC name
                    vdc_name = vdc.get("name", "Unknown")
                    
                    # Add additional info based on available fields
                    additional_info = []
                    
                    # Capacity remaining
                    if "capacityRemainingPercent" in vdc and vdc["capacityRemainingPercent"] is not None:
                        additional_info.append(f"Capacity Remaining: {vdc['capacityRemainingPercent']:.1f}%")
                    
                    # Memory utilization
                    if "memoryUtilizationPercent" in vdc and vdc["memoryUtilizationPercent"] is not None:
                        additional_info.append(f"Memory Utilization: {vdc['memoryUtilizationPercent']:.1f}%")
                    
                    # Health
                    if "health" in vdc and vdc["health"] is not None:
                        additional_info.append(f"Health: {vdc['health']:.1f}%")
                    
                    if additional_info:
                        vdc_displays.append(f"{vdc_name} ({', '.join(additional_info)})")
                    else:
                        vdc_displays.append(vdc_name)
                else:
                    vdc_displays.append(str(vdc))
            
            # Display provider VDCs
            vdcs_text = ", ".join(vdc_displays)
            st.markdown(f'<div style="color: #dbe7f7; line-height: 1.6;">{vdcs_text}</div>', unsafe_allow_html=True)


def _render_vcenter_alarms_data(component_data: Dict[str, Any]):
    """Render vCenter alarms data structure (Alarm Type -> Alarms)."""
    issues = component_data.get("issues", [])
    
    for issue_data in issues:
        issue_type = issue_data.get("issue_type", "Unknown Issue")
        vcenter_alarms = issue_data.get("vcenter_alarms", [])
        alarm_count = issue_data.get("count", len(vcenter_alarms))
        
        # Display alarm type as collapsible expander
        with st.expander(f"▸ {issue_type} ({alarm_count})", expanded=False):
            region = st.session_state.get('ops_signals_region', 'Unknown')
            date = st.session_state.get('ops_signals_date', 'Unknown')
            
            title = f"vCenter Alarms: {issue_type}"
            description = f"""## Issue Details
**Region:** {region}
**Date:** {date}
**Component:** vCenter Alarms
**Alarm Type:** {issue_type}
**Affected VMs:** {alarm_count}

### VM Summary
{', '.join([alarm.get('vm_name', str(alarm)) if isinstance(alarm, dict) else str(alarm) for alarm in vcenter_alarms[:10]])}
{'...' if len(vcenter_alarms) > 10 else ''}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
            
            git_issue_url = _create_github_issue_url(title, description)
            unique_key = f"vcenter_alarms_{issue_type}".replace(" ", "_").replace("/", "_")
            signal_info = {
                "component": "vCenter Alarms",
                "alert_name": issue_type
            }
            _render_git_issue_button(git_issue_url, unique_key, signal_info)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display vCenter alarms intelligently based on their structure
            alarm_displays = []
            for alarm in vcenter_alarms:
                if isinstance(alarm, dict):
                    # Get VM name and status
                    vm_name = alarm.get("vm_name", "Unknown")
                    status = alarm.get("status", "").upper()
                    
                    # Display format: vm_name (STATUS)
                    if status:
                        alarm_displays.append(f"{vm_name} ({status})")
                    else:
                        alarm_displays.append(vm_name)
                else:
                    alarm_displays.append(str(alarm))
            
            # Display vCenter alarms
            alarms_text = ", ".join(alarm_displays)
            st.markdown(f'<div style="color: #dbe7f7; line-height: 1.6;">{alarms_text}</div>', unsafe_allow_html=True)




def _render_director_cells_data(component_data: Dict[str, Any]):
    """Render director cells data structure (Issue Type -> Director Cells)."""
    issues = component_data.get("issues", [])
    
    for issue_data in issues:
        issue_type = issue_data.get("issue_type", "Unknown Issue")
        director_cells = issue_data.get("director_cells", [])
        cell_count = issue_data.get("count", len(director_cells))
        
        # Display issue type as collapsible expander
        with st.expander(f"▸ {issue_type} ({cell_count})", expanded=False):
            region = st.session_state.get('ops_signals_region', 'Unknown')
            date = st.session_state.get('ops_signals_date', 'Unknown')
            
            title = f"vCloud Director Cells Needing Attention: {issue_type}"
            description = f"""## Issue Details
**Region:** {region}
**Date:** {date}
**Component:** vCloud Director Cells Needing Attention
**Issue Type:** {issue_type}
**Affected Director Cells:** {cell_count}

### Director Cells
{', '.join([cell.get('name', str(cell)) if isinstance(cell, dict) else str(cell) for cell in director_cells[:10]])}
{'...' if len(director_cells) > 10 else ''}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
            
            git_issue_url = _create_github_issue_url(title, description)
            unique_key = f"director_cells_{issue_type}".replace(" ", "_").replace("/", "_")
            signal_info = {
                "component": "Director Cells",
                "alert_name": issue_type
            }
            _render_git_issue_button(git_issue_url, unique_key, signal_info)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display director cells intelligently based on their structure
            cell_displays = []
            for cell in director_cells:
                if isinstance(cell, dict):
                    # Get cell name
                    cell_name = cell.get("name", "Unknown")
                    
                    # Add additional info based on available fields
                    additional_info = []
                    
                    # Available disk space
                    if "availableDiskSpaceGB" in cell and cell["availableDiskSpaceGB"] is not None:
                        additional_info.append(f"Disk: {cell['availableDiskSpaceGB']:.2f} GB")
                    
                    # Guest filesystem utilization
                    if "guestFilesystemUtilizationPercent" in cell and cell["guestFilesystemUtilizationPercent"] is not None:
                        additional_info.append(f"FS Util: {cell['guestFilesystemUtilizationPercent']:.1f}%")
                    
                    if additional_info:
                        cell_displays.append(f"{cell_name} ({', '.join(additional_info)})")
                    else:
                        cell_displays.append(cell_name)
                else:
                    cell_displays.append(str(cell))
            # Display director cells
            cells_text = ", ".join(cell_displays)
            st.markdown(f'<div style="color: #dbe7f7; line-height: 1.6;">{cells_text}</div>', unsafe_allow_html=True)



def _render_vsan_clusters_data(component_data: Dict[str, Any]):
    """Render vSAN clusters data structure (Issue Type -> vSAN Clusters)."""
    issues = component_data.get("issues", [])
    
    for issue_data in issues:
        issue_type = issue_data.get("issue_type", "Unknown Issue")
        vsan_clusters = issue_data.get("vsan_clusters", [])
        cluster_count = issue_data.get("count", len(vsan_clusters))
        
        # Display issue type as collapsible expander
        with st.expander(f"▸ {issue_type} ({cluster_count})", expanded=False):
            region = st.session_state.get('ops_signals_region', 'Unknown')
            date = st.session_state.get('ops_signals_date', 'Unknown')
            
            title = f"vSAN Clusters Needing Attention: {issue_type}"
            description = f"""## Issue Details
**Region:** {region}
**Date:** {date}
**Component:** vSAN Clusters Needing Attention
**Issue Type:** {issue_type}
**Affected vSAN Clusters:** {cluster_count}

### vSAN Clusters
{', '.join([cluster.get('name', str(cluster)) if isinstance(cluster, dict) else str(cluster) for cluster in vsan_clusters[:10]])}
{'...' if len(vsan_clusters) > 10 else ''}

---
*This issue was automatically created from the Operational Signals Dashboard*
"""
            
            git_issue_url = _create_github_issue_url(title, description)
            unique_key = f"vsan_clusters_{issue_type}".replace(" ", "_").replace("/", "_")
            signal_info = {
                "component": "vSAN Clusters",
                "alert_name": issue_type
            }
            _render_git_issue_button(git_issue_url, unique_key, signal_info)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display vSAN clusters intelligently based on their structure
            cluster_displays = []
            for cluster in vsan_clusters:
                if isinstance(cluster, dict):
                    # Get cluster name
                    cluster_name = cluster.get("name", "Unknown")
                    
                    # Add additional info based on available fields
                    additional_info = []
                    
                    # Total disk space
                    if "totalDiskSpaceTB" in cluster and cluster["totalDiskSpaceTB"] is not None:
                        additional_info.append(f"Total: {cluster['totalDiskSpaceTB']:.2f} TB")
                    
                    # Disk space remaining
                    if "diskSpaceRemainingTB" in cluster and cluster["diskSpaceRemainingTB"] is not None:
                        additional_info.append(f"Remaining: {cluster['diskSpaceRemainingTB']:.2f} TB")
                    
                    if "diskSpaceRemainingPercent" in cluster and cluster["diskSpaceRemainingPercent"] is not None:
                        additional_info.append(f"{cluster['diskSpaceRemainingPercent']:.1f}%")
                    
                    # vSAN health score
                    if "vSANHealthScore" in cluster and cluster["vSANHealthScore"] is not None:
                        additional_info.append(f"Health: {cluster['vSANHealthScore']:.0f}")
                    
                    if additional_info:
                        cluster_displays.append(f"{cluster_name} ({', '.join(additional_info)})")
                    else:
                        cluster_displays.append(cluster_name)
                else:
                    cluster_displays.append(str(cluster))
            
            # Display vSAN clusters
            clusters_text = ", ".join(cluster_displays)
            st.markdown(f'<div style="color: #dbe7f7; line-height: 1.6;">{clusters_text}</div>', unsafe_allow_html=True)


def _render_flat_data(component_name: str, component_data: Dict[str, Any]):
    """Render flat data structure."""
    issues = component_data.get("issues", [])
    count = component_data.get("count", 0)
    
    # Component header
    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(148, 163, 184, 0.18); 
            border-radius: 12px; 
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.72), rgba(30, 41, 59, 0.42)); 
            padding: 12px 16px; 
            margin: 16px 0 8px 0;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="color: #f8fafc; font-weight: 800; font-size: 1.15rem;">
                    {html.escape(component_name)}
                </div>
                <div style="
                    background: rgba(56, 189, 248, 0.15); 
                    color: #7dd3fc; 
                    padding: 4px 12px; 
                    border-radius: 999px; 
                    font-weight: 700;
                    font-size: 0.9rem;
                    border: 1px solid rgba(125, 211, 252, 0.3);
                ">
                    {count} issue{"s" if count != 1 else ""}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Display each issue in a collapsible expander
    for idx, issue in enumerate(issues, 1):
        issue_title = _get_issue_title(issue, idx)
        
        with st.expander(f"▸ Issue {idx}: {issue_title}", expanded=False):
            _render_issue_details(issue)


def _get_issue_title(issue: Any, index: int) -> str:
    """Extract a title from an issue object."""
    if isinstance(issue, dict):
        # Try common title fields
        for field in ['title', 'name', 'description', 'summary', 'message', 'alert_name', 'resourceName']:
            if field in issue:
                title = str(issue[field])
                return title[:100] + "..." if len(title) > 100 else title
        
        # If no title field, use first value
        if issue:
            first_value = str(list(issue.values())[0])
            return first_value[:100] + "..." if len(first_value) > 100 else first_value
    
    return f"Issue {index}"


def _render_issue_details(issue: Any):
    """Render issue details."""
    if isinstance(issue, dict):
        # Display as formatted JSON
        for key, value in issue.items():
            st.markdown(f"**{key}:**")
            if isinstance(value, (dict, list)):
                st.json(value)
            else:
                st.markdown(f"```\n{value}\n```")
    else:
        # Display as text
        st.markdown(f"```\n{issue}\n```")

# Made with Bob
