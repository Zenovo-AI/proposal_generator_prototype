import streamlit as st
from langchain_groq import ChatGroq


llm = ChatGroq(groq_api_key=st.secrets.GROQ_API_KEY, model_name = "Llama-3.1-70b-versatile")