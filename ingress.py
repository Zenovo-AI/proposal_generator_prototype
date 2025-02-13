import sqlite3
import time
import traceback
import streamlit as st
from constant import SECTION_KEYWORDS, select_section
import traceback
from pathlib import Path
from db_helper import insert_file_metadata
from document_processor import DocumentProcessor

process_document = DocumentProcessor()


def ingress_file_doc(file_name: str, file_path: str = None, web_links: list = None, section=""):
    from app import RAGFactory
    import traceback
    
    # Get the section from session state
    section = st.session_state.get("current_section", section)  # Use session state or fallback to provided section

    try:
        # Map section to table name
        table_name = next((key for key, value in SECTION_KEYWORDS.items() if value == section), None)
        if not table_name:
            return {"error": "No table mapping found for the given section."}

        # Connect to the database
        conn = sqlite3.connect("files.db", check_same_thread=False)
        cursor = conn.cursor()

        # Check if file already exists in the database
        if file_path:
            cursor.execute(f"SELECT file_name FROM {table_name} WHERE file_name = ?", (file_name,))
            if cursor.fetchone():
                placeholder=st.empty()
                placeholder.sidebar.warning(f"File '{file_name}' already exists in the '{section}' section.")
                time.sleep(5)
                placeholder.empty()

        # Check if web links already exist in the database
        if web_links:
            for link in web_links:
                cursor.execute(f"SELECT file_name FROM {table_name} WHERE file_name = ?", (link,))
                if cursor.fetchone():
                    placeholder=st.empty()
                    placeholder.sidebar.warning(f"Web link '{link}' already exists in the '{section}' section.")
                    time.sleep(5)
                    placeholder.empty()

        # Initialize text content list
        text_content = []

        # Process file content if file_path is provided
        if file_path:
            file_path_str = str(file_path)  # Convert Path object to string
            if file_path_str.endswith(".pdf"):
                extracted_text = process_document.extract_text_and_tables_from_pdf(file_path_str)
                if extracted_text:
                    text_content.append(extracted_text)
            elif file_path_str.endswith(".txt"):
                text_content.append(process_document.extract_txt_content(file_path_str))
            else:
                return {"error": "Unsupported file format."}

        # Process web links if provided
        if web_links:
            for link in web_links:
                web_content = process_document.process_webpage(link)
                if web_content:
                    text_content.append(web_content)

        # Ensure there is content to process
        if not text_content:
            return {"error": "No valid content extracted from file or web links."}

        # Insert metadata into the database
        for content in text_content:
            insert_file_metadata(file_name, table_name, content)

        # Create unique working directory for the file
        working_dir = Path("./analysis_workspace")
        working_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

        # Process data using RAGFactory
        rag = RAGFactory.create_rag(str(working_dir))
        rag.insert(text_content)

        # Show success message
       st.success(f"File '{file_name}' processed and inserted successfully!")
        return {"success": True}

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

    finally:
        conn.close()


