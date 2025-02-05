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
from db_helper import check_if_file_exists_in_section, delete_file, get_uploaded_sections, initialize_database
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
        return LightRAG(
            working_dir=working_dir,
            addon_params={
                "insert_batch_size": 10  # Process 10 documents per batch
            },
            llm_model_func=gpt_4o_complete,
            embedding_func=cls._shared_embedding
        )


def main():
    st.title("Proposal and Chatbot System")
    st.write("Upload a document and ask questions based on structured knowledge retrieval.")

    initialize_session_state()

    # List of sections
    sections = list(SECTION_KEYWORDS.values())

    # Ensure session state has a default section
    if "current_section" not in st.session_state:
        st.session_state.current_section = sections[0]

    # Create selectbox outside the function
    selected_section = st.sidebar.selectbox(
        "Select a document section:", 
        options=sections, 
        key="main_nav", 
        index=sections.index(st.session_state.current_section)
    )

    # Store the selected section in session state
    st.session_state.current_section = selected_section

    # Get the section name and table name
    section, table_name = select_section(selected_section)

    # File uploader widget
    files = st.sidebar.file_uploader("Upload documents", accept_multiple_files=True, type=["pdf", "txt"])

    # Store uploaded file name in session state
    for file in files:
        file_name = file.name
        st.session_state["file_name"] = file_name

    # Optional input for web links
    web_links = st.sidebar.text_area("Enter web links (one per line)", key="web_links")

    # Ensure files_processed is in session state
    if "files_processed" not in st.session_state:
        st.session_state["files_processed"] = False

    # Ensure query input always appears
    search_mode = st.sidebar.selectbox("Select retrieval mode", ["local", "global", "hybrid", "mix"], key="mode_selection")
    query = st.text_input("Ask a question about the document:", key="query_input")

    # Process files and links if they are present and not processed yet
    if (files or web_links) and not st.session_state["files_processed"]:
        for file in files:
            file_name = file.name
            
            # Check if the file already exists in the database for the selected section
            if check_if_file_exists_in_section(file_name, section):
                st.warning(f"The file {file_name} has already been processed in the '{section}' section.")
            else:
                st.session_state["file_name"] = file_name
                placeholder = st.empty()
                placeholder.write("🔄 Processing files and links...")
                time.sleep(5)  # Simulate file processing time
                placeholder.empty()
                process_files_and_links(files, web_links, section)  
                st.session_state["files_processed"] = True
                placeholder.write("✅ Files and links processed!")
                time.sleep(5)  
                placeholder.empty()

    # Reset processing state
    if st.sidebar.button("Reset Processing", key="reset"):
        st.session_state["files_processed"] = False

    # Handle the query generation only if files are processed and a query is entered
    if query and st.button("Generate Answer", key="answer"):
        with st.spinner("Generating answer..."):
            try:
                # working_dir = Path(f"./analysis_workspace/{section}/{file_name.split('.')[0]}")
                working_dir = Path(f"./analysis_workspace/{section}")
                working_dir.mkdir(parents=True, exist_ok=True)
                rag = RAGFactory.create_rag(str(working_dir))  
                response = rag.query(query, QueryParam(mode=search_mode))
                st.session_state.chat_history.append(("You", query))
                st.session_state.chat_history.append(("Bot", response))
            except Exception as e:
                st.error(f"Error retrieving response: {e}")

        # Display chat history
        for role, message in st.session_state.chat_history:
            with st.chat_message("user" if role == "You" else "assistant"):
                st.write(message)

        # JavaScript to scroll to bottom
        st.markdown(
            """
            <script>
            window.onload = function() {
                const chatBox = document.querySelector('div.stChatMessage');
                if (chatBox) {
                    chatBox.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }
            };
            </script>
            """,
            unsafe_allow_html=True
        )

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