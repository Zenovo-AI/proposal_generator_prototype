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


def ingress_file_doc(file_name: str, file_path: str = None, web_links: list = None, section = ""):
    from app import RAGFactory
    # Get the section from session state
    section = st.session_state.current_section
    
    try:
        # Map section to table name
        table_name = next((key for key, value in SECTION_KEYWORDS.items() if value == section), None)
        if not table_name:
            return {"error": "No table mapping found for the given section."}

        # Connect to the database
        conn = sqlite3.connect("files.db", check_same_thread=False)
        cursor = conn.cursor()

        # Check if the file or web link already exists
        if file_path:
            cursor.execute(f"SELECT file_name FROM {table_name} WHERE file_name = ?", (file_name,))
            if cursor.fetchone():
                placeholder = st.sidebar.empty()
                placeholder.write(f"File '{file_name}' already exists in the '{section}' section.")
                time.sleep(5)
                placeholder.empty()
                
        elif web_links:
            for link in web_links:
                cursor.execute(f"SELECT file_name FROM {table_name} WHERE file_name = ?", (link,))
                if cursor.fetchone():
                    placeholder = st.sidebar.empty()
                    placeholder.write(f"Web link '{link}' already exists in the '{section}' section.")
                    time.sleep(5)
                    placeholder.empty()

        # Process file content
        text_content = []
        # Convert the WindowsPath object to a string
        file_path_str = str(file_path)
        if file_path_str:
            if file_path_str.endswith(".pdf"):
                text_content.append(process_document.extract_text_and_tables_from_pdf(file_path_str))
                print(type(f"Text content is of type: {text_content}"))
            elif file_path_str.endswith(".txt"):
                text_content.append(process_document.extract_txt_content(file_path_str))
            else:
                return {"error": "Unsupported file format."}

        # Process web links
        if web_links:
            for link in web_links:
                web_content = process_document.process_webpage(link)
                if web_content:
                    text_content.append(web_content)

        # Insert metadata into the database
        for content in text_content:
            insert_file_metadata(file_name or link, table_name, content)
        
        # Further processing
        results = []
        for content in text_content:
            # Create unique working directory for the file
            # working_dir = Path(f"./analysis_workspace/{section}/{file_name.split('.')[0]}")
            working_dir = Path(f"./analysis_workspace/{section}")
            working_dir.mkdir(parents=True, exist_ok=True)  # ✅ Ensure directory exists using pathlib
            rag = RAGFactory.create_rag(str(working_dir))  # Convert Path object to string if needed
            rag.insert(text_content)

            placeholder = st.empty()
            placeholder.write(f"File {file_name} has been processed and inserted successfully")
            time.sleep(5)
            placeholder.empty()

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

    finally:
        conn.close()
