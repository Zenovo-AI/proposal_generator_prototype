import streamlit as st
from langchain_groq import ChatGroq

# Initialize and retrieve api_key
st.session_state.api_key = st.session_state.api_key or st.sidebar.text_input("Enter your Groq API KEY")
if not st.session_state.api_key:
    st.error("Please enter a valid API key")
    st.stop()

llm = ChatGroq(groq_api_key=st.session_state.api_key, model_name="Llama-3.1-70b-versatile")
