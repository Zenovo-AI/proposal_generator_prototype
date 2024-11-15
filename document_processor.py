import os
import re
import pdfplumber
import trafilatura
import numpy as np
from utils import clean_text
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

class DocumentProcessor:
    SECTION_KEYWORDS = {
        "Technical Requirements": ["technical", "requirements"],
        "Project Experience": ["experience", "project"],
        "Team Profiles": ["team", "profile"],
        "Evaluation Criteria": ["evaluation", "criteria"]
    }

    def __init__(self):
        pass

    def save_uploaded_file(self, uploaded_file):
        """Save uploaded files to the 'uploaded_files' directory."""
        if not os.path.exists('uploaded_files'):
            os.makedirs('uploaded_files')
        file_path = os.path.join('uploaded_files', uploaded_file.name)
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        return file_path

    def process_pdf(self, pdf_file):
        """Extract text from a PDF file using pdfplumber."""
        with pdfplumber.open(pdf_file) as pdf:
            text = "\n\n".join(page.extract_text() for page in pdf.pages)
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
        with open(txt_file, 'r', encoding='utf-8') as file:
            return file.read()

    def process_webpage(self, url):
        """Download and extract text content from a webpage."""
        downloaded = trafilatura.fetch_url(url)
        return trafilatura.extract(downloaded)


    def _split_sentences(self, text):
        """Split text into sentences."""
        cleaned_text = clean_text(text)
        sentences = re.split(r'(?<=[.?!])\s+', cleaned_text)
        return sentences

    def _combine_sentences(self, sentences):
        """Combine sentences with context."""
        combined_sentences = []
        for i in range(len(sentences)):
            combined_sentence = sentences[i]
            if i > 0:
                combined_sentence = sentences[i-1] + ' ' + combined_sentence
            if i < len(sentences) - 1:
                combined_sentence += ' ' + sentences[i+1]
            combined_sentences.append(combined_sentence)
        return combined_sentences

    def create_vector_index(self, combined_sentences, api_key):
        """Create FAISS vector index from documents."""
        documents = [Document(page_content=sentence, metadata={"source": "local"}) for sentence in combined_sentences]
        embeddings = OpenAIEmbeddings(api_key=api_key)
        return FAISS.from_documents(documents, embeddings)
    

    def process_and_chunk_text(self, uploaded_files, web_url=None, section=None, api_key=None):
        """
        Process uploaded files and/or a webpage URL, assign a section tag,
        and chunk the text into meaningful segments.
        """
        documents = []
        all_embeddings = []
        
        for uploaded_file in uploaded_files:
            file_path = self.save_uploaded_file(uploaded_file)
            if file_path.endswith('.pdf'):
                text = self.process_pdf(file_path)
                tables = self.extract_tables_from_pdf(file_path)
                text += '\n\n'.join(str(table) for table in tables)
            elif file_path.endswith('.txt'):
                text = self.process_txt(file_path)
            else:
                continue  # Skip unsupported file types
            documents.append({"source": uploaded_file.name, "content": text, "section": section})
            
        if web_url:
            text = self.process_webpage(web_url)
            documents.append({"source": web_url, "content": text, "section": section})

        for document in documents:
            single_sentences_list = self._split_sentences(document["content"])
            combined_sentences = self._combine_sentences(single_sentences_list)
            
            # Assuming create_vector_index returns a FAISS object
            faiss_index = self.create_vector_index(combined_sentences, api_key=api_key)
            
            # Extract embeddings from FAISS index
            embeddings = faiss_index.embeddings
            
            all_embeddings.extend(embeddings)
            document_embedding = np.array(all_embeddings)
            
            faiss_index = FAISS.from_documents([Document(page_content=document["content"]) for document in documents], embeddings)
        
        return documents, document_embedding, faiss_index