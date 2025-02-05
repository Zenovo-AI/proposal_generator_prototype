from PyPDF2 import PdfReader
import streamlit as st
from langchain.docstore.document import Document
import trafilatura
from utils import clean_text
import logging
import openai
import pdfplumber

openai.api_key = st.secrets["OPENAI_API_KEY"]

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
            
            
    # Helper function to read text from a TXT file
    def extract_txt_content(self, file_path):
        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Error reading TXT file: {e}")
        

    # def extract_text_from_pdf(self, file):
    #     reader = PdfReader(file)
    #     text = ""
    #     for page in reader.pages:
    #         text += page.extract_text()
    #     return text
    
    

    def extract_text_and_tables_from_pdf(self, file):
        text = ""
        table_texts = []

        with pdfplumber.open(file) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text
                page_text = page.extract_text()
                if page_text:
                    text += f"\n\n[Page {page_num}]\n{page_text}"
                
                # Extract tables
                page_tables = page.extract_tables()
                for table_idx, table in enumerate(page_tables):
                    table_str = f"\n\n[Page {page_num} - Table {table_idx + 1}]\n"
                    for row in table:
                        cleaned_row = [cell if cell is not None else "" for cell in row]  # Replace None with ""
                        table_str += " | ".join(cleaned_row) + "\n"
                    table_texts.append(table_str)

        # Combine extracted text and tables
        full_text = text + "\n\n".join(table_texts)
        return full_text

    
    def preprocess_document(self, file):
        """
        Preprocess the document by extracting all text.
        """
        pdf_text = self.extract_text_and_tables_from_pdf(file)
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