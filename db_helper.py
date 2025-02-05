import sqlite3
import streamlit as st
from document_processor import DocumentProcessor

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
        print(f"File content: {file_content}")
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
    
    
    
def check_if_file_exists_in_section(file_name, section):
    """
    Check if the file has already been processed and exists in the database for the selected section.
    :param file_name: The name of the file to check.
    :param section: The selected section (maps to a key in SECTION_KEYWORDS).
    :return: True if the file exists in the database, False otherwise.
    """
    # Map the section to its corresponding table name using SECTION_KEYWORDS
    table_name = next((key for key, value in SECTION_KEYWORDS.items() if value == section), None)

    if not table_name:
        # If no valid table is found, return False
        return False

    # Connect to the database
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()

    # Query to check if the file already exists in the section's table
    cursor.execute(f'SELECT 1 FROM "{table_name}" WHERE file_name = ?', (file_name,))
    result = cursor.fetchone()

    # Close the connection to the database
    conn.close()

    # If a result is found, it means the file already exists, so return True
    return result is not None
