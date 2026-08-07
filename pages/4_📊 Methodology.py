import streamlit as st
from helper_functions.utility import check_password  

# Enforce secure access control
if not check_password():  
    st.stop()

st.set_page_config(layout="centered", page_title="Methodology - Merchant Chatbot")

st.title("📊 Application Methodology")
st.subheader("Implementation Details & Data Architectures")

st.markdown("""
### 🛠️ Architecture and Data Flows
The application relies on a sequential **Prompt Chaining** strategy across a decoupled architecture. Instead of processing queries in a single bloated execution step, the system chains distinct Large Language Model (LLM) operations together:

1. **Memory Caching Layer**: The local database array (`test.json`) is parsed exactly once at startup via `@st.cache_data`. This significantly optimizes latency by avoiding redundant disk operations during subsequent conversational turns.
2. **Stage 1 (Guardrail & Extraction Layer)**: Evaluates raw user inputs for malicious activities or prompt injections. Simultaneously, it extracts key target tokens (such as specified merchant names) and transforms unstructured text into an internal structured JSON data block.
3. **Stage 2 (Intent & Category Fallback Mapper)**: Evaluates the remaining ambiguous or slang expressions against known schemas to resolve missing context (e.g., mapping colloquial terms like *"bbt"* to *"Food & Beverage"*).
4. **Stage 3 (RAG Synthesis Layer)**: Consumes the validated tokens emitted by the previous stages, slices out matching records from the memory cache to construct a hyper-targeted data context, and builds a strict, grounded final answer along with rolling history tracking.

---

### 🗺️ Use Case Flowcharts
Select a specific use case below to view its complete end-to-end data processing workflow.
""")

# Implement tab layouts to cleanly separate the two required flowcharts
tab1, tab2 = st.tabs(["💬 Use Case A: Chat with Information", "🔍 Use Case B: Intelligent Search"])

with tab1:
    st.markdown("""
    **Description**: Covers sequential multi-turn conversational inquiries regarding known specific items, broad database lists, and continuing questions relying heavily on rolling memory.
    """)
    
    # Corrected function to st.mermaid_chart
    st.mermaid_chart("""
    graph TD
        A([User Submits Prompt]) --> B[Memory Cache Check: load_and_process_database]
        B --> C[Stage 1: pipeline_verify_merchant]
        C --> D{Is Input Safe?}
        
        D -- No --> E[Raise Guardrail Error Bubble]
        E --> F([Display Security Alert & Terminate])
        
        D -- Yes --> G[Extract Merchant Token & Check History Context]
        G --> H[Stage 2: pipeline_execute_rag with active history cache]
        H --> I[Append Interaction to st.session_state.messages]
        I --> J([Render Chat Bubble in Viewport Layout])

        style E fill:#ffcccc,stroke:#333,stroke-width:2px
        style J fill:#d4edda,stroke:#333,stroke-width:2px
    """)

with tab2:
    st.markdown("""
    **Description**: Triggered when users use implicit filtering parameters, regional lookups (e.g., *"Orchard"*), or colloquial semantic shorthand needing category fallback transformations.
    """)
    
    # Corrected function to st.mermaid_chart
    st.mermaid_chart("""
    graph TD
        A([User Submits Broad Query]) --> B[Stage 1: Sanitize Inputs & Extract Sub-Entities]
        B --> C{Direct Merchant Match?}
        
        C -- No --> D[Helper: map_user_query_to_category via LLM Semantic Mapping]
        C -- Yes --> G[Route Context Filter directly to Target Merchant Records]
        
        D --> E{Category Found?}
        E -- Yes --> F[Route Context Filter directly to Category Sub-Array]
        E -- No --> H[Activate Broad Database Scan Fallback]
        
        G --> I[Stage 3: pipeline_execute_rag]
        F --> I
        H --> I
        
        I --> J[Evaluate Compliance Rules: Force URL/Website Fields]
        J --> K([Render Grounded Filtered Results to User])

        style D fill:#fff3cd,stroke:#333,stroke-width:2px
        style K fill:#d4edda,stroke:#333,stroke-width:2px
    """)

st.markdown("""
---
### 🔒 Key Engineering Directives Applied
* **Prompt Injection Resilience**: Isolates system instructions from user inputs by using data-cleansing parameters prior to LLM submission.
* **Hallucination Suppression**: Restricts the generative capabilities of the model by forcing a complete block layout stop if queried components do not exist inside the current data array layer.
* **Deterministic Layout Control**: Replaces fragile non-deterministic string parsing with robust structural JSON payload validations to route program state switches.
""")
