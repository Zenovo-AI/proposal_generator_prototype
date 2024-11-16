import os
import re
import pdfplumber
import trafilatura
import numpy as np
from utils import clean_text
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document


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

    def create_vectordb(self, combined_sentences) -> FAISS:
        """Create FAISS vector database from a list of sentences."""
        try:
            # Convert sentences into Document objects
            documents = []
            for sentence in combined_sentences:
                # Extract filename from sentence
                filename = sentence.split(":")[1].strip() if ":" in sentence else "."
                
                # Create Document object with filename in metadata
                document = Document(page_content=sentence, metadata={"source": filename})
                documents.append(document)
            
            # Initialize the embeddings model
            embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

            # Create the FAISS vector database from the documents and the embedding model
            vectordb = FAISS.from_documents(documents, embedding=embeddings_model)
            
            # Return the FAISS index, documents
            return vectordb, documents
        
        except Exception as e:
            print(f"Error creating vector database: {e}")
            return None, None
    

    def process_and_chunk_text(self, uploaded_files, web_url=None, section=None):
        """
        Process uploaded files and/or a webpage URL, assign a section tag,
        and chunk the text into meaningful segments.
        """
        combined_sentences = []
        
        # Process each uploaded file (PDF, TXT)
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
            
            # Chunk document and combine sentences
            single_sentences_list = self._split_sentences(text)
            sentence_sources = [f"File: {uploaded_file.name}"] * len(single_sentences_list)
            combined_sentences.extend([f"{source}: {sentence}" for source, sentence in zip(sentence_sources, self._combine_sentences(single_sentences_list))])
            
        # Process webpage if URL is provided
        if web_url:
            text = self.process_webpage(web_url)
            single_sentences_list = self._split_sentences(text)
            sentence_sources = [f"Website: {web_url}"] * len(single_sentences_list)
            combined_sentences.extend([f"{source}: {sentence}" for source, sentence in zip(sentence_sources, self._combine_sentences(single_sentences_list))])

        # Create a single FAISS vector database from combined sentences
        vectordb, documents = self.create_vectordb(combined_sentences)
        print(f"documents: {documents}")
        
        # Return the single FAISS vector database and embeddings
        return vectordb, documents