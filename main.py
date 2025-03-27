import sqlite3
import streamlit as st
import traceback
from document_processor import DocumentProcessor
from extractor import EntityRelationshipExtractor
from db_helper import insert_file_metadata, delete_file, initialize_database, reload_session_state, get_uploaded_sections
from fast_graphrag import GraphRAG
import shutil
import google.generativeai as genai
import fitz
import time
import tempfile
import gc
import openai

# Create a temporary directory
working_dir = tempfile.mkdtemp()


openai_apikey = st.secrets["OPENAI"]["OPENAI_API_KEY"]
google_apikey = st.secrets["GOOGLE"]["GOOGLE_AI_API_KEY"]

genai.configure(api_key=google_apikey)

process_document = DocumentProcessor()

# Initialize extractor and constants
extractor = EntityRelationshipExtractor(model_name="models/gemini-1.5-flash", api_key=google_apikey)
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
    if "initialized" not in st.session_state:
        st.session_state["initialized"] = True
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "section_embeddings" not in st.session_state:
        st.session_state.section_embeddings = {}

def is_supported_file_format(file_name):
    supported_formats = [".txt", ".pdf"]
    return any(file_name.endswith(ext) for ext in supported_formats)

def prepare_working_dir():
    """
    Prepare a clean temporary working directory for GraphRAG.
    """
    temp_dir = tempfile.mkdtemp()
    shutil.rmtree(temp_dir, ignore_errors=True)  # Clear any existing contents
    temp_dir = tempfile.mkdtemp()  # Recreate a fresh temporary directory
    return temp_dir

def filter_numeric_directories(working_dir):
    """
    Ensure only numeric directories are present in the working directory.
    """
    for subdir in tempfile.TemporaryDirectory()._get_next_temp_name_iterator():
        if not subdir.isdigit():
            shutil.rmtree(subdir)


def clean_working_dir(working_dir):
    """
    Ensure the working directory is clean by recreating it as an empty directory.
    """
    # Recreate the directory by removing and reinitializing it
    shutil.rmtree(working_dir, ignore_errors=True)  # Remove the directory and its contents
    tempfile.mkdtemp(dir=working_dir)  # Recreate the temporary directory

def extract_pdf_from_db(file_name, section):
    """
    Retrieve and process PDF content from the database, save it as a temporary file.
    Args:
        file_name (str): Name of the PDF file in the database.
        section (str): Section/table where the file is stored.
    Returns:
        Tuple[str, str]: Path to the saved temporary text file and its content.
    """
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT file_content FROM {section} WHERE file_name = ?", (file_name,))
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"File '{file_name}' not found in section '{section}'.")

        file_content = result[0]
        text_content = []
        with fitz.open(stream=file_content, filetype="pdf") as pdf:
            for page in pdf:
                text_content.append(page.get_text())

        # Save extracted text to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", prefix=file_name, mode="w", encoding="utf-8")
        file_content_str = "\n".join(text_content)
        temp_file.write(file_content_str)
        temp_file.close()

        return temp_file.name, file_content_str  # Return the file path and content
    except Exception as e:
        st.error(f"Error extracting PDF content: {e}")
        raise
    finally:
        conn.close()
        
def safe_api_call(call_func, retries=5, delay=1):
    """
    Wrapper to safely execute API calls with retries and exponential backoff.
    """
    for attempt in range(retries):
        try:
            response = call_func()
            if response.status_code == 200:
                return response
            else:
                st.warning(f"API returned status {response.status_code}, retrying...")
        except Exception as e:
            st.error(f"API call failed: {e}")
        time.sleep(delay * (2 ** attempt))
    raise RuntimeError("Exceeded maximum retries for API call.")
        

@st.cache_resource(ttl=3600)
def initialize_rag(working_dir):
    return GraphRAG(
        working_dir=working_dir,
        domain="Analyze the content to extract key entities, their relationships, and relevant insights."
    )

