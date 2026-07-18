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
The application relies on a sequential **Prompt Chaining** strategy across a decoupled architecture. Instead of processing queries in a single bloated execution step, the system chains two distinct LLM operations together:

1. **Memory Caching Layer**: The database array is parsed exactly once at startup via `st.cache_data`.
2. **Stage 1 (Guardrail & Extraction Layer)**: Evaluates the raw user input for safety and explicitly extracts structural tokens (like merchant names or geographical zones). It outputs a structured JSON object containing the routing parameters.
3. **Stage 2 (RAG Synthesis Layer)**: Directly consumes the structured JSON payload emitted by Stage 1, intercepts the extracted tokens to isolate matching rows from the database, and injects only that targeted context window into `gpt-4o-mini` to synthesize the final response.

---

### 🗺️ Use Case Flowcharts

#### Use Case A: Chat with Information (Specific Merchant Queries)
This flowchart shows how the application securely processes a direct question regarding an individual vendor's deals by passing structured extraction tokens across the prompt chain.
""")

# Text-based visual flowchart for Use Case A
st.code("""
[ User enters prompt: "Perks for Amore at Bugis?" ]
                       │
                       ▼
┌─────────────────────────────────────────────┐
│    Stage 1: Guardrail & Extraction LLM      │
│  - Inspects text for prompt injections.     │
│  - Extracts merchant entity to JSON token.  │
└──────────────────────┬──────────────────────┘
                       │
             Is the input safe?
             ├── [NO]  ──> [ Display: Security Warning Error ] ──> (Halt)
             └── [YES] ──> [ Handoff JSON to Application Logic ]
                                      │
                         Does the merchant token exist?
                         ├── [NO]  ──> [ Display: "They are not our merchants." ] ──> (Halt)
                         └── [YES] 
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │  Database Context Filtering       │
                    │  - Isolate specific merchant row. │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │     Stage 2: RAG Synthesis LLM     │
                    │  - Consumes clean JSON & context. │
                    │  - Enforce strict URL presence.   │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                    [ App Outputs Final Answer to UI ]
""", language="text")

st.markdown("""
#### Use Case B: Intelligent Location-Based Search ("Any deals around Orchard?")
This flowchart shows how location-based queries extract geographic tokens in Stage 1 and seamlessly pass them down the prompt chain to filter and group multiple merchant datasets simultaneously in Stage 2.
""")

# Text-based visual flowchart for Use Case B
st.code("""
[ User enters broad prompt: "Any deals around Orchard?" ]
                                │
                                ▼
┌────────────────────────────────────────────────────────────────┐
│             Stage 1: Guardrail & Extraction LLM                │
│  - Inspects text for malicious system overrides.               │
│  - Detects spatial string token ("Orchard") -> Emits JSON.      │
└───────────────────────────────┬────────────────────────────────┘
                                │
                      Is the input safe?
                      ├── [NO] ──> [ Display: Security Warning Error ] ──> (Halt)
                      └── [YES] ──> [ Handoff JSON to Application Logic ]
                                │
                                ▼
┌────────────────────────────────────────────────────────────────┐
│               Database Context Filtering Engine                │
│  - Reads geographic constraint parameters from Stage 1 JSON.  │
│  - Isolates and bundles all active vendor rows in that zone.   │
└───────────────────────────────┬────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────┐
│                     Stage 2: Synthesis LLM                     │
│  - Consolidates clustered mall promotions and cashbacks.       │
│  - Enforces extraction of location-specific voucher URLs.      │
└───────────────────────────────┬────────────────────────────────┘
                                │
                                ▼
               [ App Outputs Filtered Search Feed to UI ]
""", language="text")

st.success("Documentation Modules Compiled successfully. Navigation links are now active on the system sidebar.")
