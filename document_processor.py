import streamlit as st
from io import BytesIO
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document
import pdfplumber
import trafilatura
from utils import clean_text
import logging

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

    def process_pdf(self, pdf_file):
        """Extract text from a PDF file using pdfplumber, maintaining paragraph structure."""
        with pdfplumber.open(pdf_file) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                paragraphs = page_text.split('\n\n')
                text += '\n\n'.join(paragraphs) + '\n\n'
        return text.strip()

    def extract_tables_from_pdf(self, pdf_file):
        """Extract tables from a PDF file."""
        with pdfplumber.open(pdf_file) as pdf:
            pages = pdf.pages
            tables = []
            for page in pages:
                for table in page.extract_tables():
                    tables.append(table)
        return tables

    def process_txt(self, txt_file):
        """Read and return the content of a TXT file."""
        with BytesIO(txt_file) as file:
            text = file.read().decode("utf-8")
            text = clean_text(text)
            return text

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
            paragraphs = input_data.split("\n\n")
            for paragraph in paragraphs:
                documents.append(Document(page_content=paragraph.strip()))
        elif isinstance(input_data, list):  # Handle file-like objects
            for uploaded_file in input_data:
                file_bytes = uploaded_file.getvalue()  # Get the file content as bytes
                if uploaded_file.name.endswith(".pdf"):
                    text = self.process_pdf(BytesIO(file_bytes))
                    paragraphs = text.split("\n\n")
                    for paragraph in paragraphs:
                        documents.append(Document(page_content=paragraph.strip()))
                elif uploaded_file.name.endswith(".txt"):
                    text = self.process_txt(file_bytes)
                    paragraphs = text.split("\n\n")
                    for paragraph in paragraphs:
                        documents.append(Document(page_content=paragraph.strip()))

        # Create FAISS vector store
        vectordb = self.create_vectordb(documents)
        return vectordb, documents

