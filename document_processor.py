import streamlit as st
from io import BytesIO
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
import fitz  # PyMuPDF for text extraction
import trafilatura
from utils import clean_text
import logging
import openai

openai.api_key = st.secrets["OPENAI"]["OPENAI_API_KEY"]

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

    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from a PDF using PyMuPDF.
        """
        text_content = []
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                text_content.append(page.get_text())
        return "\n".join(text_content)

    def preprocess_document(self, pdf_path):
        """
        Preprocess the document by extracting all text.
        """
        pdf_text = self.extract_text_from_pdf(pdf_path)
        # Return the entire content as a single Document object
        documents = [Document(page_content=pdf_text)]
        return documents

    def process_webpage(self, url):
        """
        Download and extract text content from a webpage using trafilatura.
        """
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            web_page = trafilatura.extract(downloaded)
            return clean_text(web_page) if web_page else None
        else:
            logging.error(f"Failed to fetch webpage: {url}")
            return None


    def create_vectordb(self, documents) -> FAISS:
        """
        Create FAISS vector database from a list of documents.
        """
        try:
            embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vectordb = FAISS.from_documents(documents, embedding=embeddings_model)
            return vectordb
        except Exception as e:
            logging.error(f"Error creating vector database: {e}")
            return None

    # def process_and_extract(self, input_data):
    #     """
    #     Process input data (plain text, PDFs, or URLs) and extract text.
    #     Args:
    #         input_data: Raw text, file-like object, or URL.
    #     Returns:
    #         Tuple: FAISS vector store and documents list.
    #     """
    #     documents = []

    #     if isinstance(input_data, str):
    #         # If input is a URL, process as a webpage
    #         if input_data.startswith("http"):
    #             webpage_content = self.process_webpage(input_data)
    #             if webpage_content:
    #                 documents = [Document(page_content=webpage_content.strip())]
    #         else:
    #             # Otherwise, treat as plain text
    #             documents = [Document(page_content=input_data.strip())]
    #     elif isinstance(input_data, BytesIO):
    #         # Handle file-like object (PDF)
    #         documents.extend(self.preprocess_document(input_data))
    #         print(f"Documents: {documents}")

    #     # Create FAISS vector store
    #     vectordb = self.create_vectordb(documents)
    #     print(vectordb)
    #     return vectordb, documents
    
    
    def process_and_extract(self, input_data):
        """
        Process input data (plain text or file-like object) and return as a list of documents.
        Args:
            input_data (Union[str, List[BytesIO]]): Raw text or a list of file-like objects.
        Returns:
            Tuple: FAISS vector store and documents list.
        """
        documents = []

        # Handle plain text input
        if isinstance(input_data, str):
            # If input is plain text, directly add it as a document
            documents = [Document(page_content=input_data.strip())]
            print(f"Plain Text: {documents}")

        elif isinstance(input_data, list):  # Handle file-like objects
            for uploaded_file in input_data:
                if hasattr(uploaded_file, 'getvalue'):  # If it's a file-like object
                    file_bytes = uploaded_file.getvalue()  # Get the file content as bytes
                    if uploaded_file.name.endswith(".pdf"):
                        # If it's a PDF file, preprocess the document
                        documents.extend(self.preprocess_document(BytesIO(file_bytes)))
                        print(f"PDF FILE: {documents}")
                    elif uploaded_file.name.endswith(".txt"):
                        # If it's a .txt file, directly use the content without chunking
                        text = uploaded_file.getvalue().decode("utf-8")
                        documents.append(Document(page_content=text.strip()))  # Add as a single document
                        print(f"UPLOADED: {documents}")
                elif isinstance(uploaded_file, str):  # If it's a string (plain text)
                    # If it's plain text, add directly as a document
                    documents.append(Document(page_content=uploaded_file.strip()))
                    # print(f"Plain Text: {documents}")

        # Create FAISS vector store
        vectordb = self.create_vectordb(documents)
        print(f"Vector Database: {vectordb}")
        return vectordb, documents

