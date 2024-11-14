from rag_pipeline import RAGPipeline
import logging
import os

logging.basicConfig(level=logging.INFO)

# Load API key from environment variable
api_key = os.environ.get("OPENAI_API_KEY")

# Initialize documents (replace with your actual documents)
documents = ["Doc 1", "Doc 2", "Doc 3", "Doc 4", "Doc 5"]

# Initialize the RAG pipeline
rag_pipeline = RAGPipeline(documents=documents, api_key=api_key)

class ChatBot:
    """
    A chatbot that uses a retrieval-augmented generation (RAG) pipeline to generate answers
    based on the documents stored in a FAISS index.
    """
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag_pipeline = rag_pipeline

    def process_query(self, query: str) -> dict:
        """
        Process the user's query by passing it to the RAG pipeline for answer generation.
        """
        self.rag_pipeline.set_query(query)
        result = self.rag_pipeline.run_pipeline(query)
        return result

    def run(self):
        """
        A simple loop to interact with the chatbot.
        """
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                print("Goodbye!")
                break
            
            result = self.process_query(user_input)
            print(f"Bot: {result['answer']}\nSource: {result['source']}")

if __name__ == "__main__":
    chatbot = ChatBot(rag_pipeline)
    chatbot.run()