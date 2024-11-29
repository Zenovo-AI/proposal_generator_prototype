import sqlite3
import streamlit as st
from document_processor import DocumentProcessor
from rag_pipeline import RAGPipeline
from chat_bot import ChatBot
from db_helper import insert_file_metadata, delete_file, initialize_database
import traceback

# Initialize document processor
process_document = DocumentProcessor()

SECTION_KEYWORDS = {
    "Request for Proposal (RFP) Document": "rfp_documents",
    "Terms of Reference (ToR)": "tor_documents",
    "Technical Evaluation Criteria": "evaluation_criteria_documents",
    "Company and Team Profiles": "company_profiles_documents",
    "Environmental and Social Standards": "social_standards_documents",
    "Project History and Relevant Experience": "project_history_documents",
    "Additional Requirements and Compliance Documents": "additional_requirements_documents",
}

def main():
    # Initialize session state variables if not already initialized
    if "chat_bot" not in st.session_state:
        st.session_state.chat_bot = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "section_embeddings" not in st.session_state:
        st.session_state.section_embeddings = {}
    if "uploaded_sections" not in st.session_state:
        st.session_state.uploaded_sections = set()

    # Initialize the database tables
    initialize_database()

    st.title("Proposal and Chatbot System")

    # Initialize database connection
    conn = sqlite3.connect("files.db", check_same_thread=False)
    cursor = conn.cursor()

    # Sidebar: Section Selection
    section = st.sidebar.selectbox(
        "Select a document section:",
        options=list(SECTION_KEYWORDS.keys()),
    )
    table_name = SECTION_KEYWORDS[section]

    # Sidebar: File Uploader
    uploaded_files = st.sidebar.file_uploader(
        f"Upload files to the '{section}' section",
        type=["pdf", "txt"],
        accept_multiple_files=True,
    )
    web_url = st.sidebar.text_input("Enter URL of policy webpage")

    # Handle File Upload
    if uploaded_files or web_url:
        with st.spinner("Processing and uploading files..."):
            try:
                for file in uploaded_files:
                    # Check if the file already exists in the database
                    cursor.execute(f"SELECT file_name FROM {table_name} WHERE file_name = ?", (file.name,))
                    existing_file = cursor.fetchone()

                    if existing_file:
                        st.sidebar.error(f"File '{file.name}' already exists in the '{section}' section.")
                    else:
                        # Insert file metadata into the database
                        insert_file_metadata(file.name, section)

                        # Process and store embeddings for uploaded files
                        vectordb, documents = process_document.process_and_chunk_text([file], web_url, section)
                        st.session_state.section_embeddings[section] = (vectordb, documents)
                        st.success(f"File '{file.name}' uploaded and processed successfully!")

                # Track uploaded sections
                st.session_state.uploaded_sections.add(section)

            except Exception as e:
                st.error(f"Error processing files: {e}")
                traceback.print_exc()

    # Breadcrumb display
    if st.session_state.uploaded_sections:
        breadcrumb_text = " > ".join(sorted(st.session_state.uploaded_sections))
        st.sidebar.info(f"📂 Sections with uploads: {breadcrumb_text}")

    # Handle Files from Database
    if section not in st.session_state.section_embeddings:
        try:
            cursor.execute(f"SELECT file_name FROM {table_name};")
            stored_files = [file[0] for file in cursor.fetchall()]

            if stored_files:
                # Process files from the database and update embeddings
                with st.spinner("Loading files from the database..."):
                    vectordb, documents = process_document.process_and_chunk_text(stored_files, web_url=None, section=section)
                    st.session_state.section_embeddings[section] = (vectordb, documents)
                    st.success("Files from the database processed successfully!")
            else:
                st.info("No files found in the database for this section.")

        except Exception as e:
            st.error(f"Error loading files from the database: {e}")
            traceback.print_exc()

    # Chatbot Functionality
    try:
        if section in st.session_state.section_embeddings:
            st.header("Chat with the Bot")
            vectordb, documents = st.session_state.section_embeddings[section]

            # Initialize chatbot if not already done
            if not st.session_state.chat_bot:
                st.session_state.chat_bot = ChatBot(RAGPipeline(vectordb, documents))

            # Get user input and respond
            user_input = st.text_input("Ask your question:")
            if st.button("Send"):
                if user_input.strip():
                    try:
                        response = st.session_state.chat_bot.get_response(user_input)
                        st.session_state.chat_history.append(("You", user_input))
                        st.session_state.chat_history.append(("Bot", response))
                        st.write("### Chat History")
                        for role, message in st.session_state.chat_history[-10:]:
                            st.write(f"**{role}:** {message}")
                    except Exception as e:
                        st.error(f"Error during chatbot interaction: {e}")
        else:
            st.info("Upload or process files for this section to enable chatting.")

    except Exception as e:
        st.error(f"Failed to set up chatbot: {e}")

    # Display Uploaded Files and Delete Option
    st.sidebar.write("### Uploaded Files")
    try:
        cursor.execute(f"SELECT file_name FROM {table_name};")
        uploaded_files_list = [file[0] for file in cursor.fetchall()]

        if uploaded_files_list:
            for file_name in uploaded_files_list:
                delete_key = f"delete_{section}_{file_name}"
                col1, col2 = st.sidebar.columns([3, 1])
                with col1:
                    st.sidebar.write(file_name)
                with col2:
                    if st.sidebar.button("Delete", key=delete_key):
                        try:
                            delete_file(file_name, section)
                            st.sidebar.success(f"File '{file_name}' deleted successfully!")
                        except Exception as e:
                            st.error(f"Failed to delete file '{file_name}': {e}")
        else:
            st.sidebar.info("No files uploaded for this section.")
    except Exception as e:
        st.sidebar.error(f"Failed to retrieve files: {e}")

if __name__ == "__main__":
    main()
