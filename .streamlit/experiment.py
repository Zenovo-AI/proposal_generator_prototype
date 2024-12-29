from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain_openai import ChatOpenAI
import streamlit as st
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from sentence_transformers import CrossEncoder
import pdfplumber
import re


# Utility Functions
def logical_chunking_with_context(text):
    """
    Chunk the text by logical sections, adding context from headings.
    """
    chunks = re.split(r'\n(?=[A-Z][^\n]+:|\n[A-Z ]+\n)', text)
    return [f"{chunk.splitlines()[0]}\n{chunk}" for chunk in chunks if chunk.strip()]


def extract_tables_and_text(pdf_path):
    """
    Extract text and tables from a PDF file.
    """
    tables, pages = [], []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                pages.append(page.extract_text())
            if page.extract_tables():
                tables.extend(page.extract_tables())
    return pages, tables


# RAG Pipeline Class
class RAGPipeline:
    def __init__(self):
        self.embeddings_model = OpenAIEmbeddings()
        self.vectorstore = None
        self.llm_chain = self.initialize_llm_chain()
        self.reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def initialize_llm_chain(self):
        """
        Initialize the LLM chain for query expansion.
        """
        llm = ChatOpenAI(
            model="gpt-4",
            openai_api_key=st.secrets["OPENAI"]["OPENAI_API_KEY"],
        )
        prompt = PromptTemplate(
            input_variables=["text"],
            template="Expand the following query by including only the most relevant key terms, synonyms, or related concepts directly related to the core topic. Focus on terms that define the requirements, criteria, or conditions for proposals as specified in the RFQ:\n\n{text}",
        )
        return LLMChain(llm=llm, prompt=prompt, output_key="expanded_query")


    def preprocess_document(self, pdf_path):
        """
        Preprocess the document by extracting pages and tables and chunking them.
        """
        pages, tables = extract_tables_and_text(pdf_path)
        chunks = [chunk for page in pages for chunk in logical_chunking_with_context(page)]
        documents = [Document(page_content=chunk) for chunk in chunks]
        table_docs = [Document(page_content=str(table)) for table in tables]
        documents.extend(table_docs)
        print(f"Documents: {documents}")
        return documents

    def create_vectordb(self, documents):
        """
        Create a FAISS vector store from the given documents.
        """
        self.vectorstore = FAISS.from_documents(documents, self.embeddings_model)

    def expand_query(self, query):
        """
        Expand the query using LLMChain.
        """
        response = self.llm_chain.invoke({"text": query})
        expanded_query = response.get("expanded_query", "")
        if not isinstance(expanded_query, str):
            raise ValueError(f"Expected expanded query to be a string, got: {type(expanded_query)}")
        return expanded_query



    def rerank(self, query, candidates):
        """
        Rerank the retrieved documents using the cross-encoder model.
        """
        input_pairs = [(query, doc.page_content) for doc in candidates]
        scores = self.reranker_model.predict(input_pairs)
        reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in reranked]

    def query_pipeline(self, query, k=10):
        """
        Process the query with retrieval and reranking.
        """
        expanded_query = self.expand_query(query)
        print(f"Expanded Query: {expanded_query}")
        if not isinstance(expanded_query, str):
            raise ValueError("Expanded query must be a string.")
        candidates = self.vectorstore.similarity_search(expanded_query, k=k)
        reranked = self.rerank(query, candidates)
        print(f"Reranked Answers: {reranked}")
        return reranked[0].page_content



# Main Execution
if __name__ == "__main__":
    pipeline = RAGPipeline()
    documents = pipeline.preprocess_document(r"C:\Users\ARTHUR\Downloads\rfq_no._2024-0108.pdf")
    pipeline.create_vectordb(documents)

    query = "What are the payment terms and conditions for the goods/services mentioned in the RFQ from the Vienna International Centre?"
    result = pipeline.query_pipeline(query)
    print(result)
