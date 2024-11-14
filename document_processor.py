import pdfplumber
import trafilatura
import os

# Define keywords for document sections
SECTION_KEYWORDS = {
    "Technical Requirements": ["technical", "requirements"],
    "Project Experience": ["experience", "project"],
    "Team Profiles": ["team", "profile"],
    "Evaluation Criteria": ["evaluation", "criteria"]
}

def save_uploaded_file(uploaded_file):
    """
    Save uploaded files to the 'uploaded_files' directory.
    Returns the file path for further processing.
    """
    if not os.path.exists('uploaded_files'):
        os.makedirs('uploaded_files')
    file_path = os.path.join('uploaded_files', uploaded_file.name)
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def process_pdf(pdf_file):
    """
    Extract text from a PDF file using pdfplumber.
    Returns extracted text as a single string.
    """
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n\n".join(page.extract_text() for page in pdf.pages)
    return text.strip()

def process_txt(txt_file):
    """
    Read and return the content of a TXT file.
    """
    with open(txt_file, 'r', encoding='utf-8') as file:
        return file.read()

def process_webpage(url):
    """
    Download and extract text content from a webpage.
    Uses trafilatura for web scraping and content extraction.
    """
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded)

def process_documents(uploaded_files, web_url, section):
    """
    Process uploaded files and a webpage URL, and assign a section tag.
    Returns a list of processed documents with content and metadata.
    """
    documents = []
    for uploaded_file in uploaded_files:
        file_path = save_uploaded_file(uploaded_file)
        # Extract text based on file type
        text = process_pdf(file_path) if file_path.endswith('.pdf') else process_txt(file_path)
        documents.append({"source": uploaded_file.name, "content": text, "section": section})
    
    # If a URL is provided, process it and add to documents
    if web_url:
        text = process_webpage(web_url)
        documents.append({"source": web_url, "content": text, "section": section})
    
    return documents
