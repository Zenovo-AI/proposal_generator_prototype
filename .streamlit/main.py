import sqlite3
import streamlit as st
import traceback
from chat_bot import ChatBot
from db_helper import insert_file_metadata, delete_file, initialize_database, reload_session_state, get_uploaded_sections
from document_processor import DocumentProcessor
from rag_pipeline import RAGPipeline
import numpy as np
import time
import faiss

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


def initialize_session_state():
    if 'initialized' not in st.session_state:
        initialize_database()
        reload_session_state(process_document, SECTION_KEYWORDS)
        st.session_state['initialized'] = True

    if "chat_bot" not in st.session_state:
        st.session_state.chat_bot = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "section_embeddings" not in st.session_state:
        st.session_state.section_embeddings = {}


def is_supported_file_format(file_name):
    supported_formats = ['.txt', '.pdf', '.docx', '.csv']  # Extend with your supported formats
    return any(file_name.endswith(ext) for ext in supported_formats)

def extract_pdf_from_db(file_name, section):
    """
    Retrieve and process PDF content (text and tables) from the database.
    Args:
        file_name (str): Name of the PDF file in the database.
        section (str): Section/table where the file is stored.
    Returns:
        List[str]: List of extracted pages and tables from the PDF.
    """
    import sqlite3
    import pdfplumber
    from io import BytesIO

    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT file_content FROM {section} WHERE file_name = ?", (file_name,))
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"File '{file_name}' not found in section '{section}'.")

        file_content = result[0]
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            content_list = []

            for page in pdf.pages:
                # Extract page text
                page_text = page.extract_text()
                if page_text:
                    content_list.append(page_text.strip())

                # Extract tables as strings
                tables = page.extract_tables()
                for table in tables:
                    if table:  # Ensure the table is not None
                        table_str = "\n".join(
                            ["\t".join(cell if cell is not None else "" for cell in row) for row in table if row]
                        )
                        content_list.append(table_str)

            return content_list

    except Exception as e:
        print(f"Error extracting PDF content: {e}")
        return []
    finally:
        conn.close()




def process_all_files_in_section(section):
    """
    Process all files in the given section by extracting text and creating embeddings.
    Args:
        section (str): The section (table name) to process files from.
    """
    # Initialize database connection
    conn = sqlite3.connect("files.db", check_same_thread=False)
    cursor = conn.cursor()

    try:
        # Fetch all files from the section
        cursor.execute(f"SELECT file_name, file_content FROM {section}")
        files = cursor.fetchall()

        if not files:
            st.warning(f"No files found in section '{SECTION_KEYWORDS.get(section, section)}'.")
            return

        # Process each file
        for file_name, file_content in files:
            # Extract text content from the file
            text_content = extract_pdf_from_db(file_name, section)
            if not text_content:
                st.warning(f"Unable to extract content from file: {file_name}. Skipping.")
                continue

            try:
                # Process and chunk the text content
                vectordb, documents = process_document.process_and_chunk_text(text_content)

                # Create and normalize embeddings
                embeddings = np.array([vectordb.index.reconstruct(i) for i in range(vectordb.index.ntotal)])
                faiss.normalize_L2(embeddings)

                # Update session state with embeddings
                if section not in st.session_state.get("section_embeddings", {}):
                    st.session_state.section_embeddings = {}
                    st.session_state.section_embeddings[section] = (vectordb, documents)
                else:
                    existing_vectordb, existing_docs = st.session_state.section_embeddings[section]

                    if existing_vectordb is not None:
                        existing_vectordb.merge_from(vectordb)
                        st.session_state.section_embeddings[section] = (
                            existing_vectordb,
                            existing_docs + documents,
                        )
                    else:
                        placeholder = st.empty()
                        placeholder.warning(f"Existing vector database for section '{section}' is invalid. Overwriting with new data.")
                        st.session_state.section_embeddings[section] = (vectordb, documents)
                        time.sleep(5)
                        placeholder.empty()

            except Exception as e:
                st.error(f"Error processing embeddings for file {file_name}: {e}")
                traceback.print_exc()

        # Notify user of successful embedding processing
        placeholder = st.empty()
        placeholder.success(f"Embeddings for all files in section '{SECTION_KEYWORDS.get(section, section)}' have been processed.")
        time.sleep(5)
        placeholder.empty()

    except Exception as e:
        st.error(f"Error processing files in section '{SECTION_KEYWORDS.get(section, section)}': {e}")
        traceback.print_exc()

    finally:
        # Close the database connection
        conn.close()


