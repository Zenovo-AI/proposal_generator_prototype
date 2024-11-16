from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os


load_dotenv()

llm = ChatGroq(groq_api_key=os.getenv("GROQ_API_KEY"), model_name = "llama-3.2-90b-text-preview")