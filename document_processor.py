import pdfplumber
import requests
from bs4 import BeautifulSoup
import trafilatura
import os
import shutil

def save_uploaded_file(uploaded_file):
    if not os.path.exists('uploaded_files'):
        os.makedirs('uploaded_files')
    file_path = os.path.join('uploaded_files', uploaded_file.name)
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def process_pdf(pdf_file):
    """Extract text from a PDF file using pdfplumber, maintaining paragraph structure."""
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            paragraphs = page_text.split('\n\n')
            text += '\n\n'.join(paragraphs) + '\n\n'
    return text.strip()

def process_txt(txt_file):
    """Extract text from a TXT file."""
    with open(txt_file, 'r', encoding='utf-8') as file:
        return file.read()

def process_webpage(url):
    """Extract text content from a webpage."""
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded)
    return text

def process_documents(uploaded_files, web_url):
    """Process PDF files, TXT files, and webpages."""
    documents = []

    for uploaded_file in uploaded_files:
        file_path = save_uploaded_file(uploaded_file)
        if file_path.endswith('.pdf'):
            text = process_pdf(file_path)
        elif file_path.endswith('.txt'):
            text = process_txt(file_path)
        else:
            continue  # Skip unsupported file types
        documents.append({"source": uploaded_file.name, "content": text})

    if web_url:
        text = process_webpage(web_url)
        documents.append({"source": web_url, "content": text})

    return documents
