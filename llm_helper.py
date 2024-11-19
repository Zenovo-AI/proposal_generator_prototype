from langchain_groq import ChatGroq
from main import api_key

llm = ChatGroq(groq_api_key=api_key, model_name = "Llama-3.1-70b-versatile")