def main():
    initialize_session_state()
    st.title("Proposal and Chatbot System")

    sections = list(SECTION_KEYWORDS.values())
    uploaded_sections = get_uploaded_sections(SECTION_KEYWORDS)
    default_section = uploaded_sections[0] if uploaded_sections else sections[0]

    section = st.sidebar.selectbox("Select a document section:", options=sections, index=sections.index(default_section))
    table_name = next((key for key, value in SECTION_KEYWORDS.items() if value == section), None)

    if not table_name:
        st.error("No table mapping found for section")
        return

    uploaded_files = st.sidebar.file_uploader(f"Upload files to the '{section}' section", type=["pdf", "txt"], accept_multiple_files=True)

    if uploaded_files:
        with st.spinner("Processing and uploading files..."):
            try:
                for file in uploaded_files:
                    conn = sqlite3.connect("files.db", check_same_thread=False)
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT file_name FROM {table_name} WHERE file_name = ?", (file.name,))
                    existing_file = cursor.fetchone()

                    if existing_file:
                        st.sidebar.info(f"File '{file.name}' already exists in the '{section}' section.")
                    else:
                        file_content = file.read()
                        insert_file_metadata(file.name, table_name, file_content)
                        st.success(f"File '{file.name}' uploaded successfully!")
            except Exception as e:
                st.error(f"Error processing files: {e}")
                traceback.print_exc()

    st.header("Chat with the Bot")
    user_input = st.text_input("Ask your question:")

    if st.button("Send"):
        with st.spinner("Processing all files in the selected section..."):
            try:
                process_all_files_in_section(table_name)
            except Exception as e:
                st.error(f"Error processing files for section '{section}': {e}")
                traceback.print_exc()

        if table_name in st.session_state.section_embeddings:
            vectordb, documents = st.session_state.section_embeddings[table_name]
            st.session_state.chat_bot = ChatBot(RAGPipeline(vectordb, documents))

        if user_input.strip() and st.session_state.chat_bot:
            try:
                response = st.session_state.chat_bot.get_response(user_input)
                st.session_state.chat_history.append(("You", user_input))
                st.session_state.chat_history.append(("Bot", response))
            except Exception as e:
                st.error(f"Error during chatbot interaction: {e}")
        else:
            st.info("Upload or process files for this section to enable chatting.")

    if st.session_state.chat_history:
        st.write("### Chat History")
        for role, message in st.session_state.chat_history[-10:]:
            st.write(f"**{role}:** {message}")

    st.sidebar.write("### Uploaded Files")
    try:
        conn = sqlite3.connect("files.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(f"SELECT file_name FROM {table_name};")
        uploaded_files_list = [file[0] for file in cursor.fetchall()]

        if uploaded_files_list:
            for file_name in uploaded_files_list:
                delete_key = f"delete_{table_name}_{file_name}"
                col1, col2 = st.sidebar.columns([3, 1])
                with col1:
                    st.sidebar.write(file_name)
                with col2:
                    if st.sidebar.button("Delete", key=delete_key):
                        try:
                            delete_file(file_name, table_name)
                            st.sidebar.success(f"File '{file_name}' deleted successfully!")
                        except Exception as e:
                            st.error(f"Failed to delete file '{file_name}': {e}")
        else:
            st.sidebar.info("No files uploaded for this section.")
    except Exception as e:
        st.sidebar.error(f"Failed to retrieve files: {e}")
        
    # Track uploaded sections
    # --- Sidebar: Breadcrumb Display ---
    if "uploaded_sections" not in st.session_state:
        st.session_state.uploaded_sections = set()

    if uploaded_files:
        st.session_state.uploaded_sections.add(section)

    if st.session_state.uploaded_sections:
        breadcrumb_text = " > ".join(sorted(st.session_state.uploaded_sections))
        st.sidebar.info(f"📂 Sections with uploads: {breadcrumb_text}")

if __name__ == "__main__":
    main()
