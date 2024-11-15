import os
from rag_pipeline import RAGPipeline
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

class ChatBot:
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag_pipeline = rag_pipeline

    def get_response(self, query: str, api_key: str) -> dict:
        include_metadata = True  # or False, depending on your needs
        result = self.rag_pipeline.run_pipeline(query, api_key=api_key, include_metadata=include_metadata)
        return result