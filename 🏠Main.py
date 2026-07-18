import streamlit as st

from helper_functions.utility import check_password  

# 1. Execute the gatekeeper first thing!
if not check_password():  
    st.stop()  # Keeps everything hidden until they type the password here

# 2. Main homepage content loads below ONLY if check_password() returns True
st.set_page_config(layout="centered", page_title="Merchant Portal Home")
st.title("🏠 Welcome to the Merchant Deals Portal")
st.write("Use the sidebar navigation menu on the left to explore the Chatbot, About Us, or Methodology pages.")


# 💡 NAVIGATION INFO LINE (Added inside the sidebar for clear UX)
st.sidebar.info("📌 Use the above sidebar to switch between the pages at any time.")

st.write("---") # Visual divider line

    # Feature 1: RAG Chat
    # Uses a material icon (chat) right inside the subheader
st.subheader(":material/chat: Conversational AI using RAG", divider="gray")
st.write("Chat naturally with **GPT-4o-mini**. The answer is based on our Merchant testing database")

    # Feature 2: Framework
st.subheader(":material/layers: UI Framework", divider="gray")
st.write("Built on top of **Streamlit** for real-time reactivity and lightweight processing configurations")

    # Feature 3: Security
st.subheader(":material/lock: Secure Access Gateway", divider="gray")
st.write("Completely password protected ")

st.write("---")


# The redirect action trigger
if st.button("Launch Chatbot 🚀", type="primary", use_container_width=True):
        # Automatically loads the target script execution path
        st.switch_page("pages/2_💬 AI chatbot.py")