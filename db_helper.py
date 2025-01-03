import sqlite3
import streamlit as st
from document_processor import DocumentProcessor
from utils import create_empty_vectordb
import openai

openai.api_key = st.secrets["OPENAI"]["OPENAI_API_KEY"]

# Initialize document processor
process_document = DocumentProcessor()

# Dictionary mapping table names to section display names
SECTION_KEYWORDS = {
    "rfp_documents": "Request for Proposal (RFP) Document",
    "tor_documents": "Terms of Reference (ToR)",
    "evaluation_criteria_documents": "Technical Evaluation Criteria",
    "company_profiles_documents": "Company and Team Profiles",
    "social_standards_documents": "Environmental and Social Standards",
    "project_history_documents": "Project History and Relevant Experience",
    "additional_requirements_documents": "Additional Requirements and Compliance Documents",
}

# Initialize database
def initialize_database():
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()
    
    # Create tables for each section if they don't exist
    for table_name in SECTION_KEYWORDS.keys():
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                file_name TEXT UNIQUE,
                file_content TEXT,  -- TEXT used for extracted content (string data)
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()
    conn.close()

# Insert document metadata and content into the database
def insert_file_metadata(file_name, section, file_content):
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()
    try:
        table_name = section
        cursor.execute(f"""
            INSERT INTO {table_name} (file_name, file_content)
            VALUES (?, ?);
        """, (file_name, file_content))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"File {file_name} already exists in the database.")
    except Exception as e:
        print(f"Error inserting file metadata: {e}")
    finally:
        conn.close()

# Delete document by file name
def delete_file(file_name, section):
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()
    try:
        table_name = section
        cursor.execute(f"DELETE FROM {table_name} WHERE file_name = ?", (file_name,))
        conn.commit()
        print(f"File {file_name} deleted from {table_name}.")
    except Exception as e:
        print(f"Error deleting file: {e}")
    finally:
        conn.close()

# Retrieve all uploaded sections
def get_uploaded_sections(section_keywords):
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()
    uploaded_sections = []
    for table_name, display_name in section_keywords.items():
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        if count > 0:
            uploaded_sections.append(display_name)
    conn.close()
    return uploaded_sections

# Reload session state for processing the document content
def reload_session_state(process_document, section_keywords):
    conn = sqlite3.connect('files.db', check_same_thread=False)
    cursor = conn.cursor()

    st.session_state.section_embeddings = {}
    st.session_state.uploaded_sections = set()

    for table_name, display_name in section_keywords.items():
        try:
            # Fetch all files from the database for the section
            cursor.execute(f"SELECT file_name, file_content FROM {table_name};")
            stored_files = cursor.fetchall()

            if stored_files:
                # Process all stored files, assuming content is text here
                files_to_process = [file_content for _, file_content in stored_files]
                vectordb, documents = process_document.process_and_chunk_text(files_to_process)
                st.session_state.section_embeddings[table_name] = (vectordb, documents)
                st.session_state.uploaded_sections.add(display_name)
                print(f"Embeddings for {display_name} reloaded successfully.")
            else:
                print(f"No files uploaded for {display_name}. Initializing empty FAISS index.")
                empty_vectordb = create_empty_vectordb()
                st.session_state.section_embeddings[table_name] = (empty_vectordb, [])
        except Exception as e:
            print(f"Error reloading section {display_name}: {e}")
    conn.close()
