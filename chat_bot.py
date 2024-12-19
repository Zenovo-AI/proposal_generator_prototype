from rag_pipeline import RAGPipeline


class ChatBot:
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag_pipeline = rag_pipeline

    def get_response(self, query: str) -> dict:
        result = self.rag_pipeline.run_pipeline(query)
        return result