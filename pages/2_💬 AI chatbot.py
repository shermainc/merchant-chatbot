import streamlit as st
st.write("App started")

import pandas as pd
st.write("pandas ok")

from helper_functions.llm import get_completion
st.write("llm ok")

df = pd.read_csv("pages/merchants.csv")
st.write("CSV loaded ok")
st.write(df.head())
