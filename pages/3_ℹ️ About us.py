import streamlit as st
from helper_functions.utility import check_password  

# Enforce secure access control
if not check_password():  
    st.stop()

st.set_page_config(layout="centered", page_title="About Us - Merchant Chatbot")

st.title("ℹ️ About Us")
st.subheader("Project Overview & Documentation Scope")

st.markdown("""
### 🎯 Project Objectives
The primary goal of this application is to deliver a Secure Retrieval-Augmented Generation (RAG) search and conversational assistant in Streamlit. It allows users to fluidly query our merchant deals while preventing security risks common to public AI applications.

### 🔍 Data Sources
The system references our structured merchant test database containing merchant details, branch locations, URLs, and membership deals.

### ✨ Key Features
1. **Prompt Chaining**: Executes sequential LLM operations where the structured JSON extraction from Stage 1 directly drives the RAG filtering in Stage 2.
2. **Security Firewall**: Stops prompt injections right at the gateway.
3. **Data Caching**: Uses st.cache_data to load files into RAM once for instant answers.
""")
