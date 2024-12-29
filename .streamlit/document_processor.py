import streamlit as st
from io import BytesIO
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document
import pdfplumber
from langchain.docstore.document import Document
import trafilatura
from utils import clean_text
import logging
import re

logging.basicConfig(level=logging.INFO)

class DocumentProcessor:
    SECTION_KEYWORDS = {
        "Request for Proposal (RFP) Document",
        "Terms of Reference (ToR)",
        "Technical Evaluation Criteria",
        "Company and Team Profiles",
        "Environmental and Social Standards",
        "Project History and Relevant Experience",
        "Budget and Financial Documents",
        "Additional Requirements and Compliance Documents"
    }

    def __init__(self):
        if "section_embeddings" not in st.session_state:
            st.session_state.section_embeddings = {}  # Store embeddings for each section
            
    def logical_chunking_with_context(self, text):
        """
        Chunk the text by logical sections, adding context from headings.
        """
        chunks = re.split(r'\n(?=[A-Z][^\n]+:|\n[A-Z ]+\n)', text)
        return [f"{chunk.splitlines()[0]}\n{chunk}" for chunk in chunks if chunk.strip()]
            
            
    def extract_tables_and_text(self, pdf_path):
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


    def preprocess_document(self, pdf_path):
        """
        Preprocess the document by extracting pages and tables and chunking them.
        """
        pages, tables = self.extract_tables_and_text(pdf_path)
        chunks = [chunk for page in pages for chunk in self.logical_chunking_with_context(page)]
        documents = [Document(page_content=chunk) for chunk in chunks]
        table_docs = [Document(page_content=str(table)) for table in tables]
        documents.extend(table_docs)
        print(f"Documents: {documents}")
        return documents

    def process_webpage(self, url):
        """Download and extract text content from a webpage."""
        downloaded = trafilatura.fetch_url(url)
        web_page = trafilatura.extract(downloaded)
        web_page = clean_text(web_page)
        return web_page

    def create_vectordb(self, documents) -> FAISS:
        """Create FAISS vector database from a list of documents."""
        try:
            embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vectordb = FAISS.from_documents(documents, embedding=embeddings_model)
            return vectordb
        except Exception as e:
            logging.error(f"Error creating vector database: {e}")
            return None

    def process_and_chunk_text(self, input_data):
        """
        Process input data (plain text or file-like object) and chunk it into smaller pieces.
        Args:
            input_data (Union[str, List[BytesIO]]): Raw text or a list of file-like objects.
        Returns:
            Tuple: FAISS vector store and documents list.
        """
        documents = []

        # Handle plain text input
        if isinstance(input_data, str):
            # If input is plain text, preprocess the document (convert text to chunks)
            chunks = self.logical_chunking_with_context(input_data)
            documents = [Document(page_content=chunk.strip()) for chunk in chunks]

        elif isinstance(input_data, list):  # Handle file-like objects
            for uploaded_file in input_data:
                if hasattr(uploaded_file, 'getvalue'):  # If it's a file-like object
                    file_bytes = uploaded_file.getvalue()  # Get the file content as bytes
                    if uploaded_file.name.endswith(".pdf"):
                        # If it's a PDF file, preprocess the document
                        documents.extend(self.preprocess_document(BytesIO(file_bytes)))
                    elif uploaded_file.name.endswith(".txt"):
                        # If it's a .txt file, preprocess the document
                        text = uploaded_file.getvalue().decode("utf-8")
                        chunks = self.logical_chunking_with_context(text)
                        documents.extend([Document(page_content=chunk.strip()) for chunk in chunks])
                elif isinstance(uploaded_file, str):  # If it's a string (plain text)
                    # If it's plain text, chunk it using the chunking function
                    chunks = self.logical_chunking_with_context(uploaded_file)
                    documents.extend([Document(page_content=chunk.strip()) for chunk in chunks])

        # Create FAISS vector store
        vectordb = self.create_vectordb(documents)
        return vectordb, documents


    


