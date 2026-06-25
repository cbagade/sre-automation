"""Incident Intelligence Page Component.

This page provides intelligent analysis and insights based strictly on ingested RCA data
from the vector database. It includes trend analysis, component risk assessment, and
AI-generated executive summaries.
"""

import sys
from pathlib import Path
import streamlit as st
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.incident_intelligence_agent import IncidentIntelligenceAgent


def render_incident_intelligence_page():
    """Render the Incident Intelligence page with rich UI and analytics."""
    
    # Page header
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <div style="font-size: 1.1rem; color: #94a3b8; margin-bottom: 8px;">
                Trend analysis, change correlation, and component risk insights
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Initialize agent
    try:
        agent = IncidentIntelligenceAgent()
    except Exception as e:
        st.error(f"Failed to initialize Incident Intelligence Agent: {str(e)}")
        return
    
    # Filters section
    col1, col2, col3 = st.columns([1.4, 1, 1])

    _TIME_OPTIONS = {
        "Last 1 month":   ("last_1_months",  1,  "months"),
        "Last 3 months":  ("last_3_months",  3,  "months"),
        "Last 6 months":  ("last_6_months",  6,  "months"),
        "Last 1 year":    ("last_1_years",   1,  "years"),
        "Custom range":   (None,             None, None),
    }

    with col1:
        st.markdown(
            '<div style="margin-bottom:5px;font-size:0.9rem;font-weight:700;color:#f8fafc;">Time Period</div>',
            unsafe_allow_html=True,
        )
        time_label = st.selectbox(
            "Time Period",
            options=list(_TIME_OPTIONS.keys()),
            index=1,
            label_visibility="collapsed",
            key="time_label"
        )

    with col2:
        st.markdown(
            '<div style="margin-bottom:5px;font-size:0.9rem;font-weight:700;color:#f8fafc;">Group by</div>',
            unsafe_allow_html=True,
        )
        group_by = st.selectbox(
            "Group by",
            options=["month", "quarter", "year"],
            index=0,
            format_func=lambda x: x.capitalize(),
            label_visibility="collapsed",
            key="group_by"
        )

    with col3:
        st.markdown("<div style='margin-bottom:5px;font-size:0.9rem;font-weight:700;color:transparent;'>.</div>", unsafe_allow_html=True)
        change_related_only = st.checkbox("Change-related only", value=False)

    # Custom date range pickers (only shown when Custom range is selected)
    if time_label == "Custom range":
        from datetime import date, timedelta
        cr_col1, cr_col2 = st.columns(2)
        with cr_col1:
            custom_start = st.date_input("From", value=date.today() - timedelta(days=90), key="custom_start")
        with cr_col2:
            custom_end = st.date_input("To", value=date.today(), key="custom_end")

    # Resolve time_period from selection
    _tp, _tv, _tu = _TIME_OPTIONS[time_label]
    time_period = "all" if time_label == "Custom range" else _tp
    
    
    # Generate analysis
    with st.spinner("🤖 Analyzing incident intelligence..."):
        try:
            # Get executive summary
            summary = agent.generate_executive_summary(
                time_period=time_period,
                group_by=group_by,
                change_related_only=change_related_only
            )
            
            # Get additional analytics
            trends = agent.analyze_trends(time_period=time_period, group_by=group_by, change_related_only=change_related_only)
            components = agent.analyze_components(time_period=time_period, change_related_only=change_related_only)
            change_correlation = agent.analyze_change_correlation(time_period=time_period)
            chart_data = agent.get_affected_components_chart_data(time_period=time_period, change_related_only=change_related_only)
            component_mix = agent.get_component_mix_over_time(time_period=time_period, group_by=group_by, change_related_only=change_related_only)
            recommended_actions = agent.get_recommended_actions(time_period=time_period, change_related_only=change_related_only)
            
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
            return
    
    import html as _html

    what_happened      = _html.escape(summary.get('what_happened',  'No data available'))
    most_impacted_text = _html.escape(summary.get('most_impacted',  'No data available'))
    change_pattern     = _html.escape(summary.get('change_pattern', 'No data available'))
    next_action        = _html.escape(summary.get('next_action',    'No data available'))

    # ── Unified compact header panel (summary + KPIs) ────────────────────────
    total_inc          = trends.get('total_incidents', 0)
    chg_related        = change_correlation.get('change_related_incidents', 0)
    top_component      = components.get('most_impacted', 'N/A')
    time_buckets_count = len(trends.get('time_buckets', {}))
    period_label       = time_label
    inc_status         = 'Higher activity' if total_inc   > 5 else 'Normal range'
    chg_status         = 'Needs attention' if chg_related > 0 else 'No change signal'
    chg_sc             = '#fb923c'         if chg_related > 0 else '#34d399'

    _header_html = (
        f'<div style="border:1px solid rgba(148,163,184,0.20); border-radius:14px;'
        f'background:linear-gradient(160deg,rgba(15,23,42,0.94) 0%,rgba(22,33,58,0.84) 100%);'
        f'padding:14px 18px 12px 18px; margin:16px 0 0 0;">'
        f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">'
        f'<span style="font-size:0.88rem; font-weight:800; color:#f1f5f9; letter-spacing:0.01em;">Executive Summary</span>'
        f'<span style="padding:2px 10px; border-radius:999px; border:1px solid rgba(99,179,237,0.35);'
        f'background:rgba(37,99,235,0.18); color:#93c5fd; font-size:0.65rem;'
        f'font-weight:700; letter-spacing:0.04em;">AI-generated operational intelligence</span>'
        f'</div>'
        f'<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:10px;">'

        f'<div style="background:rgba(30,41,59,0.60); border:1px solid rgba(99,179,237,0.15); border-radius:8px; padding:9px 12px;">'
        f'<div style="color:#7dd3fc; font-size:0.6rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:5px;">WHAT HAPPENED?</div>'
        f'<div style="color:#cbd5e1; font-size:0.75rem; line-height:1.45;">{what_happened}</div>'
        f'</div>'

        f'<div style="background:rgba(30,41,59,0.60); border:1px solid rgba(99,179,237,0.15); border-radius:8px; padding:9px 12px;">'
        f'<div style="color:#7dd3fc; font-size:0.6rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:5px;">MOST IMPACTED</div>'
        f'<div style="color:#cbd5e1; font-size:0.75rem; line-height:1.45;">{most_impacted_text}</div>'
        f'</div>'

        f'<div style="background:rgba(30,41,59,0.60); border:1px solid rgba(99,179,237,0.15); border-radius:8px; padding:9px 12px;">'
        f'<div style="color:#7dd3fc; font-size:0.6rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:5px;">CHANGE PATTERN</div>'
        f'<div style="color:#cbd5e1; font-size:0.75rem; line-height:1.45;">{change_pattern}</div>'
        f'</div>'

        f'<div style="background:rgba(30,41,59,0.60); border:1px solid rgba(99,179,237,0.15); border-radius:8px; padding:9px 12px;">'
        f'<div style="color:#7dd3fc; font-size:0.6rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:5px;">NEXT ACTION</div>'
        f'<div style="color:#cbd5e1; font-size:0.75rem; line-height:1.45;">{next_action}</div>'
        f'</div>'

        f'</div>'
        f'<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px; border-top:1px solid rgba(148,163,184,0.12); padding-top:10px;">'

        f'<div style="border:1px solid rgba(56,189,248,0.22); border-radius:10px; background:rgba(15,23,42,0.55); padding:10px 14px;">'
        f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">'
        f'<span style="color:#7dd3fc; font-size:0.6rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em;">TOTAL INCIDENTS</span>'
        f'<span style="background:rgba(37,99,235,0.30); color:#93c5fd; font-size:0.58rem; font-weight:800; padding:2px 6px; border-radius:4px;">INC</span>'
        f'</div>'
        f'<div style="color:#f1f5f9; font-size:1.6rem; font-weight:900; line-height:1; margin-bottom:4px;">{total_inc}</div>'
        f'<div style="color:#475569; font-size:0.68rem; margin-bottom:4px;">{period_label}</div>'
        f'<div style="color:#34d399; font-size:0.68rem; font-weight:700;">{inc_status}</div>'
        f'</div>'

        f'<div style="border:1px solid rgba(45,212,191,0.22); border-radius:10px; background:rgba(15,23,42,0.55); padding:10px 14px;">'
        f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">'
        f'<span style="color:#5eead4; font-size:0.6rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em;">CHANGE-RELATED</span>'
        f'<span style="background:rgba(20,184,166,0.25); color:#5eead4; font-size:0.58rem; font-weight:800; padding:2px 6px; border-radius:4px;">CHG</span>'
        f'</div>'
        f'<div style="color:#f1f5f9; font-size:1.6rem; font-weight:900; line-height:1; margin-bottom:4px;">{chg_related}</div>'
        f'<div style="color:#475569; font-size:0.68rem; margin-bottom:4px;">Incidents with CBC or change signal.</div>'
        f'<div style="color:{chg_sc}; font-size:0.68rem; font-weight:700;">{chg_status}</div>'
        f'</div>'

        f'<div style="border:1px solid rgba(251,191,36,0.22); border-radius:10px; background:rgba(15,23,42,0.55); padding:10px 14px;">'
        f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">'
        f'<span style="color:#fcd34d; font-size:0.6rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em;">TOP RISK COMPONENT</span>'
        f'<span style="background:rgba(245,158,11,0.25); color:#fcd34d; font-size:0.58rem; font-weight:800; padding:2px 6px; border-radius:4px;">TOP</span>'
        f'</div>'
        f'<div style="color:#f1f5f9; font-size:1.6rem; font-weight:900; line-height:1; margin-bottom:4px;">{top_component}</div>'
        f'<div style="color:#475569; font-size:0.68rem; margin-bottom:4px;">Highest recurring component in scope.</div>'
        f'<div style="color:#f87171; font-size:0.68rem; font-weight:700;">Risk concentration</div>'
        f'</div>'

        f'<div style="border:1px solid rgba(148,163,184,0.22); border-radius:10px; background:rgba(15,23,42,0.55); padding:10px 14px;">'
        f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">'
        f'<span style="color:#94a3b8; font-size:0.6rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em;">BUCKETS</span>'
        f'<span style="background:rgba(71,85,105,0.40); color:#94a3b8; font-size:0.58rem; font-weight:800; padding:2px 6px; border-radius:4px;">TME</span>'
        f'</div>'
        f'<div style="color:#f1f5f9; font-size:1.6rem; font-weight:900; line-height:1; margin-bottom:4px;">{time_buckets_count}</div>'
        f'<div style="color:#475569; font-size:0.68rem; margin-bottom:4px;">Time buckets grouped by {group_by}.</div>'
        f'<div style="color:#60a5fa; font-size:0.68rem; font-weight:700;">Trend window</div>'
        f'</div>'

        f'</div></div>'
    )
    st.markdown(_header_html, unsafe_allow_html=True)
    
    # Charts Section
    st.markdown("<div style='margin:16px 0 12px 0;'></div>", unsafe_allow_html=True)
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown(
            """
            <div style="margin-bottom: 12px;">
                <div style="font-size: 1.1rem; font-weight: 800; color: #f8fafc;">
                    Incidents over time
                </div>
                <div style="color: #94a3b8; font-size: 0.9rem;">
                    Area and bar hybrid view highlighting the highest activity bucket.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Professional area chart for incidents over time
        if trends.get('incidents_over_time'):
            import pandas as pd
            import plotly.graph_objects as go
            
            df = pd.DataFrame(trends['incidents_over_time'])
            
            # Find peak for highlighting
            peak_idx = df['count'].idxmax()
            peak_period = df.loc[peak_idx, 'period']
            
            # Create figure with dark theme
            fig = go.Figure()
            
            # Add area chart (gradient fill)
            fig.add_trace(go.Scatter(
                x=df['period'],
                y=df['count'],
                fill='tozeroy',
                fillcolor='rgba(56, 139, 153, 0.4)',
                line=dict(color='rgba(56, 139, 153, 0.8)', width=2),
                mode='lines',
                name='Incidents',
                hovertemplate='<b>%{x}</b><br>Incidents: %{y}<extra></extra>'
            ))
            
            # Add bar overlay for peak
            fig.add_trace(go.Bar(
                x=[peak_period],
                y=[df.loc[peak_idx, 'count']],
                marker=dict(color='rgba(56, 139, 153, 0.6)', line=dict(width=0)),
                name='Peak',
                showlegend=False,
                hovertemplate='<b>Peak: %{x}</b><br>Incidents: %{y}<extra></extra>'
            ))
            
            # Update layout with dark theme
            fig.update_layout(
                plot_bgcolor='rgba(15, 23, 42, 0.5)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='#94a3b8', size=11),
                margin=dict(l=40, r=20, t=20, b=40),
                height=280,
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(148, 163, 184, 0.1)',
                    zeroline=False,
                    showline=True,
                    linecolor='rgba(148, 163, 184, 0.2)',
                    tickfont=dict(size=10, color='#94a3b8')
                ),
                yaxis=dict(
                    title='Incidents',
                    showgrid=True,
                    gridcolor='rgba(148, 163, 184, 0.1)',
                    zeroline=False,
                    showline=True,
                    linecolor='rgba(148, 163, 184, 0.2)',
                    tickfont=dict(size=10, color='#94a3b8'),
                    title_font=dict(size=11, color='#94a3b8')
                ),
                hovermode='x unified',
                hoverlabel=dict(
                    bgcolor='rgba(15, 23, 42, 0.95)',
                    font_size=11,
                    font_color='#f8fafc'
                )
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # Peak detected indicator
            if trends.get('peak_period'):
                st.markdown(
                    f"""
                    <div style="display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px;
                                border-radius: 999px; background: rgba(251, 191, 36, 0.12);
                                border: 1px solid rgba(251, 191, 36, 0.3); margin-top: 10px;">
                        <div style="width: 8px; height: 8px; border-radius: 50%; background: #fcd34d;"></div>
                        <div style="color: #fcd34d; font-size: 0.85rem; font-weight: 700;">
                            Peak detected
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No time-series data available")
    
    with chart_col2:
        st.markdown(
            """
            <div style="margin-bottom: 12px;">
                <div style="font-size: 1.1rem; font-weight: 800; color: #f8fafc;">
                    Affected Components
                </div>
                <div style="color: #94a3b8; font-size: 0.9rem;">
                    Sorted recurrence risk labels for fast component-level triage.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Professional horizontal bar chart for components
        if chart_data.get('labels'):
            import pandas as pd
            import plotly.graph_objects as go
            
            df = pd.DataFrame({
                'Component': chart_data['labels'],
                'Incidents': chart_data['data']
            })
            
            # Sort by incidents descending
            df = df.sort_values('Incidents', ascending=True)
            
            # Assign risk colors based on incident count
            max_incidents = df['Incidents'].max()
            colors = []
            for count in df['Incidents']:
                if count >= max_incidents * 0.7:
                    colors.append('#ef4444')  # High - Red
                elif count >= max_incidents * 0.4:
                    colors.append('#f97316')  # Medium - Orange
                else:
                    colors.append('#fb923c')  # Low - Light Orange
            
            # Create horizontal bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                y=df['Component'],
                x=df['Incidents'],
                orientation='h',
                marker=dict(
                    color=colors,
                    line=dict(width=0)
                ),
                text=df['Incidents'],
                textposition='outside',
                textfont=dict(size=10, color='#f8fafc'),
                hovertemplate='<b>%{y}</b><br>Incidents: %{x}<extra></extra>'
            ))
            
            # Update layout with dark theme
            fig.update_layout(
                plot_bgcolor='rgba(15, 23, 42, 0.5)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='#94a3b8', size=11),
                margin=dict(l=80, r=40, t=20, b=40),
                height=280,
                xaxis=dict(
                    title='Incidents',
                    showgrid=True,
                    gridcolor='rgba(148, 163, 184, 0.1)',
                    zeroline=False,
                    showline=True,
                    linecolor='rgba(148, 163, 184, 0.2)',
                    tickfont=dict(size=10, color='#94a3b8'),
                    title_font=dict(size=11, color='#94a3b8')
                ),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showline=False,
                    tickfont=dict(size=10, color='#94a3b8')
                ),
                showlegend=False,
                hovermode='y unified',
                hoverlabel=dict(
                    bgcolor='rgba(15, 23, 42, 0.95)',
                    font_size=11,
                    font_color='#f8fafc'
                )
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # Risk concentration indicator
            st.markdown(
                """
                <div style="display: flex; gap: 12px; margin-top: 10px;">
                    <div style="display: inline-flex; align-items: center; gap: 6px;">
                        <div style="width: 12px; height: 12px; border-radius: 2px; background: #ef4444;"></div>
                        <div style="color: #94a3b8; font-size: 0.8rem;">High recurrence</div>
                    </div>
                    <div style="display: inline-flex; align-items: center; gap: 6px;">
                        <div style="width: 12px; height: 12px; border-radius: 2px; background: #f97316;"></div>
                        <div style="color: #94a3b8; font-size: 0.8rem;">Medium</div>
                    </div>
                    <div style="display: inline-flex; align-items: center; gap: 6px;">
                        <div style="width: 12px; height: 12px; border-radius: 2px; background: #fb923c;"></div>
                        <div style="color: #94a3b8; font-size: 0.8rem;">Low</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No component data available")
    
    # Component Mix Chart Section
    st.markdown("<div style='margin: 40px 0 20px 0;'></div>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="margin-bottom: 12px;">
            <div style="font-size: 1.1rem; font-weight: 800; color: #f8fafc;">
                Component Mix
            </div>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                Stacked incident mix by time bucket using the same analytics payload.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Component Mix stacked bar chart — real per-period per-component counts
    if component_mix.get('periods') and component_mix.get('components'):
        import plotly.graph_objects as go

        periods = component_mix['periods']
        mix_components = component_mix['components']
        series = component_mix['series']

        # Distinct colours — enough contrast to tell components apart
        colors = [
            '#3b82f6',  # blue
            '#10b981',  # emerald
            '#f59e0b',  # amber
            '#ef4444',  # red
            '#8b5cf6',  # violet
        ]

        fig = go.Figure()
        for idx, comp in enumerate(mix_components):
            fig.add_trace(go.Bar(
                x=periods,
                y=series[comp],
                name=comp,
                marker_color=colors[idx % len(colors)],
                hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>Incidents: %{y}<extra></extra>'
            ))

        fig.update_layout(
            barmode='stack',
            plot_bgcolor='rgba(15, 23, 42, 0.5)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(color='#94a3b8', size=11),
            margin=dict(l=40, r=20, t=20, b=60),
            height=280,
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor='rgba(148, 163, 184, 0.2)',
                tickfont=dict(size=10, color='#94a3b8')
            ),
            yaxis=dict(
                title='Incidents',
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.1)',
                zeroline=False,
                showline=True,
                linecolor='rgba(148, 163, 184, 0.2)',
                tickfont=dict(size=10, color='#94a3b8'),
                title_font=dict(size=11, color='#94a3b8')
            ),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='rgba(15, 23, 42, 0.95)',
                font_size=11,
                font_color='#f8fafc'
            ),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.4,
                xanchor='left',
                x=0,
                font=dict(size=10, color='#94a3b8'),
                bgcolor='rgba(0, 0, 0, 0)'
            )
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("No component mix data available")
    
    # Bottom Section — compact single HTML block
    st.markdown("<div style='margin:16px 0 8px 0;'></div>", unsafe_allow_html=True)

    _corr_pct   = change_correlation.get('correlation_percentage', 0)
    _corr_inc   = change_correlation.get('change_related_incidents', 0)
    _peak       = trends.get('peak_period', 'N/A')
    _peak_count = trends.get('peak_count', 0)

    # Build action items html
    _actions_html = ''
    for idx, action in enumerate(recommended_actions, 1):
        _actions_html += (
            f'<div style="display:flex; align-items:flex-start; gap:10px; '
            f'padding:8px 10px; margin-top:6px; border-radius:8px; '
            f'border:1px solid rgba(56,189,248,0.18); background:rgba(15,23,42,0.45);">'
            f'<span style="min-width:20px; height:20px; border-radius:5px; '
            f'background:linear-gradient(135deg,#2563eb,#14b8a6); '
            f'display:inline-flex; align-items:center; justify-content:center; '
            f'color:#f8fafc; font-size:0.6rem; font-weight:800; flex-shrink:0;">{idx}</span>'
            f'<span style="color:#dbeafe; font-size:0.78rem; line-height:1.45;">{_html.escape(action)}</span>'
            f'</div>'
        )

    _bottom_html = (
        f'<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">'

        # ── left column ──────────────────────────────────────────
        f'<div style="display:flex; flex-direction:column; gap:8px;">'

        f'<div style="border:1px solid rgba(99,179,237,0.2); border-radius:10px; '
        f'background:rgba(15,23,42,0.70); padding:12px 16px;">'
        f'<div style="color:#7dd3fc; font-size:0.6rem; font-weight:800; text-transform:uppercase; '
        f'letter-spacing:0.08em; margin-bottom:6px;">CHANGE CORRELATION</div>'
        f'<div style="color:#7dd3fc; font-size:1.8rem; font-weight:900; line-height:1; margin-bottom:5px;">{_corr_pct}%</div>'
        f'<div style="color:#64748b; font-size:0.72rem; line-height:1.4;">'
        f'{_corr_inc} incidents are change-related, suggesting deployment or configuration correlation.</div>'
        f'</div>'

        f'<div style="border:1px solid rgba(251,191,36,0.2); border-radius:10px; '
        f'background:rgba(15,23,42,0.70); padding:12px 16px;">'
        f'<div style="color:#fcd34d; font-size:0.6rem; font-weight:800; text-transform:uppercase; '
        f'letter-spacing:0.08em; margin-bottom:6px;">PEAK ACTIVITY PERIOD</div>'
        f'<div style="color:#fcd34d; font-size:1.8rem; font-weight:900; line-height:1; margin-bottom:5px;">{_peak}</div>'
        f'<div style="color:#64748b; font-size:0.72rem; line-height:1.4;">'
        f'Peak with {_peak_count} incidents detected in this period.</div>'
        f'</div>'

        f'</div>'

        # ── right column ─────────────────────────────────────────
        f'<div style="border:1px solid rgba(148,163,184,0.18); border-radius:10px; '
        f'background:rgba(15,23,42,0.70); padding:12px 16px;">'
        f'<div style="color:#f1f5f9; font-size:0.75rem; font-weight:800; margin-bottom:3px;">AI Recommended Actions</div>'
        f'<div style="color:#64748b; font-size:0.7rem; margin-bottom:6px;">Suggested next steps for operational review.</div>'
        f'{_actions_html}'
        f'</div>'

        f'</div>'
    )
    st.markdown(_bottom_html, unsafe_allow_html=True)


# Made with Bob