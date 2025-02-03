import json
import logging
from pathlib import Path
import sqlite3
import time
import numpy as np
import streamlit as st
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed, gpt_4o_complete
from lightrag.utils import EmbeddingFunc
from constant import SECTION_KEYWORDS, select_section
from db_helper import delete_file, get_uploaded_sections, initialize_database
from inference import process_files_and_links


def initialize_session_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "initialized" not in st.session_state:
        initialize_database()
        st.session_state.initialized = True


# Helper Function to Clean and Parse JSON
def clean_and_parse_json(raw_json):
    try:
        fixed_json = raw_json.replace("{{", "{").replace("}}", "}")
        return json.loads(fixed_json)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}. Raw data: {raw_json}")
        return None


def embedding_func(texts: list[str]) -> np.ndarray:
    embeddings = openai_embed(
        texts,
        model="text-embedding-3-large",
        api_key=st.secrets["OPENAI_API_KEY"],
        base_url=None
    )
    if embeddings is None:
        logging.error("Received empty embeddings from API.")
        return np.array([])
    return embeddings


class RAGFactory:
    _shared_embedding = EmbeddingFunc(
        embedding_dim=3072,
        max_token_size=8192,
        func=embedding_func
    )

    @classmethod
    def create_rag(cls, working_dir: str) -> LightRAG:
        """Create a LightRAG instance with shared configuration, upload to GCS if specified"""
        # if gcs_path:
         # Use the GCS path as the working directory

        return LightRAG(
            working_dir=working_dir,
            llm_model_func=gpt_4o_complete,
            embedding_func=cls._shared_embedding
        )


def main():
    st.title("Proposal and Chatbot System")
    st.write("Upload a document and ask questions based on structured knowledge retrieval.")

    initialize_session_state()
    

    # Select section and table name
    section, table_name = select_section()
    if not table_name:
        st.error("Please select a valid section to proceed.")

    # File uploader widget
    files = st.sidebar.file_uploader("Upload documents", accept_multiple_files=True, type=["pdf", "txt"])
    for file in files:
        file_name = file.name
        st.session_state["file_name"] = file_name

    # Optional input for web links
    web_links = st.sidebar.text_area("Enter web links (one per line)", key="web_links")
    
    # Check if files are already processed
    if "files_processed" not in st.session_state:
        st.session_state["files_processed"] = False

    # Ensure query input always appears
    search_mode = st.sidebar.selectbox("Select retrieval mode", ["local", "global", "hybrid", "mix"], key="mode_selection")
    query = st.text_input("Ask a question about the document:")

    # Process files and links only if they are present and not processed yet
    if (files or web_links) and not st.session_state.get("files_processed", False):
        placeholder = st.empty()
        placeholder.write("🔄 Processing files and links...")
        time.sleep(5)
        placeholder.empty()
        process_files_and_links(files, web_links, section)
        st.session_state["files_processed"] = True
        placeholder.write("✅ Files and links processed!")
        time.sleep(5)
        placeholder.empty()
        
        
    if st.sidebar.button("Reset Processing"):
        st.session_state["files_processed"] = False

    # Handle the query generation only if files are processed and a query is entered
    if query and st.button("Generate Answer") and st.session_state["files_processed"]:
        with st.spinner("Generating answer..."):
            try:
                working_dir = Path(f"./analysis_workspace/{section}/{file_name.split('.')[0]}")
                working_dir.mkdir(parents=True, exist_ok=True)
                rag = RAGFactory.create_rag(str(working_dir))  # Ensure WORKING_DIR is properly set
                response = rag.query(query, param=QueryParam(mode=search_mode))
                st.session_state.chat_history.append(("You", query))
                st.session_state.chat_history.append(("Bot", response))
            except Exception as e:
                st.error(f"Error retrieving response: {e}")

        # Display chat history
        if st.session_state.chat_history:
            st.write("### Chat History")
            for role, message in st.session_state.chat_history[-10:]:
                st.write(f"**{role}:** {message}")

    # Sidebar: Display uploaded files
    st.sidebar.write("### Uploaded Files")
    try:
        conn = sqlite3.connect("files.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(f'SELECT file_name FROM "{table_name}";')
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

    # Sidebar: Breadcrumb Display
    uploaded_sections = get_uploaded_sections(SECTION_KEYWORDS)
    if "uploaded_sections" not in st.session_state:
        st.session_state.uploaded_sections = set()

    if files:
        st.session_state.uploaded_sections.add(section)

    if st.session_state.uploaded_sections:
        breadcrumb_text = " > ".join(sorted(st.session_state.uploaded_sections))
        st.sidebar.info(f"📂 Sections with uploads: {breadcrumb_text}")

            
if __name__ == "__main__":
    main()