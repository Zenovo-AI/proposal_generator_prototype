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

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class ChatBot:
    def __init__(self, rag_pipeline):
        self.rag_pipeline = rag_pipeline
        self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.model = AutoModelForCausalLM.from_pretrained("gpt2")

    def get_response(self, question):
        # Query the RAG pipeline
        relevant_docs = self.rag_pipeline.query(question)

        if not relevant_docs:
            return "Please Call The Risk Dept"

        # Prepare context for the language model
        context = "\n".join([f"Source: {source}\nContent: {content}" for content, source, _ in relevant_docs])
        prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"

        # Generate response using the language model
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt")
        attention_mask = torch.ones(input_ids.shape, dtype=torch.long)
        
        output = self.model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_length=200,
            num_return_sequences=1,
            no_repeat_ngram_size=2,
            top_k=50,
            top_p=0.95,
            temperature=0.7
        )

        response = self.tokenizer.decode(output[0], skip_special_tokens=True)
        
        # Extract the generated answer from the response
        answer = response.split("Answer:")[-1].strip()
        
        return answer
