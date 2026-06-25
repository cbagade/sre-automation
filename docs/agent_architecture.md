# Agent Architecture & Data Flow

All diagrams use [Mermaid](https://mermaid.js.org/) syntax.

---

## 1 · Project-Wide Overview

```mermaid
graph TD
    USER([User / Browser])

    subgraph DASH["Dashboard  (Streamlit)"]
        APP[app.py]
        OPS_PAGE[Operational Signals Page]
        INC_PAGE[Incident Intelligence Page]
    end

    subgraph SRE["SRE Analysis Agent"]
        SRE_AGENT[sre_analysis_agent.py]
    end

    subgraph BREAKFAST["Breakfast Domain Agents"]
        BKF_ADV[Breakfast Advisor Agent\norchestrator]
        BKF_PLN[Healthy Breakfast Planner Agent]
        BKF_PRC[Breakfast Price Checker Agent]
        NUT_AGT[Nutrition Agent]
    end

    subgraph INTEL["Incident Intelligence Agent"]
        INC_AGENT[incident_intelligence_agent.py]
    end

    subgraph OPS_AGT["Operational Signals Agent"]
        OPS_AGENT[operational_signals_agent.py]
    end

    USER --> APP
    APP --> SRE_AGENT
    APP --> OPS_PAGE
    APP --> INC_PAGE

    OPS_PAGE --> OPS_AGENT
    INC_PAGE --> INC_AGENT

    BKF_ADV --> BKF_PLN
    BKF_ADV --> NUT_AGT
    BKF_ADV --> BKF_PRC
```

---

## 2 · SRE Analysis Agent

```mermaid
flowchart TD
    USER_Q([User Query])

    subgraph SRE_AGENT["SRE Analysis Agent  (sre_analysis_agent.py)"]
        INTENT[Intent Detection\nOpenAI gpt-4o]
        ROUTER{Route by intent}
        SYNTH[Synthesize Response\nOpenAI gpt-4o]
    end

    subgraph TOOLS["Tools"]
        RAG[rag_incident_search\nrag_incident_tool.py]
        BKBS[broadcom_kb_search\nbroadcom_kb_search_tool.py]
        KBFETCH[KB Content Fetcher\nkb_content_fetcher.py]
    end

    subgraph STORES["Data Stores"]
        CHROMA_RCA[(ChromaDB\nrca_knowledge_base)]
        DISPLAY_JSON[(rca_data_display.json)]
        EXA_WEB([Exa MCP\nWeb Search])
        BROADCOM_WEB([knowledge.broadcom.com])
    end

    TRACE[Langfuse Tracing\nconditional_observe]
    OPENAI_EMB([OpenAI\ntext-embedding-3-small])
    OPENAI_SCORE([OpenAI gpt-4o-mini\nRelevance Scoring])

    USER_Q --> INTENT
    INTENT --> ROUTER
    ROUTER -->|incident search| RAG
    ROUTER -->|kb search| BKBS

    RAG --> OPENAI_EMB
    RAG --> CHROMA_RCA
    RAG --> DISPLAY_JSON
    RAG --> SYNTH

    BKBS --> EXA_WEB
    BKBS --> OPENAI_SCORE
    BKBS --> KBFETCH
    KBFETCH --> BROADCOM_WEB
    BKBS --> SYNTH

    SYNTH --> TRACE
    SYNTH --> RESULT([JSON Response\nintent · incidents · kb_results · answer])
```

---

## 3 · Incident Intelligence Agent

```mermaid
flowchart TD
    DASH_PAGE([Incident Intelligence\nDashboard Page])

    subgraph INC_AGENT["IncidentIntelligenceAgent  (incident_intelligence_agent.py)"]
        LOAD[Load Display Data\nrca_data_display.json]
        GET_INC[get_all_incidents\ntime_period · change_related_only]
        AN_TRENDS[analyze_trends]
        AN_COMP[analyze_components]
        AN_CORR[analyze_change_correlation]
        COMP_MIX[get_component_mix_over_time]
        CHART_DATA[get_affected_components_chart_data]
        EXEC_SUM[generate_executive_summary\nOpenAI gpt-4o]
        REC_ACT[get_recommended_actions]
    end

    subgraph STORES["Data Stores"]
        CHROMA_RCA[(ChromaDB\nrca_knowledge_base)]
        DISPLAY_JSON[(rca_data_display.json)]
    end

    OPENAI([OpenAI gpt-4o])

    DASH_PAGE -->|time_period\ngroup_by\nchange_related_only| INC_AGENT

    LOAD --> DISPLAY_JSON
    GET_INC --> CHROMA_RCA
    GET_INC --> LOAD

    INC_AGENT --> GET_INC
    GET_INC --> AN_TRENDS
    GET_INC --> AN_COMP
    GET_INC --> AN_CORR
    GET_INC --> COMP_MIX
    AN_COMP --> CHART_DATA
    AN_COMP --> REC_ACT

    EXEC_SUM --> OPENAI

    AN_TRENDS --> DASH_PAGE
    AN_COMP --> DASH_PAGE
    AN_CORR --> DASH_PAGE
    COMP_MIX --> DASH_PAGE
    CHART_DATA --> DASH_PAGE
    EXEC_SUM --> DASH_PAGE
    REC_ACT --> DASH_PAGE
```

---

## 4 · Operational Signals Agent

```mermaid
flowchart TD
    DASH_PAGE([Operational Signals\nDashboard Page])

    subgraph OPS_AGENT["OperationalSignalsAgent  (operational_signals_agent.py)"]
        FETCH_SIG[Fetch Signals\nregion · date · timeslot]
        CACHE_CHK{Cache hit?}
        CACHE_WR[Write Cache]
    end

    subgraph UTILS["Utils"]
        DATE_U[date_utils.py\nget_current_timeslot\nformat_date_for_git]
        PARSER[git_issue_parser.py\nparser_registry]
        LINKER[git_issue_linker.py]
        ENHANCER[ai_text_enhancer.py]
        CACHE[cache_manager.py]
    end

    subgraph TOOLS["Tools"]
        GIT_FETCH[GitDataFetcher\ngit_data_fetcher.py]
    end

    GIT_REPO([GitHub / GitLab\nRaw JSON Files\nalerts · clusters])

    DASH_PAGE -->|region · date · refresh| FETCH_SIG
    FETCH_SIG --> CACHE_CHK
    CACHE_CHK -->|hit| CACHE
    CACHE_CHK -->|miss| GIT_FETCH
    GIT_FETCH --> GIT_REPO
    GIT_REPO -->|active_critical_immediate_alerts.json\nclusters_needing_attention.json| GIT_FETCH
    GIT_FETCH --> CACHE_WR
    CACHE_WR --> CACHE

    FETCH_SIG --> DATE_U
    FETCH_SIG --> PARSER
    FETCH_SIG --> LINKER
    FETCH_SIG --> ENHANCER

    FETCH_SIG --> DASH_PAGE
```

---

## 5 · Breakfast Advisor Agent  (multi-agent orchestrator)

```mermaid
flowchart TD
    USER([User Query])

    subgraph GUARDRAILS["Guardrails  (breakfast_advisor_agent.py)"]
        MOD[Content Safety\nOpenAI Moderation API]
        FOOD_VAL[Food-topic Validation\nkeyword + jailbreak check]
        OUT_VAL[Output Validation\noff-topic check]
    end

    subgraph ADV["Breakfast Advisor Agent  (orchestrator)"]
        ORCH[LLM Orchestration\nOpenAI gpt-4-turbo\ntool_choice loop]
    end

    subgraph SUB_AGENTS["Sub-Agents  (called as tools)"]
        PLN[Healthy Breakfast Planner Agent\nhealthy_breakfast_planner_agent.py\nOpenAI gpt-4-turbo · no tools]
        NUT[Nutrition Agent\nnutrition_agent.py]
        PRC[Breakfast Price Checker Agent\nbreakfast_price_checker_agent.py]
    end

    subgraph NUT_TOOLS["Nutrition Tools"]
        CAL_TOOL[get_food_calories\nnutrition_tools.py]
        WEB_NUT[websearch_tool\nExa MCP]
    end

    subgraph PRC_TOOLS["Price Tools"]
        WEB_PRC[websearch_tool\nExa MCP]
    end

    subgraph STORES["Data Stores"]
        CHROMA_NUT[(ChromaDB\nnutrition_db)]
        EXA([Exa MCP\nWeb Search])
    end

    TRACE[Langfuse Tracing\nconditional_observe]

    USER --> MOD
    MOD -->|safe| FOOD_VAL
    FOOD_VAL -->|food-related| ORCH

    ORCH -->|breakfast_planner_tool| PLN
    PLN --> ORCH

    ORCH -->|calorie_calculator_tool| NUT
    NUT --> CAL_TOOL
    NUT --> WEB_NUT
    CAL_TOOL --> CHROMA_NUT
    WEB_NUT --> EXA
    NUT --> ORCH

    ORCH -->|handoff| PRC
    PRC --> WEB_PRC
    WEB_PRC --> EXA
    PRC --> ORCH

    ORCH --> OUT_VAL
    OUT_VAL --> TRACE
    OUT_VAL --> RESULT([Meal Plan\nnames · ingredients\ncalories · prices])
```

---

## 6 · RAG Ingestion & Retrieval Pipeline

```mermaid
flowchart TD
    subgraph INGEST["Ingestion  (ingestion/ingest_inc_data.py)"]
        RAW_JSON[(rca_data_ingest.json\nid · document · metadata)]
        EMB[OpenAI Embeddings\ntext-embedding-3-small]
        CHROMA_WRITE[(ChromaDB\nrca_knowledge_base)]
    end

    subgraph RETRIEVAL["Retrieval  (retrieval/chatbot.py + extract_ingested_inc.py)"]
        CLI([CLI User Query])
        KW[Keyword Extraction]
        SEM[Semantic Search\nChromaDB query]
        DISPLAY[(rca_data_display.json\nenrichment)]
        OUTPUT([Formatted Incident Results])
    end

    subgraph RAG_TOOL["RAG Incident Tool  (tools/rag_incident_tool.py)"]
        RT_EMB[OpenAI Embeddings\ntext-embedding-3-small]
        RT_QUERY[ChromaDB Query\n+ keyword filter]
        RT_ENRICH[Enrich from display JSON]
        RT_OUT([JSON · incidents · scores])
    end

    RAW_JSON --> EMB --> CHROMA_WRITE

    CLI --> KW --> SEM
    SEM --> CHROMA_WRITE
    SEM --> DISPLAY --> OUTPUT

    RT_EMB --> CHROMA_WRITE
    RT_QUERY --> CHROMA_WRITE
    RT_QUERY --> RT_ENRICH
    RT_ENRICH --> DISPLAY
    RT_ENRICH --> RT_OUT
```

---

## 7 · Key External Integrations Summary

```mermaid
graph LR
    subgraph AGENTS["Agents & Tools"]
        A1[SRE Analysis Agent]
        A2[Breakfast Advisor Agent]
        A3[Nutrition Agent]
        A4[Breakfast Price Checker]
        A5[Incident Intelligence Agent]
        A6[Operational Signals Agent]
        T1[rag_incident_tool]
        T2[broadcom_kb_search_tool]
        T3[websearch_tool]
        T4[nutrition_tools]
        T5[git_data_fetcher]
    end

    subgraph EXTERNAL["External Services"]
        OAI_LLM([OpenAI LLM\ngpt-4o · gpt-4o-mini\ngpt-4-turbo])
        OAI_EMB([OpenAI Embeddings\ntext-embedding-3-small])
        OAI_MOD([OpenAI Moderation API])
        CHROMA_RCA[(ChromaDB\nrca_knowledge_base)]
        CHROMA_NUT[(ChromaDB\nnutrition_db)]
        EXA_MCP([Exa MCP\nWeb Search])
        GIT([GitHub / GitLab\nRaw API])
        LANGFUSE([Langfuse\nTracing])
    end

    A1 --> OAI_LLM
    A2 --> OAI_LLM
    A2 --> OAI_MOD
    A3 --> OAI_LLM
    A4 --> OAI_LLM
    A5 --> OAI_LLM

    T1 --> OAI_EMB
    T1 --> CHROMA_RCA
    T4 --> CHROMA_NUT
    T2 --> EXA_MCP
    T3 --> EXA_MCP
    T5 --> GIT
    A6 --> GIT

    A1 --> LANGFUSE
    A2 --> LANGFUSE
    A3 --> LANGFUSE
```