def process_all_files_in_section(section):
    """
    Process all files in the given section by extracting text, creating embeddings,
    and inserting the content into GraphRAG for entity extraction and auto-query generation.
    """

    openai.api_key = st.secrets["OPENAI"]["OPENAI_API_KEY"]
    
    try:
        conn = sqlite3.connect("files.db", check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(f"SELECT file_name, file_content FROM {section}")
        files = cursor.fetchall()

        if not files:
            st.warning(f"No files found in section '{section}'.")
            return

        # Use a temporary directory for GraphRAG
        with tempfile.TemporaryDirectory() as working_dir:
            grag = None
            for file_name, file_content in files:
                try:
                    # Extract text content
                    text_file_path, text_content = extract_pdf_from_db(file_name, section)
                    if not text_content:
                        st.warning(f"Unable to extract content from file: {file_name}. Skipping.")
                        continue

                    # Process document
                    vectordb, documents = process_document.process_and_extract(text_content)

                    # Store embeddings in session state
                    section_embeddings = st.session_state.get("section_embeddings", {})
                    section_embeddings[section] = (vectordb, documents)
                    st.session_state["section_embeddings"] = section_embeddings

                    if grag is None:
                        extraction_result = extractor.extract_entities_and_relationships(text_content)
                        entities = [
                            entity if isinstance(entity, str) else entity.get("name", "unknown")
                            for entity in (
                                extraction_result.get("people", []) +
                                extraction_result.get("places", []) +
                                extraction_result.get("things", [])
                            )
                        ]
                        example_queries = extractor.generate_example_queries(text_content)

                        # Initialize GraphRAG with valid working directory
                        grag = GraphRAG(
                            working_dir=working_dir,
                            domain="Analyze the content to extract key entities, their relationships, and relevant insights.",
                            example_queries="\n".join(example_queries),
                            entity_types=entities,
                        )

                    # Insert into GraphRAG
                    with open(text_file_path, "r", encoding="utf-8") as temp_file:
                        grag.insert(temp_file.read())

                    st.success(f"Processed and inserted file '{file_name}' successfully.")
                    
                    # Clear memory after each file
                    grag = None
                    gc.collect()

                except Exception as e:
                    st.error(f"Error processing file '{file_name}': {e}")
                    traceback.print_exc()

            # Reset and clear resources after processing
            grag = None  # Reset GraphRAG
            gc.collect()  # Run garbage collection
            shutil.rmtree(working_dir, ignore_errors=True)

    except Exception as e:
        st.error(f"Error processing files in section '{section}': {e}")
    finally:
        conn.close()



 
def main():
    initialize_session_state()
    st.title("Proposal and Chatbot System")

    # Sidebar for section selection and file upload
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
                        placeholder = st.empty()
                        placeholder.success(f"File '{file.name}' uploaded successfully!")
                        time.sleep(5)
                        placeholder.empty()

            except Exception as e:
                st.error(f"Error processing files: {e}")
                traceback.print_exc()
            finally:
                conn.close()

    # Chatbot interface
    st.header("Chat with the Bot")
    user_input = st.text_input("Ask your question:")

    if st.button("Send"):
        with st.spinner("Processing all files in the selected section..."):
            try:
                process_all_files_in_section(table_name)
            except Exception as e:
                st.error(f"Error processing files for section '{section}': {e}")
                traceback.print_exc()

        if table_name in st.session_state.get("grag_instances", {}):
            grag = st.session_state["grag_instances"][table_name]
            if user_input.strip():
                try:
                    response = st.session_state.grag.query(user_input)
                    st.session_state.chat_history.append(("You", user_input))
                    st.session_state.chat_history.append(("Bot", response))
                except Exception as e:
                    st.error(f"Error during chatbot interaction: {e}")
            else:
                st.info("Please enter a question to interact with the bot.")
        else:
            st.error("No GraphRAG instance found for this section. Please process files first.")

    # Display chat history
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
